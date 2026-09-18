"""
Antigravity QuantEngine - Market Data Session Management
Enforces explicit session boundaries, sequence tracking, and gap auditing across reconnects.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from database.engine import get_db
from core.logging import get_logger
from core.marketdata.tamper_chain import GENESIS_HASH

logger = get_logger("marketdata.session")


class MarketDataSession:
    """Represents a continuous real-time market data streaming session."""

    def __init__(self, venue: str, symbol: str):
        self.session_id = f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.venue = venue
        self.symbol = symbol
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.records_received = 0
        self.records_persisted = 0
        self.records_rejected = 0
        self.records_lost = 0
        self.gap_count = 0
        self.genesis_hash = GENESIS_HASH
        self.final_hash: Optional[str] = None
        self.is_active = True
        self._persist_session_start()

    def _persist_session_start(self) -> None:
        db = get_db()
        sql = """
            INSERT INTO market_sessions (
                session_id, venue, symbol, start_time, records_received,
                records_persisted, records_rejected, records_lost, gap_count,
                genesis_hash, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """
        db.execute_non_query(
            sql,
            (
                self.session_id,
                self.venue,
                self.symbol,
                self.start_time.isoformat(),
                0, 0, 0, 0, 0,
                self.genesis_hash
            )
        )
        logger.info(f"Initialized new market data session: {self.session_id} on {self.venue} [{self.symbol}]")

    def record_gap(self, reason: str, expected_seq: Optional[int] = None, got_seq: Optional[int] = None) -> None:
        """Explicitly record a data stream gap. Never silently stitch."""
        self.gap_count += 1
        db = get_db()
        db.execute_non_query(
            "UPDATE market_sessions SET gap_count = gap_count + 1 WHERE session_id = ?",
            (self.session_id,)
        )
        logger.warning(
            f"STREAM GAP DETECTED in session {self.session_id}: {reason} "
            f"(expected seq: {expected_seq}, got: {got_seq})"
        )

    def close_session(self, final_hash: str) -> None:
        """Close session and finalize hash state."""
        self.is_active = False
        self.end_time = datetime.now(timezone.utc)
        self.final_hash = final_hash
        db = get_db()
        sql = """
            UPDATE market_sessions SET
                end_time = ?,
                records_received = ?,
                records_persisted = ?,
                records_rejected = ?,
                records_lost = ?,
                gap_count = ?,
                final_hash = ?,
                is_active = 0
            WHERE session_id = ?
        """
        db.execute_non_query(
            sql,
            (
                self.end_time.isoformat(),
                self.records_received,
                self.records_persisted,
                self.records_rejected,
                self.records_lost,
                self.gap_count,
                self.final_hash,
                self.session_id
            )
        )
        logger.info(f"Closed market data session {self.session_id}. Final hash: {final_hash[:8]}...")
