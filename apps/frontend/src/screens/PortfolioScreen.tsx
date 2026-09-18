import React from 'react';
import { PortfolioSummary } from '../types';
import { PieChart, DollarSign, ShieldCheck, TrendingUp } from 'lucide-react';

interface PortfolioScreenProps {
  portfolio: PortfolioSummary | null;
}

export const PortfolioScreen: React.FC<PortfolioScreenProps> = ({ portfolio }) => {
  const isConfigured = portfolio && portfolio.account_state === 'CONFIGURED' && portfolio.total_equity !== null;
  const equityDisplay = isConfigured ? `$${portfolio.total_equity!.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'ACCOUNT DATA UNAVAILABLE';
  const availDisplay = isConfigured && portfolio.available_balance !== null ? `$${portfolio.available_balance!.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'UNCONFIGURED';
  const locked = portfolio?.locked_balance ?? 0;
  const exposure = portfolio?.total_exposure ?? 0;
  const unrealized = portfolio?.unrealized_pnl ?? 0;
  const realized = portfolio?.realized_pnl ?? 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <PieChart size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Portfolio Ledger & Capital Accounting
            </div>
            <div className="text-xs text-slate-400">
              Institutional portfolio-level accounting, equity valuation, and margin conservation.
            </div>
          </div>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-4 gap-3">
        <div className="metric-tile">
          <div className="metric-label">Total Portfolio Equity</div>
          <div className="metric-val text-white">{equityDisplay}</div>
          <div className="text-[10px] text-slate-400 mt-1">Cash + Unrealized P&L</div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Available Cash (USD)</div>
          <div className="metric-val text-emerald-400">{availDisplay}</div>
          <div className="text-[10px] text-slate-400 mt-1">Ready for Allocation</div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Total Market Exposure</div>
          <div className="metric-val text-sky-400">${exposure.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
          <div className="text-[10px] text-slate-400 mt-1">Sum of absolute notionals</div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Margin Utilization</div>
          <div className="metric-val text-amber-400 font-mono">
            {portfolio?.margin_utilization_pct?.toFixed(2) ?? 0}%
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Exposure / Equity</div>
        </div>
      </div>

      {/* Capital Allocation Card */}
      <div className="quant-card space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Paper Asset Allocation Ledger
          </span>
          <span className="text-[10px] font-mono text-emerald-400">Reconciled with Sandbox</span>
        </div>

        <div className="grid grid-cols-4 gap-3 font-mono text-xs">
          <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase mb-1">USD Cash</span>
            <span className="text-base font-bold text-white">{availDisplay}</span>
            <span className="text-[10px] text-slate-400 block mt-1">Base Currency</span>
          </div>

          <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase mb-1">BTC Balance</span>
            <span className="text-base font-bold text-sky-400">0.0000 BTC</span>
            <span className="text-[10px] text-slate-400 block mt-1">Paper Asset</span>
          </div>

          <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase mb-1">ETH Balance</span>
            <span className="text-base font-bold text-purple-400">0.0000 ETH</span>
            <span className="text-[10px] text-slate-400 block mt-1">Paper Asset</span>
          </div>

          <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase mb-1">SOL Balance</span>
            <span className="text-base font-bold text-amber-400">0.0000 SOL</span>
            <span className="text-[10px] text-slate-400 block mt-1">Paper Asset</span>
          </div>
        </div>
      </div>
    </div>
  );
};
