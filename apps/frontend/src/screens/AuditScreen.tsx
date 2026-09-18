import React, { useState, useEffect } from 'react';
import { AuditEvent } from '../types';
import { fetchAuditEvents, verifyAuditChain, fetchOrderAuditTrail } from '../api';
import { FileCheck2, ShieldCheck, CheckCircle2, AlertTriangle, Search } from 'lucide-react';

export const AuditScreen: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [chainVerify, setChainVerify] = useState<any>(null);
  const [orderQuery, setOrderQuery] = useState('');
  const [reconstructedOrder, setReconstructedOrder] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const loadEvents = async () => {
    try {
      const res = await fetchAuditEvents();
      setEvents(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleVerifyChain = async () => {
    setIsVerifying(true);
    try {
      const res = await verifyAuditChain();
      setChainVerify(res);
    } catch (e) {
      console.error(e);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleReconstruct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderQuery.trim()) return;
    try {
      const res = await fetchOrderAuditTrail(orderQuery.trim());
      setReconstructedOrder(res);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <FileCheck2 size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Tamper-Evident Audit Trail & Forensic Order Reconstruction
            </div>
            <div className="text-xs text-slate-400">
              Recursive SHA-256 hash-chained event logs. Zero secrets exposed.
            </div>
          </div>
        </div>

        <button
          onClick={handleVerifyChain}
          disabled={isVerifying}
          className="btn-primary text-xs flex items-center gap-2"
        >
          <ShieldCheck size={14} />
          <span>{isVerifying ? 'Checking Hashes...' : 'Verify Audit Hash Chain'}</span>
        </button>
      </div>

      {/* Verification Result Banner */}
      {chainVerify && (
        <div className={`p-3 rounded font-mono text-xs flex items-center gap-2 border ${
          chainVerify.is_valid
            ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
            : 'bg-rose-500/10 border-rose-500/40 text-rose-300'
        }`}>
          {chainVerify.is_valid ? <CheckCircle2 size={16} className="text-emerald-400" /> : <AlertTriangle size={16} className="text-rose-400" />}
          <span>
            {chainVerify.is_valid
              ? `CHAIN VERIFICATION SUCCESSFUL: ${chainVerify.records_checked} events cryptographically verified without discontinuities.`
              : `TAMPER ALERT: ${chainVerify.error_message}`}
          </span>
        </div>
      )}

      {/* Forensic Order Reconstruction Tool */}
      <div className="quant-card space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Order Forensic Reconstruction Deep-Dive
          </span>
          <span className="text-[10px] font-mono text-slate-400">Section 90 Requirement</span>
        </div>

        <form onSubmit={handleReconstruct} className="flex gap-2">
          <input
            type="text"
            placeholder="Enter Order ID (e.g. ord_20260917_...)"
            value={orderQuery}
            onChange={(e) => setOrderQuery(e.target.value)}
            className="flex-1 bg-[#0b1018] border border-slate-800 rounded px-3 py-1.5 text-xs text-white font-mono"
          />
          <button type="submit" className="btn-secondary text-xs flex items-center gap-1.5">
            <Search size={13} />
            <span>Reconstruct</span>
          </button>
        </form>

        {reconstructedOrder && (
          <div className="bg-[#0b1018] p-3 rounded border border-slate-800 font-mono text-xs space-y-2">
            <div className="text-emerald-400 font-bold">{reconstructedOrder.forensic_summary}</div>
            <div className="grid grid-cols-2 gap-2 text-slate-400 text-[11px] pt-1">
              <div>Symbol: <span className="text-white">{reconstructedOrder.symbol}</span></div>
              <div>Safety Gate: <span className="text-emerald-400">{reconstructedOrder.safety_gate_passed ? 'PASSED' : 'REJECTED'}</span></div>
              <div>Fills Recorded: <span className="text-white">{reconstructedOrder.fills?.length}</span></div>
              <div>Order Type: <span className="text-white">{reconstructedOrder.order_type}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Audit Log Table */}
      <div className="quant-card">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Immutable Audit Trail Events ({events.length})
          </span>
          <span className="text-[10px] font-mono text-emerald-400">Append-Only Chained</span>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="quant-table font-mono text-xs">
            <thead>
              <tr>
                <th>Seq #</th>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>Component</th>
                <th>Action</th>
                <th>Status</th>
                <th>Content Hash (SHA-256)</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.audit_id}>
                  <td className="font-bold text-slate-400">#{ev.sequence_num}</td>
                  <td className="text-slate-400">{new Date(ev.timestamp).toLocaleTimeString()}</td>
                  <td className="font-bold text-white">{ev.event_type}</td>
                  <td className="text-slate-300">{ev.component}</td>
                  <td className="text-sky-400">{ev.action}</td>
                  <td>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      ev.status === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                    }`}>
                      {ev.status}
                    </span>
                  </td>
                  <td className="text-slate-500 truncate max-w-xs">{ev.content_hash.slice(0, 16)}...</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-500">
                    No audit events in log.
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
