import React, { useState, useEffect } from 'react';
import { triggerEmergencyStop, resetEmergencyStop } from '../api';
import { ShieldCheck, Octagon, AlertTriangle, CheckCircle2 } from 'lucide-react';

export const RiskScreen: React.FC = () => {
  const [riskData, setRiskData] = useState<any>(null);
  const [acting, setActing] = useState(false);

  const loadRisk = async () => {
    try {
      const res = await fetch('/api/risk/status');
      const data = await res.json();
      setRiskData(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadRisk();
    const interval = setInterval(loadRisk, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleEmergency = async () => {
    setActing(true);
    try {
      if (riskData?.emergency_stop_active) {
        await resetEmergencyStop();
      } else {
        await triggerEmergencyStop();
      }
      loadRisk();
    } catch (e) {
      console.error(e);
    } finally {
      setActing(false);
    }
  };

  const limits = riskData?.limits;
  const isEmergency = riskData?.emergency_stop_active;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400">
            <ShieldCheck size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Centralized Risk Engine & Pre-Trade Safety Firewall
            </div>
            <div className="text-xs text-slate-400">
              Deterministic pre-trade risk validation, position caps, daily drawdown limits, and Emergency Stop.
            </div>
          </div>
        </div>

        <button
          onClick={handleToggleEmergency}
          disabled={acting}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold font-mono transition-all border ${
            isEmergency
              ? 'bg-amber-500/20 text-amber-300 border-amber-500 hover:bg-amber-500/30'
              : 'bg-rose-950/40 text-rose-300 border-rose-600 hover:bg-rose-900/60'
          }`}
        >
          <Octagon size={14} className={isEmergency ? 'text-amber-400' : 'text-rose-400'} />
          <span>{isEmergency ? 'CLEAR EMERGENCY STOP' : 'TRIGGER EMERGENCY STOP'}</span>
        </button>
      </div>

      {/* Emergency Stop Status Alert Banner */}
      {isEmergency && (
        <div className="bg-rose-500/15 border border-rose-500/50 p-3 rounded font-mono text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle size={16} className="text-rose-400 animate-pulse" />
          <span>EMERGENCY STOP ACTIVE: All paper order routing is immediately blocked. Existing positions are protected.</span>
        </div>
      )}

      {/* Risk Limits Matrix */}
      <div className="grid grid-cols-3 gap-3 font-mono text-xs">
        <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase mb-1">Max Order Notional</span>
          <span className="text-base font-bold text-white">${limits?.max_order_notional_usd?.toLocaleString() ?? '10,000'}</span>
          <span className="text-[10px] text-slate-400 block mt-1">Per-order firewall limit</span>
        </div>

        <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase mb-1">Max Daily Loss</span>
          <span className="text-base font-bold text-rose-400">${limits?.max_daily_loss_usd?.toLocaleString() ?? '2,500'}</span>
          <span className="text-[10px] text-slate-400 block mt-1">Hard circuit breaker threshold</span>
        </div>

        <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase mb-1">Max Portfolio Exposure</span>
          <span className="text-base font-bold text-sky-400">${limits?.max_portfolio_exposure_usd?.toLocaleString() ?? '100,000'}</span>
          <span className="text-[10px] text-slate-400 block mt-1">Gross notional ceiling</span>
        </div>

        <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase mb-1">Max Concurrent Positions</span>
          <span className="text-base font-bold text-white">{limits?.max_concurrent_positions ?? 5} Symbols</span>
          <span className="text-[10px] text-slate-400 block mt-1">Active symbol limit</span>
        </div>

        <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase mb-1">Trade Cooldown</span>
          <span className="text-base font-bold text-amber-400">{limits?.cooldown_period_seconds ?? 30} Seconds</span>
          <span className="text-[10px] text-slate-400 block mt-1">Minimum inter-trade pause</span>
        </div>

        <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
          <span className="text-slate-500 block text-[10px] uppercase mb-1">Fail-Closed on Unknown Risk</span>
          <span className="text-base font-bold text-emerald-400">ENFORCED</span>
          <span className="text-[10px] text-slate-400 block mt-1">Zero ambiguous submissions</span>
        </div>
      </div>

      {/* Risk Events History */}
      <div className="quant-card">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Recent Risk Events & Rejections
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            Total Critical Events: {riskData?.total_critical_breaches ?? 0}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="quant-table font-mono text-xs">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>Rule Name</th>
                <th>Severity</th>
                <th>Observed</th>
                <th>Limit</th>
              </tr>
            </thead>
            <tbody>
              {riskData?.recent_events?.map((ev: any) => (
                <tr key={ev.event_id}>
                  <td className="text-slate-400">{new Date(ev.timestamp).toLocaleTimeString()}</td>
                  <td className="font-bold text-white">{ev.event_type}</td>
                  <td className="text-slate-300">{ev.rule_name}</td>
                  <td>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      ev.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-300'
                    }`}>
                      {ev.severity}
                    </span>
                  </td>
                  <td className="text-slate-300">{ev.metric_value}</td>
                  <td className="text-slate-400">{ev.threshold_value}</td>
                </tr>
              ))}
              {(!riskData?.recent_events || riskData.recent_events.length === 0) && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-500">
                    No risk breaches or emergency stops recorded. Risk engine operating within normal limits.
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
