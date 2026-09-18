"""
Antigravity QuantEngine - Tamper-Evident Raw Data Preservation & Hash Chain
Preserves raw exchange wire messages in append-only JSONL with SHA-256 chaining.

Chain Invariant:
H0 = SHA256("ANTIGRAVITY_QUANTENGINE_GENESIS_v1.0")
Hi = SHA256(H(i-1) || timestamp_iso || canonical_raw_json)
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from core.logging import get_logger

logger = get_logger("marketdata.tamper_chain")

GENESIS_HASH = hashlib.sha256(b"ANTIGRAVITY_QUANTENGINE_GENESIS_v1.0").hexdigest()


class TamperEvidentRawWriter:
    """Appends raw exchange messages with cryptographically verifiable hash chaining."""

    def __init__(self, session_id: str, output_dir: Path = Path("data/raw")):
        self.session_id = session_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.output_dir / f"raw_session_{session_id}.jsonl"
        self.sequence_num = 0
        self.current_hash = GENESIS_HASH
        self._init_or_resume()

    def _init_or_resume(self) -> None:
        """If file exists, resume from the last valid hash and sequence."""
        if self.file_path.exists():
            last_record = None
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        last_record = json.loads(line)
            if last_record:
                self.sequence_num = last_record["sequence_num"]
                self.current_hash = last_record["content_hash"]
                logger.info(f"Resumed raw message chain at seq {self.sequence_num}, hash {self.current_hash[:8]}...")

        self._file = open(self.file_path, "a", encoding="utf-8")

    def append_raw_message(
        self,
        raw_message: str | Dict[str, Any],
        channel: str,
        symbol: str,
        venue: str,
        venue_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record raw wire message and compute next link in hash chain."""
        self.sequence_num += 1
        receipt_dt = datetime.now(timezone.utc).isoformat()
        monotonic_ts = time.monotonic()

        # Canonicalize raw message payload
        if isinstance(raw_message, dict):
            canonical_raw = json.dumps(raw_message, sort_keys=True, separators=(",", ":"))
        else:
            canonical_raw = str(raw_message).strip()

        # Compute tamper-evident hash Hi = SHA256(H(i-1) || receipt_dt || canonical_raw)
        hasher = hashlib.sha256()
        hasher.update(self.current_hash.encode("utf-8"))
        hasher.update(b"||")
        hasher.update(receipt_dt.encode("utf-8"))
        hasher.update(b"||")
        hasher.update(canonical_raw.encode("utf-8"))
        new_hash = hasher.hexdigest()

        record = {
            "session_id": self.session_id,
            "sequence_num": self.sequence_num,
            "venue": venue,
            "channel": channel,
            "symbol": symbol,
            "receipt_timestamp": receipt_dt,
            "monotonic_timestamp": monotonic_ts,
            "venue_timestamp": venue_timestamp,
            "previous_hash": self.current_hash,
            "content_hash": new_hash,
            "raw_payload": canonical_raw
        }

        # Append to open file handle and flush
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()

        self.current_hash = new_hash
        return record

    def close(self) -> None:
        if hasattr(self, "_file") and self._file and not self._file.closed:
            self._file.close()


def verify_tamper_chain(file_path: Path) -> Tuple[bool, int, Optional[str]]:
    """
    Cryptographically verify a raw JSONL message chain.
    Returns: (is_valid, records_checked, error_message)
    """
    path = Path(file_path)
    if not path.exists():
        return False, 0, f"File {file_path} not found"

    expected_prev = GENESIS_HASH
    seq = 0

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                return False, seq, f"Malformed JSON at line {line_num}: {e}"

            seq += 1
            if rec.get("sequence_num") != seq:
                return False, seq, f"Sequence discontinuity at line {line_num}: expected {seq}, got {rec.get('sequence_num')}"

            if rec.get("previous_hash") != expected_prev:
                return False, seq, f"Hash chain break at line {line_num}: expected prev {expected_prev}, got {rec.get('previous_hash')}"

            # Recompute hash
            canonical_raw = rec.get("raw_payload", "")
            receipt_dt = rec.get("receipt_timestamp", "")

            hasher = hashlib.sha256()
            hasher.update(expected_prev.encode("utf-8"))
            hasher.update(b"||")
            hasher.update(receipt_dt.encode("utf-8"))
            hasher.update(b"||")
            hasher.update(canonical_raw.encode("utf-8"))
            computed_hash = hasher.hexdigest()

            if computed_hash != rec.get("content_hash"):
                return False, seq, f"Tampered record at line {line_num}: expected hash {computed_hash}, got {rec.get('content_hash')}"

            expected_prev = computed_hash

    return True, seq, None
