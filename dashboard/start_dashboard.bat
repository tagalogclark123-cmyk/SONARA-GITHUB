@echo off
rem Starts the SONARA Field Monitor. Keep this window open while you use the dashboard.
cd /d "%~dp0.."
where python >nul 2>nul
if %errorlevel%==0 (
    python dashboard\server.py %*
) else (
    py dashboard\server.py %*
)
echo.
pause
