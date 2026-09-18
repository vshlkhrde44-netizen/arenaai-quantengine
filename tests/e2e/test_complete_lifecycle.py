"""
Antigravity QuantEngine - End-to-End System Lifecycle Verification
Verifies complete cycle: boot, health, market ingestion, backtesting, paper order,
risk checks, portfolio accounting, audit chain integrity, and certification report.
Implements CI E2E (MOCK_EXCHANGE) and Real Paper E2E (NOT_RUN if no keys) per Section 69, 70.
"""

import asyncio
import pytest
from starlette.testclient import TestClient

from apps.backend.main import app
from core.config import get_config, RuntimeMode
from core.marketdata.worker import get_market_data_worker
from core.security.credentials import get_credential_vault
from connectors.registry import get_connector_registry
from tests.fixtures.mock_exchange import MockExchangeAdapter
from database.engine import get_db


@pytest.mark.asyncio
async def test_full_system_lifecycle_ci_e2e():
    """
    CI E2E Test (Section 69):
    Uses a controlled exchange mock strictly for testing API state machines and accounting.
    Marked: MOCK_EXCHANGE.
    """
    cfg = get_config()
    orig_mode = cfg.system.runtime_mode
    cfg.system.runtime_mode = RuntimeMode.TEST # Allow mock in TEST mode

    registry = get_connector_registry()
    mock_adapter = MockExchangeAdapter()
    registry.register("mock_coinbase", mock_adapter)

    client = TestClient(app)

    # 1. Health check & invariants
    health_resp = client.get("/api/system/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["database_integrity"] == "OK"

    mode_resp = client.get("/api/system/mode")
    assert mode_resp.status_code == 200
    assert mode_resp.json()["paper_only"] is True
    assert mode_resp.json()["live_orders_enabled"] is False

    # 2. Market Data Ingestion verification (Live Coinbase feed)
    worker = get_market_data_worker()
    await worker.start()
    await asyncio.sleep(2.0) # Ingest live public trades
    
    tickers_resp = client.get("/api/markets/ticker")
    assert tickers_resp.status_code == 200
    await worker.stop()

    # 3. Strategy Registry & Backtesting
    strat_resp = client.get("/api/strategies/list")
    assert strat_resp.status_code == 200
    assert len(strat_resp.json()) >= 2

    bt_resp = client.post("/api/research/backtest/run", json={"strategy_id": "strat_cvd_imbalance"})
    assert bt_resp.status_code == 200
    bt_data = bt_resp.json()
    assert "result_hash" in bt_data

    # 4. Paper Order Execution through Safety Gate via Controlled Mock (CI)
    db = get_db()
    db.execute_non_query("DELETE FROM paper_positions")
    order_payload = {
        "symbol": "BTC-USD",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.05,
        "venue": "mock_coinbase"
    }
    order_resp = client.post("/api/paper/order/submit", json=order_payload)
    assert order_resp.status_code == 200
    order_data = order_resp.json()
    assert order_data["safety_gate_passed"] is True
    assert order_data["status"] == "FILLED"
    assert order_data["exchange_order_id"].startswith("mock_oid_")

    # 5. Position & Portfolio Accounting
    pos_resp = client.get("/api/positions/list")
    assert pos_resp.status_code == 200
    positions = pos_resp.json()
    assert any(p["symbol"] == "BTC-USD" for p in positions)

    port_resp = client.get("/api/portfolio/summary")
    assert port_resp.status_code == 200
    summary = port_resp.json()
    assert summary["is_paper_only"] is True

    # 6. Reconciliation
    rec_resp = client.post("/api/paper/reconcile?venue=mock_coinbase")
    assert rec_resp.status_code == 200

    # 7. Tamper-evident Audit Chain Verification
    audit_resp = client.get("/api/audit/verify-chain")
    assert audit_resp.status_code == 200
    assert audit_resp.json()["is_valid"] is True

    # 8. Deterministic Certification Report Generation
    rep_resp = client.post("/api/reports/generate")
    assert rep_resp.status_code == 200
    assert rep_resp.json()["overall_status"] == "PASS"

    # Restore runtime mode
    cfg.system.runtime_mode = orig_mode
    print("\nCI E2E TEST PASSED: State machines, execution ledger, and accounting verified.")


def test_real_paper_exchange_e2e():
    """
    REAL PAPER E2E (Section 69, 87):
    Requires explicit user-provided paper credentials.
    If credentials are absent: reports NOT_RUN / skips (never false PASS).
    """
    vault = get_credential_vault()
    cb_creds = vault.get_credentials("coinbase")
    has_creds = bool(cb_creds and cb_creds.get("api_key") and cb_creds.get("api_secret"))

    if not has_creds:
        pytest.skip("NOT_RUN: Real exchange paper API credentials not configured in vault (Section 69, 87).")

    # If credentials present, execute live authenticated test against official sandbox
    client = TestClient(app)
    order_payload = {
        "symbol": "BTC-USD",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": 0.001,
        "price": 10000.0, # Way below market, non-fillable limit
        "venue": "coinbase"
    }
    resp = client.post("/api/paper/order/submit", json=order_payload)
    assert resp.status_code == 200
    order_data = resp.json()
    assert order_data["safety_gate_passed"] is True
    assert order_data["exchange_order_id"] is not None
