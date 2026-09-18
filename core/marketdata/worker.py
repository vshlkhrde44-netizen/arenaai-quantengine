"""
Antigravity QuantEngine - Real-Time Market Data Ingestion Worker
Connects real exchange public WebSockets, manages tamper-evident raw preservation,
computes microstructure analytics, and routes live streams to the UI.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from core.config import get_config
from core.domain.models import (
    TradeRecord, TickerRecord, OrderBookRecord, MicrostructureSnapshot
)
from core.marketdata.tamper_chain import TamperEvidentRawWriter
from core.marketdata.queue import BoundedMarketDataQueue
from core.marketdata.session import MarketDataSession
from core.analytics.microstructure import MicrostructureEngine
from core.portfolio.portfolio_engine import get_portfolio_engine
from connectors.registry import get_connector_registry
from core.events.bus import get_event_bus
from core.events.events import MarketDataReceivedEvent, DisconnectEvent
from core.logging import get_logger

logger = get_logger("marketdata.worker")


class FeedHealthStatus(BaseModel):
    venue: str
    is_connected: bool
    active_symbols: List[str]
    session_id: str
    records_received: int
    queue_depth: int
    queue_utilization_pct: float
    last_trade_time: Optional[str]
    feed_latency_ms: Optional[float]
    reconnect_count: int


class MarketDataWorker:
    """Orchestrates live market data streams and feeds analytics subsystems."""

    def __init__(self):
        self.cfg = get_config()
        self.symbols = list(self.cfg.market_data.default_symbols)
        self.venue = self.cfg.market_data.default_exchange
        self.session: Optional[MarketDataSession] = None
        self.raw_writer: Optional[TamperEvidentRawWriter] = None
        self.queue = BoundedMarketDataQueue(maxsize=self.cfg.market_data.queue_max_size)
        self.microstructure_engines: Dict[str, MicrostructureEngine] = {
            sym: MicrostructureEngine(sym, tick_size=5.0 if "BTC" in sym else 0.5)
            for sym in self.symbols
        }

        # Latest state cache for instant REST query by UI
        self.latest_tickers: Dict[str, TickerRecord] = {}
        self.latest_trades: Dict[str, List[TradeRecord]] = {sym: [] for sym in self.symbols}
        self.latest_snapshots: Dict[str, MicrostructureSnapshot] = {}
        self.latest_orderbooks: Dict[str, OrderBookRecord] = {}

        self.last_trade_dt: Optional[datetime] = None
        self.reconnect_count = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize session, tamper chain, and start market data ingestion."""
        if self._running:
            return

        self._running = True
        self.session = MarketDataSession(self.venue, ",".join(self.symbols))
        self.raw_writer = TamperEvidentRawWriter(self.session.session_id)
        logger.info(f"Starting MarketDataWorker for {self.symbols} on venue {self.venue}...")

        registry = get_connector_registry()
        connector = registry.get(self.venue)
        if not connector:
            logger.error(f"Exchange connector {self.venue} not found!")
            return

        # Start ingestion loop
        await connector.market_data.connect_market_data(
            symbols=self.symbols,
            on_trade=self.on_incoming_trade,
            on_ticker=self.on_incoming_ticker,
            on_book=self.on_incoming_orderbook
        )

    async def stop(self) -> None:
        self._running = False
        registry = get_connector_registry()
        connector = registry.get(self.venue)
        if connector:
            await connector.market_data.disconnect_market_data()

        if self.session and self.raw_writer:
            self.session.close_session(self.raw_writer.current_hash)

        logger.info("MarketDataWorker stopped.")

    async def on_incoming_trade(self, trade: TradeRecord, raw_wire: str) -> None:
        """Handle incoming normalized real trade event."""
        # 1. Tamper-evident raw logging
        if self.raw_writer:
            self.raw_writer.append_raw_message(
                raw_wire, "trades", trade.symbol, trade.venue, trade.timestamp.isoformat()
            )

        # 2. Bounded queue with conservation tracking
        enqueued = await self.queue.put(trade)
        if not enqueued:
            return # Rejected by backpressure

        self.queue.record_persisted(1)
        self.last_trade_dt = trade.timestamp

        # 3. Update trades cache
        if trade.symbol in self.latest_trades:
            self.latest_trades[trade.symbol].insert(0, trade)
            if len(self.latest_trades[trade.symbol]) > 100:
                self.latest_trades[trade.symbol].pop()

        # 4. Update Microstructure Engine
        engine = self.microstructure_engines.get(trade.symbol)
        if engine:
            snapshot = engine.process_trade(trade)
            self.latest_snapshots[trade.symbol] = snapshot

        # 5. Mark to market open positions
        portfolio = get_portfolio_engine()
        portfolio.mark_to_market(trade.symbol, trade.price)

        # 6. Publish to EventBus
        bus = get_event_bus()
        await bus.publish(MarketDataReceivedEvent(
            venue=trade.venue,
            symbol=trade.symbol,
            channel="trades",
            payload=trade.model_dump(mode="json")
        ))

    async def on_incoming_ticker(self, ticker: TickerRecord, raw_wire: str) -> None:
        """Handle incoming normalized real ticker event."""
        if self.raw_writer:
            self.raw_writer.append_raw_message(
                raw_wire, "ticker", ticker.symbol, ticker.venue, ticker.timestamp.isoformat()
            )

        self.latest_tickers[ticker.symbol] = ticker

        # Mark to market with last ticker price
        portfolio = get_portfolio_engine()
        portfolio.mark_to_market(ticker.symbol, ticker.last_price)

    async def on_incoming_orderbook(self, book: OrderBookRecord, raw_wire: str) -> None:
        """Handle incoming normalized order book event."""
        if self.raw_writer:
            self.raw_writer.append_raw_message(
                raw_wire, "orderbook", book.symbol, book.venue, book.timestamp.isoformat()
            )
        self.latest_orderbooks[book.symbol] = book

        engine = self.microstructure_engines.get(book.symbol)
        if engine:
            engine.process_orderbook(book)

    def get_health_status(self) -> FeedHealthStatus:
        registry = get_connector_registry()
        connector = registry.get(self.venue)
        is_conn = connector.market_data.is_market_data_connected() if connector else False

        latency_ms = None
        if self.last_trade_dt:
            age = (datetime.now(timezone.utc) - self.last_trade_dt).total_seconds()
            latency_ms = round(age * 1000.0, 1)

        q_stats = self.queue.get_stats()

        return FeedHealthStatus(
            venue=self.venue,
            is_connected=is_conn,
            active_symbols=self.symbols,
            session_id=self.session.session_id if self.session else "none",
            records_received=q_stats["stats"]["received"],
            queue_depth=q_stats["qsize"],
            queue_utilization_pct=q_stats["utilization_pct"],
            last_trade_time=self.last_trade_dt.isoformat() if self.last_trade_dt else None,
            feed_latency_ms=latency_ms,
            reconnect_count=self.reconnect_count
        )

    def get_status(self) -> Dict[str, Any]:
        return self.get_health_status().model_dump()


_MARKET_DATA_WORKER: Optional[MarketDataWorker] = None


def get_market_data_worker() -> MarketDataWorker:
    global _MARKET_DATA_WORKER
    if _MARKET_DATA_WORKER is None:
        _MARKET_DATA_WORKER = MarketDataWorker()
    return _MARKET_DATA_WORKER
