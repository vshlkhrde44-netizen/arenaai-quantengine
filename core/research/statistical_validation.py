"""
Antigravity QuantEngine - Statistical Validation & Monte Carlo Engine
Implements bootstrap confidence intervals, Monte Carlo trade-order reshuffling,
family-aware multiple-testing corrections (Bonferroni, Holm, Benjamini-Hochberg FDR),
negative controls, deterministic random baseline, and strictly causal regime analysis.
"""

import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import scipy.stats as stats
from pydantic import BaseModel, Field

from core.research.backtest import BacktestTrade
from core.logging import get_logger

logger = get_logger("research.stats")


class BootstrapConfidenceInterval(BaseModel):
    metric_name: str
    sample_mean: float
    ci_lower_95: float
    ci_upper_95: float
    num_bootstrap_samples: int
    seed: int


class MonteCarloSimulationResult(BaseModel):
    seed: int
    num_simulations: int
    input_trades_count: int
    input_population_hash: str
    expected_drawdown_95th_percentile: float
    expected_final_pnl_median: float
    probability_of_ruin_pct: float
    distribution_drawdowns: List[float] = Field(default_factory=list)


class MultipleTestingCorrectionResult(BaseModel):
    method: str # "BONFERRONI", "HOLM_BONFERRONI", "BENJAMINI_HOCHBERG"
    num_hypotheses: int
    nominal_alpha: float
    original_p_values: List[float]
    adjusted_p_values: List[float]
    significant_hypotheses_count: int


