# Antigravity QuantEngine — Developer Guide

## 1. Local Development Setup

```bash
# Clone or enter workspace
cd /home/user

# Install Python package in editable mode with development dependencies
pip install -e ".[dev]"

# Install Frontend dependencies
cd apps/frontend
npm install
cd ../..
```

## 2. Running Verification Suite

```bash
# Run Static Safety Scan
python scripts/security_scan.py

# Run Full Pytest Suite (Unit, Integration, Property, Mutation, E2E)
PYTHONPATH=. pytest -v tests/
```

## 3. Adding a New Strategy

1. Inherit from `BaseStrategy` (`core/strategies/base.py`).
2. Implement `generate_signals(df: pd.DataFrame) -> List[Signal]`.
3. Register the strategy in `core/strategies/library.py` and register in `StrategyRegistry`.
4. Run adversarial lookahead tests with `LookaheadGuard.verify_causal_invariance(strategy, df)` to ensure no future leakage.
5. Freeze the strategy and request human review before promoting to paper trading.
