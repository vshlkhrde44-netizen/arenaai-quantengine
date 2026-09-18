import React, { useState } from 'react';
import { WalkForwardResult } from '../types';
import { runWalkForward } from '../api';
import { FastForward, ShieldAlert, CheckCircle2, TrendingUp } from 'lucide-react';

export const WalkForwardScreen: React.FC = () => {
  const [strategyId, setStrategyId] = useState('strat_cvd_imbalance');
  const [result, setResult] = useState<WalkForwardResult | null>(null);
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await runWalkForward(strategyId);
      setResult(res);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <FastForward size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Walk-Forward Out-Of-Sample Validation Engine
            </div>
            <div className="text-xs text-slate-400">
              Cross-validation with explicit Purge buffer & Embargo to eliminate label overlap and information leakage.
            </div>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={running}
          className="btn-primary text-xs flex items-center gap-1.5"
        >
          <FastForward size={14} />
          <span>{running ? 'Simulating Folds...' : 'Run Walk-Forward Analysis'}</span>
        </button>
      </div>

      {result && (
        <>
          {/* Summary KPI Tiles */}
          <div className="grid grid-cols-4 gap-3">
            <div className="metric-tile">
              <div className="metric-label">Total Out-of-Sample P&L</div>
              <div className={`metric-val ${result.overall_oos_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {result.overall_oos_pnl >= 0 ? '+' : ''}${result.overall_oos_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Across all test folds</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">OOS Win Rate</div>
              <div className="metric-val text-sky-400">
                {(result.overall_oos_win_rate * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Weighted by trades</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Degradation Ratio</div>
              <div className="metric-val text-amber-400 font-mono">
                {result.oos_degradation_ratio.toFixed(2)}x
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Test Sharpe / Train Sharpe</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Folds Evaluated</div>
              <div className="metric-val text-white font-mono">
                {result.num_folds} Folds
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Purge: 5 bars | Embargo: 5 bars</div>
            </div>
          </div>

          {/* Folds Table */}
          <div className="quant-card">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Fold-by-Fold Boundary & Performance Breakdown
              </span>
              <span className="text-[10px] font-mono text-emerald-400">
                Zero Overlap Purge Active
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="quant-table font-mono text-xs">
                <thead>
                  <tr>
                    <th>Fold #</th>
                    <th>Train Bars</th>
                    <th>Purge Gap</th>
                    <th>Test Bars (OOS)</th>
                    <th>Embargo</th>
                    <th>Train P&L</th>
                    <th>Test P&L (OOS)</th>
                    <th>Train WR</th>
                    <th>Test WR (OOS)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.folds.map((f, idx) => (
                    <tr key={idx}>
                      <td className="font-bold text-white">Fold #{f.fold_index + 1}</td>
                      <td className="text-slate-400">{f.train_start_bar} - {f.train_end_bar} ({f.train_sample_count}b)</td>
                      <td className="text-amber-400">{f.purge_bars} bars</td>
                      <td className="text-sky-400 font-semibold">{f.test_start_bar} - {f.test_end_bar} ({f.test_sample_count}b)</td>
                      <td className="text-slate-400">{f.embargo_bars} bars</td>
                      <td className={f.train_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        ${f.train_pnl.toFixed(2)}
                      </td>
                      <td className={`font-bold ${f.test_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        ${f.test_pnl.toFixed(2)}
                      </td>
                      <td className="text-slate-300">{(f.train_win_rate * 100).toFixed(1)}%</td>
                      <td className="text-sky-300 font-bold">{(f.test_win_rate * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
