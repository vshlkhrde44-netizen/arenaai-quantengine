# Antigravity QuantEngine — Technical Architecture Specification

## 1. System Overview

Antigravity QuantEngine is designed as a local-first, high-throughput quantitative research and real-time paper trading platform. It strictly decouples quantitative research, raw wire data capture, paper execution, and audit forensics.

```text
+-----------------------------------------------------------------------------------+
|                               Windows Host                                        |
|  +-----------------------------------------------------------------------------+  |
|  |                     React + TypeScript Terminal UI                          |  |
|  |   (Dashboard, Markets, Microstructure, Strategies, Backtest, Paper Trading)  |  |
|  +---------------------------------------^-------------------------------------+  |
|                                          | HTTP REST & WebSocket (/ws/stream)      |
|  +---------------------------------------v-------------------------------------+  |
|  |                            FastAPI Application                              |  |
|  |               (43 Typed Endpoints, Security Vault, State API)               |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |                                         |
|  +--------------------+------------------+-------------------+------------------+  |
|  |                    |                  |                   |                  |  |
|  v                    v                  v                   v                  v  |
| Market Data Worker  Microstructure    Risk Engine     ExecutionSafetyGate   Audit  |
| [Bounded Queue]     [CVD, Footprint]  [Drawdown/Caps] [Paper Invariant]     [Chain]|
|       |                                                      |                     |
|       v                                                      v                     |
| Public WebSocket                                     Sandbox REST API              |
| (Real Exchanges)                                     (Coinbase/Alpaca)             |
+------------------------------------------------------------------------------------+
```

## 2. Core Invariants

1. **Safety Firewall Invariant**:
   `is_production_ready = False`, `live_orders_enabled = False`, `paper_only = True`, `supports_live_orders = False`.
2. **Causal Execution Semantics**:
   Signal at bar $t$ close $\to$ Execution at bar $t+1$ open.
3. **Queue Conservation Law**:
   $\text{received} = \text{persisted} + \text{rejected} + \text{explicitly\_lost} + \text{unknown}$.
4. **Tamper-Evident Hash Chain**:
   $H_0 = \text{GENESIS}$, $H_i = \text{SHA256}(H_{i-1} \parallel \text{timestamp} \parallel \text{canonical\_payload})$.
5. **D3 Sealed Data Firewall**:
   When sealed, $D3\_READ = 0, D3\_LOAD = 0, D3\_HASH = 0$.
