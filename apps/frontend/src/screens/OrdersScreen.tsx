import React, { useState } from 'react';
import { PaperOrder } from '../types';
import { fetchOrderAuditTrail } from '../api';
import { ListOrdered, CheckCircle2, ArrowRight, ShieldCheck, FileCode } from 'lucide-react';

interface OrdersScreenProps {
  orders: PaperOrder[];
}

export const OrdersScreen: React.FC<OrdersScreenProps> = ({ orders }) => {
  const [selectedOrder, setSelectedOrder] = useState<PaperOrder | null>(orders[0] || null);
  const [auditTrail, setAuditTrail] = useState<any>(null);

  const handleSelectOrder = async (order: PaperOrder) => {
    setSelectedOrder(order);
    try {
      const res = await fetchOrderAuditTrail(order.order_id);
      setAuditTrail(res);
    } catch (e) {
      console.error(e);
    }
  };

  const steps = ['CREATED', 'VALIDATING', 'SAFETY_CHECK', 'SUBMITTING', 'ACKNOWLEDGED', 'FILLED'];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="quant-card bg-[#0e1420] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <ListOrdered size={20} />
          </div>
          <div>
            <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Paper Order State Machine & Lifecycle Tracking
            </div>
            <div className="text-xs text-slate-400">
              Deterministic state transition graph with complete timestamped audit trail.
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Orders Table */}
        <div className="quant-card col-span-2 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Orders History ({orders.length})
            </span>
            <span className="text-[10px] font-mono text-slate-400">Click to Inspect Lifecycle</span>
          </div>

          <div className="overflow-x-auto max-h-96">
            <table className="quant-table font-mono text-xs">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Qty</th>
                  <th>Status</th>
                  <th>Submitted At</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => {
                  const isSel = selectedOrder?.order_id === o.order_id;
                  return (
                    <tr
                      key={o.order_id}
                      onClick={() => handleSelectOrder(o)}
                      className={`cursor-pointer ${isSel ? 'bg-sky-500/10' : ''}`}
                    >
                      <td className="font-bold text-slate-300">{o.order_id}</td>
                      <td className="text-white">{o.symbol}</td>
                      <td className={o.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}>{o.side}</td>
                      <td>{o.quantity.toFixed(4)}</td>
                      <td>
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-slate-800 text-slate-200">
                          {o.status}
                        </span>
                      </td>
                      <td className="text-slate-500 text-[11px]">
                        {o.submitted_at ? new Date(o.submitted_at).toLocaleTimeString() : '--'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* State Machine Visualization */}
        {selectedOrder && (
          <div className="quant-card space-y-4">
            <div className="border-b border-slate-800 pb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                State Machine Tracker
              </span>
              <div className="text-[11px] font-mono text-slate-400 mt-1">
                Order: <span className="text-white font-bold">{selectedOrder.order_id}</span>
              </div>
            </div>

            {/* Stepper */}
            <div className="space-y-2 font-mono text-xs">
              {steps.map((st, idx) => {
                const isPassed = steps.indexOf(selectedOrder.status) >= idx || selectedOrder.status === 'FILLED';
                const isCurrent = selectedOrder.status === st;
                return (
                  <div key={st} className="flex items-center gap-2.5">
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        isCurrent
                          ? 'bg-sky-500 text-white ring-2 ring-sky-400'
                          : isPassed
                          ? 'bg-emerald-500 text-black'
                          : 'bg-slate-800 text-slate-500'
                      }`}
                    >
                      {idx + 1}
                    </div>
                    <span className={isCurrent ? 'text-sky-400 font-bold' : isPassed ? 'text-slate-200' : 'text-slate-600'}>
                      {st}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Timestamps */}
            <div className="bg-[#0b1018] p-3 rounded border border-slate-800 font-mono text-[11px] space-y-1.5 text-slate-400">
              <div className="flex justify-between">
                <span>Created:</span>
                <span className="text-white">{new Date(selectedOrder.created_at).toLocaleTimeString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Acknowledged:</span>
                <span className="text-white">{selectedOrder.acknowledged_at ? new Date(selectedOrder.acknowledged_at).toLocaleTimeString() : '--'}</span>
              </div>
              <div className="flex justify-between">
                <span>Filled At:</span>
                <span className="text-white">{selectedOrder.filled_at ? new Date(selectedOrder.filled_at).toLocaleTimeString() : '--'}</span>
              </div>
            </div>

            {/* Venue Raw Response */}
            {selectedOrder.raw_venue_response && (
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Venue Response Payload:</span>
                <pre className="bg-[#0b1018] p-2 rounded border border-slate-800 text-[10px] text-slate-300 font-mono overflow-x-auto max-h-32">
                  {selectedOrder.raw_venue_response}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
