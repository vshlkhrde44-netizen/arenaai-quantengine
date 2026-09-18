"""
Antigravity QuantEngine - Domain Models & Data Structures
Strict type-safe schemas enforcing quantitative rigor, provenance tracking,
and paper-only trading semantics.
"""

import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    SAFETY_CHECK = "SAFETY_CHECK"
    SUBMITTING = "SUBMITTING"
    SUBMISSION_UNCONFIRMED = "SUBMISSION_UNCONFIRMED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ReportStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT = "INSUFFICIENT"
    LOCKED = "LOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_RUN = "NOT_RUN"


class StrategyStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    PAPER_ENABLED = "PAPER_ENABLED"
    DEPRECATED = "DEPRECATED"


class DataQualityStatus(str, Enum):
    VALID = "VALID"
    GAPS_DETECTED = "GAPS_DETECTED"
    DISORDER_DETECTED = "DISORDER_DETECTED"
    DUPLICATES_DETECTED = "DUPLICATES_DETECTED"
    CORRUPTED = "CORRUPTED"


class DataClassification(str, Enum):
    REAL_EXCHANGE = "REAL_EXCHANGE"
    HISTORICAL_PROVIDER = "HISTORICAL_PROVIDER"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"
    SIMULATED_RESEARCH = "SIMULATED_RESEARCH"
    UNKNOWN = "UNKNOWN"


class MicrostructureSemantic(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class TradeRecord(BaseModel):
    trade_id: str
    venue_trade_id: Optional[str] = None
    symbol: str
    venue: str = "coinbase"
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    side: str # "BUY" or "SELL"
    data_class: DataClassification = DataClassification.REAL_EXCHANGE
    semantic: MicrostructureSemantic = MicrostructureSemantic.OBSERVED
    venue_timestamp: Optional[datetime] = None
    receipt_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    monotonic_timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1_000_000))
    sequence_number: Optional[int] = None

    @property
    def timestamp(self) -> datetime:
        return self.receipt_timestamp


class TickerRecord(BaseModel):
    symbol: str
    venue: str = "coinbase"
    bid_price: Optional[float] = Field(default=None, gt=0)
    ask_price: Optional[float] = Field(default=None, gt=0)
    bid_quantity: Optional[float] = Field(default=None, ge=0)
    ask_quantity: Optional[float] = Field(default=None, ge=0)
    last_price: Optional[float] = Field(default=None, gt=0)
    spread: Optional[float] = None
    data_class: DataClassification = DataClassification.REAL_EXCHANGE
    venue_timestamp: Optional[datetime] = None
    receipt_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    monotonic_timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1_000_000))
    sequence_number: Optional[int] = None

    @property
    def timestamp(self) -> datetime:
        return self.receipt_timestamp


class OrderBookLevel(BaseModel):
    price: float = Field(gt=0)
    quantity: float = Field(ge=0)


class OrderBookRecord(BaseModel):
    symbol: str
    venue: str = "coinbase"
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    book_imbalance: Optional[float] = None
    data_class: DataClassification = DataClassification.REAL_EXCHANGE
    venue_timestamp: Optional[datetime] = None
    receipt_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    monotonic_timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1_000_000))
    sequence_number: Optional[int] = None


class CandleRecord(BaseModel):
    symbol: str
    venue: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    buyer_volume: Optional[float] = None
    seller_volume: Optional[float] = None
    delta: Optional[float] = None
    data_class: DataClassification = DataClassification.HISTORICAL_PROVIDER


class MicrostructureSnapshot(BaseModel):
    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_price: float
    delta: float
    cvd: float
    trade_imbalance_ratio: Optional[float] = None
    absorption_detected: bool = False
    poc_price: Optional[float] = None
    vah_price: Optional[float] = None
    val_price: Optional[float] = None
    spread: Optional[float] = None
    book_imbalance: Optional[float] = None
    semantic: MicrostructureSemantic = MicrostructureSemantic.DERIVED


class OrderRecord(BaseModel):
    order_id: str
    local_request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
    client_order_id: str
    exchange_order_id: Optional[str] = None
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    strategy_hash: Optional[str] = None
    symbol: str
    venue: str = "coinbase"
    order_type: OrderType
    side: OrderSide
    quantity: float = Field(gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    status: OrderStatus = OrderStatus.CREATED
    filled_quantity: float = Field(default=0.0, ge=0)
    remaining_quantity: float = Field(default=0.0, ge=0)
    average_fill_price: Optional[float] = None
    fee_total: float = Field(default=0.0, ge=0)
    cumulative_fees: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status_reason: Optional[str] = None
    safety_gate_passed: bool = False
    safety_gate_reason: Optional[str] = None
    raw_venue_response: Optional[str] = None
    is_paper: bool = Field(default=True, frozen=True)


class FillRecord(BaseModel):
    fill_id: str
    order_id: str
    exchange_order_id: Optional[str] = None
    exchange_fill_id: Optional[str] = None
    symbol: str
    side: OrderSide
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = Field(default=0.0, ge=0)
    fee_asset: str = "USD"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_paper: bool = Field(default=True, frozen=True)


class PositionRecord(BaseModel):
    position_id: str = Field(default_factory=lambda: f"pos_{uuid.uuid4().hex[:8]}")
    symbol: str
    venue: str = "coinbase"
    side: PositionSide = PositionSide.FLAT
    quantity: float = Field(default=0.0, ge=0)
    entry_price: float = Field(default=0.0, ge=0)
    average_entry_price: float = Field(default=0.0, ge=0)
    current_price: float = Field(default=0.0, ge=0)
    current_market_price: float = Field(default=0.0, ge=0)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    cumulative_fees: float = 0.0
    status: PositionStatus = PositionStatus.CLOSED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
