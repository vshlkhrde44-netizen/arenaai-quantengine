# Antigravity QuantEngine - Start Production Local Server
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "  Starting Antigravity QuantEngine (Unified Production Mode)" -ForegroundColor Green
Write-Host "  Serving React UI + FastAPI Backend on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Mode: PAPER TRADING ONLY | Live Trading: PERMANENTLY DISABLED" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Green

# Ensure frontend is built
if (-not (Test-Path "apps/frontend/dist")) {
    Write-Host "[*] Building frontend assets..."
    Set-Location apps/frontend
    npm run build
    Set-Location ../..
}

# Open browser
Start-Process "http://127.0.0.1:8000"

# Run backend serving static assets
python -m apps.backend.main
