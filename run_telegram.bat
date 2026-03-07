@echo off
REM ============================================================
REM  Run Aisha's Telegram Bot
REM  Double-click this to start the bot!
REM ============================================================

call venv\Scripts\activate.bat

echo.
echo  Starting Aisha Telegram Bot...
echo  Press Ctrl+C to stop
echo.

python src\telegram\bot.py

pause
