"""
Antigravity QuantEngine - CI Mock Exchange Adapter
Strictly quarantined in tests/fixtures for API state machine verification (Section 69, 70).
Impossible to register or execute in PAPER_TRADING runtime.
"""

import uuid
from typing import Dict, Any, List, Optional
from connectors.exchanges.base import (
    ExchangeAdapter, CapabilityDescriptor, MarketDataAdapter,
    PaperExecutionAdapter, AccountAdapter
)
from core.domain.models import OrderRecord, PositionRecord


class MockExecutionAdapter(PaperExecutionAdapter):
    async def submit_paper_order(self, order: OrderRecord) -> Dict[str, Any]:
        venue_id = f"mock_oid_{uuid.uuid4().hex[:8]}"
        fill_price = order.price if order.price else 60000.0
        return {
            "success": True,
            "status_code": 200,
            "venue_order_id": venue_id,
            "venue_fill_id": f"mock_fid_{uuid.uuid4().hex[:6]}",
            "filled": True,
            "status": "done",
            "fill_price": fill_price,
            "fill_qty": order.quantity,
            "fill_fee": round(order.quantity * fill_price * 0.0005, 4)
        }

    async def cancel_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        return {"success": True, "status": "cancelled"}

    async def query_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        return {"success": True, "status": "done"}


class MockAccountAdapter(AccountAdapter):
    async def fetch_paper_balances(self) -> Optional[Dict[str, float]]:
        return {"USD": 100000.0, "BTC": 0.05}

    async def fetch_paper_positions(self) -> Optional[List[PositionRecord]]:
        return []


class MockExchangeAdapter(ExchangeAdapter):
    """Controlled exchange mock strictly for CI testing of state machines (Section 69)."""

    def __init__(self):
        caps = CapabilityDescriptor(
            venue_name="mock_exchange",
            is_paper_only=True,
            is_mock=True,
            supports_live_orders=False,
            supports_paper_orders=True,
            supports_live_market_data=True,
            paper_rest_url="https://api-public.sandbox.exchange.coinbase.com",
            live_market_ws_url="wss://ws-feed.exchange.coinbase.com"
        )
        super().__init__(caps)
        self._execution = MockExecutionAdapter()
        self._account = MockAccountAdapter()

    @property
    def market_data(self) -> MarketDataAdapter:
        raise NotImplementedError("Use primary Coinbase feed for market data.")

    @property
    def execution(self) -> PaperExecutionAdapter:
        return self._execution

    @property
    def account(self) -> AccountAdapter:
        return self._account
