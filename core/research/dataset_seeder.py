"""
Antigravity QuantEngine - Real Historical Dataset Acquisition
Fetches genuine historical candles from public exchange REST endpoints.
ZERO-FABRICATION (P0-01, P0-06, Section 2, 11, 17):
If download fails, raises DATA_ACQUISITION_FAILED. Never creates synthetic fallback candles.
Never estimates aggressor volume from candle OHLC ratios.
Never automatically promotes strategies to paper trading (P0-24, P0-25).
"""

import json
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List
import pandas as pd

from core.domain.models import DataClassification, MicrostructureSemantic
from core.research.dataset import get_dataset_manager
from core.strategies.base import get_strategy_registry
from core.strategies.library import MicrostructureCVDStrategy, VolumeProfilePOCBreakoutStrategy
from core.logging import get_logger

logger = get_logger("research.acquisition")


class DataAcquisitionError(Exception):
    """Raised when genuine historical data acquisition fails."""
    pass


def fetch_real_candles(symbol: str = "BTC-USD", granularity: int = 3600) -> pd.DataFrame:
    """
    Fetch genuine historical candles from Coinbase Public REST API.
    Raises DataAcquisitionError if unreachable or invalid.
    """
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles?granularity={granularity}"
    req = urllib.request.Request(url, headers={"User-Agent": "AntigravityQuantEngine/2.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise DataAcquisitionError(f"DATA_ACQUISITION_FAILED: Failed to download historical candles from Coinbase: {e}")

    if not isinstance(data, list) or len(data) == 0:
        raise DataAcquisitionError(f"DATA_ACQUISITION_FAILED: Coinbase returned empty or invalid candle data for {symbol}")

    # Coinbase candles format: [time, low, high, open, close, volume]
    rows = []
    for c in reversed(data): # Chronological order
        ts = datetime.fromtimestamp(c[0], tz=timezone.utc)
        low, high, open_p, close_p, vol = float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])
        
        # Section 17: If only OHLCV exists, TRUE_AGGRESSOR_DELTA = UNAVAILABLE
        # No candle-derived fake aggressor volume!
        rows.append({
            "timestamp": ts.isoformat(),
            "symbol": symbol,
            "open": open_p,
            "high": high,
            "low": low,
            "close": close_p,
            "volume": vol,
            "data_class": DataClassification.HISTORICAL_PROVIDER.value,
            "buyer_volume": None,
            "seller_volume": None,
            "delta": None
        })

    df = pd.DataFrame(rows)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def acquire_and_register_historical_dataset(symbol: str = "BTC-USD", timeframe: str = "1h") -> str:
    """
    Explicitly acquire and register a genuine historical dataset.
    CRITICAL (P0-01): If download fails, fail closed. No synthetic fallback.
    """
    granularity = 3600 if timeframe == "1h" else 86400
    df = fetch_real_candles(symbol=symbol, granularity=granularity)
    
    dm = get_dataset_manager()
    dataset_id = dm.register_dataset(
        name=f"Coinbase {symbol} {timeframe} Real Historical",
        venue="coinbase",
        symbol=symbol,
        timeframe=timeframe,
        df=df,
        is_sealed=False
    )
    logger.info(f"Successfully registered genuine historical dataset: {dataset_id}")
    return dataset_id


def register_default_strategies() -> None:
    """
    Register standard research strategies into the registry without automatic promotion (P0-24).
    Promotion to paper trading requires explicit operator authorization.
    """
    registry = get_strategy_registry()
    strat1 = MicrostructureCVDStrategy()
    strat2 = VolumeProfilePOCBreakoutStrategy()
    
    if strat1.strategy_id not in registry.strategies:
        registry.register_strategy(strat1, "Institutional order flow delta imbalance strategy.")
    if strat2.strategy_id not in registry.strategies:
        registry.register_strategy(strat2, "Volume profile Value Area breakout strategy.")
    
    logger.info("Registered research strategies. Awaiting explicit operator review and promotion.")


if __name__ == "__main__":
    register_default_strategies()
