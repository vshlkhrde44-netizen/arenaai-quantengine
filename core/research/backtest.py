"""
Antigravity QuantEngine - Deterministic Backtesting Engine
Executes quantitative strategies under strict causal conditions.
Strict Cost Modeling (P0-12, Section 28, 29):
  gross_pnl = (raw_exit - raw_entry) * qty
  slippage_cost = (abs(entry_fill - raw_entry) + abs(raw_exit - exit_fill)) * qty
  fee_cost = notional_traded * fee_bps
  net_pnl = gross_pnl - fee_cost - slippage_cost
Strict Sharpe & Profit Factor (P0-13, P0-14, Section 30, 31).
"""

import hashlib
import json
import uuid
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from core.strategies.base import BaseStrategy
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("research.backtest")


class CostModel(BaseModel):
    fee_rate_bps: float = 5.0 # 5 bps (0.05%)
    slippage_bps: float = 2.0 # 2 bps (0.02%)


class BacktestTrade(BaseModel):
    trade_id: str
    symbol: str
    side: str
    entry_bar: int
    entry_time: str
    entry_price: Optional[float] = None
    raw_entry_price: Optional[float] = None
    entry_fill_price: Optional[float] = None
    exit_bar: int
    exit_time: str
    exit_price: Optional[float] = None
    raw_exit_price: Optional[float] = None
    exit_fill_price: Optional[float] = None
    quantity: float
    gross_pnl: float
    fees: Optional[float] = None
    fee_cost: float = 0.0
    slippage: Optional[float] = None
    slippage_cost: float = 0.0
    other_cost: float = 0.0
    net_pnl: float
    exit_reason: str

    def __init__(self, **data):
        super().__init__(**data)
        if self.entry_price is not None and self.raw_entry_price is None:
            self.raw_entry_price = self.entry_price
        if self.entry_price is not None and self.entry_fill_price is None:
            self.entry_fill_price = self.entry_price
        if self.exit_price is not None and self.raw_exit_price is None:
            self.raw_exit_price = self.exit_price
        if self.exit_price is not None and self.exit_fill_price is None:
            self.exit_fill_price = self.exit_price
        if self.fees is not None and self.fee_cost == 0.0:
            self.fee_cost = self.fees
        if self.slippage is not None and self.slippage_cost == 0.0:
            self.slippage_cost = self.slippage


class BacktestResult(BaseModel):
    backtest_id: str
    strategy_id: str
    strategy_version: str
    dataset_id: str
    dataset_hash: str
    initial_capital: float
    final_equity: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_pnl: float
    fee_cost: float
    slippage_cost: float
    other_cost: float = 0.0
    net_pnl: float
    profit_factor: Optional[float] = None
    profit_factor_label: str = "UNDEFINED" # "INFINITE", "UNDEFINED", or numeric string
    max_drawdown_pct: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    trades: List[BacktestTrade] = Field(default_factory=list)
    equity_curve: List[float] = Field(default_factory=list)
    result_hash: str


