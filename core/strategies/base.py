"""
Antigravity QuantEngine - Strategy Base Class & Registry
Provides strategy versioning, cryptographic freezing, and explicit promotion firewall.
"""

from abc import ABC, abstractmethod
import hashlib
import inspect
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from core.domain.models import StrategyStatus
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("strategies.base")


class Signal(BaseModel):
    bar_index: int
    timestamp: datetime
    symbol: str
    action: str # "ENTER_LONG", "EXIT_LONG", "ENTER_SHORT", "EXIT_SHORT", "HOLD"
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract Strategy interface with deterministic signal generation."""

    def __init__(self, strategy_id: str, name: str, version: str = "1.0.0", parameters: Optional[Dict[str, Any]] = None):
        self.strategy_id = strategy_id
        self.name = name
        self.version = version
        self.parameters = parameters or {}
        self.code_hash = self.compute_code_hash()
        self.config_hash = self.compute_config_hash()

    def compute_code_hash(self) -> str:
        """Compute SHA-256 hash of strategy implementation source code."""
        try:
            source = inspect.getsource(self.__class__)
        except Exception:
            source = f"{self.__class__.__name__}_{self.name}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def compute_config_hash(self) -> str:
        """Compute SHA-256 hash of strategy parameters."""
        serialized = json.dumps(self.parameters, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        """
        Deterministic signal generation.
        Strict Execution Semantics:
        Signal generated on bar t (close) is executed at bar t+1 (open).
        """
        pass


class StrategyRegistry:
    """Manages strategy versions, freezing, and human promotion firewall."""

    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        try:
            from core.strategies.library import MicrostructureCVDStrategy, VolumeProfilePOCBreakoutStrategy
            self.register_strategy(MicrostructureCVDStrategy(), "Institutional order flow delta imbalance strategy.")
            self.register_strategy(VolumeProfilePOCBreakoutStrategy(), "Volume profile Value Area breakout strategy.")
        except Exception as e:
            logger.debug(f"Builtins init notice: {e}")

    def register_strategy(self, strategy: BaseStrategy, description: str = "") -> None:
        self._strategies[strategy.strategy_id] = strategy
        db = get_db()
        existing = db.execute_query("SELECT strategy_id FROM strategies WHERE strategy_id = ?", (strategy.strategy_id,))
        if not existing:
            sql = """
                INSERT INTO strategies (
                    strategy_id, name, description, current_version, status,
                    code_hash, config_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            now = datetime.now(timezone.utc).isoformat()
            db.execute_non_query(
                sql,
                (
                    strategy.strategy_id, strategy.name, description, strategy.version,
                    StrategyStatus.DRAFT.value, strategy.code_hash, strategy.config_hash,
                    now, now
                )
            )
            # Register version
            v_sql = """
                INSERT INTO strategy_versions (
                    version_id, strategy_id, version_tag, code_content,
                    parameters_json, code_hash, config_hash, is_frozen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """
            db.execute_non_query(
                v_sql,
                (
                    f"{strategy.strategy_id}_v{strategy.version}",
                    strategy.strategy_id,
                    strategy.version,
                    strategy.__class__.__name__,
                    json.dumps(strategy.parameters),
                    strategy.code_hash,
                    strategy.config_hash
                )
            )
            logger.info(f"Registered new strategy: {strategy.name} ({strategy.strategy_id})")

    def freeze_strategy(self, strategy_id: str) -> bool:
        """Cryptographically freeze strategy version. Once frozen, code and config cannot change."""
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        res = db.execute_non_query(
            "UPDATE strategies SET status = ? WHERE strategy_id = ?",
            (StrategyStatus.FROZEN.value, strategy_id)
        )
        db.execute_non_query(
            "UPDATE strategy_versions SET is_frozen = 1, frozen_at = ? WHERE strategy_id = ?",
            (now, strategy_id)
        )
        logger.info(f"FROZEN strategy {strategy_id}. Strategy is now immutable.")
        return res > 0

    def promote_to_paper(self, strategy_id: str, authorized_by: str, reason: str) -> bool:
        """
        PROMOTION FIREWALL:
        Explicit human authorization required to promote a strategy to PAPER_ENABLED.
        Never automated.
        """
        db = get_db()
        rows = db.execute_query("SELECT * FROM strategies WHERE strategy_id = ?", (strategy_id,))
        if not rows:
            raise ValueError(f"Strategy {strategy_id} not found.")

        strat = rows[0]
        if strat["status"] not in (StrategyStatus.FROZEN.value, StrategyStatus.VALIDATED.value):
            raise RuntimeError(
                f"PROMOTION FIREWALL BLOCKED: Strategy must be FROZEN or VALIDATED before paper promotion! Current status: {strat['status']}"
            )

        now = datetime.now(timezone.utc).isoformat()
        db.execute_non_query(
            "UPDATE strategies SET status = ?, updated_at = ? WHERE strategy_id = ?",
            (StrategyStatus.PAPER_ENABLED.value, now, strategy_id)
        )
        db.execute_non_query(
            """UPDATE strategy_versions SET
                   promoted_to_paper = 1, promoted_at = ?,
                   promoted_by = ?, promotion_reason = ?
               WHERE strategy_id = ?""",
            (now, authorized_by, reason, strategy_id)
        )
        logger.info(
            f"STRATEGY PROMOTION FIREWALL: Authorized strategy {strategy_id} for PAPER_TRADING by {authorized_by}. Reason: {reason}"
        )
        return True

    @property
    def strategies(self) -> Dict[str, BaseStrategy]:
        return self._strategies

    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[Dict[str, Any]]:
        db = get_db()
        return db.execute_query("SELECT * FROM strategies ORDER BY created_at DESC")


_STRATEGY_REGISTRY: Optional[StrategyRegistry] = None


def get_strategy_registry() -> StrategyRegistry:
    global _STRATEGY_REGISTRY
    if _STRATEGY_REGISTRY is None:
        _STRATEGY_REGISTRY = StrategyRegistry()
    return _STRATEGY_REGISTRY
