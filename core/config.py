"""
Antigravity QuantEngine - System Configuration & Invariants
Enforces strict safety invariants: Paper Trading Only, No Live Orders.
"""

import os
from enum import Enum
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field, model_validator


class RuntimeMode(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    RESEARCH = "RESEARCH"
    DATA_CAPTURE = "DATA_CAPTURE"
    PAPER_TRADING = "PAPER_TRADING"
    # NOTE: LIVE_TRADING and PRODUCTION_TRADING are strictly prohibited and not present in this enum.


class SystemSettings(BaseModel):
    app_name: str = "Antigravity QuantEngine"
    version: str = "1.0.0"
    runtime_mode: RuntimeMode = RuntimeMode.PAPER_TRADING
    paper_only: bool = True
    live_orders_enabled: bool = False
    is_production_ready: bool = False
    host: str = Field(default_factory=lambda: os.environ.get("QUANTENGINE_HOST", "127.0.0.1"))
    port: int = 8000
    log_level: str = "INFO"

    @model_validator(mode="after")
    def verify_safety_invariants(self) -> "SystemSettings":
        if not self.paper_only:
            raise ValueError("FATAL SAFETY INVARIANT VIOLATION: paper_only must be True. Live trading prohibited.")
        if self.live_orders_enabled:
            raise ValueError("FATAL SAFETY INVARIANT VIOLATION: live_orders_enabled must be False.")
        if self.is_production_ready:
            raise ValueError("FATAL SAFETY INVARIANT VIOLATION: is_production_ready must be False.")
        return self


class SecuritySettings(BaseModel):
    credential_storage: str = "ENCRYPTED_VAULT"
    vault_path: Path = Path("data/vault/credentials.enc")
    mask_secrets_in_logs: bool = True
    allow_remote_access: bool = False
    operator_session_token_required: bool = True


class DatabaseSettings(BaseModel):
    sqlite_path: Path = Path("data/quantengine.db")
    duckdb_path: Path = Path("data/analytics.duckdb")
    raw_data_dir: Path = Path("data/raw")
    datasets_dir: Path = Path("data/datasets")
    reports_dir: Path = Path("data/reports")
    manifests_dir: Path = Path("data/manifests")


class MarketDataSettings(BaseModel):
    default_exchange: str = "coinbase"
    auto_connect_on_startup: bool = False # Section 61: Boot disconnected until explicit user setup
    default_symbols: List[str] = ["BTC-USD", "ETH-USD", "SOL-USD"]
    queue_max_size: int = 50000
    tamper_chain_enabled: bool = True
    stale_data_threshold_seconds: float = 5.0
    reconnect_delay_seconds: float = 2.0
    max_reconnect_attempts: int = 10


class RiskSettings(BaseModel):
    max_position_size_usd: float = 50000.0
    max_order_notional_usd: float = 10000.0
    max_daily_loss_usd: float = 2500.0
    max_portfolio_exposure_usd: float = 100000.0
    max_concurrent_positions: int = 5
    cooldown_period_seconds: int = 30
    stop_loss_default_pct: float = 0.02
    emergency_stop_active: bool = False
    fail_closed_on_unknown_risk: bool = True


class PaperExecutionSettings(BaseModel):
    venue: str = "coinbase_sandbox"
    paper_endpoint: str = "https://api-public.sandbox.exchange.coinbase.com"
    paper_ws_endpoint: str = "wss://ws-feed.exchange.coinbase.com"
    reconciliation_interval_seconds: int = 15
    auto_cancel_on_disconnect: bool = True
    approved_endpoints: List[str] = [
        "https://api-public.sandbox.exchange.coinbase.com",
        "https://paper-api.alpaca.markets"
    ]


class AppConfig(BaseModel):
    system: SystemSettings = Field(default_factory=SystemSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    market_data: MarketDataSettings = Field(default_factory=MarketDataSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    paper_execution: PaperExecutionSettings = Field(default_factory=PaperExecutionSettings)

    @classmethod
    def load_from_yaml(cls, path: str = "configs/default_config.yaml") -> "AppConfig":
        file_path = Path(path)
        if not file_path.exists():
            return cls()
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)


# Global singleton instance
_GLOBAL_CONFIG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = AppConfig.load_from_yaml()
    return _GLOBAL_CONFIG


def reset_config(cfg: AppConfig) -> None:
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = cfg
