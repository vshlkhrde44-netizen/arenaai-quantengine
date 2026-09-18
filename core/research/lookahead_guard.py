"""
Antigravity QuantEngine - Adversarial Lookahead Leakage Protection
Mathematically verifies causal purity and lookahead prevention across features and strategies.
Implements intentionally malicious strategies to prove firewall enforcement (P0-15, Section 32, 33).
"""

from typing import Tuple, List, Optional, Dict, Any
import pandas as pd
import numpy as np

from core.strategies.base import BaseStrategy, Signal
from core.logging import get_logger

logger = get_logger("research.lookahead")


class LookaheadViolationError(Exception):
    """Raised when future data influences past signals or decisions."""
    pass


# ---------------------------------------------------------------------------
# Section 33: Intentionally Malicious Strategies for Firewall Proof
# ---------------------------------------------------------------------------

class FutureCloseStrategy(BaseStrategy):
    """Malicious strategy that looks ahead at future close prices (t+1)."""
    def __init__(self):
        super().__init__("malicious_future_close", "1.0", "Malicious strategy peeking at t+1 close.")

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals = []
        if len(df) < 5:
            return signals
        # Peeks into future close
        future_close = df["close"].shift(-1)
        for i in range(len(df) - 1):
            if pd.notna(future_close.iloc[i]) and future_close.iloc[i] > df["close"].iloc[i] * 1.002:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    strategy_version="1.0",
                    symbol=str(df["symbol"].iloc[i] if "symbol" in df else "BTC-USD"),
                    action="ENTER_LONG",
                    confidence=0.99,
                    bar_index=i,
                    price=float(df["close"].iloc[i]),
                    timestamp=str(df.get("timestamp", [f"bar_{i}"])[i])
                ))
        return signals


class FutureVolumeStrategy(BaseStrategy):
    """Malicious strategy that peeks at future volume surges (t+2)."""
    def __init__(self):
        super().__init__("malicious_future_volume", "1.0", "Malicious strategy peeking at t+2 volume.")

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals = []
        if len(df) < 5 or "volume" not in df:
            return signals
        future_vol = df["volume"].shift(-2)
        for i in range(len(df) - 2):
            if pd.notna(future_vol.iloc[i]) and future_vol.iloc[i] > df["volume"].iloc[i] * 2.0:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    strategy_version="1.0",
                    symbol=str(df["symbol"].iloc[i] if "symbol" in df else "BTC-USD"),
                    action="ENTER_LONG",
                    confidence=0.95,
                    bar_index=i,
                    price=float(df["close"].iloc[i]),
                    timestamp=str(df.get("timestamp", [f"bar_{i}"])[i])
                ))
        return signals


class FutureLabelStrategy(BaseStrategy):
    """Malicious strategy that inspects forward labels."""
    def __init__(self):
        super().__init__("malicious_future_label", "1.0", "Malicious strategy peeking at future return labels.")

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals = []
        if len(df) < 5:
            return signals
        # Forward 3-bar return
        fwd_ret = df["close"].shift(-3) / df["close"] - 1.0
        for i in range(len(df) - 3):
            if pd.notna(fwd_ret.iloc[i]) and fwd_ret.iloc[i] > 0.01:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    strategy_version="1.0",
                    symbol=str(df["symbol"].iloc[i] if "symbol" in df else "BTC-USD"),
                    action="ENTER_LONG",
                    confidence=0.98,
                    bar_index=i,
                    price=float(df["close"].iloc[i]),
                    timestamp=str(df.get("timestamp", [f"bar_{i}"])[i])
                ))
        return signals


class FutureFeatureStrategy(BaseStrategy):
    """Malicious strategy using a centered moving average (future leak)."""
    def __init__(self):
        super().__init__("malicious_future_feature", "1.0", "Centered rolling feature leaking future bars.")

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals = []
        if len(df) < 10:
            return signals
        # Centered rolling window leaks future bars into current value
        centered_ma = df["close"].rolling(window=5, center=True).mean()
        for i in range(len(df)):
            if pd.notna(centered_ma.iloc[i]) and df["close"].iloc[i] > centered_ma.iloc[i]:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    strategy_version="1.0",
                    symbol=str(df["symbol"].iloc[i] if "symbol" in df else "BTC-USD"),
                    action="ENTER_LONG",
                    confidence=0.90,
                    bar_index=i,
                    price=float(df["close"].iloc[i]),
                    timestamp=str(df.get("timestamp", [f"bar_{i}"])[i])
                ))
        return signals


