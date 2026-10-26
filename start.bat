@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run:
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

"venv\Scripts\python.exe" main.py %*
pause
