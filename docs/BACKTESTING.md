# Antigravity QuantEngine — Deterministic Backtesting Specification

## 1. Execution Semantics

To prevent lookahead leakage, execution follows strict causality:
```text
Signal generated at bar t (close)
       ↓
Order executed at bar t+1 (open)
```
Execution at the same bar close is strictly forbidden unless specifically configured with intra-bar order book data.

## 2. Cost Ladders

All backtest reports transparently separate:
- **Gross P&L**: Raw price difference $\times$ quantity.
- **Transaction Fees**: Configurable per-trade commission (default: 5 bps per side).
- **Slippage**: Configurable market impact model (default: 2 bps per side).
- **Net P&L**: $\text{Gross P\&L} - \text{Fees} - \text{Slippage}$.

## 3. Ambiguity Resolution

If both Stop-Loss and Take-Profit price thresholds are breached within the same bar's High-Low range, the simulator deterministically applies the **SL-first rule** (worst-case assumption).
