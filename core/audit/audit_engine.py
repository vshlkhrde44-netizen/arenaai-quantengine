"""
Antigravity QuantEngine - Immutable Audit Trail & Order Forensic Reconstruction
Maintains a cryptographic hash-chained audit log and provides complete order reconstruction.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from database.engine import get_db
from core.marketdata.tamper_chain import GENESIS_HASH
from core.logging import get_logger

logger = get_logger("audit.engine")


class AuditEventRecord(BaseModel):
    audit_id: str
    sequence_num: int
    event_type: str
    component: str
    action: str
    actor: str = "SYSTEM"
    status: str
    details: Dict[str, Any]
    previous_hash: str
    content_hash: str
    timestamp: str


class OrderAuditReconstruction(BaseModel):
    order_id: str
    client_order_id: str
    venue: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    status: str
    order_type: str
    strategy_id: Optional[str]
    strategy_version_id: Optional[str]
    safety_gate_passed: bool
    safety_gate_reason: Optional[str]
    created_at: str
    submitted_at: Optional[str]
    acknowledged_at: Optional[str]
    filled_at: Optional[str]
    cancelled_at: Optional[str]
    fills: List[Dict[str, Any]] = Field(default_factory=list)
    risk_events: List[Dict[str, Any]] = Field(default_factory=list)
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    forensic_summary: str


class AuditEngine:
    """Manages append-only tamper-evident audit logs."""

    def __init__(self):
        self._last_hash = GENESIS_HASH
        self._sequence = 0
        self._init_state()

    def _init_state(self) -> None:
        db = get_db()
        rows = db.execute_query(
            "SELECT sequence_num, content_hash FROM audit_events ORDER BY sequence_num DESC LIMIT 1"
        )
        if rows:
            self._sequence = rows[0]["sequence_num"]
            self._last_hash = rows[0]["content_hash"]

    def log_event(
        self,
        event_type: str,
        component: str,
        action: str,
        status: str,
        details: Dict[str, Any],
        actor: str = "SYSTEM"
    ) -> AuditEventRecord:
        """Append cryptographically chained event to audit log."""
        self._sequence += 1
        now_str = datetime.now(timezone.utc).isoformat()
        audit_id = f"aud_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Canonicalize details for hashing
        clean_details = {k: v for k, v in details.items() if not ("secret" in k.lower() or "key" in k.lower())}
        canonical_str = json.dumps(clean_details, sort_keys=True, separators=(",", ":"))

        hasher = hashlib.sha256()
        hasher.update(self._last_hash.encode("utf-8"))
        hasher.update(b"||")
        hasher.update(now_str.encode("utf-8"))
        hasher.update(b"||")
        hasher.update(f"{event_type}:{component}:{action}:{status}".encode("utf-8"))
        hasher.update(b"||")
        hasher.update(canonical_str.encode("utf-8"))
        content_hash = hasher.hexdigest()

        record = AuditEventRecord(
            audit_id=audit_id,
            sequence_num=self._sequence,
            event_type=event_type,
            component=component,
            action=action,
            actor=actor,
            status=status,
            details=clean_details,
            previous_hash=self._last_hash,
            content_hash=content_hash,
            timestamp=now_str
        )

        db = get_db()
        sql = """
            INSERT INTO audit_events (
                audit_id, sequence_num, event_type, component,
                action, actor, status, details_json, previous_hash,
                content_hash, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_non_query(
            sql,
            (
                audit_id, self._sequence, event_type, component,
                action, actor, status, json.dumps(clean_details),
                self._last_hash, content_hash, now_str
            )
        )

        self._last_hash = content_hash
        return record

    def reconstruct_order_lifecycle(self, order_id: str) -> Optional[OrderAuditReconstruction]:
        """
        Reconstruct complete forensic audit trail for a paper order:
        order state, strategy, safety gate, exchange response, fills, risk events.
        """
        db = get_db()
        order_rows = db.execute_query("SELECT * FROM paper_orders WHERE order_id = ?", (order_id,))
        if not order_rows:
            return None

        o = order_rows[0]
        fills = db.execute_query("SELECT * FROM paper_fills WHERE order_id = ?", (order_id,))
        
        # Search audit events mentioning this order_id
        audit_events = db.execute_query(
            "SELECT * FROM audit_events WHERE details_json LIKE ? ORDER BY sequence_num ASC",
            (f"%{order_id}%",)
        )

        # Risk events
        risk_events = db.execute_query(
            "SELECT * FROM risk_events WHERE details_json LIKE ? ORDER BY timestamp ASC",
            (f"%{order_id}%",)
        )

        forensic = (
            f"Paper Order {order_id} ({o['symbol']} {o['side']} {o['quantity']} @ {o['price'] or 'MARKET'}) "
            f"progressed to status {o['status']}. Safety gate: {'PASSED' if o['safety_gate_passed'] else 'FAILED'}. "
            f"Fills recorded: {len(fills)}. Cumulative fees: ${float(o['cumulative_fees']):.4f}."
        )

        return OrderAuditReconstruction(
            order_id=o["order_id"],
            client_order_id=o["client_order_id"],
            venue=o["venue"],
            symbol=o["symbol"],
            side=o["side"],
            quantity=float(o["quantity"]),
            price=float(o["price"]) if o["price"] else None,
            status=o["status"],
            order_type=o["order_type"],
            strategy_id=o["strategy_id"],
            strategy_version_id=o["strategy_version_id"],
            safety_gate_passed=bool(o["safety_gate_passed"]),
            safety_gate_reason=o["safety_gate_reason"],
            created_at=o["created_at"],
            submitted_at=o["submitted_at"],
            acknowledged_at=o["acknowledged_at"],
            filled_at=o["filled_at"],
            cancelled_at=o["cancelled_at"],
            fills=[dict(f) for f in fills],
            risk_events=[dict(r) for r in risk_events],
            audit_events=[dict(a) for a in audit_events],
            forensic_summary=forensic
        )

    def verify_audit_chain_integrity(self) -> Tuple[bool, int, Optional[str]]:
        """Verify the cryptographic hash chain across all audit events in SQLite."""
        db = get_db()
        events = db.execute_query("SELECT * FROM audit_events ORDER BY sequence_num ASC")
        if not events:
            return True, 0, None

        expected_prev = GENESIS_HASH
        for i, ev in enumerate(events, start=1):
            if ev["sequence_num"] != i:
                return False, i, f"Audit sequence discontinuity at row {i}: expected {i}, got {ev['sequence_num']}"

            if ev["previous_hash"] != expected_prev:
                return False, i, f"Audit previous_hash mismatch at seq {i}: expected {expected_prev}, got {ev['previous_hash']}"

            # Recompute hash
            hasher = hashlib.sha256()
            hasher.update(expected_prev.encode("utf-8"))
            hasher.update(b"||")
            hasher.update(ev["timestamp"].encode("utf-8"))
            hasher.update(b"||")
            hasher.update(f"{ev['event_type']}:{ev['component']}:{ev['action']}:{ev['status']}".encode("utf-8"))
            hasher.update(b"||")
            
            clean_details = json.loads(ev["details_json"])
            canonical_str = json.dumps(clean_details, sort_keys=True, separators=(",", ":"))
            hasher.update(canonical_str.encode("utf-8"))
            computed_hash = hasher.hexdigest()

            if computed_hash != ev["content_hash"]:
                return False, i, f"Audit content tampering detected at seq {i}: computed {computed_hash}, stored {ev['content_hash']}"

            expected_prev = computed_hash

        return True, len(events), None


_AUDIT_ENGINE: Optional[AuditEngine] = None


def get_audit_engine() -> AuditEngine:
    global _AUDIT_ENGINE
    if _AUDIT_ENGINE is None:
        _AUDIT_ENGINE = AuditEngine()
    return _AUDIT_ENGINE
