# Antigravity QuantEngine — Security Architecture & Credential Protection

## 1. Zero Plaintext Secret Rule

API keys, secrets, passphrases, and HMAC signatures must never exist in:
- Source code or version control
- `.env` files or JSON configurations
- SQLite database tables
- Application logs (structured loggers automatically redact matching tokens)
- Browser `localStorage` or `sessionStorage`
- Network request URLs or query parameters
- Error tracebacks and exception payloads

## 2. AES-256-GCM Hardware-Bound Credential Vault

The `CredentialVault` (`core/security/credentials.py`) uses:
- **Cipher**: AES-256-GCM (Galois/Counter Mode with 128-bit authentication tag)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 200,000 iterations
- **Entropy Sources**: 32-byte cryptographic salt (`data/vault/vault.salt`) combined with machine-bound hardware identifiers (Computer name, CPU processor, node).
- **Access Restrictions**: Only server-side worker adapters load credentials to construct ephemeral HMAC signatures. The frontend receives only masked identifiers (`API-KEY-****-3a1b`).

## 3. Production Endpoint Hard-Block

The `ExecutionSafetyGate` verifies that every requested order endpoint explicitly belongs to an official sandbox (`api-public.sandbox.exchange.coinbase.com` or `paper-api.alpaca.markets`). Any string matching live trading domains produces a fatal exception and triggers an immediate audit rejection event before any network packet is transmitted.
