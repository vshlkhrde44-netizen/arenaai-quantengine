# Antigravity QuantEngine - Start Development Servers
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "  Starting Antigravity QuantEngine Development Environment" -ForegroundColor Green
Write-Host "  Mode: PAPER TRADING ONLY | Live Trading: PERMANENTLY DISABLED" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Green

# Start FastAPI backend in background
Write-Host "[*] Starting FastAPI Backend on http://127.0.0.1:8000..."
$BackendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python -m apps.backend.main
}

Start-Sleep -Seconds 2

# Start Vite Frontend dev server
Write-Host "[*] Starting Vite React Frontend on http://127.0.0.1:3000..."
Set-Location apps/frontend
npm run dev
