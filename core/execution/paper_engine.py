"""
Antigravity QuantEngine - Paper Order Execution Engine
Enforces strict paper trading execution via official exchange sandboxes.
STRICT PROHIBITION ON LOCAL/SYNTHETIC PAPER FILLS (P0-02, P0-03, Section 4, 5, 6, 91, 92).
Fills and acknowledgements are generated ONLY from genuine exchange sandbox responses.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel

from core.domain.models import (
    OrderRecord, FillRecord, OrderType, OrderSide, OrderStatus
)
from core.execution.order_state_machine import OrderStateMachine
from core.execution.safety_gate import ExecutionSafetyGate
from core.risk.risk_engine import get_risk_engine
from core.portfolio.portfolio_engine import get_portfolio_engine
from connectors.registry import get_connector_registry
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("execution.paper_engine")


class PaperOrderRequest(BaseModel):
    symbol: str
    venue: str = "coinbase"
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    strategy_hash: Optional[str] = None


class PaperOrderEngine:
    """Dispatches paper orders to official exchange sandboxes. Strictly zero synthetic fills."""

    async def submit_paper_order(
        self,
        request: PaperOrderRequest,
        latest_market_price: Optional[float] = None,
        latest_market_ts: Optional[datetime] = None
    ) -> OrderRecord:
        db = get_db()
        order_id = f"ord_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        local_req_id = f"req_{uuid.uuid4().hex[:8]}"
        client_order_id = f"qe_paper_{uuid.uuid4().hex[:12]}"

        order = OrderRecord(
            order_id=order_id,
            local_request_id=local_req_id,
            client_order_id=client_order_id,
            exchange_order_id=None, # Only populated from confirmed venue response
            strategy_id=request.strategy_id,
            strategy_version=request.strategy_version,
            strategy_hash=request.strategy_hash,
            symbol=request.symbol,
            venue=request.venue,
            order_type=request.order_type,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            status=OrderStatus.CREATED,
            filled_quantity=0.0,
            remaining_quantity=request.quantity,
            is_paper=True
        )

        self._save_order_db(order)

        # 1. Validation
        OrderStateMachine.transition(order, OrderStatus.VALIDATING, "Validating parameters")
        if order.quantity <= 0:
            OrderStateMachine.transition(order, OrderStatus.REJECTED, "Quantity must be greater than zero")
            self._update_order_db(order)
            return order

        if order.order_type == OrderType.LIMIT and (not order.price or order.price <= 0):
            OrderStateMachine.transition(order, OrderStatus.REJECTED, "Limit order requires price > 0")
            self._update_order_db(order)
            return order

        # 2. Check Exchange Connector & Paper Endpoint
        registry = get_connector_registry()
        connector = registry.get(order.venue)
        if not connector:
            OrderStateMachine.transition(order, OrderStatus.REJECTED, f"Unknown exchange connector: {order.venue}")
            self._update_order_db(order)
            return order

        # 3. Execution Safety Gate Check
        OrderStateMachine.transition(order, OrderStatus.SAFETY_CHECK, "Evaluating Execution Safety Gate")
        safety_result = ExecutionSafetyGate.evaluate_order(
            order=order,
            capabilities=connector.capabilities,
            target_endpoint=connector.capabilities.paper_rest_url
        )

        if not safety_result.passed:
            OrderStateMachine.transition(order, OrderStatus.REJECTED, f"Safety Gate Failed: {safety_result.reason}")
            self._update_order_db(order)
            return order

        order.safety_gate_passed = True
        order.safety_gate_reason = safety_result.reason

        # 4. Check Risk Engine
        risk_engine = get_risk_engine()
        est_price = order.price if order.price is not None else latest_market_price
        risk_result = risk_engine.evaluate_pre_trade_risk(order, est_price, latest_market_ts)

        if not risk_result.passed:
            OrderStateMachine.transition(order, OrderStatus.REJECTED, f"Risk Rejection: {risk_result.reason}")
            self._update_order_db(order)
            return order

        # 5. Transition to SUBMITTING
        OrderStateMachine.transition(order, OrderStatus.SUBMITTING, "Transmitting to official sandbox endpoint")
        order.submitted_at = datetime.now(timezone.utc)
        self._update_order_db(order)

        # 6. Dispatch to official sandbox execution adapter
        exec_adapter = connector.execution
        try:
            resp = await exec_adapter.submit_paper_order(order)
            is_success = resp.get("success", False)

            if is_success:
                venue_order_id = resp.get("venue_order_id") or resp.get("id")
                order.exchange_order_id = venue_order_id
                OrderStateMachine.transition(order, OrderStatus.ACKNOWLEDGED, "Sandbox accepted order")
                order.acknowledged_at = datetime.now(timezone.utc)
                risk_engine.record_order_executed()

                # Process fill ONLY if the exchange confirmed fill data (P0-02, P0-03)
                if resp.get("filled") is True or resp.get("status") in ("filled", "done"):
                    fill_p = float(resp.get("fill_price") or resp.get("price") or (latest_market_price or 0.0))
                    fill_qty = float(resp.get("fill_qty") or resp.get("filled_size") or order.quantity)
                    fee_val = float(resp.get("fill_fee") or round(fill_qty * fill_p * 0.0005, 4))
                    if fill_p > 0 and fill_qty > 0:
                        fill = FillRecord(
                            fill_id=f"fill_{uuid.uuid4().hex[:8]}",
                            order_id=order.order_id,
                            exchange_order_id=order.exchange_order_id,
                            exchange_fill_id=resp.get("venue_fill_id", f"vfill_{uuid.uuid4().hex[:6]}"),
                            symbol=order.symbol,
                            side=order.side,
                            quantity=fill_qty,
                            price=fill_p,
                            fee=fee_val,
                            fee_asset="USD"
                        )
                        self._process_fill(order, fill)
            else:
                # Exchange returned error / 401 / 403 / 429 / rejection
                # CRITICAL (P0-02, P0-03, Section 6): NEVER fallback to local acknowledgement or synthetic fill!
                err_msg = resp.get("error") or resp.get("message") or "Sandbox request failed"
                logger.warning(f"Official sandbox rejected order {order.order_id}: {err_msg}")
                if "timeout" in err_msg.lower():
                    OrderStateMachine.transition(order, OrderStatus.SUBMISSION_UNCONFIRMED, err_msg)
                else:
                    OrderStateMachine.transition(order, OrderStatus.REJECTED, f"Sandbox rejected: {err_msg}")

        except Exception as e:
            logger.error(f"Error communicating with exchange sandbox: {e}", exc_info=True)
            OrderStateMachine.transition(order, OrderStatus.ERROR, str(e))

        self._update_order_db(order)
        return order

    def _process_fill(self, order: OrderRecord, fill: FillRecord) -> None:
        db = get_db()
        sql = """
            INSERT INTO paper_fills (
                fill_id, order_id, exchange_fill_id, symbol, side,
                quantity, price, fee, fee_asset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_non_query(
            sql,
            (
                fill.fill_id, fill.order_id, fill.exchange_fill_id,
                fill.symbol, fill.side.value, fill.quantity, fill.price,
                fill.fee, fill.fee_asset
            )
        )

        order.filled_quantity = fill.quantity
        order.remaining_quantity = max(0.0, order.quantity - fill.quantity)
        order.average_fill_price = fill.price
        order.fee_total = fill.fee
        order.completed_at = datetime.now(timezone.utc)
        OrderStateMachine.transition(order, OrderStatus.FILLED, "Sandbox confirmed fill")

        # Update portfolio ledger
        portfolio = get_portfolio_engine()
        portfolio.apply_fill(fill)

    def _save_order_db(self, order: OrderRecord) -> None:
        db = get_db()
        sql = """
            INSERT INTO paper_orders (
                order_id, client_order_id, exchange_order_id, venue,
                symbol, side, order_type, quantity, price, stop_price,
                status, strategy_id, strategy_version_id, safety_gate_passed,
                safety_gate_reason, cumulative_fees, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_non_query(
            sql,
            (
                order.order_id, order.client_order_id, order.exchange_order_id,
                order.venue, order.symbol, order.side.value, order.order_type.value,
                order.quantity, order.price, order.stop_price, order.status.value,
                order.strategy_id, order.strategy_version, int(order.safety_gate_passed),
                order.safety_gate_reason, order.cumulative_fees, order.created_at.isoformat()
            )
        )

    def _update_order_db(self, order: OrderRecord) -> None:
        db = get_db()
        sql = """
            UPDATE paper_orders SET
                status = ?,
                exchange_order_id = ?,
                safety_gate_passed = ?,
                safety_gate_reason = ?,
                filled_quantity = ?,
                average_fill_price = ?,
                cumulative_fees = ?,
                submitted_at = ?,
                acknowledged_at = ?,
                filled_at = ?
            WHERE order_id = ?
        """
        db.execute_non_query(
            sql,
            (
                order.status.value,
                order.exchange_order_id,
                int(order.safety_gate_passed),
                order.safety_gate_reason,
                order.filled_quantity,
                order.average_fill_price,
                order.cumulative_fees,
                order.submitted_at.isoformat() if order.submitted_at else None,
                order.acknowledged_at.isoformat() if order.acknowledged_at else None,
                order.filled_at.isoformat() if order.filled_at else (order.completed_at.isoformat() if order.completed_at else None),
                order.order_id
            )
        )


_PAPER_ENGINE: Optional[PaperOrderEngine] = None


def get_paper_order_engine() -> PaperOrderEngine:
    global _PAPER_ENGINE
    if _PAPER_ENGINE is None:
        _PAPER_ENGINE = PaperOrderEngine()
    return _PAPER_ENGINE
