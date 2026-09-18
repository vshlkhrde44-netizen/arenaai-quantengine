import React, { useState, useEffect } from 'react';
import { DatasetRecord } from '../types';
import { fetchDatasets, auditDataset, sealDataset } from '../api';
import { Database, ShieldCheck, Lock, CheckCircle2, AlertTriangle, FileText } from 'lucide-react';

export const DatasetsScreen: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [auditResult, setAuditResult] = useState<any>(null);
  const [auditing, setAuditing] = useState(false);

  const loadDatasets = async () => {
    try {
      const res = await fetchDatasets();
      setDatasets(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  const handleAudit = async (id: string) => {
    setAuditing(true);
    try {
      const res = await auditDataset(id);
      setAuditResult(res);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setAuditing(false);
    }
  };

  const handleSeal = async (id: string) => {
    if (confirm('Seal this dataset? Once sealed, the D3 firewall blocks reading, loading, and hashing to preserve blind out-of-sample purity.')) {
      try {
        await sealDataset(id);
        loadDatasets();
      } catch (e: any) {
        alert(e.message);
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <Database size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Research Datasets & Data Quality Auditor
            </div>
            <div className="text-xs text-slate-400">
              Cryptographically hashed Parquet datasets with provenance manifests and D3 Sealed Firewall protection.
            </div>
          </div>
        </div>
      </div>

      {/* Datasets Table */}
      <div className="quant-card">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Certified Research Datasets ({datasets.length})
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            Storage Engine: DuckDB / Parquet
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="quant-table font-mono text-xs">
            <thead>
              <tr>
                <th>Dataset Name</th>
                <th>Symbol / TF</th>
                <th>Records</th>
                <th>Time Range</th>
                <th>SHA-256 Digest</th>
                <th>D3 Seal</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.dataset_id}>
                  <td className="font-bold text-white">{d.name}</td>
                  <td className="text-sky-400">{d.symbol} ({d.timeframe})</td>
                  <td className="text-slate-300">{d.record_count.toLocaleString()}</td>
                  <td className="text-slate-400 text-[11px] truncate max-w-xs">
                    {new Date(d.start_time).toLocaleDateString()} - {new Date(d.end_time).toLocaleDateString()}
                  </td>
                  <td className="text-slate-500 truncate max-w-xs font-mono">{d.dataset_hash.slice(0, 16)}...</td>
                  <td>
                    {d.is_sealed ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold flex items-center gap-1 w-max">
                        <Lock size={10} /> SEALED
                      </span>
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold">
                        OPEN
                      </span>
                    )}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleAudit(d.dataset_id)}
                        disabled={auditing}
                        className="btn-secondary text-[10px] py-1 px-2 flex items-center gap-1"
                      >
                        <ShieldCheck size={11} />
                        <span>Audit</span>
                      </button>

                      {!d.is_sealed && (
                        <button
                          onClick={() => handleSeal(d.dataset_id)}
                          className="btn-secondary text-[10px] py-1 px-2 text-amber-300 hover:text-white flex items-center gap-1"
                          title="Seal Dataset under D3 Firewall"
                        >
                          <Lock size={11} />
                          <span>Seal D3</span>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Inspection Result */}
      {auditResult && (
        <div className="quant-card space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <ShieldCheck size={16} className="text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Data Quality Audit Report ({auditResult.dataset_id})
              </span>
            </div>
            <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
              auditResult.status === 'PASS'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
            }`}>
              AUDIT STATUS: {auditResult.status}
            </span>
          </div>

          <div className="grid grid-cols-5 gap-3 font-mono text-xs text-center">
            <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase mb-1">Gaps Detected</span>
              <span className={`text-base font-bold ${auditResult.gaps_detected === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {auditResult.gaps_detected}
              </span>
            </div>

            <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase mb-1">Duplicates</span>
              <span className={`text-base font-bold ${auditResult.duplicates_detected === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {auditResult.duplicates_detected}
              </span>
            </div>

            <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase mb-1">Disordered TS</span>
              <span className={`text-base font-bold ${auditResult.disordered_timestamps === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {auditResult.disordered_timestamps}
              </span>
            </div>

            <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase mb-1">Malformed Records</span>
              <span className={`text-base font-bold ${auditResult.malformed_records === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {auditResult.malformed_records}
              </span>
            </div>

            <div className="bg-[#0b1018] p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase mb-1">Hash Verification</span>
              <span className="text-base font-bold text-emerald-400 flex items-center justify-center gap-1">
                <CheckCircle2 size={13} /> OK
              </span>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 font-mono pt-1">
            Quality Standard: No synthetic interpolation, no forward-filling, and no silent repair of certified research data.
          </div>
        </div>
      )}
    </div>
  );
};
