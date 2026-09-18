import asyncio
import pytest
from core.marketdata.queue import BoundedMarketDataQueue
from core.portfolio.portfolio_engine import get_portfolio_engine


@pytest.mark.asyncio
async def test_queue_conservation_law_invariant():
    queue = BoundedMarketDataQueue(maxsize=10)

    # Put 5 items
    for i in range(5):
        await queue.put({"item": i})

    assert queue.stats.received == 5
    queue.record_persisted(3)
    queue.record_rejected(1)
    queue.record_unknown(1)

    # Conservation law check: received == persisted + rejected + lost + unknown
    assert queue.stats.is_conserved is True
    assert queue.stats.discrepancy == 0


def test_portfolio_equity_conservation():
    port = get_portfolio_engine()
    summary = port.get_portfolio_summary()

    # Invariant: Total Equity == Available Cash + Locked Cash + Unrealized PnL
    expected_equity = summary.available_balance + summary.locked_balance + summary.unrealized_pnl
    assert summary.total_equity == pytest.approx(expected_equity, abs=0.02)
