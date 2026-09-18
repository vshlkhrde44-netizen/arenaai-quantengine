# Antigravity QuantEngine

> **Institutional-Grade Local-First Quant Research & Real-Time Paper Trading Engine**  
> *Production-Quality Windows-Installable Architecture with Real Exchange Market Data and Official Sandbox Execution.*

---

## CRITICAL SAFETY INVARIANT — NO LIVE TRADING

```text
==============================================================================
                    SAFETY NOTICE: NO LIVE TRADING CAPABILITY
==============================================================================
Antigravity QuantEngine is strictly an institutional quant research and paper
trading engine. It contains NO functionality, endpoints, or code paths for
submitting live production orders.

Safety Invariants Enforced by Architecture:
- is_production_ready   = False
- live_orders_enabled   = False
- paper_only            = True
- supports_live_orders  = False
==============================================================================
```

---

## 1. Executive Overview

Antigravity QuantEngine integrates:
1. **Real-Time Market Data Ingestion**: Live trades, tickers, order books directly from public exchange WebSockets (Coinbase Exchange, Alpaca, Kraken) with sub-200ms latency.
2. **Cryptographic Raw Wire Preservation**: Append-only JSONL files with recursive SHA-256 hash chaining ($H_i = \text{SHA256}(H_{i-1} \parallel \text{timestamp} \parallel \text{payload})$).
3. **Market Microstructure Analytics**: Order flow Delta, Cumulative Volume Delta (CVD), Footprint price bin matrices, Point of Control (POC), Value Area (VAH/VAL), and Absorption detection.
4. **Quant Research & Deterministic Backtesting**: Causal simulation (signal at $t$ close $\to$ execution at $t+1$ open), transparent cost ladders (gross, fees, slippage, net), and deterministic result hashing.
5. **Adversarial Lookahead Protection**: Truncation invariance and future perturbation tests that prove zero future information leaks into historical decisions.
6. **Walk-Forward Validation**: Out-of-sample cross-validation with configurable Purge buffers and post-test Embargo to prevent label overlap.
7. **Statistical Inference & Monte Carlo Lab**: Bootstrap 95% confidence intervals, Monte Carlo trade-order reshuffling (500+ permutations), and family-aware multiple testing corrections (Bonferroni, Holm, Benjamini-Hochberg FDR).
8. **Strategy Registry & Freezing Firewall**: State machine (`DRAFT`, `FROZEN`, `RESEARCH_ONLY`, `VALIDATED`, `PAPER_ENABLED`, `DISABLED`, `RETIRED`) with explicit human authorization required for paper promotion.
9. **Official Paper Execution**: Orders are routed through the `ExecutionSafetyGate` and `RiskEngine` exclusively to exchange sandbox endpoints.
10. **Local-First Windows Installation**: Windows batch launcher, PowerShell native installer, Start Menu shortcuts, and Inno Setup installer script.

---

## 2. Architecture Quickstart

```text
antigravity-quantengine/
├── apps/
│   ├── backend/             # FastAPI, Pydantic, uvicorn, background workers
│   └── frontend/            # React 18, TypeScript, Vite, Tailwind dark theme
├── core/
│   ├── domain/              # Domain models (orders, fills, tickers, positions)
│   ├── events/              # EventBus and typed domain events
│   ├── execution/           # ExecutionSafetyGate, PaperOrderEngine, OrderStateMachine
│   ├── marketdata/          # WS worker, tamper-evident hash chain, bounded queue
│   ├── research/            # Dataset manager, backtest, walk-forward, lookahead guard
│   ├── strategies/          # Strategy registry, freezing, library
│   ├── risk/                # Pre-trade risk engine, emergency stop, limits
│   ├── portfolio/           # Deterministic position & capital accounting
│   ├── analytics/           # Microstructure, CVD, footprint, volume profile
│   ├── audit/               # Immutable audit trail, quality auditor
│   ├── provenance/          # Provenance manifests & code hashing
│   └── reporting/           # Deterministic certification report generator
├── connectors/              # Coinbase Sandbox, Alpaca Paper, Kraken
├── data/                    # Raw JSONL, Parquet datasets, manifests, reports, vault
├── database/                # SQLite WAL migrations and schemas
├── installer/               # Windows launchers, PowerShell installer, Inno Setup script
├── scripts/                 # Static safety scan (security_scan.py)
├── tests/                   # 30 automated unit, integration, property, mutation, e2e tests
└── docs/                    # Complete architectural and operations documentation
```

---

## 3. Quick Run Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Local Development Mode
```bash
# 1. Run Static Safety Scan
python scripts/security_scan.py

# 2. Run All Automated Verification Tests
PYTHONPATH=. pytest -v tests/

# 3. Build React Frontend
cd apps/frontend && npm install && npm run build && cd ../..

# 4. Start Unified Server (serves React UI + API)
python -m apps.backend.main
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## 4. Windows Installation

### Option A: PowerShell Native Installer
```powershell
.\installer\Install-QuantEngine.ps1
```
Creates application folder in `%LOCALAPPDATA%\AntigravityQuantEngine`, builds desktop and Start Menu shortcuts, and initializes SQLite WAL operational database.

### Option B: Standalone Desktop Launcher
Double-click `QuantEngine_Launcher.bat` or run:
```powershell
.\installer\QuantEngine_Launcher.ps1
```

---

## 5. Automated Verification Summary

All 30 automated tests in `tests/` pass with 100% success:
- **Unit Tests**: State machines, hash chains, P&L calculations, microstructure, risk engine, statistics.
- **Integration Tests**: Safety gate live endpoint blocking, exchange adapters, SQLite WAL persistence.
- **Property-Based Tests**: Queue conservation equation, portfolio equity conservation.
- **Mutation Tests**: Adversarial lookahead adversary failure, raw JSONL tamper detection.
- **Fault Injection Tests**: Bounded queue overflow fail-closed, stale market data timeout.
- **End-to-End Tests**: Complete market ingestion $\to$ paper order $\to$ sandbox fill $\to$ audit chain $\to$ certification report.
