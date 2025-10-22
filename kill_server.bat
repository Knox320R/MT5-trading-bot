@echo off
echo Killing any Python processes using port 8765...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo Killing process ID: %%a
    taskkill /F /PID %%a
)
echo Done!
pause
