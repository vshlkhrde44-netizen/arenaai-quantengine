# QuantEngine V2 — SOFTWARE_SECURITY Report
**Status**: `PASS`  
**Evaluated**: `2026-09-17T21:51:43.731266+00:00`  
**Config Hash**: `052485751566dbbd...`  

## Checks & Forensic Evidence

### [SEC-01] Strict Localhost Binding (127.0.0.1)
- **Status**: `PASS`
- **Computed Value**: `host=127.0.0.1`
- **Expected Value**: `127.0.0.1`
- **Evidence Digest**: `d2c65b5b6bea0654b3a1a846a4e86f8e0e0ec7229d7b6602373f32d2c1fe70c8`
- **Audit Notes**: Default server binds strictly to 127.0.0.1 for local isolation.

### [SEC-02] Cryptographic Vault Integrity & Health
- **Status**: `PASS`
- **Computed Value**: `HEALTHY`
- **Expected Value**: `HEALTHY`
- **Evidence Digest**: `b20bf836bf686c596927597bfea4e9eb4e0561b05ed18b209cc89ce54625c33b`
- **Audit Notes**: AES-256-GCM OS/DPAPI key derivation active.
