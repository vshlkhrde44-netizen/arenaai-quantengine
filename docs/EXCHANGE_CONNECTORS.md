# Antigravity QuantEngine — Exchange Connectors Specification

## 1. Connector Interface Architecture

Every exchange connector implements the `ExchangeAdapter` composite interface:

```python
class ExchangeAdapter(ABC):
    capabilities: CapabilityDescriptor
    market_data: MarketDataAdapter
    execution: PaperExecutionAdapter
    account: AccountAdapter
```

## 2. Mandatory Capability Descriptor

Every connector must explicitly declare its capabilities:
- `supports_live_orders`: **MUST BE FALSE** across all connectors.
- `supports_live_market_data`: True if public WebSocket feed is supported.
- `supports_paper_orders`: True if an official testnet or sandbox exists.
- `supports_orderbook`: True if L2 depth is provided.
- `supports_trades`: True if public trades are available.
- `supports_ticker`: True if best bid/ask/last is streamed.
- `paper_rest_url`: Explicit sandbox endpoint.

## 3. Implemented Venues

### Coinbase Exchange
- **Market Data**: Public WebSocket at `wss://ws-feed.exchange.coinbase.com` for real-time tickers and trades.
- **Paper Execution**: Official Coinbase Exchange Sandbox at `https://api-public.sandbox.exchange.coinbase.com`.
- **Authentication**: HMAC-SHA256 signature using `CB-ACCESS-KEY`, `CB-ACCESS-SIGN`, `CB-ACCESS-TIMESTAMP`, `CB-ACCESS-PASSPHRASE`.

### Alpaca Paper
- **Paper Execution**: Official Alpaca Paper Trading REST API at `https://paper-api.alpaca.markets/v2`.
- **Authentication**: `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`.
- **Safety Invariant**: Strict rejection of any non-`paper-api` Alpaca URL.
