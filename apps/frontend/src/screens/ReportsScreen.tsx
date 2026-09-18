import React, { useState, useEffect } from 'react';
import { fetchReports, generateCertificationReport } from '../api';
import { FileCheck2, FileText, CheckCircle2, Download, RefreshCw } from 'lucide-react';

export const ReportsScreen: React.FC = () => {
  const [reports, setReports] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any>(null);
  const [generating, setGenerating] = useState(false);

  const loadReports = async () => {
    try {
      const res = await fetchReports();
      setReports(res);
      if (res.length > 0 && !selectedReport) {
        loadReportDetail(res[0].report_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadReportDetail = async (id: string) => {
    try {
      const res = await fetch(`/api/reports/${id}`);
      const data = await res.json();
      setSelectedReport(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await generateCertificationReport();
      loadReports();
      loadReportDetail(res.report_id);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <FileCheck2 size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Deterministic Certification Deliverables & Reports
            </div>
            <div className="text-xs text-slate-400">
              Evidence-based reproducible reports with cryptographic input and analytical payload digests.
            </div>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="btn-primary text-xs flex items-center gap-2"
        >
          <FileText size={14} />
          <span>{generating ? 'Generating Certification...' : 'Generate Certification Report'}</span>
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Reports Index */}
        <div className="space-y-2">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Available Reports ({reports.length})</div>
          {reports.map((r) => {
            const isSel = selectedReport?.report_id === r.report_id;
            return (
              <div
                key={r.report_id}
                onClick={() => loadReportDetail(r.report_id)}
                className={`quant-card cursor-pointer p-3 transition-all ${
                  isSel ? 'border-sky-500/60 bg-[#121927]' : 'hover:border-slate-700'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-bold text-xs text-white truncate max-w-[170px]">{r.report_title}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
                    r.overall_status === 'PASS' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {r.overall_status}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-slate-500">{new Date(r.created_at).toLocaleString()}</div>
              </div>
            );
          })}
          {reports.length === 0 && (
            <div className="text-slate-500 text-xs p-4 text-center">No reports yet. Click generate above.</div>
          )}
        </div>

        {/* Selected Report Viewer */}
        {selectedReport && (
          <div className="quant-card col-span-2 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold font-mono text-white">{selectedReport.report_title}</h3>
                <span className="text-xs text-slate-400 font-mono">ID: {selectedReport.report_id}</span>
              </div>
              <span className={`font-mono text-xs font-bold px-2 py-1 rounded ${
                selectedReport.overall_status === 'PASS'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
              }`}>
                STATUS: {selectedReport.overall_status}
              </span>
            </div>

            {/* Markdown Deliverable Content */}
            {selectedReport.markdown_content && (
              <pre className="bg-[#0b1018] p-4 rounded border border-slate-800 font-mono text-xs text-slate-200 overflow-y-auto max-h-96 whitespace-pre-wrap leading-relaxed">
                {selectedReport.markdown_content}
              </pre>
            )}

            <div className="text-[10px] text-slate-500 font-mono pt-1">
              Analytical Payload Digest: {selectedReport.analytical_payload_hash}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
