@echo off
title BlackBox Sentinel - Workspace Setup & Sync
echo =================================================================
echo   [BlackBox Sentinel] Multi-Developer Workspace Setup Tool
echo =================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking and creating virtual environment if needed...
if not exist "venv\" (
    echo Creating python virtualenv 'venv'...
    python -m venv venv
)

echo [2/3] Activating virtual environment & installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Running workspace sync diagnostics...
python sync_workspace.py

echo.
echo =================================================================
echo  Setup Complete! 
echo  To start coding:
echo    - Open 'blackbox-sentinel.code-workspace' in VS Code or Antigravity
echo    - Press F5 to launch the full pipeline or web servers!
echo =================================================================
pause
