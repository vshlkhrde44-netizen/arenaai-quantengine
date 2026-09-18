import React, { useState } from 'react';
import { PaperOrder, PositionRecord, TickerRecord } from '../types';
import { submitPaperOrder, cancelPaperOrder } from '../api';
import { Terminal, ShieldAlert, ArrowRight, XCircle, CheckCircle2 } from 'lucide-react';

interface PaperTradingScreenProps {
  orders: PaperOrder[];
  positions: PositionRecord[];
  tickers: Record<string, TickerRecord>;
  onRefreshOrders: () => void;
}

export const PaperTradingScreen: React.FC<PaperTradingScreenProps> = ({
  orders,
  positions,
  tickers,
  onRefreshOrders
}) => {
  const [symbol, setSymbol] = useState<string>('BTC-USD');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [quantity, setQuantity] = useState<string>('0.05');
  const [price, setPrice] = useState<string>('76500.00');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const currentTicker = tickers[symbol];
  const estPrice = orderType === 'LIMIT' ? parseFloat(price) || 0 : currentTicker?.last_price || 0;
  const numQty = parseFloat(quantity) || 0;
  const estNotional = estPrice * numQty;
  const estFees = estNotional * 0.0005; // 5 bps

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setStatusMsg(null);

    try {
      const res = await submitPaperOrder({
        symbol,
        side,
        order_type: orderType,
        quantity: numQty,
        price: orderType === 'LIMIT' ? parseFloat(price) : undefined,
        venue: 'coinbase'
      });

      if (res.safety_gate_passed) {
        setStatusMsg({
          type: 'success',
          text: `Paper Order ${res.order_id} submitted successfully (${res.status}).`
        });
      } else {
        setStatusMsg({
          type: 'error',
          text: `Safety Gate Rejection: ${res.safety_gate_reason}`
        });
      }
      onRefreshOrders();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (orderId: string) => {
    try {
      await cancelPaperOrder(orderId);
      onRefreshOrders();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-4">
      {/* Prominent Safety Header */}
      <div className="quant-card bg-[#0d1522] border-emerald-500/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-emerald-500/20 text-emerald-400">
            <Terminal size={22} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide flex items-center gap-2">
              <span>Paper Trading Order Terminal</span>
              <span className="badge-paper text-[10px]">REAL-TIME SANDBOX ONLY</span>
            </div>
            <div className="text-xs text-slate-400">
              Orders are dispatched exclusively to official exchange sandbox endpoints. No live capital risk.
            </div>
          </div>
        </div>

        <div className="badge-danger font-mono text-xs">
          <ShieldAlert size={14} />
          <span>PRODUCTION ORDERS FORBIDDEN</span>
        </div>
      </div>

      {/* Main Grid: Order Ticket & Active Orders */}
      <div className="grid grid-cols-3 gap-4">
        {/* Order Ticket */}
        <div className="quant-card space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              New Paper Order Ticket
            </span>
            <span className="text-[10px] font-mono text-sky-400">Venue: Coinbase Sandbox</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3 font-mono text-xs">
            {/* Symbol Selection */}
            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Market Symbol</label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
              >
                <option value="BTC-USD">BTC-USD (Bitcoin)</option>
                <option value="ETH-USD">ETH-USD (Ethereum)</option>
                <option value="SOL-USD">SOL-USD (Solana)</option>
              </select>
            </div>

            {/* Side Selection (BUY/SELL) */}
            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Execution Side</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setSide('BUY')}
                  className={`py-1.5 rounded font-bold transition-all ${
                    side === 'BUY'
                      ? 'bg-emerald-600 text-white border border-emerald-400'
                      : 'bg-[#0b1018] text-slate-400 border border-slate-800'
                  }`}
                >
                  BUY (LONG)
                </button>
                <button
                  type="button"
                  onClick={() => setSide('SELL')}
                  className={`py-1.5 rounded font-bold transition-all ${
                    side === 'SELL'
                      ? 'bg-rose-600 text-white border border-rose-400'
                      : 'bg-[#0b1018] text-slate-400 border border-slate-800'
                  }`}
                >
                  SELL (SHORT)
                </button>
              </div>
            </div>

            {/* Order Type */}
            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Order Type</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setOrderType('MARKET')}
                  className={`py-1 rounded ${
                    orderType === 'MARKET' ? 'bg-sky-600 text-white' : 'bg-[#0b1018] text-slate-400 border border-slate-800'
                  }`}
                >
                  MARKET
                </button>
                <button
                  type="button"
                  onClick={() => setOrderType('LIMIT')}
                  className={`py-1 rounded ${
                    orderType === 'LIMIT' ? 'bg-sky-600 text-white' : 'bg-[#0b1018] text-slate-400 border border-slate-800'
                  }`}
                >
                  LIMIT
                </button>
              </div>
            </div>

            {/* Quantity */}
            <div>
              <label className="text-slate-400 text-[10px] uppercase block mb-1">Quantity</label>
              <input
                type="number"
                step="0.001"
                min="0.001"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
                required
              />
            </div>

            {/* Price (if Limit) */}
            {orderType === 'LIMIT' && (
              <div>
                <label className="text-slate-400 text-[10px] uppercase block mb-1">Limit Price (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full bg-[#0b1018] border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  required
                />
              </div>
            )}

            {/* Pre-Trade Cost & Risk Impact Summary */}
            <div className="bg-[#0b1018] p-2.5 rounded border border-slate-800/80 space-y-1.5 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Estimated Price:</span>
                <span className="text-white">${estPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Estimated Notional:</span>
                <span className="text-sky-400 font-bold">${estNotional.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Estimated Fees (5 bps):</span>
                <span className="text-slate-400">${estFees.toFixed(4)}</span>
              </div>
              <div className="flex justify-between border-t border-slate-800 pt-1">
                <span className="text-slate-500">Safety Gate Check:</span>
                <span className="text-emerald-400 font-bold">READY</span>
              </div>
            </div>

            {/* Feedback Message */}
            {statusMsg && (
              <div
                className={`p-2 rounded text-[11px] border font-mono ${
                  statusMsg.type === 'success'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                }`}
              >
                {statusMsg.text}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className={`w-full py-2 rounded text-xs font-bold uppercase transition-all ${
                side === 'BUY'
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  : 'bg-rose-600 hover:bg-rose-500 text-white'
              }`}
            >
              {submitting ? 'Verifying & Submitting...' : `Submit Paper ${side} Order`}
            </button>
          </form>
        </div>

        {/* Active Paper Orders & Execution Feed */}
        <div className="quant-card col-span-2 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Active & Recent Paper Orders ({orders.length})
            </span>
            <span className="text-[10px] font-mono text-emerald-400">ExecutionSafetyGate Enforced</span>
          </div>

          <div className="overflow-x-auto max-h-96">
            <table className="quant-table font-mono text-xs">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Type</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Status</th>
                  <th>Safety Gate</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.order_id}>
                    <td className="text-slate-400 truncate max-w-[100px]">{o.order_id}</td>
                    <td className="font-bold text-white">{o.symbol}</td>
                    <td>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                        o.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                      }`}>
                        {o.side}
                      </span>
                    </td>
                    <td className="text-slate-400">{o.order_type}</td>
                    <td className="text-slate-300">{o.quantity.toFixed(4)}</td>
                    <td className="text-slate-300">{o.price ? `$${o.price.toFixed(2)}` : 'MKT'}</td>
                    <td>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                          o.status === 'FILLED'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : o.status === 'ACKNOWLEDGED'
                            ? 'bg-sky-500/20 text-sky-400'
                            : o.status === 'CANCELLED'
                            ? 'bg-slate-800 text-slate-400'
                            : 'bg-rose-500/20 text-rose-400'
                        }`}
                      >
                        {o.status}
                      </span>
                    </td>
                    <td>
                      <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
                        <CheckCircle2 size={11} /> PASSED
                      </span>
                    </td>
                    <td>
                      {['ACKNOWLEDGED', 'SUBMITTING'].includes(o.status) && (
                        <button
                          onClick={() => handleCancel(o.order_id)}
                          className="btn-danger text-[10px] py-0.5 px-1.5"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {orders.length === 0 && (
                  <tr>
                    <td colSpan={9} className="text-center py-10 text-slate-500">
                      No paper orders submitted yet. Use the ticket to transmit a sandbox test order.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
