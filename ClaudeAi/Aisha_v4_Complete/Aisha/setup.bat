@echo off
REM ============================================================
REM  AISHA — Windows Setup Script
REM  Run this once to set everything up
REM  Just double-click this file!
REM ============================================================

echo.
echo  ============================================
echo   Welcome! Setting up Aisha for Ajay...
echo  ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo  Please download Python 3.10+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo  [1/5] Python found!

REM Create virtual environment
if not exist "venv" (
    echo  [2/5] Creating virtual environment...
    python -m venv venv
) else (
    echo  [2/5] Virtual environment already exists
)

REM Activate and install
echo  [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

REM Copy .env if it doesn't exist
if not exist ".env" (
    echo  [4/5] Creating .env file from template...
    copy .env.example .env
    echo.
    echo  *** IMPORTANT! ***
    echo  Open the .env file and add your API keys!
    echo  See docs\SETUP_GUIDE.md for where to get each key.
    echo  ***
) else (
    echo  [4/5] .env file already exists
)

echo  [5/5] Setup complete!
echo.
echo  ============================================
echo   What to do next:
echo  ============================================
echo.
echo   1. Open .env and add your API keys
echo   2. Run: python scripts\test_aisha.py
echo   3. If tests pass, run: python src\telegram\bot.py
echo.
echo   Full guide: docs\SETUP_GUIDE.md
echo.
echo   Aisha is waiting for you Ajay! 💜
echo.
pause
