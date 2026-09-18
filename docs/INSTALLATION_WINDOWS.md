# Antigravity QuantEngine — Windows Installation & User Guide

## 1. Quick Installation (PowerShell)

1. Open PowerShell as a regular user (administrative privileges are not required).
2. Navigate to the downloaded directory.
3. Run the installer script:
   ```powershell
   .\installer\Install-QuantEngine.ps1
   ```
4. The installer:
   - Sets up `%LOCALAPPDATA%\AntigravityQuantEngine\`
   - Copies application assets and builds SQLite operational tables
   - Creates an **Antigravity QuantEngine** shortcut on your Desktop and Start Menu.

## 2. Launching the Terminal

Double-click the **Antigravity QuantEngine** desktop icon, or run:
```cmd
QuantEngine_Launcher.bat
```
Your browser will automatically open to `http://127.0.0.1:8000`.

## 3. First-Run Setup Wizard

1. Open the **Settings & Vault** tab.
2. Select your exchange venue (e.g., Coinbase Exchange Sandbox or Alpaca Paper).
3. Enter your sandbox API Key, Secret, and Passphrase.
4. Click **Save Encrypted Paper Credentials** (encrypted using hardware-bound AES-256-GCM).
5. Switch to **Paper Trading** or **Dashboard** to monitor live market data and submit test paper orders.