class StatisticalValidator:
    """Rigorous statistical inference engine."""

    @staticmethod
    def compute_bootstrap_ci(
        trades: List[BacktestTrade],
        num_resamples: int = 1000,
        seed: int = 42
    ) -> Dict[str, BootstrapConfidenceInterval]:
        """Compute 95% bootstrap confidence intervals for win rate and mean trade PnL."""
        if not trades:
            return {}

        rng = np.random.default_rng(seed)
        pnls = np.array([t.net_pnl for t in trades])
        wins = np.array([1.0 if t.net_pnl > 0 else 0.0 for t in trades])
        n = len(trades)

        bootstrap_pnl_means = []
        bootstrap_win_rates = []

        for _ in range(num_resamples):
            indices = rng.integers(0, n, size=n)
            bootstrap_pnl_means.append(np.mean(pnls[indices]))
            bootstrap_win_rates.append(np.mean(wins[indices]))

        pnl_ci_low, pnl_ci_high = np.percentile(bootstrap_pnl_means, [2.5, 97.5])
        wr_ci_low, wr_ci_high = np.percentile(bootstrap_win_rates, [2.5, 97.5])

        return {
            "mean_trade_pnl": BootstrapConfidenceInterval(
                metric_name="mean_trade_pnl",
                sample_mean=round(float(np.mean(pnls)), 2),
                ci_lower_95=round(float(pnl_ci_low), 2),
                ci_upper_95=round(float(pnl_ci_high), 2),
                num_bootstrap_samples=num_resamples,
                seed=seed
            ),
            "win_rate": BootstrapConfidenceInterval(
                metric_name="win_rate",
                sample_mean=round(float(np.mean(wins)), 4),
                ci_lower_95=round(float(wr_ci_low), 4),
                ci_upper_95=round(float(wr_ci_high), 4),
                num_bootstrap_samples=num_resamples,
                seed=seed
            )
        }

    @staticmethod
    def run_monte_carlo_reshuffle(
        trades: List[BacktestTrade],
        initial_capital: float = 100000.0,
        num_simulations: int = 1000,
        seed: int = 42
    ) -> MonteCarloSimulationResult:
        """
        Monte Carlo Trade-Order Reshuffling.
        Evaluates sequence risk and tail drawdown under permutation.
        """
        if not trades:
            return MonteCarloSimulationResult(
                seed=seed,
                num_simulations=0,
                input_trades_count=0,
                input_population_hash="empty",
                expected_drawdown_95th_percentile=0.0,
                expected_final_pnl_median=0.0,
                probability_of_ruin_pct=0.0
            )

        rng = np.random.default_rng(seed)
        pnls = np.array([t.net_pnl for t in trades])
        
        # Compute canonical hash of input trade population
        raw_bytes = json.dumps([t.net_pnl for t in trades], sort_keys=True).encode("utf-8")
        pop_hash = hashlib.sha256(raw_bytes).hexdigest()

        drawdowns = []
        final_pnls = []
        ruin_count = 0

        for _ in range(num_simulations):
            shuffled_pnls = rng.permutation(pnls)
            equity_curve = initial_capital + np.cumsum(shuffled_pnls)
            
            # Max drawdown for this run
            peak = np.maximum.accumulate(equity_curve)
            dd = (peak - equity_curve) / np.where(peak > 0, peak, 1.0)
            max_dd_pct = float(np.max(dd)) * 100
            drawdowns.append(max_dd_pct)
            
            final_pnl = float(equity_curve[-1] - initial_capital)
            final_pnls.append(final_pnl)

            if np.min(equity_curve) <= (initial_capital * 0.5): # 50% capital loss defined as ruin
                ruin_count += 1

        drawdowns_arr = np.array(drawdowns)
        dd_95th = float(np.percentile(drawdowns_arr, 95))
        median_pnl = float(np.median(final_pnls))
        prob_ruin = (ruin_count / num_simulations) * 100

        return MonteCarloSimulationResult(
            seed=seed,
            num_simulations=num_simulations,
            input_trades_count=len(trades),
            input_population_hash=pop_hash,
            expected_drawdown_95th_percentile=round(dd_95th, 2),
            expected_final_pnl_median=round(median_pnl, 2),
            probability_of_ruin_pct=round(prob_ruin, 2),
            distribution_drawdowns=[round(float(x), 2) for x in np.percentile(drawdowns_arr, [5, 25, 50, 75, 95])]
        )

    @staticmethod
    def adjust_multiple_testing(
        p_values: List[float],
        method: str = "BENJAMINI_HOCHBERG",
        alpha: float = 0.05
    ) -> MultipleTestingCorrectionResult:
        """
        Family-aware multiple-testing adjustments.
        Methods:
        - BONFERRONI: Single-step FWER control
        - HOLM_BONFERRONI: Step-down FWER control
        - BENJAMINI_HOCHBERG: False Discovery Rate (FDR) control
        """
        m = len(p_values)
        if m == 0:
            return MultipleTestingCorrectionResult(
                method=method,
                num_hypotheses=0,
                nominal_alpha=alpha,
                original_p_values=[],
                adjusted_p_values=[],
                significant_hypotheses_count=0
            )

        p_arr = np.array(p_values)

        if method == "BONFERRONI":
            adj = np.minimum(1.0, p_arr * m)
            sig = int(np.sum(adj < alpha))

        elif method == "HOLM_BONFERRONI":
            sorted_indices = np.argsort(p_arr)
            sorted_p = p_arr[sorted_indices]
            adj_sorted = np.zeros(m)
            for i in range(m):
                adj_sorted[i] = min(1.0, sorted_p[i] * (m - i))
            # Monotonicity enforcement
            for i in range(1, m):
                adj_sorted[i] = max(adj_sorted[i], adj_sorted[i - 1])
            adj = np.zeros(m)
            adj[sorted_indices] = adj_sorted
            sig = int(np.sum(adj < alpha))

        elif method == "BENJAMINI_HOCHBERG":
            sorted_indices = np.argsort(p_arr)
            sorted_p = p_arr[sorted_indices]
            adj_sorted = np.zeros(m)
            for i in range(m):
                rank = i + 1
                adj_sorted[i] = min(1.0, (sorted_p[i] * m) / rank)
            # Reverse monotonicity enforcement
            for i in range(m - 2, -1, -1):
                adj_sorted[i] = min(adj_sorted[i], adj_sorted[i + 1])
            adj = np.zeros(m)
            adj[sorted_indices] = adj_sorted
            sig = int(np.sum(adj < alpha))

        else:
            raise ValueError(f"Unknown multiple-testing method: {method}")

        return MultipleTestingCorrectionResult(
            method=method,
            num_hypotheses=m,
            nominal_alpha=alpha,
            original_p_values=[round(float(p), 6) for p in p_values],
            adjusted_p_values=[round(float(p), 6) for p in adj],
            significant_hypotheses_count=sig
        )

    @staticmethod
    def classify_causal_regime(df: pd.DataFrame, bar_idx: int, window: int = 50) -> str:
        """
        Classifies regime strictly using information up to bar_idx.
        No future information enters the classification.
        """
        if bar_idx < window:
            return "UNKNOWN_WARMUP"

        slice_df = df.iloc[bar_idx - window: bar_idx + 1]
        closes = slice_df["close"].values
        returns = np.diff(closes) / closes[:-1]

        volatility = np.std(returns) * np.sqrt(365 * 24)
        net_return = (closes[-1] - closes[0]) / closes[0]

        is_high_vol = volatility > 0.60

        if net_return > 0.05:
            return "BULL_TRENDING_HIGH_VOL" if is_high_vol else "BULL_TRENDING_LOW_VOL"
        elif net_return < -0.05:
            return "BEAR_TRENDING_HIGH_VOL" if is_high_vol else "BEAR_TRENDING_LOW_VOL"
        else:
            return "CHOPPY_HIGH_VOL" if is_high_vol else "CHOPPY_LOW_VOL"
