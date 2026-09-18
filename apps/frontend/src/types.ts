export interface TickerRecord {
  symbol: string;
  venue: string;
  bid_price: number | null;
  bid_quantity: number | null;
  ask_price: number | null;
  ask_quantity: number | null;
  last_price: number;
  volume_24h: number | null;
  timestamp: string;
  spread?: number | null;
  spread_bps?: number | null;
}

export interface TradeRecord {
  trade_id: string;
  symbol: string;
  price: number;
  quantity: number;
  side: 'BUY' | 'SELL';
  timestamp: string;
  venue: string;
}

export interface OrderBookLevel {
  price: number;
  quantity: number;
}

export interface OrderBookRecord {
  symbol: string;
  venue: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: string;
  sequence_number?: number | null;
  total_bid_depth?: number;
  total_ask_depth?: number;
  book_imbalance?: number | null;
}

export interface MicrostructureSnapshot {
  symbol: string;
  timestamp: string;
  last_price: number;
  delta: number;
  cvd: number;
  trade_imbalance_ratio: number;
  absorption_detected: boolean;
  poc_price: number | null;
  vah_price: number | null;
  val_price: number | null;
  spread: number | null;
  book_imbalance: number | null;
}

export interface FootprintLevel {
  price: number;
  buy_volume: number;
  sell_volume: number;
  total_volume: number;
  delta: number;
}

export interface PortfolioSummary {
  account_state: string;
  total_equity: number | null;
  available_balance: number | null;
  locked_balance: number | null;
  unrealized_pnl: number;
  realized_pnl: number;
  total_exposure: number;
  margin_utilization_pct: number | null;
  risk_utilization_pct: number | null;
  active_positions_count: number;
  open_orders_count: number;
  daily_pnl: number;
  status_message: string;
  is_paper_only: boolean;
  live_trading_disabled: boolean;
}

export interface PaperOrder {
  order_id: string;
  client_order_id: string;
  exchange_order_id: string | null;
  venue: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT';
  quantity: number;
  price: number | null;
  status: string;
  safety_gate_passed: boolean;
  safety_gate_reason: string | null;
  created_at: string;
  submitted_at: string | null;
  acknowledged_at: string | null;
  filled_at: string | null;
  cancelled_at: string | null;
  filled_quantity: number;
  average_fill_price: number;
  cumulative_fees: number;
  raw_venue_response: string | null;
}

export interface PositionRecord {
  symbol: string;
  venue: string;
  side: 'LONG' | 'SHORT' | 'FLAT';
  quantity: number;
  average_entry_price: number;
  current_market_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  cumulative_fees: number;
  last_updated: string;
}

export interface StrategyRecord {
  strategy_id: string;
  name: string;
  description: string;
  current_version: string;
  status: string;
  code_hash: string;
  config_hash: string;
  created_at: string;
  updated_at: string;
}

export interface BacktestResult {
  run_id: string;
  strategy_id: string;
  strategy_version: string;
  dataset_id: string;
  initial_capital: number;
  final_equity: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown_pct: number;
  gross_pnl: number;
  total_fees: number;
  total_slippage: number;
  net_pnl: number;
  trades: any[];
  equity_curve: number[];
  config_hash: string;
  dataset_hash: string;
  code_hash: string;
  result_hash: string;
}

export interface WalkForwardResult {
  wf_id: string;
  strategy_id: string;
  dataset_id: string;
  num_folds: number;
  overall_oos_pnl: number;
  overall_oos_win_rate: number;
  oos_degradation_ratio: number;
  folds: any[];
}

export interface DatasetRecord {
  dataset_id: string;
  name: string;
  source_venue: string;
  symbol: string;
  timeframe: string;
  start_time: string;
  end_time: string;
  record_count: number;
  parquet_path: string;
  dataset_hash: string;
  is_sealed: number;
  created_at: string;
}

export interface AuditEvent {
  audit_id: string;
  sequence_num: number;
  event_type: string;
  component: string;
  action: string;
  actor: string;
  status: string;
  details_json: string;
  previous_hash: string;
  content_hash: string;
  timestamp: string;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  database_integrity: string;
  audit_chain_integrity: {
    valid: boolean;
    events_verified: number;
    error: string | null;
  };
  system_resources: {
    cpu_percent: number;
    memory_rss_mb: number;
    memory_percent: number;
  };
  market_data_feed: {
    venue: string;
    is_connected: boolean;
    active_symbols: string[];
    session_id: string;
    records_received: number;
    queue_depth: number;
    queue_utilization_pct: number;
    last_trade_time: string | null;
    feed_latency_ms: number | null;
    reconnect_count: number;
  };
  emergency_stop_active: boolean;
}
