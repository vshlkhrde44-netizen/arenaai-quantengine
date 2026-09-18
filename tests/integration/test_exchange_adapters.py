import pytest
from connectors.exchanges.coinbase_connector import CoinbaseExchangeAdapter, CoinbasePaperExecutionAdapter
from connectors.exchanges.alpaca_connector import AlpacaExchangeAdapter, AlpacaPaperExecutionAdapter


def test_coinbase_adapter_capabilities_safety():
    adapter = CoinbaseExchangeAdapter()
    caps = adapter.capabilities
    assert caps.supports_live_orders is False
    assert caps.is_paper_only is True
    assert "sandbox" in caps.paper_rest_url


def test_coinbase_execution_adapter_rejects_live_url():
    with pytest.raises(RuntimeError) as exc_info:
        CoinbasePaperExecutionAdapter("https://api.exchange.coinbase.com")
    assert "non-sandbox" in str(exc_info.value)


def test_alpaca_execution_adapter_rejects_live_url():
    with pytest.raises(RuntimeError) as exc_info:
        AlpacaPaperExecutionAdapter("https://api.alpaca.markets/v2")
    assert "Must use paper-api" in str(exc_info.value)
