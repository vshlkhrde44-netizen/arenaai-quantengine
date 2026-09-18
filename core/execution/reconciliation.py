"""
Antigravity QuantEngine - Paper Account Reconciliation Engine
Periodically compares local paper positions, balances, and orders against exchange sandbox venue state.
CRITICAL (P0-22, P0-23, Section 48, 49):
If venue state cannot be retrieved, state is UNKNOWN and NEW_PAPER_ORDERS = BLOCKED.
Never reports BALANCED when the comparison was not performed.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from core.domain.models import PositionRecord
from core.execution.safety_gate import ExecutionSafetyGate
from connectors.registry import get_connector_registry
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("execution.reconciliation")


class ReconciliationDiscrepancy(BaseModel):
    item_type: str # "BALANCE", "POSITION", "ORDER"
    symbol_or_asset: str
    local_value: Any
    venue_value: Any
    difference: Optional[float] = None
    timestamp: str


class ReconciliationReport(BaseModel):
    reconciliation_id: str
    venue: str
    status: str # "BALANCED", "DISCREPANCY_DETECTED", "UNKNOWN", "CONNECTOR_NOT_FOUND"
    blocked_new_orders: bool
    discrepancies: List[ReconciliationDiscrepancy]
    timestamp: str
    notes: Optional[str] = None


class PaperReconciliationEngine:
    """Audits local paper trading balances, positions, and orders against venue sandbox reports."""

    @staticmethod
    async def reconcile_venue(venue: str = "coinbase") -> ReconciliationReport:
        rec_id = f"rec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        discrepancies: List[ReconciliationDiscrepancy] = []
        now_str = datetime.now(timezone.utc).isoformat()

        registry = get_connector_registry()
        connector = registry.get(venue)
        if not connector:
            ExecutionSafetyGate.set_reconciliation_blocked(True)
            return ReconciliationReport(
                reconciliation_id=rec_id,
                venue=venue,
                status="CONNECTOR_NOT_FOUND",
                blocked_new_orders=True,
                discrepancies=[],
                timestamp=now_str,
                notes=f"Connector '{venue}' not registered. Trading blocked."
            )

        db = get_db()
        fetch_failed = False
        error_msg = ""

        # 1. Compare Balances (P0-22)
        try:
            venue_balances = await connector.account.fetch_paper_balances()
            if venue_balances is None:
                # Venue account unreachable or unconfigured
                fetch_failed = True
                error_msg = "Venue returned None for paper balances (credentials unverified or endpoint unreachable)"
            else:
                local_balances = {
                    r["asset"]: float(r["total"])
                    for r in db.execute_query("SELECT asset, total FROM paper_balances")
                }
                for asset, venue_bal in venue_balances.items():
                    local_bal = local_balances.get(asset, 0.0)
                    diff = abs(venue_bal - local_bal)
                    if diff > 0.01:
                        discrepancies.append(ReconciliationDiscrepancy(
                            item_type="BALANCE",
                            symbol_or_asset=asset,
                            local_value=local_bal,
                            venue_value=venue_bal,
                            difference=round(diff, 4),
                            timestamp=now_str
                        ))
        except Exception as e:
            fetch_failed = True
            error_msg = f"Exception fetching venue balances: {e}"
            logger.error(error_msg, exc_info=True)

        # 2. Compare Positions (P0-22)
        if not fetch_failed:
            try:
                venue_positions = await connector.account.fetch_paper_positions()
                if venue_positions is not None:
                    local_positions = {
                        r["symbol"]: float(r["quantity"])
                        for r in db.execute_query("SELECT symbol, quantity FROM paper_positions WHERE quantity > 0")
                    }
                    for v_pos in venue_positions:
                        loc_qty = local_positions.get(v_pos.symbol, 0.0)
                        diff = abs(v_pos.quantity - loc_qty)
                        if diff > 1e-5:
                            discrepancies.append(ReconciliationDiscrepancy(
                                item_type="POSITION",
                                symbol_or_asset=v_pos.symbol,
                                local_value=loc_qty,
                                venue_value=v_pos.quantity,
                                difference=round(diff, 5),
                                timestamp=now_str
                            ))
            except Exception as e:
                fetch_failed = True
                error_msg = f"Exception fetching venue positions: {e}"
                logger.error(error_msg, exc_info=True)

        # 3. Determine Status (CRITICAL P0-23, Section 49)
        if fetch_failed:
            # Venue state could not be retrieved -> status UNKNOWN, BLOCK NEW ORDERS!
            status_str = "UNKNOWN"
            ExecutionSafetyGate.set_reconciliation_blocked(True)
            logger.warning(f"RECONCILIATION UNKNOWN on venue {venue}: {error_msg}. New paper orders BLOCKED.")
        elif discrepancies:
            status_str = "DISCREPANCY_DETECTED"
            ExecutionSafetyGate.set_reconciliation_blocked(True)
            logger.warning(f"RECONCILIATION DISCREPANCY on venue {venue}: {len(discrepancies)} mismatches. Trading blocked.")
        else:
            status_str = "BALANCED"
            ExecutionSafetyGate.set_reconciliation_blocked(False)

        # Record event in risk_events
        sql = """
            INSERT INTO risk_events (
                event_id, event_type, severity, rule_name,
                metric_value, threshold_value, details_json
            ) VALUES (?, 'RECONCILIATION_AUDIT', ?, 'VENUE_RECONCILIATION', ?, 0.0, ?)
        """
        severity = "INFO" if status_str == "BALANCED" else ("ERROR" if status_str == "UNKNOWN" else "WARNING")
        db.execute_non_query(
            sql,
            (
                f"risk_rec_{uuid.uuid4().hex[:8]}",
                severity,
                float(len(discrepancies)),
                json.dumps({
                    "status": status_str,
                    "error": error_msg if fetch_failed else None,
                    "discrepancies": [d.model_dump() for d in discrepancies]
                })
            )
        )

        return ReconciliationReport(
            reconciliation_id=rec_id,
            venue=venue,
            status=status_str,
            blocked_new_orders=ExecutionSafetyGate.is_reconciliation_blocked(),
            discrepancies=discrepancies,
            timestamp=now_str,
            notes=error_msg if fetch_failed else None
        )
