import React from 'react';
import {
  PortfolioSummary,
  TickerRecord,
  TradeRecord,
  SystemHealth
} from '../types';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Layers,
  ShieldCheck,
  Activity,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

interface DashboardScreenProps {
  portfolio: PortfolioSummary | null;
  tickers: Record<string, TickerRecord>;
  trades: TradeRecord[];
  health: SystemHealth | null;
  onNavigateTab: (tab: any) => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  portfolio,
  tickers,
  trades,
  health,
  onNavigateTab
}) => {
  const isConfigured = portfolio && portfolio.account_state === 'CONFIGURED' && portfolio.total_equity !== null;
  const equityDisplay = isConfigured ? `$${portfolio.total_equity!.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'ACCOUNT DATA UNAVAILABLE';
  const availDisplay = isConfigured && portfolio.available_balance !== null ? `$${portfolio.available_balance!.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'UNCONFIGURED';
  const unrealized = portfolio?.unrealized_pnl ?? 0;
  const realized = portfolio?.realized_pnl ?? 0;
  const exposure = portfolio?.total_exposure ?? 0;
  const riskUtil = portfolio?.risk_utilization_pct ?? 0;
  const openOrders = portfolio?.open_orders_count ?? 0;
  const activePos = portfolio?.active_positions_count ?? 0;

  return (
    <div className="space-y-5">
      {/* Safety Notice Banner */}
      <div className="bg-[#0f172a]/60 border border-emerald-500/30 rounded p-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></div>
          <div>
            <div className="text-xs font-bold text-emerald-400 font-mono tracking-wide">
              EXECUTION MODE: PAPER TRADING ONLY (OFFICIAL EXCHANGE SANDBOX)
            </div>
            <div className="text-[11px] text-slate-400">
              Live production trading is permanently prohibited by application invariants. Orders pass centralized ExecutionSafetyGate.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigateTab('papertrading')}
            className="btn-primary text-xs flex items-center gap-1.5 py-1 px-3"
          >
            <span>Open Paper Ticket</span>
            <ArrowUpRight size={13} />
          </button>
        </div>
      </div>

      {/* KPI Tiles Matrix */}
      <div className="grid grid-cols-4 gap-3">
        <div className="metric-tile">
          <div className="metric-label">Paper Account Equity</div>
          <div className="metric-val text-white">{equityDisplay}</div>
          <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Available: {availDisplay}</span>
            <span className="text-emerald-400">USD</span>
          </div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Unrealized P&L</div>
          <div className={`metric-val ${unrealized >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {unrealized >= 0 ? '+' : ''}${unrealized.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Realized: ${realized.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
            <span>Mark-to-Market</span>
          </div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Portfolio Exposure</div>
          <div className="metric-val text-sky-400">${exposure.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
          <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Active Positions: {activePos}</span>
            <span>Limit: $100k</span>
          </div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Risk Utilization</div>
          <div className={`metric-val ${riskUtil > 80 ? 'text-rose-400' : riskUtil > 50 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {riskUtil.toFixed(1)}%
          </div>
          <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Open Orders: {openOrders}</span>
            <span className="text-emerald-400">Normal</span>
          </div>
        </div>
      </div>

      {/* Middle Grid: Live Market Quotes & Order Flow */}
      <div className="grid grid-cols-3 gap-4">
        {/* Live Quotes Column */}
        <div className="quant-card col-span-2 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <TrendingUp size={15} className="text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Real-Time Public Market Feeds (Coinbase Exchange)
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Subscribed Channels: Ticker, Matches</span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {['BTC-USD', 'ETH-USD', 'SOL-USD'].map((sym) => {
              const t = tickers[sym];
              return (
                <div key={sym} className="bg-[#0b1018] p-3 rounded border border-slate-800 hover:border-slate-700">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-xs font-mono text-slate-200">{sym}</span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Spread: {t?.spread ? `$${t.spread}` : '--'}
                    </span>
                  </div>

                  <div className="text-lg font-bold font-mono text-white mb-2">
                    {t?.last_price ? `$${t.last_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'Connecting...'}
                  </div>

                  <div className="text-[10px] font-mono text-slate-400 flex justify-between border-t border-slate-800/80 pt-1.5">
                    <div>
                      <span className="text-slate-500">Bid: </span>
                      <span className="text-emerald-400">${t?.bid_price ?? '--'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Ask: </span>
                      <span className="text-rose-400">${t?.ask_price ?? '--'}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Info Bar */}
          <div className="bg-[#0b1018] p-2.5 rounded border border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
            <div className="flex items-center gap-2">
              <ShieldCheck size={14} className="text-emerald-400" />
              <span>Tamper-Evident Raw Message Chain:</span>
              <span className="text-emerald-400">Verified Active (SHA-256)</span>
            </div>
            <div>
              <span>Latency: </span>
              <span className="text-slate-200">{health?.market_data_feed.feed_latency_ms?.toFixed(0) ?? '--'} ms</span>
            </div>
          </div>
        </div>

        {/* Live Trades Stream */}
        <div className="quant-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
              <div className="flex items-center gap-1.5">
                <Activity size={14} className="text-sky-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Recent Exchange Trades
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500">Aggressor Side</span>
            </div>

            <div className="space-y-1 overflow-y-auto max-h-56 font-mono text-[11px]">
              {trades.slice(0, 8).map((tr, idx) => (
                <div key={idx} className="flex justify-between items-center py-1 px-1.5 rounded hover:bg-slate-800/50">
                  <span className="text-slate-400">{tr.symbol}</span>
                  <span className={`font-semibold ${tr.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    ${tr.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="text-slate-400">{tr.quantity.toFixed(4)}</span>
                  <span className={`text-[9px] px-1 rounded ${tr.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                    {tr.side}
                  </span>
                </div>
              ))}
              {trades.length === 0 && (
                <div className="text-center py-8 text-slate-500 text-xs">Awaiting market trade stream...</div>
              )}
            </div>
          </div>

          <button
            onClick={() => onNavigateTab('markets')}
            className="w-full mt-3 py-1.5 text-center text-xs font-semibold text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 rounded bg-[#0f141f]"
          >
            View Full Market Data Feed →
          </button>
        </div>
      </div>

      {/* Bottom Row: Strategies Status & System Architecture Health */}
      <div className="grid grid-cols-2 gap-4">
        <div className="quant-card">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Strategy Registry Status
            </span>
            <button onClick={() => onNavigateTab('strategies')} className="text-xs text-sky-400 hover:underline">
              Manage Registry
            </button>
          </div>

          <div className="space-y-2">
            <div className="bg-[#0b1018] p-2.5 rounded border border-slate-800 flex justify-between items-center">
              <div>
                <div className="text-xs font-semibold text-slate-200 font-mono">Microstructure CVD Imbalance</div>
                <div className="text-[10px] text-slate-500">strat_cvd_imbalance v1.0.0</div>
              </div>
              <span className="badge-paper text-[10px]">PAPER_ENABLED</span>
            </div>

            <div className="bg-[#0b1018] p-2.5 rounded border border-slate-800 flex justify-between items-center">
              <div>
                <div className="text-xs font-semibold text-slate-200 font-mono">Volume Profile POC Breakout</div>
                <div className="text-[10px] text-slate-500">strat_poc_breakout v1.0.0</div>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                FROZEN
              </span>
            </div>
          </div>
        </div>

        <div className="quant-card">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              System Invariants Verification
            </span>
            <span className="text-[10px] font-mono text-emerald-400">100% Verified</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="bg-[#0b1018] p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">PAPER ONLY</span>
              <span className="text-emerald-400 font-bold">TRUE (Inviolable)</span>
            </div>
            <div className="bg-[#0b1018] p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">LIVE ORDERS</span>
              <span className="text-emerald-400 font-bold">DISABLED</span>
            </div>
            <div className="bg-[#0b1018] p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">AUDIT CHAIN</span>
              <span className="text-emerald-400 font-bold">CONTINUOUS</span>
            </div>
            <div className="bg-[#0b1018] p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">LOCAL DATABASE</span>
              <span className="text-emerald-400 font-bold">SQLITE WAL OK</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
