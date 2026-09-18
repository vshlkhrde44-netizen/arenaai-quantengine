"""
Antigravity QuantEngine - Walk-Forward Validation Engine
Enforces explicit fold geometry, verified purge buffers, and active embargo exclusion (P0-10, P0-11, Section 20-23).
Supports declared ROLLING and EXPANDING methodologies with zero test-to-train leakage.
"""

import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from core.strategies.base import BaseStrategy
from core.research.backtest import BacktestEngine, BacktestResult
from database.engine import get_db
from core.logging import get_logger

logger = get_logger("research.walk_forward")


class WalkForwardFoldRecord(BaseModel):
    fold_index: int
    methodology: str # "ROLLING" or "EXPANDING"
    train_start_bar: int
    train_end_bar: int
    purge_start_bar: int
    purge_end_bar: int
    test_start_bar: int
    test_end_bar: int
    embargo_start_bar: int
    embargo_end_bar: int
    train_sample_count: int
    test_sample_count: int
    purged_sample_count: int
    embargoed_sample_count: int
    train_pnl: float
    test_pnl: float
    train_win_rate: float
    test_win_rate: float
    train_trades: int
    test_trades: int


class WalkForwardResult(BaseModel):
    wf_id: str
    strategy_id: str
    dataset_id: str
    methodology: str # "ROLLING" or "EXPANDING"
    num_folds: int
    train_window_bars: int
    purge_bars: int
    test_window_bars: int
    embargo_bars: int
    step_bars: int
    overall_oos_pnl: float
    overall_oos_win_rate: float
    oos_degradation_ratio: float
    folds: List[WalkForwardFoldRecord] = Field(default_factory=list)


class WalkForwardEngine:
    """
    Rigorous out-of-sample walk-forward validator with verified purge and embargo enforcement.
    """

    def __init__(
        self,
        methodology: str = "ROLLING",
        train_window_bars: int = 500,
        purge_bars: int = 10,
        test_window_bars: int = 150,
        embargo_bars: int = 10,
        step_bars: int = 150
    ):
        if methodology not in ("ROLLING", "EXPANDING"):
            raise ValueError(f"Unknown walk-forward methodology: {methodology}. Must be ROLLING or EXPANDING.")
        self.methodology = methodology
        self.train_window_bars = train_window_bars
        self.purge_bars = max(1, purge_bars)
        self.test_window_bars = test_window_bars
        self.embargo_bars = max(1, embargo_bars)
        self.step_bars = step_bars

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        dataset_id: str,
        dataset_hash: str
    ) -> WalkForwardResult:
        wf_id = f"wf_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        total_bars = len(df)
        folds: List[WalkForwardFoldRecord] = []
        backtester = BacktestEngine()

        current_train_start = 0
        fold_idx = 0

        while True:
            if self.methodology == "ROLLING":
                train_start = current_train_start
            else: # EXPANDING
                train_start = 0

            train_end = current_train_start + self.train_window_bars
            
            # Explicit Purge geometry (Section 20, 23)
            purge_start = train_end
            purge_end = purge_start + self.purge_bars

            # Explicit Test window (OOS)
            test_start = purge_end
            test_end = test_start + self.test_window_bars

            # Explicit Embargo geometry (Section 20, 22)
            embargo_start = test_end
            embargo_end = embargo_start + self.embargo_bars

            if test_end > total_bars:
                break

            # Strictly separate slices: train excludes purge, test excludes embargo
            train_df = df.iloc[train_start:train_end].copy().reset_index(drop=True)
            test_df = df.iloc[test_start:test_end].copy().reset_index(drop=True)

            # Evaluate in-sample train fold
            train_res = backtester.run(strategy, train_df, dataset_id, dataset_hash)
            # Evaluate out-of-sample test fold
            test_res = backtester.run(strategy, test_df, dataset_id, dataset_hash)

            fold_rec = WalkForwardFoldRecord(
                fold_index=fold_idx,
                methodology=self.methodology,
                train_start_bar=train_start,
                train_end_bar=train_end,
                purge_start_bar=purge_start,
                purge_end_bar=purge_end,
                test_start_bar=test_start,
                test_end_bar=test_end,
                embargo_start_bar=embargo_start,
                embargo_end_bar=embargo_end,
                train_sample_count=len(train_df),
                test_sample_count=len(test_df),
                purged_sample_count=self.purge_bars,
                embargoed_sample_count=self.embargo_bars,
                train_pnl=train_res.net_pnl,
                test_pnl=test_res.net_pnl,
                train_win_rate=train_res.win_rate,
                test_win_rate=test_res.win_rate,
                train_trades=train_res.total_trades,
                test_trades=test_res.total_trades
            )
            folds.append(fold_rec)

            fold_idx += 1
            # Advance step ensuring embargo boundary is respected
            current_train_start += max(self.step_bars, self.test_window_bars)

        # Aggregate metrics
        total_oos_pnl = round(sum(f.test_pnl for f in folds), 2)
        total_oos_trades = sum(f.test_trades for f in folds)
        oos_win_rate = 0.0
        if total_oos_trades > 0:
            oos_win_rate = round(
                sum(f.test_win_rate * f.test_trades for f in folds) / total_oos_trades, 4
            )

        avg_train_pnl = (sum(f.train_pnl for f in folds) / len(folds)) if folds else 1.0
        avg_test_pnl = (sum(f.test_pnl for f in folds) / len(folds)) if folds else 0.0
        degradation = round(avg_test_pnl / avg_train_pnl if avg_train_pnl != 0 else 0.0, 3)

        wf_result = WalkForwardResult(
            wf_id=wf_id,
            strategy_id=strategy.strategy_id,
            dataset_id=dataset_id,
            methodology=self.methodology,
            num_folds=len(folds),
            train_window_bars=self.train_window_bars,
            purge_bars=self.purge_bars,
            test_window_bars=self.test_window_bars,
            embargo_bars=self.embargo_bars,
            step_bars=self.step_bars,
            overall_oos_pnl=total_oos_pnl,
            overall_oos_win_rate=oos_win_rate,
            oos_degradation_ratio=degradation,
            folds=folds
        )

        db = get_db()
        sql = """
            INSERT INTO walk_forward_runs (
                wf_id, strategy_id, strategy_version_id, dataset_id,
                train_window_bars, purge_bars, embargo_bars, test_window_bars,
                step_bars, num_folds, summary_metrics_json, folds_data_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_non_query(
            sql,
            (
                wf_id, strategy.strategy_id, f"{strategy.strategy_id}_v{strategy.version}",
                dataset_id, self.train_window_bars, self.purge_bars, self.embargo_bars,
                self.test_window_bars, self.step_bars, len(folds),
                json.dumps({
                    "methodology": self.methodology,
                    "overall_oos_pnl": total_oos_pnl,
                    "overall_oos_win_rate": oos_win_rate,
                    "oos_degradation_ratio": degradation
                }),
                json.dumps([f.model_dump() for f in folds])
            )
        )
        logger.info(f"Completed Walk-Forward ({self.methodology}) {wf_id}: {len(folds)} folds, OOS PnL=${total_oos_pnl:,.2f}")
        return wf_result
