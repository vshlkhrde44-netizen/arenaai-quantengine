"""
Antigravity QuantEngine - Alpaca Paper Exchange Connector
Provides official paper execution via Alpaca Paper API (https://paper-api.alpaca.markets/v2).
Live trading endpoints are strictly prohibited and hard-blocked.
"""

import json
from typing import Dict, Any, List, Optional
import aiohttp

from connectors.exchanges.base import (
    ExchangeAdapter, MarketDataAdapter, PaperExecutionAdapter, AccountAdapter, CapabilityDescriptor
)
from core.domain.models import OrderRecord, PositionRecord, OrderStatus
from core.security.credentials import get_credential_vault
from core.logging import get_logger

logger = get_logger("connector.alpaca")

ALPACA_PAPER_REST = "https://paper-api.alpaca.markets/v2"


class AlpacaPaperExecutionAdapter(PaperExecutionAdapter):
    """Executes paper orders exclusively on Alpaca Paper Trading REST API."""

    def __init__(self, paper_url: str = ALPACA_PAPER_REST):
        # Strict endpoint verification
        if "paper-api.alpaca.markets" not in paper_url:
            raise RuntimeError(f"FATAL SAFETY FIREWALL: Prohibited Alpaca URL '{paper_url}'. Must use paper-api!")
        self.paper_url = paper_url

    def _get_headers(self) -> Dict[str, str]:
        vault = get_credential_vault()
        creds = vault.get_credentials("alpaca")
        if not creds:
            return {"Content-Type": "application/json", "User-Agent": "AntigravityQuantEngine/1.0"}
        return {
            "APCA-API-KEY-ID": creds.get("api_key", ""),
            "APCA-API-SECRET-KEY": creds.get("api_secret", ""),
            "Content-Type": "application/json",
            "User-Agent": "AntigravityQuantEngine/1.0"
        }

    async def submit_paper_order(self, order: OrderRecord) -> Dict[str, Any]:
        if "paper-api" not in self.paper_url:
            raise RuntimeError("CRITICAL SAFETY FIREWALL: Attempted to submit order to non-paper Alpaca URL!")

        url = f"{self.paper_url}/orders"
        payload = {
            "symbol": order.symbol.replace("-", ""),
            "qty": str(order.quantity),
            "side": order.side.value.lower(),
            "type": order.order_type.value.lower(),
            "time_in_force": order.time_in_force.value.lower(),
            "client_order_id": order.client_order_id
        }
        if order.order_type.value == "LIMIT" and order.price is not None:
            payload["limit_price"] = str(order.price)

        headers = self._get_headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    resp_json = await resp.json()
                    return {
                        "status_code": resp.status,
                        "success": resp.status in (200, 201),
                        "venue_order_id": resp_json.get("id"),
                        "response": resp_json
                    }
            except Exception as e:
                logger.error(f"Alpaca paper order submit error: {e}")
                return {"status_code": 0, "success": False, "error": str(e)}

    async def cancel_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        url = f"{self.paper_url}/orders/{order_id}"
        headers = self._get_headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    return {"status_code": resp.status, "success": resp.status in (200, 204)}
            except Exception as e:
                return {"status_code": 0, "success": False, "error": str(e)}

    async def query_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        url = f"{self.paper_url}/orders/{order_id}"
        headers = self._get_headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    data = await resp.json()
                    return {"status_code": resp.status, "data": data}
            except Exception as e:
                return {"status_code": 0, "error": str(e)}


class AlpacaAccountAdapter(AccountAdapter):
    """Fetches paper account balances and positions from Alpaca Paper API."""

    def __init__(self, paper_url: str = ALPACA_PAPER_REST):
        self.paper_url = paper_url

    async def fetch_paper_balances(self) -> Dict[str, float]:
        url = f"{self.paper_url}/account"
        headers = AlpacaPaperExecutionAdapter(self.paper_url)._get_headers()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    if resp.status == 200:
                        acc = await resp.json()
                        return {
                            "USD": float(acc.get("cash", 0.0)),
                            "equity": float(acc.get("equity", 0.0)),
                            "buying_power": float(acc.get("buying_power", 0.0))
                        }
                    return {}
            except Exception:
                return {}

    async def fetch_paper_positions(self) -> List[PositionRecord]:
        return []


class AlpacaExchangeAdapter(ExchangeAdapter):
    def __init__(self):
        caps = CapabilityDescriptor(
            venue_name="alpaca",
            is_paper_only=True,
            supports_live_orders=False,
            supports_live_market_data=False, # Use Coinbase / Kraken for crypto feeds
            supports_paper_orders=True,
            supports_testnet=True,
            supports_orderbook=False,
            supports_trades=False,
            supports_ticker=False,
            supports_candles=False,
            supports_account_data=True,
            supports_native_trade_id=True,
            supports_sequence_numbers=False,
            paper_rest_url=ALPACA_PAPER_REST,
            live_market_ws_url="unavailable"
        )
        super().__init__(caps)
        self._execution = AlpacaPaperExecutionAdapter(ALPACA_PAPER_REST)
        self._account = AlpacaAccountAdapter(ALPACA_PAPER_REST)

    @property
    def market_data(self) -> MarketDataAdapter:
        raise NotImplementedError("Alpaca market data adapter disabled; use primary Coinbase feed.")

    @property
    def execution(self) -> PaperExecutionAdapter:
        return self._execution

    @property
    def account(self) -> AccountAdapter:
        return self._account
