# Antigravity QuantEngine — Data Model & Storage Specifications

## 1. Storage Tier Architecture

1. **Operational Metadata & State**: SQLite 3 configured with Write-Ahead Logging (`WAL`) and `PRAGMA synchronous = NORMAL`.
2. **Raw Exchange Wire Messages**: Append-only JSONL files (`data/raw/raw_session_<session_id>.jsonl`) preserving raw payloads and recursive SHA-256 links.
3. **Analytical Research Datasets**: Apache Parquet files queried via DuckDB with column-oriented compression.
4. **Provenance Manifests**: JSON documents tracking software versions, source venues, code hashes, and canonical hashes.

## 2. SQLite Operational Schema

- `market_sessions`: Tracks stream boundaries, session IDs, received/persisted counters, and stream gaps.
- `datasets`: Records dataset identifiers, symbols, record counts, Parquet paths, and D3 sealed status.
- `dataset_audits`: Records automated checks for gaps, duplicates, disorder, and malformed records.
- `strategies`: Registered strategies, current versions, lifecycle states, code hashes, and config hashes.
- `strategy_versions`: Version history, frozen flags, and human promotion authorization logs.
- `backtest_runs`: Deterministic simulation outputs, gross/net P&L, fees, slippage, and result hashes.
- `walk_forward_runs`: Fold boundaries, train/test window metrics, and OOS degradation ratios.
- `paper_orders`: Complete state machine tracking, client order IDs, venue order IDs, and safety checks.
- `paper_fills`: Individual execution fills, execution prices, quantities, and transaction fees.
- `paper_positions`: Real-time mark-to-market positions, average entry prices, realized & unrealized P&L.
- `paper_balances`: Multi-asset cash balances (USD, BTC, ETH, SOL).
- `risk_events`: Circuit breaker triggers, limit breaches, and emergency stop logs.
- `audit_events`: Tamper-evident hash-chained system audit trail.
