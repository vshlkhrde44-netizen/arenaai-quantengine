# ==============================================================================
# Antigravity QuantEngine - Windows PowerShell Launcher
# STRICT SAFETY ENFORCEMENT: PAPER TRADING ONLY
# ==============================================================================

[Console]::Title = "Antigravity QuantEngine [PAPER TRADING ONLY]"
$Host.UI.RawUI.ForegroundColor = "Green"

Write-Host "=============================================================================="
Write-Host "          ANTIGRAVITY QUANTENGINE - INSTITUTIONAL TERMINAL"
Write-Host "=============================================================================="
Write-Host "  Execution Mode: [ PAPER TRADING ONLY ]"
Write-Host "  Live Trading:   [ PERMANENTLY DISABLED - INVIOLABLE ]"
Write-Host "=============================================================================="
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir\.."
Set-Location $ProjectRoot

# Verify Python
try {
    $pythonVer = python --version
    Write-Host "[*] Python runtime: $pythonVer"
} catch {
    Write-Error "[!] Python 3.11+ is required to execute Antigravity QuantEngine."
    exit 1
}

# Verify Environment
Write-Host "[*] Verifying operational SQLite schemas and cryptographic hash chains..."
python -c "from database.engine import get_db; get_db()"

# Launch browser
Write-Host "[*] Opening browser at http://127.0.0.1:8000..."
Start-Process "http://127.0.0.1:8000"

# Execute backend server
Write-Host "[*] Antigravity QuantEngine running on http://127.0.0.1:8000. Press Ctrl+C to terminate."
python -m apps.backend.main
