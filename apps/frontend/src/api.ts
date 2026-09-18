import {
  PortfolioSummary,
  TickerRecord,
  TradeRecord,
  OrderBookRecord,
  MicrostructureSnapshot,
  PaperOrder,
  PositionRecord,
  StrategyRecord,
  BacktestResult,
  WalkForwardResult,
  DatasetRecord,
  AuditEvent,
  SystemHealth
} from './types';

const BASE_URL = ''; // Relative URL proxied by Vite

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${BASE_URL}/api/system/health`);
  return res.json();
}

export async function fetchSystemMode(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/system/mode`);
  return res.json();
}

export async function fetchTickers(): Promise<Record<string, TickerRecord>> {
  const res = await fetch(`${BASE_URL}/api/markets/ticker`);
  return res.json();
}

export async function fetchTrades(symbol: string = 'BTC-USD', limit: number = 50): Promise<TradeRecord[]> {
  const res = await fetch(`${BASE_URL}/api/markets/trades?symbol=${symbol}&limit=${limit}`);
  return res.json();
}

export async function fetchOrderBook(symbol: string = 'BTC-USD'): Promise<OrderBookRecord> {
  const res = await fetch(`${BASE_URL}/api/markets/orderbook?symbol=${symbol}`);
  return res.json();
}

export async function fetchMicrostructure(symbol: string = 'BTC-USD'): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/microstructure/analytics?symbol=${symbol}`);
  return res.json();
}

export async function fetchPortfolioSummary(): Promise<PortfolioSummary> {
  const res = await fetch(`${BASE_URL}/api/portfolio/summary`);
  return res.json();
}

export async function fetchOrders(): Promise<PaperOrder[]> {
  const res = await fetch(`${BASE_URL}/api/orders/list`);
  return res.json();
}

export async function fetchPositions(): Promise<PositionRecord[]> {
  const res = await fetch(`${BASE_URL}/api/positions/list`);
  return res.json();
}

export async function fetchStrategies(): Promise<StrategyRecord[]> {
  const res = await fetch(`${BASE_URL}/api/strategies/list`);
  return res.json();
}

export async function freezeStrategy(strategy_id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/strategies/freeze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy_id })
  });
  return res.json();
}

export async function promoteStrategy(strategy_id: string, authorized_by: string, reason: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/strategies/promote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy_id, authorized_by, reason })
  });
  return res.json();
}

export async function submitPaperOrder(payload: {
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT';
  quantity: number;
  price?: number;
  venue?: string;
}): Promise<PaperOrder> {
  const res = await fetch(`${BASE_URL}/api/paper/order/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ venue: 'coinbase', ...payload })
  });
  return res.json();
}

export async function cancelPaperOrder(order_id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/paper/order/cancel/${order_id}`, {
    method: 'POST'
  });
  return res.json();
}

export async function triggerEmergencyStop(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/paper/emergency-stop`, { method: 'POST' });
  return res.json();
}

export async function resetEmergencyStop(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/paper/reset-emergency-stop`, { method: 'POST' });
  return res.json();
}

export async function fetchDatasets(): Promise<DatasetRecord[]> {
  const res = await fetch(`${BASE_URL}/api/datasets/list`);
  return res.json();
}

export async function auditDataset(dataset_id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/datasets/audit/${dataset_id}`, { method: 'POST' });
  return res.json();
}

export async function sealDataset(dataset_id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/datasets/seal/${dataset_id}`, { method: 'POST' });
  return res.json();
}

export async function runBacktest(strategy_id: string = 'strat_cvd_imbalance'): Promise<BacktestResult> {
  const res = await fetch(`${BASE_URL}/api/research/backtest/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy_id, initial_capital: 100000.0, fee_rate_bps: 5.0, slippage_bps: 2.0 })
  });
  return res.json();
}

export async function runWalkForward(strategy_id: string = 'strat_cvd_imbalance'): Promise<WalkForwardResult> {
  const res = await fetch(`${BASE_URL}/api/research/walk-forward/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy_id, train_window_bars: 150, test_window_bars: 50, step_bars: 50 })
  });
  return res.json();
}

export async function runMonteCarlo(strategy_id: string = 'strat_cvd_imbalance'): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/research/monte-carlo/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy_id, num_simulations: 500, seed: 42 })
  });
  return res.json();
}

export async function runLookaheadTest(strategy_id: string = 'strat_cvd_imbalance'): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/research/lookahead-test?strategy_id=${strategy_id}`, {
    method: 'POST'
  });
  return res.json();
}

export async function fetchAuditEvents(): Promise<AuditEvent[]> {
  const res = await fetch(`${BASE_URL}/api/audit/events?limit=100`);
  return res.json();
}

export async function verifyAuditChain(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/audit/verify-chain`);
  return res.json();
}

export async function fetchOrderAuditTrail(order_id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/orders/${order_id}/audit-trail`);
  return res.json();
}

export async function fetchReports(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/api/reports/list`);
  return res.json();
}

export async function generateCertificationReport(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/reports/generate`, { method: 'POST' });
  return res.json();
}

export async function fetchCredentials(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/settings/credentials`);
  return res.json();
}

export async function saveCredentials(payload: {
  exchange: string;
  api_key: string;
  api_secret: string;
  passphrase?: string;
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/settings/credentials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, is_paper: true })
  });
  return res.json();
}
