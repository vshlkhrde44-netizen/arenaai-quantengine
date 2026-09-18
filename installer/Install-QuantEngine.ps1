# ==============================================================================
# Antigravity QuantEngine - Windows Native Installation Script
# Installs application to %LOCALAPPDATA%\AntigravityQuantEngine
# Registers Start Menu and Desktop Shortcuts
# Initializes SQLite WAL Operational State
# ==============================================================================

param (
    [string]$InstallDir = "$env:LOCALAPPDATA\AntigravityQuantEngine",
    [switch]$NoShortcuts
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "       Installing Antigravity QuantEngine (Local-First Windows)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  Mode: PAPER TRADING ONLY | Live Trading Disabled by Invariants" -ForegroundColor Green
Write-Host ""

$SourceDir = Resolve-Path "$PSScriptRoot\.."

# 1. Create target directories
Write-Host "[1/5] Creating application directories in $InstallDir..."
New-Item -ItemType Directory -Force -Path "$InstallDir\apps" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\core" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\connectors" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\data\raw" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\data\datasets" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\data\reports" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\data\manifests" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\data\vault" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\database" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\configs" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\installer" | Out-Null

# 2. Copy application trees
Write-Host "[2/5] Copying core engine, backend, frontend distribution..."
Copy-Item -Recurse -Force "$SourceDir\apps\backend" "$InstallDir\apps\"
Copy-Item -Recurse -Force "$SourceDir\apps\frontend\dist" "$InstallDir\apps\frontend\dist"
Copy-Item -Recurse -Force "$SourceDir\core" "$InstallDir\"
Copy-Item -Recurse -Force "$SourceDir\connectors" "$InstallDir\"
Copy-Item -Recurse -Force "$SourceDir\database" "$InstallDir\"
Copy-Item -Recurse -Force "$SourceDir\configs" "$InstallDir\"
Copy-Item -Force "$SourceDir\installer\QuantEngine_Launcher.bat" "$InstallDir\"
Copy-Item -Force "$SourceDir\installer\QuantEngine_Launcher.ps1" "$InstallDir\"
Copy-Item -Force "$SourceDir\installer\Uninstall-QuantEngine.ps1" "$InstallDir\"
Copy-Item -Force "$SourceDir\pyproject.toml" "$InstallDir\"
Copy-Item -Force "$SourceDir\README.md" "$InstallDir\"
Copy-Item -Force "$SourceDir\LICENSE" "$InstallDir\"

# 3. Setup Python dependencies in target
Write-Host "[3/5] Verifying Python dependencies..."
python -m pip install -e "$InstallDir" --quiet

# 4. Initialize Database
Write-Host "[4/5] Initializing operational SQLite state & migrations..."
Set-Location $InstallDir
python -c "from database.engine import get_db; get_db()"
python -c "from core.research.dataset_seeder import register_default_strategies; register_default_strategies()"

# 5. Create Shortcuts
if (-not $NoShortcuts) {
    Write-Host "[5/5] Creating Windows Desktop and Start Menu shortcuts..."
    $WshShell = New-Object -ComObject WScript.Shell
    
    # Desktop Shortcut
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $Shortcut = $WshShell.CreateShortcut("$DesktopPath\Antigravity QuantEngine.lnk")
    $Shortcut.TargetPath = "$InstallDir\QuantEngine_Launcher.bat"
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = "Antigravity QuantEngine - Institutional Paper Trading & Research"
    $Shortcut.Save()

    # Start Menu Shortcut
    $StartMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    $StartShortcut = $WshShell.CreateShortcut("$StartMenuPath\Antigravity QuantEngine.lnk")
    $StartShortcut.TargetPath = "$InstallDir\QuantEngine_Launcher.bat"
    $StartShortcut.WorkingDirectory = $InstallDir
    $StartShortcut.Description = "Antigravity QuantEngine"
    $StartShortcut.Save()
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "   Antigravity QuantEngine installation completed successfully!" -ForegroundColor Green
Write-Host "   Launch from Desktop Shortcut or run: $InstallDir\QuantEngine_Launcher.bat" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Green
