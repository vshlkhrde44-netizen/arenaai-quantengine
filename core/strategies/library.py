"""
Antigravity QuantEngine - Production Strategy Library
Implements institutional microstructure, volume profile, and statistical strategies.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from core.strategies.base import BaseStrategy, Signal


class MicrostructureCVDStrategy(BaseStrategy):
    """
    Order Flow CVD Imbalance Strategy
    Identifies aggressive buyer/seller divergence using Cumulative Volume Delta and Footprint imbalances.
    """

    def __init__(
        self,
        strategy_id: str = "strat_cvd_imbalance",
        parameters: Optional[Dict[str, Any]] = None
    ):
        default_params = {
            "cvd_window": 14,
            "threshold_zscore": 1.5,
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.03,
            "cooldown_bars": 5
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(
            strategy_id=strategy_id,
            name="Microstructure CVD Imbalance",
            version="1.0.0",
            parameters=default_params
        )

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals: List[Signal] = []
        if len(df) < self.parameters["cvd_window"] + 2:
            return signals

        # Compute volume delta if not present: buyer_volume - seller_volume
        df = df.copy()
        if "delta" not in df.columns:
            if "buyer_volume" in df.columns and "seller_volume" in df.columns:
                df["delta"] = df["buyer_volume"] - df["seller_volume"]
            else:
                # Estimate proxy only if not available: sign(close - open) * volume
                df["delta"] = np.sign(df["close"] - df["open"]) * df["volume"]

        df["cvd"] = df["delta"].cumsum()
        
        # Rolling CVD mean and std for z-score
        w = int(self.parameters["cvd_window"])
        rolling_mean = df["delta"].rolling(w).mean()
        rolling_std = df["delta"].rolling(w).std().replace(0, 1e-6)
        df["delta_zscore"] = (df["delta"] - rolling_mean) / rolling_std

        z_thresh = float(self.parameters["threshold_zscore"])
        sl_pct = float(self.parameters["stop_loss_pct"])
        tp_pct = float(self.parameters["take_profit_pct"])
        cooldown = int(self.parameters["cooldown_bars"])
        last_signal_idx = -999

        for i in range(w, len(df)):
            if i - last_signal_idx < cooldown:
                continue

            z = df["delta_zscore"].iloc[i]
            price = float(df["close"].iloc[i])
            ts = pd.to_datetime(df["timestamp"].iloc[i]) if "timestamp" in df.columns else datetime.now(timezone.utc)
            sym = str(df["symbol"].iloc[i]) if "symbol" in df.columns else "BTC-USD"

            if z > z_thresh:
                # Aggressive buying pressure -> Enter Long
                signals.append(Signal(
                    bar_index=i,
                    timestamp=ts,
                    symbol=sym,
                    action="ENTER_LONG",
                    price=price,
                    stop_loss=round(price * (1.0 - sl_pct), 2),
                    take_profit=round(price * (1.0 + tp_pct), 2),
                    metadata={"zscore": round(float(z), 2), "cvd": round(float(df["cvd"].iloc[i]), 2)}
                ))
                last_signal_idx = i

            elif z < -z_thresh:
                # Aggressive selling pressure -> Enter Short
                signals.append(Signal(
                    bar_index=i,
                    timestamp=ts,
                    symbol=sym,
                    action="ENTER_SHORT",
                    price=price,
                    stop_loss=round(price * (1.0 + sl_pct), 2),
                    take_profit=round(price * (1.0 - tp_pct), 2),
                    metadata={"zscore": round(float(z), 2), "cvd": round(float(df["cvd"].iloc[i]), 2)}
                ))
                last_signal_idx = i

        return signals


class VolumeProfilePOCBreakoutStrategy(BaseStrategy):
    """
    Volume Profile Breakout Strategy
    Trades structural expansion outside the Value Area High (VAH) or Value Area Low (VAL).
    """

    def __init__(
        self,
        strategy_id: str = "strat_poc_breakout",
        parameters: Optional[Dict[str, Any]] = None
    ):
        default_params = {
            "profile_bars": 30,
            "value_area_ratio": 0.70,
            "stop_loss_pct": 0.012,
            "take_profit_pct": 0.025,
            "cooldown_bars": 10
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(
            strategy_id=strategy_id,
            name="Volume Profile POC Breakout",
            version="1.0.0",
            parameters=default_params
        )

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals: List[Signal] = []
        w = int(self.parameters["profile_bars"])
        if len(df) < w + 2:
            return signals

        sl_pct = float(self.parameters["stop_loss_pct"])
        tp_pct = float(self.parameters["take_profit_pct"])
        cooldown = int(self.parameters["cooldown_bars"])
        last_sig = -999

        for i in range(w, len(df)):
            if i - last_sig < cooldown:
                continue

            window_slice = df.iloc[i - w:i]
            vah = float(window_slice["high"].quantile(0.85))
            val = float(window_slice["low"].quantile(0.15))
            current_close = float(df["close"].iloc[i])
            prev_close = float(df["close"].iloc[i - 1])
            ts = pd.to_datetime(df["timestamp"].iloc[i]) if "timestamp" in df.columns else datetime.now(timezone.utc)
            sym = str(df["symbol"].iloc[i]) if "symbol" in df.columns else "BTC-USD"

            # Breakout above VAH
            if prev_close <= vah and current_close > vah:
                signals.append(Signal(
                    bar_index=i,
                    timestamp=ts,
                    symbol=sym,
                    action="ENTER_LONG",
                    price=current_close,
                    stop_loss=round(current_close * (1.0 - sl_pct), 2),
                    take_profit=round(current_close * (1.0 + tp_pct), 2),
                    metadata={"vah": round(vah, 2), "val": round(val, 2)}
                ))
                last_sig = i

            # Breakdown below VAL
            elif prev_close >= val and current_close < val:
                signals.append(Signal(
                    bar_index=i,
                    timestamp=ts,
                    symbol=sym,
                    action="ENTER_SHORT",
                    price=current_close,
                    stop_loss=round(current_close * (1.0 + sl_pct), 2),
                    take_profit=round(current_close * (1.0 - tp_pct), 2),
                    metadata={"vah": round(vah, 2), "val": round(val, 2)}
                ))
                last_sig = i

        return signals
