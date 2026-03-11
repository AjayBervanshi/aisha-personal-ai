@echo off
REM ============================================================
REM  Test Aisha — verify everything works
REM  Run this before starting the bot!
REM ============================================================

call venv\Scripts\activate.bat

echo.
echo  Running Aisha system check...
echo.

python scripts\test_aisha.py -i

pause
