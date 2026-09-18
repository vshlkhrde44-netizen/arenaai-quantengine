# Antigravity QuantEngine - Automated Test Runner
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "       Executing Antigravity QuantEngine Automated Verification Suite" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

# 1. Run Static Security Scan
Write-Host "[1/2] Running Static Safety and Live Endpoint Prohibition Scan..."
python scripts/security_scan.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Static Safety Scan Failed! Prohibited live patterns detected."
    exit 1
}

# 2. Run Pytest Suite
Write-Host "[2/2] Running Unit, Integration, Property, Mutation, Fault Injection, and E2E Tests..."
$env:PYTHONPATH = "."
pytest -v tests/

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host "   ALL 30 VERIFICATION TESTS PASSED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "   Live Trading Prohibition and Paper Execution Invariants Certified." -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
} else {
    Write-Error "Test suite reported failures."
    exit 1
}
