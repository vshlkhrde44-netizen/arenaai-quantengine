import React, { useState, useEffect } from 'react';
import { StrategyRecord } from '../types';
import { fetchStrategies, freezeStrategy, promoteStrategy } from '../api';
import { Cpu, ShieldCheck, Lock, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export const StrategiesScreen: React.FC = () => {
  const [strategies, setStrategies] = useState<StrategyRecord[]>([]);
  const [selectedStrat, setSelectedStrat] = useState<StrategyRecord | null>(null);
  const [promoteAuthor, setPromoteAuthor] = useState('Lead_Quant_Architect');
  const [promoteReason, setPromoteReason] = useState('Passed statistical bootstrap and causal lookahead invariance.');
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadStrategies = async () => {
    try {
      const res = await fetchStrategies();
      setStrategies(res);
      if (res.length > 0 && !selectedStrat) {
        setSelectedStrat(res[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStrategies();
  }, []);

  const handleFreeze = async (id: string) => {
    try {
      const res = await freezeStrategy(id);
      setActionMsg(res.message);
      loadStrategies();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handlePromote = async (id: string) => {
    try {
      const res = await promoteStrategy(id, promoteAuthor, promoteReason);
      setActionMsg(res.message);
      loadStrategies();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <Cpu size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Strategy Registry & Freezing Firewall
            </div>
            <div className="text-xs text-slate-400">
              Version-controlled quant strategy definitions with deterministic SHA-256 hashes and human-authorized promotion.
            </div>
          </div>
        </div>

        {actionMsg && (
          <div className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded border border-emerald-500/30">
            {actionMsg}
          </div>
        )}
      </div>

      {/* Strategies Grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* List of Strategies */}
        <div className="space-y-3">
          {strategies.map((strat) => {
            const isSelected = selectedStrat?.strategy_id === strat.strategy_id;
            return (
              <div
                key={strat.strategy_id}
                onClick={() => setSelectedStrat(strat)}
                className={`quant-card cursor-pointer transition-all ${
                  isSelected ? 'border-sky-500/60 bg-[#121927]' : 'hover:border-slate-700'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="font-bold text-xs font-mono text-slate-100">{strat.name}</div>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      strat.status === 'PAPER_ENABLED'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : strat.status === 'FROZEN'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {strat.status}
                  </span>
                </div>

                <div className="text-[11px] text-slate-400 line-clamp-2 mb-3">
                  {strat.description || 'Institutional quantitative alpha model.'}
                </div>

                <div className="text-[10px] font-mono text-slate-500 flex justify-between border-t border-slate-800/80 pt-2">
                  <span>Version: v{strat.current_version}</span>
                  <span>ID: {strat.strategy_id}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detail & Firewall Actions Column */}
        {selectedStrat && (
          <div className="quant-card col-span-2 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold font-mono text-white">{selectedStrat.name}</h3>
                <span className="text-xs text-slate-400 font-mono">Strategy ID: {selectedStrat.strategy_id}</span>
              </div>
              <span className="badge-info font-mono text-xs">v{selectedStrat.current_version}</span>
            </div>

            {/* Cryptographic Hashes */}
            <div className="bg-[#0b1018] p-3 rounded border border-slate-800 font-mono text-xs space-y-2">
              <div className="flex justify-between items-center py-1 border-b border-slate-800/80">
                <span className="text-slate-500">Source Code Hash:</span>
                <span className="text-sky-400 truncate max-w-sm">{selectedStrat.code_hash}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800/80">
                <span className="text-slate-500">Configuration Hash:</span>
                <span className="text-emerald-400 truncate max-w-sm">{selectedStrat.config_hash}</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-500">Created Timestamp:</span>
                <span className="text-slate-300">{new Date(selectedStrat.created_at).toLocaleString()}</span>
              </div>
            </div>

            {/* Promotion Firewall Box */}
            <div className="bg-[#101726] p-4 rounded border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold font-mono text-slate-200">
                <ShieldCheck size={16} className="text-emerald-400" />
                <span>Strategy Promotion Firewall</span>
              </div>
              <div className="text-xs text-slate-400">
                A strategy cannot automatically enter paper trading. Promotion requires verification that the strategy is FROZEN and explicitly approved by an authorized quant reviewer with a recorded reason.
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[10px] font-mono text-slate-400 block mb-1 uppercase">Authorized Reviewer</label>
                  <input
                    type="text"
                    value={promoteAuthor}
                    onChange={(e) => setPromoteAuthor(e.target.value)}
                    className="w-full bg-[#0a0e16] border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-slate-400 block mb-1 uppercase">Audit Rationale</label>
                  <input
                    type="text"
                    value={promoteReason}
                    onChange={(e) => setPromoteReason(e.target.value)}
                    className="w-full bg-[#0a0e16] border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                {selectedStrat.status === 'DRAFT' && (
                  <button
                    onClick={() => handleFreeze(selectedStrat.strategy_id)}
                    className="btn-secondary text-xs flex items-center gap-1.5"
                  >
                    <Lock size={13} />
                    <span>Cryptographically Freeze Strategy</span>
                  </button>
                )}

                {selectedStrat.status !== 'PAPER_ENABLED' && (
                  <button
                    onClick={() => handlePromote(selectedStrat.strategy_id)}
                    className="btn-primary text-xs flex items-center gap-1.5"
                  >
                    <ArrowUpRight size={13} />
                    <span>Authorize & Promote to Paper Trading</span>
                  </button>
                )}

                {selectedStrat.status === 'PAPER_ENABLED' && (
                  <div className="text-xs font-mono text-emerald-400 flex items-center gap-1.5 font-bold">
                    <CheckCircle2 size={14} />
                    <span>Active in Paper Trading Subsystem</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
