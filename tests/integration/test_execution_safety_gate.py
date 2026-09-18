import pytest
from core.config import get_config, RuntimeMode, AppConfig, reset_config
from core.domain.models import OrderRecord, OrderSide, OrderType
from connectors.exchanges.base import CapabilityDescriptor
from core.execution.safety_gate import ExecutionSafetyGate


@pytest.fixture(autouse=True)
def reset_safety_gate():
    ExecutionSafetyGate.set_reconciliation_blocked(False)
    yield
    ExecutionSafetyGate.set_reconciliation_blocked(False)


def create_test_order() -> OrderRecord:
    return OrderRecord(
        order_id="ord_gate_test",
        client_order_id="c_gate_test",
        venue="coinbase",
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=65000.0
    )


def test_production_url_hard_failure():
    """Attempting order submission to a live Coinbase production URL must hard-fail."""
    order = create_test_order()
    caps = CapabilityDescriptor(
        venue_name="coinbase",
        is_paper_only=True,
        supports_live_orders=False,
        supports_paper_orders=True,
        paper_rest_url="https://api.exchange.coinbase.com/orders", # Malicious live endpoint!
        live_market_ws_url="wss://ws-feed.exchange.coinbase.com"
    )

    result = ExecutionSafetyGate.evaluate_order(
        order=order,
        capabilities=caps,
        target_endpoint="https://api.exchange.coinbase.com/orders"
    )
    assert result.passed is False
    assert "prohibited live endpoint keyword" in result.reason
    assert result.checks["target_endpoint_is_sandbox"] is False


def test_alpaca_live_endpoint_hard_failure():
    """Attempting order submission to Alpaca live production URL must hard-fail."""
    order = create_test_order()
    caps = CapabilityDescriptor(
        venue_name="alpaca",
        is_paper_only=True,
        supports_live_orders=False,
        supports_paper_orders=True,
        paper_rest_url="https://api.alpaca.markets/v2/orders", # Live URL (missing paper-api)
        live_market_ws_url="unavailable"
    )

    result = ExecutionSafetyGate.evaluate_order(
        order=order,
        capabilities=caps,
        target_endpoint="https://api.alpaca.markets/v2/orders"
    )
    assert result.passed is False
    assert result.checks["target_endpoint_is_sandbox"] is False


def test_non_paper_mode_hard_failure():
    """Orders submitted when runtime_mode is RESEARCH or DEVELOPMENT must be rejected."""
    order = create_test_order()
    caps = CapabilityDescriptor(
        venue_name="coinbase",
        is_paper_only=True,
        supports_live_orders=False,
        supports_paper_orders=True,
        paper_rest_url="https://api-public.sandbox.exchange.coinbase.com",
        live_market_ws_url="wss://ws-feed.exchange.coinbase.com"
    )

    # Temporarily switch mode to RESEARCH
    cfg = get_config()
    cfg.system.runtime_mode = RuntimeMode.RESEARCH

    result = ExecutionSafetyGate.evaluate_order(
        order=order,
        capabilities=caps,
        target_endpoint="https://api-public.sandbox.exchange.coinbase.com"
    )
    assert result.passed is False
    assert "only PAPER_TRADING permits orders" in result.reason

    # Restore
    cfg.system.runtime_mode = RuntimeMode.PAPER_TRADING


def test_legitimate_sandbox_order_passes():
    """Valid paper order directed at official sandbox must pass safety gate."""
    order = create_test_order()
    caps = CapabilityDescriptor(
        venue_name="coinbase",
        is_paper_only=True,
        supports_live_orders=False,
        supports_paper_orders=True,
        paper_rest_url="https://api-public.sandbox.exchange.coinbase.com",
        live_market_ws_url="wss://ws-feed.exchange.coinbase.com"
    )

    result = ExecutionSafetyGate.evaluate_order(
        order=order,
        capabilities=caps,
        target_endpoint="https://api-public.sandbox.exchange.coinbase.com"
    )
    assert result.passed is True
    assert result.checks["runtime_mode_is_paper"] is True
    assert result.checks["target_endpoint_is_sandbox"] is True
    assert result.checks["connector_supports_live_is_false"] is True
