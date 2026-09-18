"""
Antigravity QuantEngine - Market Microstructure Analytics Engine
Computes real-time Order Flow Delta, CVD, Footprint, Volume Profile,
Point of Control (POC), Value Area (VAH/VAL), and Absorption detection.

Semantic Firewall Rules:
1. Aggressor trade != Liquidity sweep
2. Trade imbalance != Order-book imbalance
3. Candle direction != Aggressor side
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from core.domain.models import (
    TradeRecord, OrderBookRecord, OrderSide, MicrostructureSnapshot
)
from core.logging import get_logger

logger = get_logger("analytics.microstructure")


class FootprintLevel(BaseModel):
    price: float
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    total_volume: float = 0.0
    delta: float = 0.0


class VolumeProfile(BaseModel):
    poc_price: float # Point of Control (highest volume price)
    total_volume: float
    vah_price: float # Value Area High (top of 70% volume area)
    val_price: float # Value Area Low (bottom of 70% volume area)
    profile: Dict[float, float] # price -> volume


class MicrostructureEngine:
    """Computes microstructure metrics over real-time trade and order book streams."""

    def __init__(self, symbol: str, tick_size: float = 0.5):
        self.symbol = symbol
        self.tick_size = tick_size
        self.current_cvd = 0.0
        self.trade_history: List[TradeRecord] = []
        self.max_history = 5000

        # Bar/Footprint state
        self.footprint_levels: Dict[float, FootprintLevel] = {}
        self.current_bar_buy_vol = 0.0
        self.current_bar_sell_vol = 0.0

        # Latest book
        self.latest_book: Optional[OrderBookRecord] = None

    def _round_to_tick(self, price: float) -> float:
        return round(round(price / self.tick_size) * self.tick_size, 4)

    def process_trade(self, trade: TradeRecord) -> MicrostructureSnapshot:
        """Ingest a single real trade and update microstructure state."""
        self.trade_history.append(trade)
        if len(self.trade_history) > self.max_history:
            self.trade_history.pop(0)

        price_tick = self._round_to_tick(trade.price)

        # Update Delta & CVD strictly from observed aggressor side (Section 16, 17)
        side_str = trade.side.value if hasattr(trade.side, "value") else str(trade.side)
        is_buy = (side_str.upper() == "BUY")
        trade_delta = trade.quantity if is_buy else -trade.quantity
        self.current_cvd += trade_delta

        # Update Footprint at price level
        if price_tick not in self.footprint_levels:
            self.footprint_levels[price_tick] = FootprintLevel(price=price_tick)

        fp = self.footprint_levels[price_tick]
        if is_buy:
            fp.buy_volume += trade.quantity
            self.current_bar_buy_vol += trade.quantity
        else:
            fp.sell_volume += trade.quantity
            self.current_bar_sell_vol += trade.quantity

        fp.total_volume += trade.quantity
        fp.delta = fp.buy_volume - fp.sell_volume

        # Absorption check: High volume at level but minimal price movement
        absorption = False
        if len(self.footprint_levels) > 5:
            avg_vol = sum(lvl.total_volume for lvl in self.footprint_levels.values()) / len(self.footprint_levels)
            if fp.total_volume > avg_vol * 2.5:
                absorption = True

        # Volume Profile calculation
        profile = self.calculate_volume_profile()

        # Trade Imbalance Ratio (Buy Volume / Sell Volume)
        # CRITICAL (P0-14): Never substitute artificial 99.0 for infinite/undefined
        imbalance_ratio: Optional[float] = 1.0
        if self.current_bar_sell_vol > 0:
            imbalance_ratio = round(self.current_bar_buy_vol / self.current_bar_sell_vol, 3)
        elif self.current_bar_buy_vol > 0:
            imbalance_ratio = None # Documented representation: undefined / infinite ratio

        spread = None
        book_imbalance = None
        if self.latest_book:
            if self.latest_book.asks and self.latest_book.bids:
                spread = round(self.latest_book.asks[0].price - self.latest_book.bids[0].price, 4)

        ts = getattr(trade, "receipt_timestamp", getattr(trade, "timestamp", datetime.now(timezone.utc)))

        return MicrostructureSnapshot(
            symbol=self.symbol,
            timestamp=ts,
            last_price=trade.price,
            delta=round(trade_delta, 4),
            cvd=round(self.current_cvd, 4),
            trade_imbalance_ratio=imbalance_ratio,
            absorption_detected=absorption,
            poc_price=profile.poc_price if profile else None,
            vah_price=profile.vah_price if profile else None,
            val_price=profile.val_price if profile else None,
            spread=spread,
            book_imbalance=book_imbalance
        )

    def process_orderbook(self, book: OrderBookRecord) -> None:
        """Update resting order book state."""
        self.latest_book = book

    def calculate_volume_profile(self, value_area_pct: float = 0.70) -> Optional[VolumeProfile]:
        """Compute POC, VAH, and VAL from aggregated footprint."""
        if not self.footprint_levels:
            return None

        total_vol = sum(lvl.total_volume for lvl in self.footprint_levels.values())
        if total_vol == 0:
            return None

        # Sort prices ascending
        sorted_prices = sorted(self.footprint_levels.keys())
        price_vol_map = {p: self.footprint_levels[p].total_volume for p in sorted_prices}

        # Point of Control (POC): Price with absolute maximum volume
        poc_price = max(price_vol_map.items(), key=lambda x: x[1])[0]

        # Calculate Value Area (70% of total volume around POC)
        target_vol = total_vol * value_area_pct
        accum_vol = price_vol_map[poc_price]
        poc_idx = sorted_prices.index(poc_price)
        up_idx = poc_idx + 1
        down_idx = poc_idx - 1

        vah_price = poc_price
        val_price = poc_price

        while accum_vol < target_vol and (up_idx < len(sorted_prices) or down_idx >= 0):
            vol_up = price_vol_map[sorted_prices[up_idx]] if up_idx < len(sorted_prices) else 0.0
            vol_down = price_vol_map[sorted_prices[down_idx]] if down_idx >= 0 else 0.0

            if vol_up >= vol_down and up_idx < len(sorted_prices):
                accum_vol += vol_up
                vah_price = sorted_prices[up_idx]
                up_idx += 1
            elif down_idx >= 0:
                accum_vol += vol_down
                val_price = sorted_prices[down_idx]
                down_idx -= 1
            else:
                break

        return VolumeProfile(
            poc_price=poc_price,
            total_volume=round(total_vol, 4),
            vah_price=vah_price,
            val_price=val_price,
            profile={p: round(v, 4) for p, v in price_vol_map.items()}
        )

    def get_footprint_summary(self) -> List[Dict[str, Any]]:
        """Return formatted footprint bars for UI visualization."""
        levels = sorted(self.footprint_levels.values(), key=lambda x: x.price, reverse=True)
        return [
            {
                "price": lvl.price,
                "buy_volume": round(lvl.buy_volume, 4),
                "sell_volume": round(lvl.sell_volume, 4),
                "total_volume": round(lvl.total_volume, 4),
                "delta": round(lvl.delta, 4)
            }
            for lvl in levels
        ]
