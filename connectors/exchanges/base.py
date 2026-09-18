"""
Antigravity QuantEngine - Exchange Connector Base Architecture
Defines strict interfaces, capability descriptors, and safety boundaries for all exchange integrations.
Enforces non-optimistic capability declarations (P0-21, Section 46).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pydantic import BaseModel, Field
from core.domain.models import (
    TradeRecord, TickerRecord, OrderBookRecord, OrderRecord, FillRecord, PositionRecord
)


class CapabilityDescriptor(BaseModel):
    """
    Explicit declaration of exchange capabilities and safety invariants.
    All capability flags default strictly to FALSE (P0-21).
    """
    venue_name: str
    is_paper_only: bool = True
    is_mock: bool = False # Section 70: Mock firewall indicator
    supports_live_orders: bool = Field(default=False, frozen=True) # HARD CODED FALSE
    supports_live_market_data: bool = False
    supports_paper_orders: bool = False
    supports_testnet: bool = False
    supports_orderbook: bool = False
    supports_trades: bool = False
    supports_ticker: bool = False
    supports_candles: bool = False
    supports_account_data: bool = False
    supports_native_trade_id: bool = False
    supports_sequence_numbers: bool = False
    paper_rest_url: str
    paper_ws_url: Optional[str] = None
    live_market_ws_url: str

    def verify_safety(self) -> None:
        if self.supports_live_orders:
            raise RuntimeError(f"FATAL SECURITY VIOLATION: {self.venue_name} has live order capability enabled!")
        if not self.is_paper_only:
            raise RuntimeError(f"FATAL SECURITY VIOLATION: {self.venue_name} is not paper_only!")


class MarketDataAdapter(ABC):
    """Handles real-time public exchange market data feeds."""

    @abstractmethod
    async def connect_market_data(
        self,
        symbols: List[str],
        on_trade: Callable[[TradeRecord, str], Awaitable[None]],
        on_ticker: Callable[[TickerRecord, str], Awaitable[None]],
        on_book: Optional[Callable[[OrderBookRecord, str], Awaitable[None]]] = None
    ) -> None:
        pass

    @abstractmethod
    async def disconnect_market_data(self) -> None:
        pass

    @abstractmethod
    def is_market_data_connected(self) -> bool:
        pass


class PaperExecutionAdapter(ABC):
    """Handles order routing to official sandbox/paper-trading API."""

    @abstractmethod
    async def submit_paper_order(self, order: OrderRecord) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def query_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        pass


class AccountAdapter(ABC):
    """Fetches balances and positions from exchange paper account."""

    @abstractmethod
    async def fetch_paper_balances(self) -> Optional[Dict[str, float]]:
        pass

    @abstractmethod
    async def fetch_paper_positions(self) -> Optional[List[PositionRecord]]:
        pass


class ExchangeAdapter(ABC):
    """Top-level composite exchange adapter."""

    def __init__(self, capabilities: CapabilityDescriptor):
        self.capabilities = capabilities
        self.capabilities.verify_safety()

    @property
    @abstractmethod
    def market_data(self) -> MarketDataAdapter:
        pass

    @property
    @abstractmethod
    def execution(self) -> PaperExecutionAdapter:
        pass

    @property
    @abstractmethod
    def account(self) -> AccountAdapter:
        pass
