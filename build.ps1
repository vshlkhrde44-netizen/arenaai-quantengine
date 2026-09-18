# Antigravity QuantEngine - Full System Build Script
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "       Building Antigravity QuantEngine (Frontend & Backend)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# 1. Static Safety Scan
Write-Host "[1/4] Running Static Safety and Live Endpoint Prohibition Scan..."
python scripts/security_scan.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Static Safety Scan Failed! Prohibited live patterns detected."
    exit 1
}

# 2. Python Dependencies
Write-Host "[2/4] Installing Python dependencies..."
python -m pip install -e . --quiet

# 3. Frontend Build
Write-Host "[3/4] Building React TypeScript Frontend (Vite)..."
Set-Location apps/frontend
npm run build
Set-Location ../..

# 4. Verify Build Integrity
Write-Host "[4/4] Verifying System Compilation & Safe Isolation..."
python -c "import core.config; print('System configuration verified safely.')"

Write-Host ""
Write-Host "Antigravity QuantEngine build completed successfully!" -ForegroundColor Green
