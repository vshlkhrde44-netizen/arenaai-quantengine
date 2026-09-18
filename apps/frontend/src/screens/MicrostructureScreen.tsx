import React, { useState, useEffect } from 'react';
import { MicrostructureSnapshot, FootprintLevel } from '../types';
import { fetchMicrostructure } from '../api';
import { Layers, Activity, ArrowRight, ShieldAlert } from 'lucide-react';

export const MicrostructureScreen: React.FC = () => {
  const [symbol, setSymbol] = useState<string>('BTC-USD');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadMicrostructure = async () => {
    try {
      const res = await fetchMicrostructure(symbol);
      setData(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadMicrostructure();
    const interval = setInterval(loadMicrostructure, 1500);
    return () => clearInterval(interval);
  }, [symbol]);

  const snap: MicrostructureSnapshot | null = data?.snapshot;
  const profile = data?.profile;
  const footprint: FootprintLevel[] = data?.footprint || [];

  return (
    <div className="space-y-4">
      {/* Header Selector */}
      <div className="flex items-center justify-between bg-[#0e141f] p-3 rounded border border-slate-800">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Symbol:</span>
          {['BTC-USD', 'ETH-USD', 'SOL-USD'].map((s) => (
            <button
              key={s}
              onClick={() => setSymbol(s)}
              className={`px-3 py-1.5 rounded text-xs font-mono font-bold ${
                symbol === s
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                  : 'bg-[#151c28] text-slate-400 border border-slate-800 hover:text-white'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-500">CVD: </span>
            <span className={`font-bold ${(snap?.cvd ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {(snap?.cvd ?? 0) >= 0 ? '+' : ''}{snap?.cvd ?? 0}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Aggression Ratio: </span>
            <span className="text-sky-400 font-bold">{snap?.trade_imbalance_ratio ?? '--'}x</span>
          </div>
          <div>
            <span className="text-slate-500">Absorption Alert: </span>
            <span className={`font-bold ${snap?.absorption_detected ? 'text-rose-400' : 'text-emerald-400'}`}>
              {snap?.absorption_detected ? 'DETECTED' : 'CLEAR'}
            </span>
          </div>
        </div>
      </div>

      {/* Semantic Firewall Banner */}
      <div className="bg-[#121622] border border-slate-800 p-2.5 rounded text-[11px] text-slate-400 font-mono flex items-center gap-3">
        <ShieldAlert size={16} className="text-amber-400 flex-shrink-0" />
        <div>
          <strong>Semantic Firewall Enforced:</strong> Aggressor trade != Liquidity sweep | Trade imbalance != Resting book imbalance | Candle direction != Aggressor side. Missing order book state is explicitly declared UNAVAILABLE, never fabricated.
        </div>
      </div>

      {/* Microstructure Metrics Tiles */}
      <div className="grid grid-cols-4 gap-3">
        <div className="metric-tile">
          <div className="metric-label">Cumulative Volume Delta (CVD)</div>
          <div className={`metric-val ${(snap?.cvd ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {(snap?.cvd ?? 0) >= 0 ? '+' : ''}{snap?.cvd ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Aggregated Net Taker Flow</div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Point of Control (POC)</div>
          <div className="metric-val text-amber-400">
            {profile?.poc_price ? `$${profile.poc_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Highest Volume Node</div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Value Area High (VAH)</div>
          <div className="metric-val text-emerald-400">
            {profile?.vah_price ? `$${profile.vah_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Top 70% Volume Boundary</div>
        </div>

        <div className="metric-tile">
          <div className="metric-label">Value Area Low (VAL)</div>
          <div className="metric-val text-rose-400">
            {profile?.val_price ? `$${profile.val_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Bottom 70% Volume Boundary</div>
        </div>
      </div>

      {/* Footprint Chart / Price Bin Table */}
      <div className="quant-card">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <div className="flex items-center gap-2">
            <Layers size={15} className="text-sky-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Footprint Matrix: Price Level x Buyer Volume x Seller Volume x Delta
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">Current Session Bins</span>
        </div>

        <div className="overflow-x-auto">
          <table className="quant-table">
            <thead>
              <tr>
                <th>Price Tick</th>
                <th>Buyer Volume (Taker Buy)</th>
                <th>Seller Volume (Taker Sell)</th>
                <th>Total Volume</th>
                <th>Net Level Delta</th>
                <th>Volume Share</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {footprint.map((lvl, idx) => {
                const isPOC = profile?.poc_price === lvl.price;
                const totalVol = profile?.total_volume || 1;
                const sharePct = ((lvl.total_volume / totalVol) * 100).toFixed(1);
                return (
                  <tr key={idx} className={isPOC ? 'bg-amber-500/10 border-l-2 border-amber-400' : ''}>
                    <td className="font-bold text-white flex items-center gap-2">
                      <span>${lvl.price.toFixed(2)}</span>
                      {isPOC && (
                        <span className="text-[9px] px-1 rounded bg-amber-500/20 text-amber-300 font-bold">
                          POC
                        </span>
                      )}
                    </td>
                    <td className="text-emerald-400">{lvl.buy_volume.toFixed(4)}</td>
                    <td className="text-rose-400">{lvl.sell_volume.toFixed(4)}</td>
                    <td className="text-slate-200">{lvl.total_volume.toFixed(4)}</td>
                    <td className={`font-bold ${lvl.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {lvl.delta >= 0 ? '+' : ''}{lvl.delta.toFixed(4)}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded h-1.5 overflow-hidden">
                          <div className="bg-sky-400 h-full" style={{ width: `${Math.min(100, Number(sharePct) * 2)}%` }}></div>
                        </div>
                        <span className="text-[10px] text-slate-400">{sharePct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {footprint.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-500">
                    Awaiting sufficient trade volume to render footprint bins...
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
