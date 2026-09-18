# ==============================================================================
# Antigravity QuantEngine - Windows Native Uninstaller Script
# Removes program files, shortcuts, and preserves user research data
# ==============================================================================

param (
    [string]$InstallDir = "$env:LOCALAPPDATA\AntigravityQuantEngine",
    [switch]$PurgeUserData
)

Write-Host "Uninstalling Antigravity QuantEngine..." -ForegroundColor Yellow

# Remove Shortcuts
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$StartMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"

if (Test-Path "$DesktopPath\Antigravity QuantEngine.lnk") {
    Remove-Item "$DesktopPath\Antigravity QuantEngine.lnk" -Force
}
if (Test-Path "$StartMenuPath\Antigravity QuantEngine.lnk") {
    Remove-Item "$StartMenuPath\Antigravity QuantEngine.lnk" -Force
}

# Remove Application Directory
if (Test-Path $InstallDir) {
    if ($PurgeUserData) {
        Remove-Item -Recurse -Force $InstallDir
        Write-Host "Completely purged $InstallDir"
    } else {
        # Keep data folder, remove code
        Get-ChildItem -Path $InstallDir -Exclude "data" | Remove-Item -Recurse -Force
        Write-Host "Removed application files. Preserved historical datasets and reports in $InstallDir\data"
    }
}

Write-Host "Antigravity QuantEngine uninstalled successfully." -ForegroundColor Green
