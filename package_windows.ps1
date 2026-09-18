# Antigravity QuantEngine - Windows Packaging Script
param (
    [string]$OutputDir = "dist_installer"
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "       Packaging Antigravity QuantEngine for Windows Distribution" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

# 1. Safety Scan
python scripts/security_scan.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Safety scan failed! Packaging aborted."
    exit 1
}

# 2. Build Frontend
Write-Host "[*] Building frontend distribution..."
Set-Location apps/frontend
npm run build
Set-Location ../..

# 3. Create installer package directory
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# 4. Check for Inno Setup (ISCC.exe)
$ISCC = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $ISCC) {
    Write-Host "[*] Compiling Inno Setup standalone executable..."
    & $ISCC installer\QuantEngine_Installer.iss
    Write-Host "[+] Generated Windows Installer: $OutputDir\AntigravityQuantEngine_Setup_v1.0.0.exe" -ForegroundColor Green
} else {
    Write-Host "[*] Inno Setup compiler (ISCC.exe) not found in Program Files."
    Write-Host "[*] Bundling PowerShell-based Windows native installer package..."
    # Exclude data/ directory so that runtime state, databases, credentials, and logs are NEVER shipped (P0-27)
    Compress-Archive -Path "apps", "core", "connectors", "database", "configs", "installer", "pyproject.toml", "README.md", "LICENSE" -DestinationPath "$OutputDir\AntigravityQuantEngine_v1.0.0_Windows.zip" -Force
    Write-Host "[+] Generated Windows Installation Archive: $OutputDir\AntigravityQuantEngine_v1.0.0_Windows.zip" -ForegroundColor Green
}
