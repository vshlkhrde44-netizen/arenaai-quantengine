import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from core.marketdata.queue import BoundedMarketDataQueue
from core.domain.models import OrderRecord, OrderSide, OrderType
from core.risk.risk_engine import RiskEngine


@pytest.mark.asyncio
async def test_queue_overflow_fail_closed():
    # Capacity = 2
    queue = BoundedMarketDataQueue(maxsize=2)
    
    # Put 2 items (fills queue)
    await queue.put("msg1", timeout=0.1)
    await queue.put("msg2", timeout=0.1)
    assert queue.qsize == 2

    # Put 3rd item -> Must FAIL CLOSED immediately without silent dropping
    success = await queue.put("msg3", timeout=0.05)
    assert success is False
    assert queue.stats.explicitly_lost == 1
    assert queue.stats.received == 3
    
    # When the 2 enqueued items are persisted
    queue.record_persisted(2)
    assert queue.stats.is_conserved is True


def test_stale_data_triggers_risk_halt():
    risk = RiskEngine()
    order = OrderRecord(
        order_id="ord_stale_1",
        client_order_id="c_stale_1",
        venue="coinbase",
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.01,
        price=65000.0
    )

    # Simulated market data timestamp from 60 seconds ago (stale > 10s threshold)
    stale_dt = datetime.now(timezone.utc) - timedelta(seconds=60)
    result = risk.evaluate_pre_trade_risk(order, estimated_price=65000.0, latest_market_data_ts=stale_dt)

    assert result.passed is False
    assert result.rule_name == "STALE_DATA_CHECK"
    assert "Stale market data" in result.reason
