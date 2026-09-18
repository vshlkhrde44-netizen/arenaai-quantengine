"""
Antigravity QuantEngine - Exchange Connector Registry
Factory and safety verification registry for exchange adapters.
"""

from typing import Dict, Optional, List, Any
from connectors.exchanges.base import ExchangeAdapter
from connectors.exchanges.coinbase_connector import CoinbaseExchangeAdapter
from connectors.exchanges.alpaca_connector import AlpacaExchangeAdapter
from core.logging import get_logger

logger = get_logger("connector.registry")


class ExchangeRegistry:
    def __init__(self):
        self._connectors: Dict[str, ExchangeAdapter] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        coinbase = CoinbaseExchangeAdapter()
        self.register("coinbase", coinbase)
        alpaca = AlpacaExchangeAdapter()
        self.register("alpaca", alpaca)

    def register(self, name: str, adapter: ExchangeAdapter) -> None:
        # Enforce global safety invariants before allowing registration
        adapter.capabilities.verify_safety()
        if adapter.capabilities.supports_live_orders:
            raise RuntimeError(f"FATAL: Attempted to register unsafe connector {name} with live order support!")

        # Section 70: Mock Exchange Firewall Enforcement
        from core.config import get_config, RuntimeMode
        cfg = get_config()
        is_mock = getattr(adapter.capabilities, "is_mock", False) or "mock" in name.lower()
        if is_mock and cfg.system.runtime_mode != RuntimeMode.TEST:
            raise RuntimeError(
                f"MOCK_EXCHANGE_FIREWALL_VIOLATION: Mock exchange '{name}' cannot be activated in "
                f"runtime mode '{cfg.system.runtime_mode.value}'. Only TEST mode permits mocks (Section 70)."
            )

        self._connectors[name.lower()] = adapter
        logger.info(f"Registered safe exchange connector: {name} (paper_only={adapter.capabilities.is_paper_only})")

    def get(self, name: str) -> Optional[ExchangeAdapter]:
        return self._connectors.get(name.lower())

    def list_connectors(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "capabilities": adapter.capabilities.model_dump()
            }
            for name, adapter in self._connectors.items()
        ]


_REGISTRY: Optional[ExchangeRegistry] = None


def get_connector_registry() -> ExchangeRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ExchangeRegistry()
    return _REGISTRY
