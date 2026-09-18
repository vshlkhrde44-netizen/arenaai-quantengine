import React from 'react';
import { PositionRecord } from '../types';
import { Briefcase, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface PositionsScreenProps {
  positions: PositionRecord[];
}

export const PositionsScreen: React.FC<PositionsScreenProps> = ({ positions }) => {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <Briefcase size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Paper Positions & Mark-to-Market Accounting
            </div>
            <div className="text-xs text-slate-400">
              Deterministic position state machine tracking long/short positions, cost basis, realized & unrealized P&L.
            </div>
          </div>
        </div>
      </div>

      {/* Positions Table */}
      <div className="quant-card">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Current Position Book ({positions.length})
          </span>
          <span className="text-[10px] font-mono text-slate-400">Live Mark-to-Market Pricing</span>
        </div>

        <div className="overflow-x-auto">
          <table className="quant-table font-mono text-xs">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Avg Entry Price</th>
                <th>Market Price</th>
                <th>Unrealized P&L</th>
                <th>Realized P&L</th>
                <th>Cumulative Fees</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.symbol}>
                  <td className="font-bold text-white">{p.symbol}</td>
                  <td>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                        p.side === 'LONG'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : p.side === 'SHORT'
                          ? 'bg-rose-500/20 text-rose-400'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {p.side}
                    </span>
                  </td>
                  <td className="text-slate-200">{p.quantity.toFixed(4)}</td>
                  <td className="text-slate-300">${p.average_entry_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                  <td className="text-white font-semibold">${p.current_market_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                  <td className={`font-bold ${p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl.toFixed(2)}
                  </td>
                  <td className={`font-bold ${p.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {p.realized_pnl >= 0 ? '+' : ''}${p.realized_pnl.toFixed(2)}
                  </td>
                  <td className="text-slate-400">${p.cumulative_fees.toFixed(4)}</td>
                  <td className="text-slate-500 text-[11px]">{new Date(p.last_updated).toLocaleTimeString()}</td>
                </tr>
              ))}
              {positions.length === 0 && (
                <tr>
                  <td colSpan={9} className="text-center py-10 text-slate-500">
                    No active positions currently open.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
