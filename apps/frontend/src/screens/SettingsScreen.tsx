import React, { useState, useEffect } from 'react';
import { fetchCredentials, saveCredentials } from '../api';
import { Settings, Key, ShieldCheck, Lock, CheckCircle2, AlertTriangle, Eye, EyeOff } from 'lucide-react';

export const SettingsScreen: React.FC = () => {
  const [credentials, setCredentials] = useState<Record<string, any>>({});
  const [exchange, setExchange] = useState('coinbase');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const loadCreds = async () => {
    try {
      const res = await fetchCredentials();
      setCredentials(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadCreds();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatusMsg(null);
    try {
      const res = await saveCredentials({
        exchange,
        api_key: apiKey,
        api_secret: apiSecret,
        passphrase: passphrase || undefined
      });
      setStatusMsg({ type: 'success', text: res.message });
      setApiKey('');
      setApiSecret('');
      setPassphrase('');
      loadCreds();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <Settings size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Security Vault & Sandbox Configuration
            </div>
            <div className="text-xs text-slate-400">
              AES-256-GCM encrypted credential vault. Secrets are never exposed to browser or logs.
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Credential Vault Form */}
        <div className="quant-card space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Key size={15} className="text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Configure Paper Exchange Credentials
              </span>
            </div>
            <span className="text-[10px] font-mono text-emerald-400">Encrypted at Rest</span>
          </div>

          <form onSubmit={handleSave} className="space-y-3 font-mono text-xs">
            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Exchange Venue</label>
              <select
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
                className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
              >
                <option value="coinbase">Coinbase Exchange (Sandbox)</option>
                <option value="alpaca">Alpaca Paper Trading</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Sandbox API Key</label>
              <input
                type="text"
                placeholder="Enter paper API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
                required
              />
            </div>

            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Sandbox API Secret</label>
              <input
                type="password"
                placeholder="Enter paper API secret"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
                required
              />
            </div>

            {exchange === 'coinbase' && (
              <div>
                <label className="text-slate-400 text-[10px] uppercase block mb-1">Sandbox API Passphrase</label>
                <input
                  type="password"
                  placeholder="Enter paper passphrase"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
                />
              </div>
            )}

            {statusMsg && (
              <div className={`p-2 rounded text-[11px] border font-mono ${
                statusMsg.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}>
                {statusMsg.text}
              </div>
            )}

            <button
              type="submit"
              disabled={saving}
              className="btn-primary w-full text-xs py-2 uppercase font-bold"
            >
              {saving ? 'Encrypting & Storing...' : 'Save Encrypted Paper Credentials'}
            </button>
          </form>
        </div>

        {/* Vault Status & Invariants */}
        <div className="space-y-4">
          <div className="quant-card space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Active Vault Status (Masked Keys)
              </span>
              <span className="text-[10px] font-mono text-slate-400">Zero Plaintext In Frontend</span>
            </div>

            <div className="space-y-2 font-mono text-xs">
              {Object.keys(credentials).map((exch) => {
                const c = credentials[exch];
                return (
                  <div key={exch} className="bg-[#0b1018] p-2.5 rounded border border-slate-800 flex justify-between items-center">
                    <div>
                      <span className="font-bold text-white uppercase">{c.exchange}</span>
                      <div className="text-[10px] text-slate-400 mt-0.5">Key: {c.masked_key}</div>
                    </div>
                    <span className="badge-paper text-[10px]">ENCRYPTED</span>
                  </div>
                );
              })}
              {Object.keys(credentials).length === 0 && (
                <div className="text-slate-500 text-xs py-4 text-center">No exchange credentials currently stored.</div>
              )}
            </div>
          </div>

          <div className="quant-card space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200 block border-b border-slate-800 pb-2">
              Architectural Safety Invariants
            </span>
            <div className="space-y-1.5 font-mono text-xs text-slate-300">
              <div className="flex justify-between">
                <span>paper_only:</span>
                <span className="text-emerald-400 font-bold">True</span>
              </div>
              <div className="flex justify-between">
                <span>live_orders_enabled:</span>
                <span className="text-emerald-400 font-bold">False</span>
              </div>
              <div className="flex justify-between">
                <span>is_production_ready:</span>
                <span className="text-emerald-400 font-bold">False</span>
              </div>
              <div className="flex justify-between">
                <span>ExecutionSafetyGate:</span>
                <span className="text-emerald-400 font-bold">Mandatory</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