class BacktestEngine:
    """
    Deterministic backtesting engine enforcing strict causal execution.
    Signal at bar t close -> execution at bar t+1 open.
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        cost_model: Optional[CostModel] = None,
        position_size_pct: float = 0.10,
        max_holding_bars: int = 50
    ):
        self.initial_capital = initial_capital
        self.cost_model = cost_model or CostModel()
        self.position_size_pct = position_size_pct
        self.max_holding_bars = max_holding_bars

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        dataset_id: str,
        dataset_hash: str
    ) -> BacktestResult:
        bt_id = f"bt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 1. Generate signals causally
        signals = strategy.generate_signals(df)
        signals_by_bar = {s.bar_index: s for s in signals}

        equity = self.initial_capital
        equity_curve = [round(equity, 2)]
        trades: List[BacktestTrade] = []
        current_position: Optional[Dict[str, Any]] = None

        n_bars = len(df)
        slip_rate = (self.cost_model.slippage_bps / 10000.0)
        fee_rate = (self.cost_model.fee_rate_bps / 10000.0)

        for i in range(1, n_bars):
            bar = df.iloc[i]
            bar_open = float(bar["open"])
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])
            bar_time = str(bar.get("timestamp", f"bar_{i}"))

            # Check open position exits
            if current_position is not None:
                side = current_position["side"]
                raw_entry = current_position["raw_entry"]
                entry_fill = current_position["entry_fill"]
                qty = current_position["quantity"]
                bars_held = i - current_position["entry_bar"]

                sl = current_position.get("stop_loss")
                tp = current_position.get("take_profit")

                closed = False
                raw_exit = bar_open
                exit_reason = ""

                # Stop loss / Take profit priority
                if side == "LONG":
                    if sl is not None and bar_low <= sl:
                        raw_exit = sl
                        exit_reason = "STOP_LOSS"
                        closed = True
                    elif tp is not None and bar_high >= tp:
                        raw_exit = tp
                        exit_reason = "TAKE_PROFIT"
                        closed = True
                else: # SHORT
                    if sl is not None and bar_high >= sl:
                        raw_exit = sl
                        exit_reason = "STOP_LOSS"
                        closed = True
                    elif tp is not None and bar_low <= tp:
                        raw_exit = tp
                        exit_reason = "TAKE_PROFIT"
                        closed = True

                # Check max holding period
                if not closed and bars_held >= self.max_holding_bars:
                    raw_exit = bar_open
                    exit_reason = "MAX_HOLD"
                    closed = True

                # Check opposite signal from prior bar
                if not closed and (i - 1) in signals_by_bar:
                    prev_sig = signals_by_bar[i - 1]
                    if (side == "LONG" and prev_sig.action in ("EXIT_LONG", "ENTER_SHORT")) or \
                       (side == "SHORT" and prev_sig.action in ("EXIT_SHORT", "ENTER_LONG")):
                        raw_exit = bar_open
                        exit_reason = "SIGNAL"
                        closed = True

                if closed:
                    # Exit fill price including slippage
                    exit_fill = raw_exit * (1.0 - slip_rate if side == "LONG" else 1.0 + slip_rate)

                    # Section 28: Separate Gross, Fees, Slippage, Net
                    gross_pnl = (raw_exit - raw_entry) * qty if side == "LONG" else (raw_entry - raw_exit) * qty
                    slippage_cost = (abs(entry_fill - raw_entry) + abs(raw_exit - exit_fill)) * qty
                    fee_cost = (entry_fill * qty + exit_fill * qty) * fee_rate
                    net_pnl = gross_pnl - fee_cost - slippage_cost

                    equity += net_pnl
                    trades.append(BacktestTrade(
                        trade_id=f"trade_{len(trades)+1}",
                        symbol=current_position["symbol"],
                        side=side,
                        entry_bar=current_position["entry_bar"],
                        entry_time=current_position["entry_time"],
                        raw_entry_price=round(raw_entry, 4),
                        entry_fill_price=round(entry_fill, 4),
                        exit_bar=i,
                        exit_time=bar_time,
                        raw_exit_price=round(raw_exit, 4),
                        exit_fill_price=round(exit_fill, 4),
                        quantity=round(qty, 4),
                        gross_pnl=round(gross_pnl, 2),
                        fee_cost=round(fee_cost, 2),
                        slippage_cost=round(slippage_cost, 2),
                        net_pnl=round(net_pnl, 2),
                        exit_reason=exit_reason
                    ))
                    current_position = None

            # Entry execution from prior bar signal (t-1 close -> t open)
            if current_position is None and (i - 1) in signals_by_bar:
                sig = signals_by_bar[i - 1]
                if sig.action in ("ENTER_LONG", "ENTER_SHORT"):
                    side = "LONG" if sig.action == "ENTER_LONG" else "SHORT"
                    raw_entry = bar_open
                    entry_fill = raw_entry * (1.0 + slip_rate if side == "LONG" else 1.0 - slip_rate)

                    notional = equity * self.position_size_pct
                    quantity = notional / entry_fill

                    current_position = {
                        "symbol": sig.symbol,
                        "side": side,
                        "raw_entry": raw_entry,
                        "entry_fill": entry_fill,
                        "quantity": quantity,
                        "entry_bar": i,
                        "entry_time": bar_time,
                        "stop_loss": sig.stop_loss,
                        "take_profit": sig.take_profit
                    }

            equity_curve.append(round(equity, 2))

        # Close any lingering position at end-of-data (Section 29: exact same cost rules!)
        if current_position is not None:
            raw_exit = float(df.iloc[-1]["close"])
            side = current_position["side"]
            raw_entry = current_position["raw_entry"]
            entry_fill = current_position["entry_fill"]
            qty = current_position["quantity"]

            exit_fill = raw_exit * (1.0 - slip_rate if side == "LONG" else 1.0 + slip_rate)
            gross_pnl = (raw_exit - raw_entry) * qty if side == "LONG" else (raw_entry - raw_exit) * qty
            slippage_cost = (abs(entry_fill - raw_entry) + abs(raw_exit - exit_fill)) * qty
            fee_cost = (entry_fill * qty + exit_fill * qty) * fee_rate
            net_pnl = gross_pnl - fee_cost - slippage_cost

            equity += net_pnl
            trades.append(BacktestTrade(
                trade_id=f"trade_{len(trades)+1}",
                symbol=current_position["symbol"],
                side=side,
                entry_bar=current_position["entry_bar"],
                entry_time=current_position["entry_time"],
                raw_entry_price=round(raw_entry, 4),
                entry_fill_price=round(entry_fill, 4),
                exit_bar=n_bars - 1,
                exit_time=str(df.iloc[-1].get("timestamp", "end")),
                raw_exit_price=round(raw_exit, 4),
                exit_fill_price=round(exit_fill, 4),
                quantity=round(qty, 4),
                gross_pnl=round(gross_pnl, 2),
                fee_cost=round(fee_cost, 2),
                slippage_cost=round(slippage_cost, 2),
                net_pnl=round(net_pnl, 2),
                exit_reason="END_OF_DATA"
            ))

        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.net_pnl > 0)
        losing_trades = sum(1 for t in trades if t.net_pnl < 0)
        win_rate = round((winning_trades / total_trades) if total_trades > 0 else 0.0, 4)

        gross_wins = sum(t.gross_pnl for t in trades if t.gross_pnl > 0)
        gross_losses = abs(sum(t.gross_pnl for t in trades if t.gross_pnl < 0))

        # Section 31: Profit Factor representation
        if gross_losses > 0:
            profit_factor = round(gross_wins / gross_losses, 3)
            profit_factor_label = str(profit_factor)
        elif gross_wins > 0:
            profit_factor = None
            profit_factor_label = "INFINITE"
        else:
            profit_factor = None
            profit_factor_label = "UNDEFINED"

        gross_pnl_total = sum(t.gross_pnl for t in trades)
        total_fees = sum(t.fee_cost for t in trades)
        total_slippage = sum(t.slippage_cost for t in trades)
        net_pnl_total = sum(t.net_pnl for t in trades)

        # Drawdown calculation
        eq_arr = np.array(equity_curve)
        peak = np.maximum.accumulate(eq_arr)
        dd = (peak - eq_arr) / np.where(peak > 0, peak, 1.0)
        max_dd_pct = round(float(np.max(dd)) * 100, 2) if len(dd) > 0 else 0.0

        # Section 30: Sharpe & Sortino calculation from equity curve bar returns
        eq_series = pd.Series(equity_curve)
        bar_returns = eq_series.pct_change().dropna()
        sharpe = None
        sortino = None

        if len(bar_returns) > 5:
            mean_ret = bar_returns.mean()
            std_ret = bar_returns.std()
            # Assuming hourly bars: annualization factor = sqrt(24 * 365) = sqrt(8760)
            ann_factor = np.sqrt(8760)
            if std_ret > 1e-8:
                sharpe = round(float((mean_ret / std_ret) * ann_factor), 3)

            downside_returns = bar_returns[bar_returns < 0]
            down_std = downside_returns.std() if len(downside_returns) > 2 else 0.0
            if down_std > 1e-8:
                sortino = round(float((mean_ret / down_std) * ann_factor), 3)

        # Deterministic analytical identity hash (Section 34, 35)
        result_payload = {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "net_pnl": round(net_pnl_total, 2),
            "max_drawdown_pct": max_dd_pct,
            "profit_factor": profit_factor_label,
            "dataset_hash": dataset_hash
        }
        res_hash = hashlib.sha256(json.dumps(result_payload, sort_keys=True).encode("utf-8")).hexdigest()

        bt_result = BacktestResult(
            backtest_id=bt_id,
            strategy_id=strategy.strategy_id,
            strategy_version=f"{strategy.strategy_id}_v{strategy.version}",
            dataset_id=dataset_id,
            dataset_hash=dataset_hash,
            initial_capital=self.initial_capital,
            final_equity=round(equity, 2),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            gross_pnl=round(gross_pnl_total, 2),
            fee_cost=round(total_fees, 2),
            slippage_cost=round(total_slippage, 2),
            net_pnl=round(net_pnl_total, 2),
            profit_factor=profit_factor,
            profit_factor_label=profit_factor_label,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            trades=trades,
            equity_curve=equity_curve,
            result_hash=res_hash
        )

        db = get_db()
        sql = """
            INSERT INTO backtest_runs (
                run_id, strategy_id, strategy_version_id, dataset_id,
                parameters_json, start_time, end_time, initial_capital, final_equity,
                total_trades, win_rate, profit_factor, sharpe_ratio, sortino_ratio,
                max_drawdown, gross_pnl, total_fees, total_slippage, net_pnl,
                config_hash, dataset_hash, code_hash, result_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_non_query(
            sql,
            (
                bt_id, strategy.strategy_id, f"{strategy.strategy_id}_v{strategy.version}",
                dataset_id, json.dumps(self.cost_model.model_dump()),
                str(df.iloc[0].get("timestamp", "start")), str(df.iloc[-1].get("timestamp", "end")),
                self.initial_capital, round(equity, 2), total_trades, win_rate,
                profit_factor if profit_factor is not None else 0.0, sharpe, sortino,
                max_dd_pct, round(gross_pnl_total, 2), round(total_fees, 2), round(total_slippage, 2),
                round(net_pnl_total, 2), "cfg_default", dataset_hash, strategy.code_hash, res_hash
            )
        )
        logger.info(f"Completed Backtest {bt_id}: {total_trades} trades, Net PnL=${net_pnl_total:,.2f}")
        return bt_result
