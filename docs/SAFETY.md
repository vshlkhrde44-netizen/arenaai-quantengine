# Antigravity QuantEngine — Safety Architecture & Prohibition Specification

## 1. Absolute Prohibition of Live Trading

The Antigravity QuantEngine codebase contains no supported paths, flags, endpoints, or mechanisms for submitting production orders with real capital.

### Safety Invariants
```python
is_production_ready = False
live_orders_enabled = False
paper_only = True
supports_live_orders = False
```

These invariants are enforced in:
1. Pydantic system configuration validators (`core/config.py`).
2. Exchange capability descriptors (`connectors/exchanges/base.py`).
3. The centralized `ExecutionSafetyGate` (`core/execution/safety_gate.py`).
4. Pre-build static AST scans (`scripts/security_scan.py`).

## 2. Emergency Stop (STOP PAPER TRADING)

Activating the Emergency Stop:
1. Immediately flips `emergency_stop_active = True`.
2. Blocks any subsequent paper order submissions.
3. Cancels all pending/acknowledged paper orders on the venue.
4. Preserves open positions and existing state.
5. Emits an immutable audit event in the cryptographic chain.
