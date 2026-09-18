"""
Antigravity QuantEngine - Domain Events
Typed event classes with correlation IDs and strict immutability.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str


class MarketDataReceivedEvent(BaseEvent):
    event_type: str = "MARKET_DATA_RECEIVED"
    venue: str
    symbol: str
    channel: str
    payload: Dict[str, Any]


class OrderRequestedEvent(BaseEvent):
    event_type: str = "ORDER_REQUESTED"
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float] = None
    order_type: str


class OrderSafetyEvaluatedEvent(BaseEvent):
    event_type: str = "ORDER_SAFETY_EVALUATED"
    order_id: str
    passed: bool
    reason: str
    checks_performed: Dict[str, bool]


class OrderSubmittedEvent(BaseEvent):
    event_type: str = "ORDER_SUBMITTED"
    order_id: str
    client_order_id: str
    venue: str
    paper_endpoint: str


class OrderAcknowledgedEvent(BaseEvent):
    event_type: str = "ORDER_ACKNOWLEDGED"
    order_id: str
    exchange_order_id: str
    status: str


class OrderFilledEvent(BaseEvent):
    event_type: str = "ORDER_FILLED"
    order_id: str
    fill_id: str
    symbol: str
    side: str
    fill_quantity: float
    fill_price: float
    fee: float


class OrderCancelledEvent(BaseEvent):
    event_type: str = "ORDER_CANCELLED"
    order_id: str
    reason: str


class RiskBreachEvent(BaseEvent):
    event_type: str = "RISK_BREACH"
    rule_name: str
    severity: str
    metric_value: float
    threshold_value: float
    details: Dict[str, Any]


class DisconnectEvent(BaseEvent):
    event_type: str = "DISCONNECT"
    venue: str
    session_id: str
    reason: str
    gap_detected: bool


class TamperAlertEvent(BaseEvent):
    event_type: str = "TAMPER_ALERT"
    component: str
    target: str
    expected_hash: str
    actual_hash: str
    details: str
