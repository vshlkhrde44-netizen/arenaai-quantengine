import React, { useState } from 'react';
import { runMonteCarlo } from '../api';
import { Scale, RefreshCw, BarChart2, ShieldCheck, Activity } from 'lucide-react';

export const StatisticalLabScreen: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await runMonteCarlo('strat_cvd_imbalance');
      setData(res);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const mc = data?.monte_carlo;
  const boot = data?.bootstrap_ci;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <Scale size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Statistical Inference & Monte Carlo Reshuffling Lab
            </div>
            <div className="text-xs text-slate-400">
              Permutation reshuffling for sequence risk, bootstrap confidence intervals, and multiple-testing corrections.
            </div>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="btn-primary text-xs flex items-center gap-1.5"
        >
          <Scale size={14} />
          <span>{loading ? 'Simulating 500 Permutations...' : 'Run Monte Carlo & Bootstrap'}</span>
        </button>
      </div>

      {data && (
        <>
          {/* Key Monte Carlo Metrics */}
          <div className="grid grid-cols-4 gap-3">
            <div className="metric-tile">
              <div className="metric-label">95th Percentile Max Drawdown</div>
              <div className="metric-val text-rose-400 font-mono">
                {mc?.expected_drawdown_95th_percentile?.toFixed(2)}%
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Permutation tail risk</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Median Final P&L</div>
              <div className={`metric-val ${(mc?.expected_final_pnl_median ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                ${mc?.expected_final_pnl_median?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">500 reshuffles</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Probability of Ruin (50% Loss)</div>
              <div className="metric-val text-emerald-400 font-mono">
                {mc?.probability_of_ruin_pct?.toFixed(2)}%
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Simulated sequences</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Bootstrap Win Rate (95% CI)</div>
              <div className="metric-val text-sky-400 font-mono text-base">
                [{(boot?.win_rate?.ci_lower_95 * 100).toFixed(1)}% - {(boot?.win_rate?.ci_upper_95 * 100).toFixed(1)}%]
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Mean: {(boot?.win_rate?.sample_mean * 100).toFixed(1)}%</div>
            </div>
          </div>

          {/* Drawdown Quantiles Card */}
          <div className="quant-card space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Monte Carlo Drawdown Distribution Percentiles
              </span>
              <span className="text-[10px] font-mono text-slate-400">Input Population Hash: {mc?.input_population_hash?.slice(0, 16)}...</span>
            </div>

            <div className="grid grid-cols-5 gap-3 font-mono text-center">
              {['5th Percentile', '25th Percentile', '50th (Median)', '75th Percentile', '95th (Worst-Case)'].map((label, idx) => {
                const val = mc?.distribution_drawdowns?.[idx] ?? 0;
                return (
                  <div key={idx} className="bg-[#0b1018] p-3 rounded border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase mb-1">{label}</div>
                    <div className="text-sm font-bold text-white">{val.toFixed(2)}%</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Multiple Testing Correction Info */}
          <div className="quant-card">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Multiple-Testing Correction Framework
              </span>
              <span className="text-[10px] font-mono text-sky-400">FWER & FDR Control</span>
            </div>

            <div className="grid grid-cols-3 gap-3 font-mono text-xs">
              <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
                <div className="text-slate-300 font-bold mb-1">Bonferroni Single-Step</div>
                <div className="text-[11px] text-slate-400 mb-2">Alpha_adj = Alpha / M (Strict Family-Wise Error Rate)</div>
                <span className="text-emerald-400 font-bold">Standard Invariant</span>
              </div>
              <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
                <div className="text-slate-300 font-bold mb-1">Holm-Bonferroni Step-Down</div>
                <div className="text-[11px] text-slate-400 mb-2">Sequential step-down adjustment with higher statistical power.</div>
                <span className="text-sky-400 font-bold">Recommended for Variants</span>
              </div>
              <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
                <div className="text-slate-300 font-bold mb-1">Benjamini-Hochberg FDR</div>
                <div className="text-[11px] text-slate-400 mb-2">Controls False Discovery Rate across multi-parameter sweeps.</div>
                <span className="text-amber-400 font-bold">High-Throughput Mode</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
