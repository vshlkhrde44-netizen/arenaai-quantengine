from datetime import datetime, timezone, timedelta
from core.domain.models import OrderRecord, OrderSide, OrderType
from core.risk.risk_engine import RiskEngine
from core.config import get_config


def test_risk_max_order_notional_rejection():
    risk = RiskEngine()
    # Limit is 10,000 USD
    # Create order with notional = 1.0 * 65,000 = 65,000 USD (> 10k)
    order = OrderRecord(
        order_id="ord_risk_1",
        client_order_id="c_risk_1",
        venue="coinbase",
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
        price=65000.0
    )
    result = risk.evaluate_pre_trade_risk(order, estimated_price=65000.0)
    assert result.passed is False
    assert result.rule_name == "MAX_ORDER_NOTIONAL"


def test_risk_emergency_stop_halts_orders():
    risk = RiskEngine()
    risk.trigger_emergency_stop("Test emergency stop trigger")

    # Small order that would otherwise pass
    order = OrderRecord(
        order_id="ord_risk_2",
        client_order_id="c_risk_2",
        venue="coinbase",
        symbol="ETH-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.01,
        price=2500.0 # Notional = 25 USD (< 10k)
    )
    result = risk.evaluate_pre_trade_risk(order, estimated_price=2500.0)
    assert result.passed is False
    assert result.rule_name == "EMERGENCY_STOP"

    # Reset
    risk.reset_emergency_stop()
    # Mock portfolio exposure check by testing emergency stop state directly or reset check
    assert risk.emergency_stop_triggered is False
    assert get_config().risk.emergency_stop_active is False
