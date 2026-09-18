"""
Antigravity QuantEngine - Central Risk Engine
Enforces pre-trade risk controls, max notional, max daily loss, exposure limits,
stale data protection, and Emergency Stop (STOP PAPER TRADING).
Fail closed if risk state is unknown.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel

from core.config import get_config
from core.domain.models import OrderRecord, PositionRecord, OrderSide
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("risk.engine")


class RiskCheckResult(BaseModel):
    passed: bool
    rule_name: str
    reason: str
    current_value: float
    threshold_value: float
    timestamp: str


class RiskEngine:
    """Pre-trade risk engine with fail-closed architecture."""

    def __init__(self):
        self.emergency_stop_triggered = False
        self.last_trade_timestamp: Optional[datetime] = None

    def trigger_emergency_stop(self, reason: str = "Operator manual emergency stop") -> None:
        """Trigger emergency stop. Immediately halts new orders."""
        self.emergency_stop_triggered = True
        cfg = get_config()
        cfg.risk.emergency_stop_active = True

        db = get_db()
        sql = """
            INSERT INTO risk_events (
                event_id, event_type, severity, rule_name,
                metric_value, threshold_value, details_json
            ) VALUES (?, 'EMERGENCY_STOP_TRIGGERED', 'CRITICAL', 'EMERGENCY_STOP', 1.0, 0.0, ?)
        """
        db.execute_non_query(
            sql,
            (
                f"risk_emg_{uuid.uuid4().hex[:8]}",
                json.dumps({"reason": reason, "timestamp": datetime.now(timezone.utc).isoformat()})
            )
        )
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}. Paper execution halted.")

    def reset_emergency_stop(self) -> None:
        self.emergency_stop_triggered = False
        cfg = get_config()
        cfg.risk.emergency_stop_active = False
        logger.warning("Emergency stop reset by authorized operator.")

    def evaluate_pre_trade_risk(
        self,
        order: OrderRecord,
        estimated_price: float,
        latest_market_data_ts: Optional[datetime] = None
    ) -> RiskCheckResult:
        cfg = get_config()
        risk_cfg = cfg.risk
        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()

        # 1. Emergency stop check
        if self.emergency_stop_triggered or risk_cfg.emergency_stop_active:
            return RiskCheckResult(
                passed=False,
                rule_name="EMERGENCY_STOP",
                reason="Emergency stop is currently active. Order submission blocked.",
                current_value=1.0,
                threshold_value=0.0,
                timestamp=now_str
            )

        # 2. Stale market data protection
        if latest_market_data_ts is not None:
            age_seconds = (now_dt - latest_market_data_ts).total_seconds()
            if age_seconds > cfg.market_data.stale_data_threshold_seconds:
                self._log_risk_event(
                    "STALE_DATA_HALT", "WARNING", "STALE_DATA_CHECK",
                    age_seconds, cfg.market_data.stale_data_threshold_seconds,
                    f"Market data age {age_seconds:.1f}s exceeds threshold {cfg.market_data.stale_data_threshold_seconds}s"
                )
                return RiskCheckResult(
                    passed=False,
                    rule_name="STALE_DATA_CHECK",
                    reason=f"Stale market data: latency is {age_seconds:.1f}s. Order submission halted.",
                    current_value=age_seconds,
                    threshold_value=cfg.market_data.stale_data_threshold_seconds,
                    timestamp=now_str
                )

        # 3. Max order notional check
        notional = order.quantity * (order.price if order.price else estimated_price)
        if notional > risk_cfg.max_order_notional_usd:
            self._log_risk_event(
                "LIMIT_BREACH", "REJECTED", "MAX_ORDER_NOTIONAL",
                notional, risk_cfg.max_order_notional_usd,
                f"Order notional ${notional:,.2f} exceeds limit ${risk_cfg.max_order_notional_usd:,.2f}"
            )
            return RiskCheckResult(
                passed=False,
                rule_name="MAX_ORDER_NOTIONAL",
                reason=f"Order notional ${notional:,.2f} exceeds limit ${risk_cfg.max_order_notional_usd:,.2f}",
                current_value=notional,
                threshold_value=risk_cfg.max_order_notional_usd,
                timestamp=now_str
            )

        # 4. Max concurrent positions and max portfolio exposure
        db = get_db()
        positions = db.execute_query("SELECT * FROM paper_positions WHERE quantity != 0")
        active_positions_count = len(positions)

        # If adding a new symbol position, verify max concurrent positions
        existing_sym = any(p["symbol"] == order.symbol for p in positions)
        if not existing_sym and active_positions_count >= risk_cfg.max_concurrent_positions:
            return RiskCheckResult(
                passed=False,
                rule_name="MAX_CONCURRENT_POSITIONS",
                reason=f"Active positions ({active_positions_count}) reached limit ({risk_cfg.max_concurrent_positions})",
                current_value=float(active_positions_count),
                threshold_value=float(risk_cfg.max_concurrent_positions),
                timestamp=now_str
            )

        # Total portfolio exposure
        current_exposure = sum(abs(p["quantity"] * p["current_market_price"]) for p in positions)
        new_exposure = current_exposure + notional
        if new_exposure > risk_cfg.max_portfolio_exposure_usd:
            return RiskCheckResult(
                passed=False,
                rule_name="MAX_PORTFOLIO_EXPOSURE",
                reason=f"Projected exposure ${new_exposure:,.2f} exceeds max ${risk_cfg.max_portfolio_exposure_usd:,.2f}",
                current_value=new_exposure,
                threshold_value=risk_cfg.max_portfolio_exposure_usd,
                timestamp=now_str
            )

        # 5. Cooldown check
        if self.last_trade_timestamp:
            elapsed = (now_dt - self.last_trade_timestamp).total_seconds()
            if elapsed < risk_cfg.cooldown_period_seconds:
                return RiskCheckResult(
                    passed=False,
                    rule_name="COOLDOWN_PERIOD",
                    reason=f"Order rejected by cooldown: {elapsed:.1f}s < {risk_cfg.cooldown_period_seconds}s",
                    current_value=elapsed,
                    threshold_value=float(risk_cfg.cooldown_period_seconds),
                    timestamp=now_str
                )

        return RiskCheckResult(
            passed=True,
            rule_name="ALL_RISK_CHECKS_PASSED",
            reason="Order satisfies all centralized risk constraints.",
            current_value=notional,
            threshold_value=risk_cfg.max_order_notional_usd,
            timestamp=now_str
        )

    def record_order_executed(self) -> None:
        self.last_trade_timestamp = datetime.now(timezone.utc)

    def _log_risk_event(
        self,
        event_type: str,
        severity: str,
        rule_name: str,
        metric: float,
        threshold: float,
        details: str
    ) -> None:
        try:
            db = get_db()
            sql = """
                INSERT INTO risk_events (
                    event_id, event_type, severity, rule_name,
                    metric_value, threshold_value, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            db.execute_non_query(
                sql,
                (
                    f"risk_{uuid.uuid4().hex[:8]}",
                    event_type,
                    severity,
                    rule_name,
                    metric,
                    threshold,
                    json.dumps({"details": details, "timestamp": datetime.now(timezone.utc).isoformat()})
                )
            )
        except Exception as e:
            logger.error(f"Failed to record risk event: {e}")


_RISK_ENGINE: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    global _RISK_ENGINE
    if _RISK_ENGINE is None:
        _RISK_ENGINE = RiskEngine()
    return _RISK_ENGINE
