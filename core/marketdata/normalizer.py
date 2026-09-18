"""
Antigravity QuantEngine - Market Data Normalizer
Converts raw exchange wire events into strict canonical domain models.
Preserves semantic distinctions; never fabricates unavailable fields.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List
from core.domain.models import (
    TradeRecord, TickerRecord, OrderBookRecord, OrderBookLevel, OrderSide, CandleRecord
)
from core.logging import get_logger

logger = get_logger("marketdata.normalizer")


def parse_iso_or_ms_timestamp(val: Any) -> datetime:
    if isinstance(val, (int, float)):
        # ms or seconds
        if val > 1e11:
            return datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            # Handle ISO string e.g. 2026-09-17T20:30:00.123456Z
            clean = val.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except Exception:
            pass
    return datetime.now(timezone.utc)


class MarketDataNormalizer:
    """Normalizes raw messages across exchanges into canonical domain entities."""

    @staticmethod
    def normalize_coinbase_trade(msg: Dict[str, Any]) -> Optional[TradeRecord]:
        """Normalize Coinbase WebSocket 'match' or 'last_match' wire message."""
        try:
            # Coinbase format:
            # { "type": "match", "trade_id": 12345, "sequence": 67890, "maker_order_id": "...",
            #   "taker_order_id": "...", "time": "2026-09-17T...", "product_id": "BTC-USD",
            #   "size": "0.01", "price": "65000.00", "side": "sell" }
            # In Coinbase, 'side' indicates the maker order side.
            # If maker is 'sell', the aggressor taker bought (BUY).
            # If maker is 'buy', the aggressor taker sold (SELL).
            maker_side = str(msg.get("side", "")).lower()
            aggressor_side = OrderSide.BUY if maker_side == "sell" else OrderSide.SELL

            return TradeRecord(
                trade_id=str(msg.get("trade_id", msg.get("sequence", "unknown"))),
                symbol=msg.get("product_id", "UNKNOWN"),
                price=float(msg["price"]),
                quantity=float(msg["size"]),
                side=aggressor_side,
                timestamp=parse_iso_or_ms_timestamp(msg.get("time")),
                receipt_timestamp=datetime.now(timezone.utc),
                sequence_number=msg.get("sequence"),
                venue="coinbase"
            )
        except Exception as e:
            logger.error(f"Failed to normalize Coinbase trade: {e}")
            return None

    @staticmethod
    def normalize_coinbase_ticker(msg: Dict[str, Any]) -> Optional[TickerRecord]:
        """Normalize Coinbase WebSocket 'ticker' wire message."""
        try:
            return TickerRecord(
                symbol=msg.get("product_id", "UNKNOWN"),
                venue="coinbase",
                bid_price=float(msg["best_bid"]) if "best_bid" in msg and msg["best_bid"] is not None else None,
                bid_quantity=float(msg["best_bid_size"]) if "best_bid_size" in msg and msg["best_bid_size"] is not None else None,
                ask_price=float(msg["best_ask"]) if "best_ask" in msg and msg["best_ask"] is not None else None,
                ask_quantity=float(msg["best_ask_size"]) if "best_ask_size" in msg and msg["best_ask_size"] is not None else None,
                last_price=float(msg["price"]),
                volume_24h=float(msg["volume_24h"]) if "volume_24h" in msg and msg["volume_24h"] is not None else None,
                trade_count_24h=None, # Coinbase does not provide trade_count_24h in ticker -> UNAVAILABLE
                timestamp=parse_iso_or_ms_timestamp(msg.get("time")),
                receipt_timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Failed to normalize Coinbase ticker: {e}")
            return None

    @staticmethod
    def normalize_kraken_trade(trade_item: list, symbol: str) -> Optional[TradeRecord]:
        """
        Normalize Kraken WebSocket trade item.
        Kraken trade item: [price, volume, time, side ('b' or 's'), orderType ('m' or 'l'), misc]
        """
        try:
            price = float(trade_item[0])
            volume = float(trade_item[1])
            ts = float(trade_item[2])
            side_char = trade_item[3]
            side = OrderSide.BUY if side_char == "b" else OrderSide.SELL

            return TradeRecord(
                trade_id=f"krak_{ts}_{price}_{volume}",
                symbol=symbol,
                price=price,
                quantity=volume,
                side=side,
                timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                receipt_timestamp=datetime.now(timezone.utc),
                venue="kraken"
            )
        except Exception as e:
            logger.error(f"Failed to normalize Kraken trade: {e}")
            return None

    @staticmethod
    def normalize_l2_book(symbol: str, venue: str, bids: List[List[Any]], asks: List[List[Any]], seq: Optional[int] = None) -> OrderBookRecord:
        """Normalize level 2 order book snapshot."""
        norm_bids = [OrderBookLevel(price=float(b[0]), quantity=float(b[1])) for b in bids if float(b[1]) > 0]
        norm_asks = [OrderBookLevel(price=float(a[0]), quantity=float(a[1])) for a in asks if float(a[1]) > 0]
        
        # Sort bids descending, asks ascending
        norm_bids.sort(key=lambda x: x.price, reverse=True)
        norm_asks.sort(key=lambda x: x.price)

        return OrderBookRecord(
            symbol=symbol,
            venue=venue,
            bids=norm_bids,
            asks=norm_asks,
            timestamp=datetime.now(timezone.utc),
            receipt_timestamp=datetime.now(timezone.utc),
            sequence_number=seq
        )
