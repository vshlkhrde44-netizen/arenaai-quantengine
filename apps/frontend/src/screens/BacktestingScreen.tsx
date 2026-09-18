import React, { useState } from 'react';
import { BacktestResult } from '../types';
import { runBacktest } from '../api';
import { PlaySquare, TrendingUp, DollarSign, RefreshCw, BarChart2 } from 'lucide-react';

export const BacktestingScreen: React.FC = () => {
  const [strategyId, setStrategyId] = useState('strat_cvd_imbalance');
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [running, setRunning] = useState(false);

  const handleRunBacktest = async () => {
    setRunning(true);
    try {
      const res = await runBacktest(strategyId);
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
          <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <PlaySquare size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Deterministic Backtesting Engine
            </div>
            <div className="text-xs text-slate-400">
              Causal bar-by-bar backtesting: Signal at close(t) executed at open(t+1). Transparent fee & slippage ladders.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={strategyId}
            onChange={(e) => setStrategyId(e.target.value)}
            className="bg-[#0b1018] border border-slate-800 rounded px-3 py-1.5 text-xs text-white font-mono"
          >
            <option value="strat_cvd_imbalance">Microstructure CVD Imbalance</option>
            <option value="strat_poc_breakout">Volume Profile Breakout</option>
          </select>

          <button
            onClick={handleRunBacktest}
            disabled={running}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            <PlaySquare size={14} />
            <span>{running ? 'Simulating Backtest...' : 'Execute Backtest'}</span>
          </button>
        </div>
      </div>

      {result && (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-4 gap-3">
            <div className="metric-tile">
              <div className="metric-label">Net P&L (After Costs)</div>
              <div className={`metric-val ${result.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {result.net_pnl >= 0 ? '+' : ''}${result.net_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                <span>Gross: ${result.gross_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                <span className="text-rose-400">Fees: -${result.total_fees.toFixed(2)}</span>
              </div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Win Rate / Profit Factor</div>
              <div className="metric-val text-sky-400">
                {(result.win_rate * 100).toFixed(1)}% <span className="text-xs text-slate-500">({result.profit_factor} PF)</span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                <span>Wins: {result.winning_trades}</span>
                <span>Losses: {result.losing_trades}</span>
              </div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Sharpe & Sortino</div>
              <div className="metric-val text-amber-400">
                {result.sharpe_ratio ?? '--'} <span className="text-xs text-slate-500">(Sortino: {result.sortino_ratio ?? '--'})</span>
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Annualized 252 days</div>
            </div>

            <div className="metric-tile">
              <div className="metric-label">Max Drawdown</div>
              <div className="metric-val text-rose-400">
                {result.max_drawdown_pct.toFixed(2)}%
              </div>
              <div className="text-[10px] text-slate-400 mt-1">Peak-to-Trough</div>
            </div>
          </div>

          {/* Cryptographic Hashes Bar */}
          <div className="bg-[#0b1018] p-3 rounded border border-slate-800 font-mono text-[11px] text-slate-400 flex items-center justify-between">
            <div>
              <span>Run ID: </span>
              <span className="text-white font-bold">{result.run_id}</span>
            </div>
            <div>
              <span>Dataset Digest: </span>
              <span className="text-sky-400">{result.dataset_hash.slice(0, 16)}...</span>
            </div>
            <div>
              <span>Result Hash: </span>
              <span className="text-emerald-400 font-bold">{result.result_hash.slice(0, 16)}...</span>
            </div>
          </div>

          {/* Trades Log Table */}
          <div className="quant-card">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Simulated Execution Log ({result.total_trades} Trades)
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                Gross, Fees & Slippage Transparently Isolated
              </span>
            </div>

            <div className="overflow-x-auto max-h-80">
              <table className="quant-table font-mono text-xs">
                <thead>
                  <tr>
                    <th>Trade ID</th>
                    <th>Side</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>Quantity</th>
                    <th>Gross P&L</th>
                    <th>Fees</th>
                    <th>Net P&L</th>
                    <th>Exit Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, idx) => (
                    <tr key={idx}>
                      <td className="text-slate-400">{t.trade_id}</td>
                      <td>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                          t.side === 'LONG' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="text-slate-200">${t.entry_price.toFixed(2)}</td>
                      <td className="text-slate-200">${t.exit_price.toFixed(2)}</td>
                      <td className="text-slate-400">{t.quantity.toFixed(4)}</td>
                      <td className={t.gross_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        ${t.gross_pnl.toFixed(2)}
                      </td>
                      <td className="text-slate-400">-${t.fees.toFixed(2)}</td>
                      <td className={`font-bold ${t.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        ${t.net_pnl.toFixed(2)}
                      </td>
                      <td className="text-slate-400 text-[10px]">{t.exit_reason}</td>
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
