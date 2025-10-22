@echo off
echo Starting MT5 Real-Time Dashboard...
echo.

REM Get the full path to the HTML file
set "HTML_FILE=%~dp0interface\index.html"

REM Open the dashboard in default browser
echo Opening dashboard in browser...
start "" "%HTML_FILE%"

REM Wait 2 seconds for browser to start
timeout /t 2 /nobreak >nul

REM Start the Python server
echo Starting WebSocket server...
python "%~dp0realtime_server.py"
