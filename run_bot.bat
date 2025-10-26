@echo off
title MT5 Trading Bot
color 0A

echo ======================================================================
echo                    Starting MT5 Trading Bot
echo ======================================================================
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the bot
python bot.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo [ERROR] Bot stopped with error
    pause
)
