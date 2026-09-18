# Antigravity QuantEngine — Paper Trading Operational Guide

## 1. Paper Trading Definition

Paper trading in Antigravity QuantEngine means:
> **Real-Time Exchange Public Market Data + Official Exchange Sandbox Execution**

It is **NOT** a synthetic random-walk simulator. Prices, trades, and order books are captured directly from live exchange feeds. Paper orders are dispatched to official exchange sandboxes (e.g. Coinbase Sandbox REST API).

## 2. Order Lifecycle State Machine

An order progresses through an explicit, non-bypassable state machine:
```text
CREATED
   ↓
VALIDATING (checks symbol, quantity > 0, price)
   ↓
SAFETY_CHECK (passes ExecutionSafetyGate)
   ↓
SUBMITTING (transmits to sandbox endpoint)
   ↓
ACKNOWLEDGED (sandbox returns order ID)
   ↓
FILLED (executed against sandbox fills or simulated execution price)
```

Alternative paths:
- `REJECTED`: Fails validation, safety gate, or risk limits.
- `CANCEL_PENDING` $\to$ `CANCELLED`: User or strategy cancels order.
- `ERROR`: Network or venue exception.

## 3. Account Reconciliation

The `PaperReconciliationEngine` periodically queries exchange sandbox balance and position endpoints, comparing them with the internal SQLite ledger. Discrepancies generate a `RECONCILIATION_ALERT` without destructively overwriting historical logs.
