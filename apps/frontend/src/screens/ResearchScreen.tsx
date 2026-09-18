import React, { useState } from 'react';
import { runLookaheadTest } from '../api';
import { FlaskConical, ShieldCheck, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

export const ResearchScreen: React.FC = () => {
  const [strategyId, setStrategyId] = useState('strat_cvd_imbalance');
  const [lookaheadResult, setLookaheadResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const handleRunLookahead = async () => {
    setTesting(true);
    try {
      const res = await runLookaheadTest(strategyId);
      setLookaheadResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-purple-500/10 border border-purple-500/30 text-purple-400">
            <FlaskConical size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Quant Research Lab & Adversarial Lookahead Guard
            </div>
            <div className="text-xs text-slate-400">
              Hypothesis testing, causal validation, and automated lookahead leakage detection.
            </div>
          </div>
        </div>
      </div>

      {/* Adversarial Lookahead Protector Card */}
      <div className="quant-card space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Adversarial Lookahead Leakage Test
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Invariance Theorem: Signal(bars[0:t]) == Signal(bars[0:T])[t]
          </span>
        </div>

        <div className="text-xs text-slate-300">
          The lookahead guard subjects the strategy to two adversarial tests:
          <ul className="list-disc list-inside mt-1.5 space-y-1 text-slate-400 font-mono text-[11px]">
            <li><strong>Truncation Invariance:</strong> Evaluates bar <i>t</i> on truncated data vs future data. If future bars alter past signals, lookahead is flagged.</li>
            <li><strong>Future Perturbation:</strong> Multiplies future bars (t+1..T) by 1.5x. Past signals must remain 100% invariant.</li>
          </ul>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <select
            value={strategyId}
            onChange={(e) => setStrategyId(e.target.value)}
            className="bg-[#0b1018] border border-slate-800 rounded px-3 py-1.5 text-xs text-white font-mono"
          >
            <option value="strat_cvd_imbalance">Microstructure CVD Imbalance (strat_cvd_imbalance)</option>
            <option value="strat_poc_breakout">Volume Profile Breakout (strat_poc_breakout)</option>
          </select>

          <button
            onClick={handleRunLookahead}
            disabled={testing}
            className="btn-primary text-xs flex items-center gap-2"
          >
            <FlaskConical size={14} />
            <span>{testing ? 'Running Adversarial Tests...' : 'Execute Lookahead Attack Test'}</span>
          </button>
        </div>

        {lookaheadResult && (
          <div className="mt-4 p-4 rounded bg-[#0b1018] border border-slate-800 font-mono text-xs space-y-2.5">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="text-slate-400">Overall Causal Lookahead Status:</span>
              <span className={`font-bold px-2 py-0.5 rounded ${
                lookaheadResult.status === 'PASS'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}>
                {lookaheadResult.status === 'PASS' ? 'CAUSAL PURITY CERTIFIED (PASS)' : 'LEAKAGE DETECTED (FAIL)'}
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-800/80">
              <span className="text-slate-400">Truncation Invariance Test:</span>
              <span className={lookaheadResult.causal_invariance_passed ? 'text-emerald-400 font-bold flex items-center gap-1' : 'text-rose-400 font-bold'}>
                {lookaheadResult.causal_invariance_passed ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                {lookaheadResult.causal_invariance_passed ? 'PASSED (0 Discrepancies)' : lookaheadResult.causal_invariance_error}
              </span>
            </div>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-400">Future Perturbation Test:</span>
              <span className={lookaheadResult.future_perturbation_passed ? 'text-emerald-400 font-bold flex items-center gap-1' : 'text-rose-400 font-bold'}>
                {lookaheadResult.future_perturbation_passed ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                {lookaheadResult.future_perturbation_passed ? 'PASSED (Future has 0 influence on past)' : lookaheadResult.future_perturbation_error}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
