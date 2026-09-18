import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy, Signal
from core.research.lookahead_guard import LookaheadGuard
from core.strategies.library import MicrostructureCVDStrategy


class LeakyAdversaryStrategy(BaseStrategy):
    """
    Intentionally malformed adversarial strategy that looks ahead into bar t+1!
    Must be detected and rejected by the LookaheadGuard.
    """

    def __init__(self):
        super().__init__("strat_leaky_adversary", "Leaky Adversary", "1.0.0", {})

    def generate_signals(self, df: pd.DataFrame):
        signals = []
        # CHEAT: Uses future bar t+1 price to determine signal at bar t!
        for i in range(len(df) - 1):
            current_p = df["close"].iloc[i]
            future_p = df["close"].iloc[i + 1] # LOOKAHEAD LEAKAGE!
            
            if future_p > current_p:
                signals.append(Signal(
                    bar_index=i,
                    timestamp=pd.to_datetime(df["timestamp"].iloc[i]),
                    symbol=str(df["symbol"].iloc[i]),
                    action="ENTER_LONG",
                    price=current_p
                ))
        return signals


def test_adversarial_lookahead_detection():
    # Construct test series
    dates = pd.date_range("2026-01-01", periods=100, freq="1h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "symbol": "BTC-USD",
        "open": np.linspace(60000, 65000, 100),
        "high": np.linspace(60100, 65100, 100),
        "low": np.linspace(59900, 64900, 100),
        "close": np.linspace(60050, 65050, 100) + np.random.normal(0, 10, 100),
        "volume": np.ones(100) * 10,
        "buyer_volume": np.ones(100) * 6,
        "seller_volume": np.ones(100) * 4,
    })

    # 1. Clean strategy MUST PASS
    clean_strat = MicrostructureCVDStrategy()
    clean_pass, err = LookaheadGuard.verify_causal_invariance(clean_strat, df)
    assert clean_pass is True
    assert err is None

    # 2. Leaky strategy MUST FAIL
    leaky_strat = LeakyAdversaryStrategy()
    leaky_pass, leaky_err = LookaheadGuard.verify_causal_invariance(leaky_strat, df)
    assert leaky_pass is False
    assert "LOOKAHEAD LEAKAGE DETECTED" in leaky_err
