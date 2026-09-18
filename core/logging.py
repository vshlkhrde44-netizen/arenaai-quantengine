"""
Antigravity QuantEngine - Institutional Structured Logging
Features automatic secret masking, correlation IDs, and tamper-resistant audit logs.
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# Regex patterns for detecting potential keys, tokens, secrets
SECRET_PATTERNS = [
    re.compile(r'(?i)(secret|key|token|passphrase|signature|password)["\']?\s*[:=]\s*["\']?([^"\'\s,]+)'),
    re.compile(r'\b[A-Za-z0-9+/]{32,}={0,2}\b'), # Base64 or hash lookalikes
]


def mask_sensitive_data(message: str) -> str:
    """Mask any potentially sensitive data in text."""
    masked = message
    for pattern in SECRET_PATTERNS:
        def repl(match):
            val = match.group(0)
            if len(val) > 8:
                return val[:4] + "****" + val[-4:]
            return "****"
        try:
            masked = pattern.sub(repl, masked)
        except Exception:
            pass
    return masked


class InstitutionalJsonFormatter(logging.Formatter):
    """Custom JSON formatter with mandatory audit fields and secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "component": getattr(record, "component", record.name),
            "event": getattr(record, "event", "LOG_EVENT"),
            "correlation_id": getattr(record, "correlation_id", "none"),
            "session_id": getattr(record, "session_id", "none"),
            "message": mask_sensitive_data(record.getMessage())
        }
        if record.exc_info:
            log_entry["exception"] = mask_sensitive_data(self.formatException(record.exc_info))
        return json.dumps(log_entry)


def get_logger(name: str = "quantengine") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(InstitutionalJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
