import React, { useState, useEffect } from 'react';
import { ShieldAlert, Activity, Octagon, CheckCircle2, RefreshCw } from 'lucide-react';
import { triggerEmergencyStop, resetEmergencyStop } from '../api';

interface TopBarProps {
  isConnected: boolean;
  feedLatencyMs: number | null;
  venue: string;
  emergencyStopActive: boolean;
  onRefreshHealth: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  isConnected,
  feedLatencyMs,
  venue,
  emergencyStopActive,
  onRefreshHealth
}) => {
  const [utcTime, setUtcTime] = useState<string>('');
  const [isActing, setIsActing] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleEmergencyStop = async () => {
    setIsActing(true);
    try {
      if (emergencyStopActive) {
        await resetEmergencyStop();
      } else {
        await triggerEmergencyStop();
      }
      onRefreshHealth();
    } catch (e) {
      console.error(e);
    } finally {
      setIsActing(false);
    }
  };

  return (
    <header className="bg-[#0b0e14] border-b border-[#1e293b] px-5 py-2.5 flex items-center justify-between select-none">
      {/* Brand & Safety Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center text-emerald-400 font-black text-xs">
            AQ
          </div>
          <span className="font-bold tracking-wider text-sm uppercase text-slate-100">
            Antigravity <span className="text-emerald-400">QuantEngine</span>
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
            v1.0.0-PROD
          </span>
        </div>

        {/* Global Safety Enforcement Badge */}
        <div className="flex items-center gap-2 pl-3 border-l border-slate-800">
          <div className="badge-paper font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            PAPER TRADING ONLY
          </div>
          <div className="badge-danger font-mono text-[10px]">
            <ShieldAlert size={12} />
            LIVE TRADING PERMANENTLY DISABLED
          </div>
        </div>
      </div>

      {/* Real-Time Market Data Stream Indicators & Actions */}
      <div className="flex items-center gap-4">
        {/* Connection & Latency */}
        <div className="flex items-center gap-3 text-xs bg-[#111622] px-3 py-1.5 rounded border border-slate-800 font-mono">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span className="text-slate-300 uppercase">{venue} WS</span>
          </div>

          <span className="text-slate-600">|</span>

          <div className="flex items-center gap-1 text-slate-400">
            <Activity size={12} className={isConnected ? 'text-emerald-400' : 'text-slate-600'} />
            <span>{feedLatencyMs !== null ? `${feedLatencyMs.toFixed(0)} ms` : '--'}</span>
          </div>

          <span className="text-slate-600">|</span>

          <span className="text-slate-400">{utcTime || 'UTC'}</span>
        </div>

        {/* Emergency Stop Button */}
        <button
          onClick={handleToggleEmergencyStop}
          disabled={isActing}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold transition-all border ${
            emergencyStopActive
              ? 'bg-amber-500/20 text-amber-300 border-amber-500 hover:bg-amber-500/30'
              : 'bg-rose-950/40 text-rose-300 border-rose-600 hover:bg-rose-900/60'
          }`}
          title={emergencyStopActive ? 'Click to reset emergency stop' : 'Click to halt all paper order execution'}
        >
          <Octagon size={13} className={emergencyStopActive ? 'text-amber-400' : 'text-rose-400'} />
          <span>{emergencyStopActive ? 'RESET EMERGENCY STOP' : 'STOP PAPER TRADING'}</span>
        </button>

        <button
          onClick={onRefreshHealth}
          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
          title="Refresh All Systems"
        >
          <RefreshCw size={13} />
        </button>
      </div>
    </header>
  );
};
