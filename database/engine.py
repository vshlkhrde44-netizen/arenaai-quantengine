"""
Antigravity QuantEngine - Database Engine & Connection Manager
Operates high-performance SQLite in WAL mode with transactional safety.
"""

import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from core.config import get_config
from core.logging import get_logger
from database.schemas import INITIAL_SCHEMA_SQL

logger = get_logger("database.engine")


class DatabaseEngine:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            cfg = get_config()
            db_path = cfg.database.sqlite_path
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initialize tables and execute initial migrations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(INITIAL_SCHEMA_SQL)
            
            # Check if initial migration is registered
            cursor.execute("SELECT version FROM schema_migrations WHERE version = 1")
            row = cursor.fetchone()
            if not row:
                checksum = hashlib.sha256(INITIAL_SCHEMA_SQL.encode("utf-8")).hexdigest()
                cursor.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) VALUES (1, '001_initial_schema', ?)",
                    (checksum,)
                )
                logger.info("Applied migration 001_initial_schema successfully.")

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_non_query(self, sql: str, params: tuple = ()) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def verify_integrity(self) -> bool:
        """Run SQLite PRAGMA integrity_check."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            return result == "ok"


_DB_INSTANCE: Optional[DatabaseEngine] = None


def get_db() -> DatabaseEngine:
    global _DB_INSTANCE
    if _DB_INSTANCE is None:
        _DB_INSTANCE = DatabaseEngine()
    return _DB_INSTANCE
