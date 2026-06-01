@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python game.py
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 game.py
    goto :eof
)

echo Python was not found on this computer.
echo Install Python 3 and make sure it is added to PATH, then try again.
pause