class FutureRegimeStrategy(BaseStrategy):
    """Malicious strategy classifying regimes using whole-sample global statistics."""
    def __init__(self):
        super().__init__("malicious_future_regime", "1.0", "Global full-sample mean classification.")

    def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
        signals = []
        if len(df) < 10:
            return signals
        # Whole-sample mean leaks future distribution into bar 0
        global_mean = df["close"].mean()
        for i in range(len(df)):
            if df["close"].iloc[i] > global_mean:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    strategy_version="1.0",
                    symbol=str(df["symbol"].iloc[i] if "symbol" in df else "BTC-USD"),
                    action="ENTER_LONG",
                    confidence=0.85,
                    bar_index=i,
                    price=float(df["close"].iloc[i]),
                    timestamp=str(df.get("timestamp", [f"bar_{i}"])[i])
                ))
        return signals


# ---------------------------------------------------------------------------
# Section 32: Adversarial Testing Suite
# ---------------------------------------------------------------------------

class LookaheadGuard:
    """Rigorous causal lookahead testing engine."""

    @staticmethod
    def verify_causal_invariance(strategy: BaseStrategy, df: pd.DataFrame, sample_points: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Verify truncation invariance:
        Signal at bar t when evaluating full dataframe [0:T] MUST exactly match
        signal at bar t when evaluating truncated dataframe [0:t].
        """
        if len(df) < 40:
            return True, None

        full_signals = strategy.generate_signals(df)
        full_signals_by_bar = {s.bar_index: s.action for s in full_signals}

        test_indices = np.linspace(25, len(df) - 5, num=min(sample_points, len(df) - 30), dtype=int)

        for t in test_indices:
            truncated_df = df.iloc[: t + 1].copy()
            truncated_signals = strategy.generate_signals(truncated_df)
            truncated_sig_at_t = None
            for s in truncated_signals:
                if s.bar_index == t:
                    truncated_sig_at_t = s.action

            full_sig_at_t = full_signals_by_bar.get(t)

            if truncated_sig_at_t != full_sig_at_t:
                msg = (
                    f"LOOKAHEAD LEAKAGE DETECTED at bar {t}: "
                    f"Truncated signal was '{truncated_sig_at_t}', but full future dataset gave '{full_sig_at_t}'! "
                    f"Future bars past bar {t} are illegally leaking into decision."
                )
                logger.error(msg)
                return False, msg

        return True, None

    @staticmethod
    def verify_future_perturbation_invariance(strategy: BaseStrategy, df: pd.DataFrame, test_bar: int = 30) -> Tuple[bool, Optional[str]]:
        """
        Perturb future bars (open, high, low, close, volume).
        Signals up to test_bar MUST NOT CHANGE.
        """
        if len(df) <= test_bar + 10:
            return True, None

        base_signals = strategy.generate_signals(df)
        base_sigs_up_to_t = [s for s in base_signals if s.bar_index <= test_bar]

        # Multi-attribute perturbation per Section 32
        perturbed_df = df.copy()
        mask = (perturbed_df.index > test_bar)
        perturbed_df.loc[mask, "open"] *= 1.3
        perturbed_df.loc[mask, "high"] *= 1.4
        perturbed_df.loc[mask, "low"] *= 0.7
        perturbed_df.loc[mask, "close"] *= 1.35
        if "volume" in perturbed_df.columns:
            perturbed_df.loc[mask, "volume"] *= 5.0

        new_signals = strategy.generate_signals(perturbed_df)
        new_sigs_up_to_t = [s for s in new_signals if s.bar_index <= test_bar]

        if len(base_sigs_up_to_t) != len(new_sigs_up_to_t):
            return False, f"Perturbation count mismatch: {len(base_sigs_up_to_t)} vs {len(new_sigs_up_to_t)}"

        for s1, s2 in zip(base_sigs_up_to_t, new_sigs_up_to_t):
            if s1.bar_index != s2.bar_index or s1.action != s2.action or s1.price != s2.price:
                return False, f"Perturbation altered signal at bar {s1.bar_index}: {s1.action} -> {s2.action}"

        return True, None
