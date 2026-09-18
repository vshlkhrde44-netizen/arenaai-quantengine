"""
Antigravity QuantEngine - Position & Portfolio Accounting Engine
Implements deterministic position accounting, mark-to-market valuations,
realized & unrealized P&L, and portfolio-level risk utilization.
NO FAKE ACCOUNT BALANCES (P0-04, Section 7): Returns UNKNOWN / UNAVAILABLE when unpopulated.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.domain.models import (
    PositionRecord, PositionSide, OrderSide, FillRecord
)
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("portfolio.engine")


class PortfolioSummary(BaseModel):
    account_state: str = "UNKNOWN" # "CONFIGURED" or "UNKNOWN"
    total_equity: Optional[float] = None
    available_balance: Optional[float] = None
    locked_balance: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_exposure: float = 0.0
    margin_utilization_pct: Optional[float] = None
    risk_utilization_pct: Optional[float] = None
    active_positions_count: int = 0
    open_orders_count: int = 0
    daily_pnl: float = 0.0
    status_message: str = "ACCOUNT DATA UNAVAILABLE"
    is_paper_only: bool = True
    live_trading_disabled: bool = True


class PortfolioEngine:
    """Deterministic position and portfolio state accountant."""

    def __init__(self):
        pass

    def apply_fill(self, fill: FillRecord) -> PositionRecord:
        """
        Update position and balance deterministically following a verified fill.
        Handles: open, increase, reduce, reverse, fully close.
        """
        db = get_db()
        rows = db.execute_query("SELECT * FROM paper_positions WHERE symbol = ?", (fill.symbol,))
        
        pos_qty = 0.0
        pos_entry = 0.0
        pos_side = PositionSide.FLAT
        realized_pnl = 0.0
        cum_fees = 0.0

        if rows:
            r = rows[0]
            pos_qty = float(r["quantity"])
            pos_entry = float(r["average_entry_price"])
            pos_side = PositionSide(r["side"])
            realized_pnl = float(r["realized_pnl"])
            cum_fees = float(r["cumulative_fees"])

        cum_fees += fill.fee
        fill_qty = fill.quantity
        fill_price = fill.price
        fill_is_buy = (fill.side == OrderSide.BUY)

        # Signed quantity convention: positive for Long, negative for Short
        current_signed_qty = pos_qty if pos_side == PositionSide.LONG else (-pos_qty if pos_side == PositionSide.SHORT else 0.0)
        fill_signed_qty = fill_qty if fill_is_buy else -fill_qty
        new_signed_qty = current_signed_qty + fill_signed_qty

        # Case 1: Was FLAT, now OPENING
        if pos_side == PositionSide.FLAT:
            pos_side = PositionSide.LONG if fill_is_buy else PositionSide.SHORT
            pos_qty = fill_qty
            pos_entry = fill_price

        # Case 2: Adding to same side (INCREASING)
        elif (current_signed_qty > 0 and fill_signed_qty > 0) or (current_signed_qty < 0 and fill_signed_qty < 0):
            total_notional = (pos_qty * pos_entry) + (fill_qty * fill_price)
            pos_qty += fill_qty
            pos_entry = total_notional / pos_qty

        # Case 3: Reducing or Reversing
        else:
            closing_qty = min(abs(current_signed_qty), fill_qty)
            if pos_side == PositionSide.LONG:
                trade_pnl = (fill_price - pos_entry) * closing_qty
            else:
                trade_pnl = (pos_entry - fill_price) * closing_qty

            realized_pnl += trade_pnl

            if abs(new_signed_qty) < 1e-8:
                pos_side = PositionSide.FLAT
                pos_qty = 0.0
                pos_entry = 0.0
            elif (current_signed_qty > 0 and new_signed_qty > 0) or (current_signed_qty < 0 and new_signed_qty < 0):
                pos_qty = abs(new_signed_qty)
            else:
                pos_side = PositionSide.SHORT if new_signed_qty < 0 else PositionSide.LONG
                pos_qty = abs(new_signed_qty)
                pos_entry = fill_price

        # Update database position
        sql = """
            INSERT INTO paper_positions (
                symbol, venue, side, quantity, average_entry_price,
                current_market_price, unrealized_pnl, realized_pnl,
                cumulative_fees, last_updated
            ) VALUES (?, 'coinbase', ?, ?, ?, ?, 0.0, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET
                side = excluded.side,
                quantity = excluded.quantity,
                average_entry_price = excluded.average_entry_price,
                realized_pnl = excluded.realized_pnl,
                cumulative_fees = excluded.cumulative_fees,
                last_updated = CURRENT_TIMESTAMP
        """
        db.execute_non_query(
            sql,
            (fill.symbol, pos_side.value, pos_qty, pos_entry, fill_price, realized_pnl, cum_fees)
        )

        # Update USD balance if row exists
        cash_delta = (-fill_qty * fill_price - fill.fee) if fill_is_buy else (fill_qty * fill_price - fill.fee)
        bal_exists = db.execute_query("SELECT COUNT(*) as cnt FROM paper_balances WHERE asset = 'USD'")[0]["cnt"] > 0
        if bal_exists:
            db.execute_non_query(
                "UPDATE paper_balances SET total = total + ?, available = available + ? WHERE asset = 'USD'",
                (cash_delta, cash_delta)
            )

        logger.info(
            f"Updated position {fill.symbol}: {pos_side.value} {pos_qty:.4f} @ {pos_entry:.2f} | "
            f"Realized PnL: ${realized_pnl:,.2f}"
        )

        return PositionRecord(
            symbol=fill.symbol,
            venue="coinbase",
            side=pos_side,
            quantity=pos_qty,
            average_entry_price=pos_entry,
            current_market_price=fill_price,
            unrealized_pnl=0.0,
            realized_pnl=realized_pnl,
            cumulative_fees=cum_fees,
            last_updated=datetime.now(timezone.utc)
        )

    def mark_to_market(self, symbol: str, current_price: float) -> Optional[PositionRecord]:
        """Recalculate unrealized P&L using live market price."""
        db = get_db()
        rows = db.execute_query("SELECT * FROM paper_positions WHERE symbol = ?", (symbol,))
        if not rows:
            return None

        r = rows[0]
        qty = float(r["quantity"])
        entry = float(r["average_entry_price"])
        side = PositionSide(r["side"])

        unrealized = 0.0
        if side == PositionSide.LONG and qty > 0:
            unrealized = (current_price - entry) * qty
        elif side == PositionSide.SHORT and qty > 0:
            unrealized = (entry - current_price) * qty

        db.execute_non_query(
            "UPDATE paper_positions SET current_market_price = ?, unrealized_pnl = ? WHERE symbol = ?",
            (current_price, unrealized, symbol)
        )

        return PositionRecord(
            symbol=symbol,
            venue=r["venue"],
            side=side,
            quantity=qty,
            average_entry_price=entry,
            current_market_price=current_price,
            unrealized_pnl=round(unrealized, 2),
            realized_pnl=float(r["realized_pnl"]),
            cumulative_fees=float(r["cumulative_fees"]),
            last_updated=datetime.now(timezone.utc)
        )

    def get_portfolio_summary(self) -> PortfolioSummary:
        """
        Compute aggregate portfolio accounting metrics.
        CRITICAL (P0-04, Section 7): If balances have not been retrieved or configured,
        returns account_state='UNKNOWN' and status_message='ACCOUNT DATA UNAVAILABLE'.
        """
        db = get_db()
        bal_rows = db.execute_query("SELECT * FROM paper_balances WHERE asset = 'USD'")
        pos_rows = db.execute_query("SELECT * FROM paper_positions WHERE quantity > 0")
        
        unrealized = round(sum(float(p["unrealized_pnl"]) for p in pos_rows), 2)
        realized = round(sum(float(p["realized_pnl"]) for p in pos_rows), 2)
        exposure = round(sum(float(p["quantity"]) * float(p["current_market_price"]) for p in pos_rows), 2)

        orders_count = db.execute_query(
            "SELECT COUNT(*) as cnt FROM paper_orders WHERE status IN ('ACKNOWLEDGED', 'PARTIALLY_FILLED', 'SUBMITTING')"
        )[0]["cnt"]

        if not bal_rows:
            return PortfolioSummary(
                account_state="UNKNOWN",
                total_equity=None,
                available_balance=None,
                locked_balance=None,
                unrealized_pnl=unrealized,
                realized_pnl=realized,
                total_exposure=exposure,
                margin_utilization_pct=None,
                risk_utilization_pct=None,
                active_positions_count=len(pos_rows),
                open_orders_count=orders_count,
                daily_pnl=round(unrealized + realized, 2),
                status_message="ACCOUNT DATA UNAVAILABLE",
                is_paper_only=True,
                live_trading_disabled=True
            )

        usd_total = round(float(bal_rows[0]["total"]), 2)
        usd_avail = round(float(bal_rows[0]["available"]), 2)
        usd_locked = round(float(bal_rows[0]["locked"]), 2)

        total_equity = round(usd_total + unrealized, 2)
        margin_util = (exposure / total_equity * 100) if total_equity > 0 else 0.0
        risk_util = (exposure / 100000.0 * 100)

        return PortfolioSummary(
            account_state="CONFIGURED",
            total_equity=round(total_equity, 2),
            available_balance=round(usd_avail, 2),
            locked_balance=round(usd_locked, 2),
            unrealized_pnl=round(unrealized, 2),
            realized_pnl=round(realized, 2),
            total_exposure=round(exposure, 2),
            margin_utilization_pct=round(margin_util, 2),
            risk_utilization_pct=round(risk_util, 2),
            active_positions_count=len(pos_rows),
            open_orders_count=orders_count,
            daily_pnl=round(unrealized + realized, 2),
            status_message="BALANCED",
            is_paper_only=True,
            live_trading_disabled=True
        )


_PORTFOLIO_ENGINE: Optional[PortfolioEngine] = None


def get_portfolio_engine() -> PortfolioEngine:
    global _PORTFOLIO_ENGINE
    if _PORTFOLIO_ENGINE is None:
        _PORTFOLIO_ENGINE = PortfolioEngine()
    return _PORTFOLIO_ENGINE
