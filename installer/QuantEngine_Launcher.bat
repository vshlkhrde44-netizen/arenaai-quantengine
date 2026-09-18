@echo off
REM ==============================================================================
REM Antigravity QuantEngine - Windows Desktop Launcher
REM INSTITUTIONAL QUANT RESEARCH & REAL-TIME PAPER TRADING ONLY
REM LIVE PRODUCTION TRADING PERMANENTLY DISABLED
REM ==============================================================================

title Antigravity QuantEngine [PAPER TRADING ONLY]
color 0A

echo ==============================================================================
echo           ANTIGRAVITY QUANTENGINE - INSTITUTIONAL TERMINAL
echo ==============================================================================
echo  Execution Mode: [ PAPER TRADING ONLY ]
echo  Live Trading:   [ PERMANENTLY DISABLED - INVIOLABLE ]
echo ==============================================================================
echo.

cd /d "%~dp0\.."

echo [*] Verifying Python runtime environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ERROR: Python 3.11+ was not found in PATH.
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

echo [*] Initializing QuantEngine SQLite operational state and migration engine...
python -c "from database.engine import get_db; get_db()" >nul 2>&1

echo [*] Launching Antigravity QuantEngine local web application...
start "" "http://127.0.0.1:8000"

echo [*] Starting QuantEngine background engine on http://127.0.0.1:8000
python -m apps.backend.main

pause
