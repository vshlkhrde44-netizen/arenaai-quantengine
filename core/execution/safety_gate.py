"""
Antigravity QuantEngine - Execution Safety Firewall (ExecutionSafetyGate)
Centralized, non-bypassable safety gate enforcing paper-only trading invariants.
Rejects live order attempts before network transmission using exact canonical
endpoint allowlists (P0-20, Section 45).
"""

import json
from urllib.parse import urlsplit
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel

from core.config import get_config, RuntimeMode
from core.domain.models import OrderRecord
from connectors.exchanges.base import CapabilityDescriptor
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("execution.safety_gate")


class SafetyCheckResult(BaseModel):
    passed: bool
    reason: str
    checks: Dict[str, bool]
    timestamp: str


class ExecutionSafetyGate:
    """
    Non-bypassable execution firewall. Evaluates every paper order prior to dispatch.
    CRITICAL: Validates against an exact canonical endpoint allowlist (P0-20).
    Never uses substring checks like '"sandbox" in url'.
    """

    APPROVED_CANONICAL_HOSTS: Set[str] = {
        "api-public.sandbox.exchange.coinbase.com",
        "paper-api.alpaca.markets"
    }

    PROHIBITED_HOSTS: Set[str] = {
        "api.coinbase.com",
        "api.exchange.coinbase.com",
        "api.alpaca.markets",
        "api.binance.com",
        "api.kraken.com",
        "api.bybit.com",
        "api.okx.com"
    }

    _reconciliation_blocked: bool = False

    @classmethod
    def set_reconciliation_blocked(cls, blocked: bool) -> None:
        """Section 49: If reconciliation state is UNKNOWN, block new paper orders."""
        cls._reconciliation_blocked = blocked

    @classmethod
    def is_reconciliation_blocked(cls) -> bool:
        return cls._reconciliation_blocked

    @classmethod
    def evaluate_order(
        cls,
        order: OrderRecord,
        capabilities: CapabilityDescriptor,
        target_endpoint: str
    ) -> SafetyCheckResult:
        cfg = get_config()
        checks: Dict[str, bool] = {}
        failure_reasons = []

        # 1. Check runtime mode (PAPER_TRADING permits orders, and TEST permits CI mock orders per Section 69, 70)
        mode_valid = (cfg.system.runtime_mode in (RuntimeMode.PAPER_TRADING, RuntimeMode.TEST))
        checks["runtime_mode_is_paper"] = mode_valid
        if not mode_valid:
            failure_reasons.append(f"Runtime mode is '{cfg.system.runtime_mode}', only PAPER_TRADING permits orders.")

        # 2. Check global paper-only invariant
        checks["paper_only_invariant"] = cfg.system.paper_only
        if not cfg.system.paper_only:
            failure_reasons.append("System paper_only flag is False (FATAL SAFETY VIOLATION).")

        # 3. Check live orders disabled invariant
        checks["live_orders_disabled"] = not cfg.system.live_orders_enabled
        if cfg.system.live_orders_enabled:
            failure_reasons.append("Live orders flag is True (FATAL SAFETY VIOLATION).")

        # 4. Check production ready invariant
        checks["not_production_ready"] = not cfg.system.is_production_ready
        if cfg.system.is_production_ready:
            failure_reasons.append("is_production_ready is True (FATAL SAFETY VIOLATION).")

        # 5. Check connector paper capabilities
        checks["connector_supports_paper"] = capabilities.supports_paper_orders
        checks["connector_supports_live_is_false"] = not capabilities.supports_live_orders
        if not capabilities.supports_paper_orders:
            failure_reasons.append(f"Venue {capabilities.venue_name} does not support official paper orders.")
        if capabilities.supports_live_orders:
            failure_reasons.append(f"Venue {capabilities.venue_name} has live order capability enabled (PROHIBITED).")

        # 6. EXACT CANONICAL ENDPOINT VALIDATION (P0-20, Section 45)
        parsed = urlsplit(target_endpoint)
        is_canonical_paper = False

        if parsed.scheme != "https":
            failure_reasons.append(f"Target URL scheme '{parsed.scheme}' is prohibited. Must be HTTPS.")
        elif parsed.hostname in cls.PROHIBITED_HOSTS:
            failure_reasons.append(f"Target URL contains prohibited live endpoint keyword / production host: '{parsed.hostname}'")
        elif parsed.hostname not in cls.APPROVED_CANONICAL_HOSTS:
            failure_reasons.append(
                f"Target URL contains prohibited live endpoint keyword / unapproved host: '{parsed.hostname}'. "
                f"Approved canonical endpoints: {sorted(list(cls.APPROVED_CANONICAL_HOSTS))}."
            )
        else:
            is_canonical_paper = True

        checks["exact_canonical_paper_endpoint"] = is_canonical_paper
        checks["target_endpoint_is_sandbox"] = is_canonical_paper

        # 7. Check Emergency Stop
        checks["emergency_stop_inactive"] = not cfg.risk.emergency_stop_active
        if cfg.risk.emergency_stop_active:
            failure_reasons.append("Emergency stop is currently ACTIVE. Paper trading halted.")

        # 8. Check Reconciliation Gate (Section 49)
        checks["reconciliation_state_known"] = not cls._reconciliation_blocked
        if cls._reconciliation_blocked:
            failure_reasons.append("Reconciliation state is UNKNOWN. New paper orders blocked until venue reconciliation restored.")

        passed = len(failure_reasons) == 0
        reason_str = "All safety invariants verified. Approved for sandbox transmission." if passed else " | ".join(failure_reasons)

        result = SafetyCheckResult(
            passed=passed,
            reason=reason_str,
            checks=checks,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        cls._log_safety_audit(order, result)

        if not passed:
            logger.error(f"EXECUTION SAFETY FIREWALL REJECTION for Order {order.order_id}: {reason_str}")

        return result

    @classmethod
    def _log_safety_audit(cls, order: OrderRecord, result: SafetyCheckResult) -> None:
        try:
            from core.audit.audit_engine import get_audit_engine
            audit = get_audit_engine()
            details = {
                "order_id": order.order_id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "quantity": order.quantity,
                "side": order.side.value,
                "passed": result.passed,
                "reason": result.reason,
                "checks": result.checks
            }
            audit.log_event(
                event_type="SAFETY_GATE_EVALUATION",
                component="ExecutionSafetyGate",
                action="EVALUATE_ORDER",
                status="SUCCESS" if result.passed else "REJECTED",
                details=details
            )
        except Exception as e:
            logger.error(f"Failed to log safety audit event: {e}")
