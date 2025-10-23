@echo off
echo ====================================
echo  Installing Trading Bot Dependencies
echo ====================================
echo.

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install required packages from requirements.txt
echo Installing required packages...
pip install -r requirements.txt
echo.

echo ====================================
echo  Installation Complete!
echo ====================================
echo.
echo You can now run the bot with:
echo   python bot.py
echo.
pause
