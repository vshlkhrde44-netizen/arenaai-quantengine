# Antigravity QuantEngine — Operational Troubleshooting Guide

## Common Issues & Resolutions

### 1. "Static Safety Scan Failed: prohibited live endpoint keyword detected"
- **Cause**: Code contains references to live trading domains or flags (`live_orders_enabled=True`).
- **Fix**: Check `scripts/security_scan.py` output. Ensure all execution URLs point exclusively to sandbox or paper domains.

### 2. "ExecutionSafetyGate Rejection: Runtime mode is 'RESEARCH'"
- **Cause**: An order was submitted while the engine was in research or development mode.
- **Fix**: Orders are permitted only in `PAPER_TRADING` mode. Set `system.runtime_mode: PAPER_TRADING` in `configs/default_config.yaml`.

### 3. "D3 SEALED DATA FIREWALL VIOLATION: Dataset is cryptographically sealed"
- **Cause**: An attempt was made to inspect or load an out-of-sample sealed test dataset.
- **Fix**: Sealed datasets cannot be read by research strategies to preserve blind out-of-sample purity. Use training datasets for strategy research.

### 4. "Audit sequence discontinuity or content tampering detected"
- **Cause**: An external process modified or deleted rows from the SQLite `audit_events` table.
- **Fix**: SQLite database must be restored from backup or re-initialized via `database/engine.py`.
