"""
Antigravity QuantEngine - Coinbase Official Exchange Connector
Provides real-time public market data via Coinbase WebSocket
and paper trading execution via Coinbase Exchange Sandbox REST API.
"""

import asyncio
import json
import base64
import hmac
import hashlib
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
import aiohttp
import websockets

from connectors.exchanges.base import (
    ExchangeAdapter, MarketDataAdapter, PaperExecutionAdapter, AccountAdapter, CapabilityDescriptor
)
from core.domain.models import (
    TradeRecord, TickerRecord, OrderBookRecord, OrderRecord, PositionRecord, OrderStatus, OrderSide
)
from core.marketdata.normalizer import MarketDataNormalizer
from core.security.credentials import get_credential_vault
from core.logging import get_logger

logger = get_logger("connector.coinbase")


COINBASE_PUBLIC_WS = "wss://ws-feed.exchange.coinbase.com"
COINBASE_SANDBOX_REST = "https://api-public.sandbox.exchange.coinbase.com"


class CoinbaseMarketDataAdapter(MarketDataAdapter):
    """Ingests live market data from Coinbase Exchange."""

    def __init__(self):
        self._ws = None
        self._running = False
        self._connected = False
        self._task: Optional[asyncio.Task] = None

    def is_market_data_connected(self) -> bool:
        return self._connected and self._running

    async def connect_market_data(
        self,
        symbols: List[str],
        on_trade: Callable[[TradeRecord, str], Awaitable[None]],
        on_ticker: Callable[[TickerRecord, str], Awaitable[None]],
        on_book: Optional[Callable[[OrderBookRecord, str], Awaitable[None]]] = None
    ) -> None:
        if self._running:
            await self.disconnect_market_data()

        self._running = True
        self._task = asyncio.create_task(
            self._ws_loop(symbols, on_trade, on_ticker, on_book)
        )

    async def disconnect_market_data(self) -> None:
        self._running = False
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        logger.info("Coinbase market data disconnected.")

    async def _ws_loop(
        self,
        symbols: List[str],
        on_trade: Callable[[TradeRecord, str], Awaitable[None]],
        on_ticker: Callable[[TickerRecord, str], Awaitable[None]],
        on_book: Optional[Callable[[OrderBookRecord, str], Awaitable[None]]]
    ) -> None:
        retry_delay = 2.0
        while self._running:
            try:
                logger.info(f"Connecting to Coinbase live WS ({COINBASE_PUBLIC_WS}) for {symbols}...")
                async with websockets.connect(
                    COINBASE_PUBLIC_WS,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=10_000_000
                ) as ws:
                    self._ws = ws
                    self._connected = True
                    retry_delay = 2.0
                    
                    # Subscribe to real channels
                    sub_message = {
                        "type": "subscribe",
                        "product_ids": symbols,
                        "channels": ["ticker", "matches"]
                    }
                    await ws.send(json.dumps(sub_message))
                    logger.info(f"Subscribed to Coinbase channels: {sub_message['channels']}")

                    book_bids: Dict[str, Dict[float, float]] = {s: {} for s in symbols}
                    book_asks: Dict[str, Dict[float, float]] = {s: {} for s in symbols}

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw_msg)
                            msg_type = msg.get("type")

                            if msg_type in ("match", "last_match"):
                                trade = MarketDataNormalizer.normalize_coinbase_trade(msg)
                                if trade:
                                    await on_trade(trade, raw_msg)

                            elif msg_type == "ticker":
                                ticker = MarketDataNormalizer.normalize_coinbase_ticker(msg)
                                if ticker:
                                    await on_ticker(ticker, raw_msg)

                            elif msg_type == "snapshot" and on_book:
                                prod = msg.get("product_id")
                                if prod in book_bids:
                                    book_bids[prod] = {float(b[0]): float(b[1]) for b in msg.get("bids", [])}
                                    book_asks[prod] = {float(a[0]): float(a[1]) for a in msg.get("asks", [])}
                                    book_rec = MarketDataNormalizer.normalize_l2_book(
                                        prod, "coinbase",
                                        [[p, q] for p, q in book_bids[prod].items()],
                                        [[p, q] for p, q in book_asks[prod].items()]
                                    )
                                    await on_book(book_rec, raw_msg)

                            elif msg_type == "l2update" and on_book:
                                prod = msg.get("product_id")
                                if prod in book_bids:
                                    for side, price_str, size_str in msg.get("changes", []):
                                        p = float(price_str)
                                        q = float(size_str)
                                        target = book_bids[prod] if side == "buy" else book_asks[prod]
                                        if q == 0.0:
                                            target.pop(p, None)
                                        else:
                                            target[p] = q
                                    book_rec = MarketDataNormalizer.normalize_l2_book(
                                        prod, "coinbase",
                                        [[p, q] for p, q in book_bids[prod].items()],
                                        [[p, q] for p, q in book_asks[prod].items()]
                                    )
                                    await on_book(book_rec, raw_msg)

                        except Exception as parse_err:
                            logger.error(f"Error processing Coinbase WS message: {parse_err}")

            except asyncio.CancelledError:
                self._connected = False
                break
            except (websockets.ConnectionClosed, Exception) as e:
                self._connected = False
                if not self._running:
                    break
                logger.warning(f"Coinbase WS disconnected: {e}. Reconnecting in {retry_delay:.1f}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 30.0)


class CoinbasePaperExecutionAdapter(PaperExecutionAdapter):
    """Executes paper orders on the Coinbase Exchange Sandbox REST API."""

    def __init__(self, sandbox_url: str = COINBASE_SANDBOX_REST):
        # Strict validation of endpoint
        if "sandbox" not in sandbox_url:
            raise RuntimeError(
                f"FATAL SAFETY FIREWALL: Attempted to initialize Coinbase execution with non-sandbox URL: {sandbox_url}"
            )
        self.sandbox_url = sandbox_url

    def _sign_request(self, method: str, request_path: str, body: str = "", timestamp: Optional[str] = None) -> Dict[str, str]:
        """Sign request for Coinbase Sandbox REST."""
        vault = get_credential_vault()
        creds = vault.get_credentials("coinbase")
        if not creds:
            # When testing without credentials, return headers without auth
            return {"Content-Type": "application/json", "User-Agent": "AntigravityQuantEngine/1.0"}

        api_key = creds.get("api_key", "")
        api_secret = creds.get("api_secret", "")
        passphrase = creds.get("passphrase", "")

        ts = timestamp or str(time.time())
        message = ts + method.upper() + request_path + body
        
        try:
            hmac_key = base64.b64decode(api_secret)
            signature = hmac.new(hmac_key, message.encode("utf-8"), hashlib.sha256)
            signature_b64 = base64.b64encode(signature.digest()).decode("utf-8")
        except Exception:
            signature_b64 = ""

        return {
            "CB-ACCESS-KEY": api_key,
            "CB-ACCESS-SIGN": signature_b64,
            "CB-ACCESS-TIMESTAMP": ts,
            "CB-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
            "User-Agent": "AntigravityQuantEngine/1.0"
        }

    async def submit_paper_order(self, order: OrderRecord) -> Dict[str, Any]:
        """Submit paper order to Coinbase Sandbox REST endpoint."""
        # Absolute safety check
        if "sandbox" not in self.sandbox_url:
            raise RuntimeError("CRITICAL SAFETY BLOCK: Refusing order submission to non-sandbox endpoint!")

        path = "/orders"
        url = f"{self.sandbox_url}{path}"
        
        payload: Dict[str, Any] = {
            "client_oid": order.client_order_id,
            "product_id": order.symbol,
            "side": order.side.value.lower(),
            "type": order.order_type.value.lower()
        }

        if order.order_type.value == "MARKET":
            payload["size"] = str(order.quantity)
        elif order.order_type.value == "LIMIT":
            payload["size"] = str(order.quantity)
            payload["price"] = str(order.price)
            payload["time_in_force"] = order.time_in_force.value

        body = json.dumps(payload)
        headers = self._sign_request("POST", path, body)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=body, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    resp_text = await resp.text()
                    resp_data = {}
                    try:
                        resp_data = json.loads(resp_text)
                    except Exception:
                        resp_data = {"raw": resp_text}

                    return {
                        "status_code": resp.status,
                        "success": resp.status in (200, 201),
                        "venue_order_id": resp_data.get("id"),
                        "response": resp_data
                    }
            except Exception as e:
                logger.error(f"Sandbox paper order POST failed: {e}")
                return {"status_code": 0, "success": False, "error": str(e)}

    async def cancel_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel paper order on Coinbase Sandbox."""
        path = f"/orders/{order_id}"
        url = f"{self.sandbox_url}{path}"
        headers = self._sign_request("DELETE", path)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    resp_text = await resp.text()
                    return {"status_code": resp.status, "success": resp.status in (200, 204), "raw": resp_text}
            except Exception as e:
                logger.error(f"Sandbox paper order cancel failed: {e}")
                return {"status_code": 0, "success": False, "error": str(e)}

    async def query_paper_order(self, order_id: str, client_order_id: str, symbol: str) -> Dict[str, Any]:
        path = f"/orders/{order_id}"
        url = f"{self.sandbox_url}{path}"
        headers = self._sign_request("GET", path)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    data = await resp.json()
                    return {"status_code": resp.status, "data": data}
            except Exception as e:
                return {"status_code": 0, "error": str(e)}


class CoinbaseAccountAdapter(AccountAdapter):
    """Fetches paper account balances and positions from Coinbase Sandbox."""

    def __init__(self, sandbox_url: str = COINBASE_SANDBOX_REST):
        self.sandbox_url = sandbox_url

    async def fetch_paper_balances(self) -> Dict[str, float]:
        path = "/accounts"
        url = f"{self.sandbox_url}{path}"
        vault = get_credential_vault()
        creds = vault.get_credentials("coinbase")
        if not creds:
            return {}

        headers = CoinbasePaperExecutionAdapter(self.sandbox_url)._sign_request("GET", path)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                    if resp.status == 200:
                        accounts = await resp.json()
                        return {acc["currency"]: float(acc.get("balance", 0.0)) for acc in accounts}
                    return {}
            except Exception:
                return {}

    async def fetch_paper_positions(self) -> List[PositionRecord]:
        return []


class CoinbaseExchangeAdapter(ExchangeAdapter):
    """Full Coinbase adapter combining live market data and sandbox paper execution."""

    def __init__(self):
        caps = CapabilityDescriptor(
            venue_name="coinbase",
            is_paper_only=True,
            supports_live_orders=False,
            supports_live_market_data=True,
            supports_paper_orders=True,
            supports_testnet=True,
            supports_orderbook=False,
            supports_trades=True,
            supports_ticker=True,
            supports_candles=True,
            supports_account_data=True,
            supports_native_trade_id=True,
            supports_sequence_numbers=True,
            paper_rest_url=COINBASE_SANDBOX_REST,
            paper_ws_url=COINBASE_PUBLIC_WS,
            live_market_ws_url=COINBASE_PUBLIC_WS
        )
        super().__init__(caps)
        self._market_data = CoinbaseMarketDataAdapter()
        self._execution = CoinbasePaperExecutionAdapter(COINBASE_SANDBOX_REST)
        self._account = CoinbaseAccountAdapter(COINBASE_SANDBOX_REST)

    @property
    def market_data(self) -> MarketDataAdapter:
        return self._market_data

    @property
    def execution(self) -> PaperExecutionAdapter:
        return self._execution

    @property
    def account(self) -> AccountAdapter:
        return self._account
