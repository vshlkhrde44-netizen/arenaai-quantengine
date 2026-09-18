"""
Antigravity QuantEngine - Database Schemas & DDL
Defines versioned schemas for operational state, market data sessions,
strategies, paper orders, positions, risk events, and audit logs.
"""

INITIAL_SCHEMA_SQL = """
-- Antigravity QuantEngine Initial Schema (v1.0.0)
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- System Schema Version Tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT NOT NULL
);

-- Exchange Connections & Health
CREATE TABLE IF NOT EXISTS exchange_connections (
    id TEXT PRIMARY KEY,
    venue TEXT NOT NULL,
    connection_type TEXT NOT NULL, -- WEBSOCKET_MARKET_DATA, REST_SANDBOX, etc.
    status TEXT NOT NULL, -- CONNECTED, DISCONNECTED, RECONNECTING, ERROR
    is_paper_only INTEGER NOT NULL DEFAULT 1,
    endpoint_url TEXT NOT NULL,
    connected_at TIMESTAMP,
    disconnected_at TIMESTAMP,
    reconnect_count INTEGER DEFAULT 0,
    last_heartbeat TIMESTAMP,
    metadata_json TEXT
);

-- Market Data Sessions (Enforces explicit session boundaries on reconnect)
CREATE TABLE IF NOT EXISTS market_sessions (
    session_id TEXT PRIMARY KEY,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    records_received INTEGER DEFAULT 0,
    records_persisted INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    records_lost INTEGER DEFAULT 0,
    gap_count INTEGER DEFAULT 0,
    genesis_hash TEXT NOT NULL,
    final_hash TEXT,
    is_active INTEGER DEFAULT 1
);

-- Raw Wire Message Logs Metadata & Tamper Chain
CREATE TABLE IF NOT EXISTS raw_message_batches (
    batch_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    start_timestamp TIMESTAMP NOT NULL,
    end_timestamp TIMESTAMP NOT NULL,
    start_hash TEXT NOT NULL,
    end_hash TEXT NOT NULL,
    sha256_checksum TEXT NOT NULL,
    is_verified INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES market_sessions(session_id)
);

-- Research Datasets & Provenance
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    record_count INTEGER NOT NULL,
    parquet_path TEXT NOT NULL,
    dataset_hash TEXT NOT NULL,
    is_sealed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dataset_manifests (
    manifest_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    venue TEXT NOT NULL,
    software_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    normalized_hash TEXT NOT NULL,
    dataset_hash TEXT NOT NULL,
    transformation_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE IF NOT EXISTS dataset_audits (
    audit_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL, -- PASS, FAIL, UNVERIFIED, NOT_APPLICABLE
    gaps_detected INTEGER DEFAULT 0,
    overlaps_detected INTEGER DEFAULT 0,
    duplicates_detected INTEGER DEFAULT 0,
    disordered_timestamps INTEGER DEFAULT 0,
    malformed_records INTEGER DEFAULT 0,
    hash_verified INTEGER DEFAULT 0,
    details_json TEXT,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

-- Strategy Registry & Freezing
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    current_version TEXT NOT NULL,
    status TEXT NOT NULL, -- DRAFT, FROZEN, RESEARCH_ONLY, VALIDATED, PAPER_ENABLED, DISABLED, RETIRED
    code_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_versions (
    version_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    version_tag TEXT NOT NULL,
    code_content TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    is_frozen INTEGER DEFAULT 0,
    frozen_at TIMESTAMP,
    promoted_to_paper INTEGER DEFAULT 0,
    promoted_at TIMESTAMP,
    promoted_by TEXT,
    promotion_reason TEXT,
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- Research Experiments & Backtest Runs
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    initial_capital REAL NOT NULL,
    final_equity REAL NOT NULL,
    total_trades INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    profit_factor REAL NOT NULL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown REAL NOT NULL,
    gross_pnl REAL NOT NULL,
    total_fees REAL NOT NULL,
    total_slippage REAL NOT NULL,
    net_pnl REAL NOT NULL,
    config_hash TEXT NOT NULL,
    dataset_hash TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    result_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS walk_forward_runs (
    wf_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    train_window_bars INTEGER NOT NULL,
    purge_bars INTEGER NOT NULL,
    embargo_bars INTEGER NOT NULL,
    test_window_bars INTEGER NOT NULL,
    step_bars INTEGER NOT NULL,
    num_folds INTEGER NOT NULL,
    summary_metrics_json TEXT NOT NULL,
    folds_data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paper Orders (Strict State Machine & Safety Trace)
CREATE TABLE IF NOT EXISTS paper_orders (
    order_id TEXT PRIMARY KEY,
    client_order_id TEXT UNIQUE NOT NULL,
    exchange_order_id TEXT,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL, -- BUY, SELL
    order_type TEXT NOT NULL, -- MARKET, LIMIT, STOP, STOP_LIMIT
    quantity REAL NOT NULL,
    price REAL,
    stop_price REAL,
    time_in_force TEXT DEFAULT 'GTC',
    status TEXT NOT NULL, -- CREATED, VALIDATING, SAFETY_CHECK, SUBMITTING, ACKNOWLEDGED, PARTIALLY_FILLED, FILLED, REJECTED, CANCEL_PENDING, CANCELLED, EXPIRED, ERROR
    strategy_id TEXT,
    strategy_version_id TEXT,
    safety_gate_passed INTEGER NOT NULL DEFAULT 0,
    safety_gate_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    filled_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    filled_quantity REAL DEFAULT 0.0,
    average_fill_price REAL DEFAULT 0.0,
    cumulative_fees REAL DEFAULT 0.0,
    raw_venue_response TEXT
);

-- Paper Fills
CREATE TABLE IF NOT EXISTS paper_fills (
    fill_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    exchange_fill_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL DEFAULT 0.0,
    fee_asset TEXT DEFAULT 'USD',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES paper_orders(order_id)
);

-- Paper Positions
CREATE TABLE IF NOT EXISTS paper_positions (
    symbol TEXT PRIMARY KEY,
    venue TEXT NOT NULL,
    side TEXT NOT NULL, -- LONG, SHORT, FLAT
    quantity REAL NOT NULL DEFAULT 0.0,
    average_entry_price REAL NOT NULL DEFAULT 0.0,
    current_market_price REAL NOT NULL DEFAULT 0.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    cumulative_fees REAL NOT NULL DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paper Account Balances
CREATE TABLE IF NOT EXISTS paper_balances (
    asset TEXT PRIMARY KEY,
    total REAL NOT NULL DEFAULT 0.0,
    available REAL NOT NULL DEFAULT 0.0,
    locked REAL NOT NULL DEFAULT 0.0,
    last_reconciled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Risk Events & Breaches
CREATE TABLE IF NOT EXISTS risk_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL, -- LIMIT_BREACH, MAX_DRAWDOWN_WARNING, EMERGENCY_STOP_TRIGGERED, STALE_DATA_HALT
    severity TEXT NOT NULL, -- INFO, WARNING, CRITICAL, REJECTED
    rule_name TEXT NOT NULL,
    metric_value REAL,
    threshold_value REAL,
    details_json TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tamper-Evident Audit Trail
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    sequence_num INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    component TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'SYSTEM',
    status TEXT NOT NULL, -- SUCCESS, REJECTED, FAILED
    details_json TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_seq ON audit_events(sequence_num);
CREATE INDEX IF NOT EXISTS idx_orders_status ON paper_orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON paper_orders(symbol);
"""
