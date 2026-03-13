@echo off
REM ============================================================
REM  Genoresearch Dashboard — http://localhost:5555
REM ============================================================
cd /d "%~dp0"
echo.
echo   Starting Genoresearch Dashboard...
echo   Open: http://localhost:5555
echo.
python dashboard.py --port 5555
pause
