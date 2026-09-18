from datetime import datetime, timezone
from core.analytics.microstructure import MicrostructureEngine
from core.domain.models import TradeRecord, OrderSide, OrderBookRecord, OrderBookLevel


def test_microstructure_delta_and_cvd():
    engine = MicrostructureEngine("BTC-USD", tick_size=10.0)
    now = datetime.now(timezone.utc)

    # 1. Buy trade of 2.0 BTC
    t1 = TradeRecord(trade_id="t1", symbol="BTC-USD", price=65000.0, quantity=2.0, side=OrderSide.BUY, timestamp=now, venue="coinbase")
    s1 = engine.process_trade(t1)
    assert s1.delta == 2.0
    assert s1.cvd == 2.0

    # 2. Sell trade of 0.5 BTC
    t2 = TradeRecord(trade_id="t2", symbol="BTC-USD", price=65000.0, quantity=0.5, side=OrderSide.SELL, timestamp=now, venue="coinbase")
    s2 = engine.process_trade(t2)
    assert s2.delta == -0.5
    assert s2.cvd == 1.5

    # 3. Buy trade of 3.5 BTC @ 65010
    t3 = TradeRecord(trade_id="t3", symbol="BTC-USD", price=65010.0, quantity=3.5, side=OrderSide.BUY, timestamp=now, venue="coinbase")
    s3 = engine.process_trade(t3)
    assert s3.delta == 3.5
    assert s3.cvd == 5.0 # 2.0 - 0.5 + 3.5 = 5.0


def test_volume_profile_poc_calculation():
    engine = MicrostructureEngine("ETH-USD", tick_size=5.0)
    now = datetime.now(timezone.utc)

    # Ingest trades at different price levels
    # 2500 level: 10 volume
    # 2505 level: 25 volume (should be POC!)
    # 2510 level: 5 volume
    engine.process_trade(TradeRecord(trade_id="1", symbol="ETH-USD", price=2500.0, quantity=10.0, side=OrderSide.BUY, timestamp=now, venue="coinbase"))
    engine.process_trade(TradeRecord(trade_id="2", symbol="ETH-USD", price=2505.0, quantity=25.0, side=OrderSide.BUY, timestamp=now, venue="coinbase"))
    engine.process_trade(TradeRecord(trade_id="3", symbol="ETH-USD", price=2510.0, quantity=5.0, side=OrderSide.SELL, timestamp=now, venue="coinbase"))

    profile = engine.calculate_volume_profile()
    assert profile is not None
    assert profile.poc_price == 2505.0
    assert profile.total_volume == 40.0
