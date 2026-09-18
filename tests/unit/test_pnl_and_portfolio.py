import pytest
from core.domain.models import FillRecord, OrderSide, PositionSide
from core.portfolio.portfolio_engine import PortfolioEngine


from database.engine import get_db

def test_portfolio_position_accounting():
    port = PortfolioEngine()
    test_symbol = "TEST-PNL-BTC"
    
    # Ensure clean state for test symbol
    db = get_db()
    db.execute_non_query("DELETE FROM paper_positions WHERE symbol = ?", (test_symbol,))
    
    # Fill 1: BUY 1.0 BTC @ 60,000 USD, fee = 30 USD
    f1 = FillRecord(
        fill_id="f1",
        order_id="o1",
        symbol=test_symbol,
        side=OrderSide.BUY,
        quantity=1.0,
        price=60000.0,
        fee=30.0
    )
    pos = port.apply_fill(f1)
    assert pos.side == PositionSide.LONG
    assert pos.quantity == 1.0
    assert pos.average_entry_price == 60000.0
    assert pos.realized_pnl == 0.0

    # Fill 2: BUY 1.0 BTC @ 70,000 USD (Increasing position)
    f2 = FillRecord(
        fill_id="f2",
        order_id="o2",
        symbol=test_symbol,
        side=OrderSide.BUY,
        quantity=1.0,
        price=70000.0,
        fee=35.0
    )
    pos2 = port.apply_fill(f2)
    assert pos2.quantity == 2.0
    assert pos2.average_entry_price == 65000.0 # Average entry (60k + 70k) / 2

    # Fill 3: SELL 1.0 BTC @ 75,000 USD (Partial reduction)
    # Expected realized PnL = (75,000 - 65,000) * 1.0 = +10,000 USD
    f3 = FillRecord(
        fill_id="f3",
        order_id="o3",
        symbol=test_symbol,
        side=OrderSide.SELL,
        quantity=1.0,
        price=75000.0,
        fee=37.5
    )
    pos3 = port.apply_fill(f3)
    assert pos3.quantity == 1.0
    assert pos3.average_entry_price == 65000.0
    assert pos3.realized_pnl == 10000.0

    # Fill 4: SELL 1.0 BTC @ 80,000 USD (Fully close position)
    # Realized PnL from this slice = (80,000 - 65,000) * 1.0 = +15,000 USD
    # Total cumulative realized PnL = 10,000 + 15,000 = 25,000 USD
    f4 = FillRecord(
        fill_id="f4",
        order_id="o4",
        symbol=test_symbol,
        side=OrderSide.SELL,
        quantity=1.0,
        price=80000.0,
        fee=40.0
    )
    pos4 = port.apply_fill(f4)
    assert pos4.side == PositionSide.FLAT
    assert pos4.quantity == 0.0
    assert pos4.realized_pnl == 25000.0
    
    # Clean up test position after verification
    db.execute_non_query("DELETE FROM paper_positions WHERE symbol = ?", (test_symbol,))
