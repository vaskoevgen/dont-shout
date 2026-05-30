@echo off
setlocal

echo === dont-shout installer ===
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install it from https://python.org and re-run this script.
    echo        Make sure to tick "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: Stop any running instance using PID file
set "PID_FILE=%~dp0.dont-shout.pid"
if exist "%PID_FILE%" (
    echo Stopping running dont-shout instance...
    set /p OLD_PID=<"%PID_FILE%"
    taskkill /pid %OLD_PID% /f >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
)

:: Install dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip >nul

python -m pip install pyaudio
if errorlevel 1 (
    echo ERROR: Could not install pyaudio.
    echo Try manually: pip install pyaudio
    pause
    exit /b 1
)

python -m pip install plyer pycaw pyttsx3
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.

:: Get the directory where this script lives
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"

:: Find pythonw.exe (runs Python without a console window)
for /f "delims=" %%i in ('where pythonw 2^>nul') do set "PYTHONW=%%i"
if not defined PYTHONW (
    for /f "delims=" %%i in ('where python') do set "PYTHONW=%%i"
)

echo Creating startup shortcut...

:: Create a .vbs launcher so there's no console window
set "LAUNCHER=%APP_DIR%\launch.vbs"
(
    echo Set objShell = CreateObject("WScript.Shell"^)
    echo objShell.Run """" ^& "%PYTHONW%" ^& """ """ ^& "%APP_DIR%\main.py" ^& """", 0, False
) > "%LAUNCHER%"

:: Add to Windows startup folder
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy "%LAUNCHER%" "%STARTUP%\dont-shout.vbs" >nul

echo.
echo Done!
echo.
echo  - dont-shout will start automatically when you log in.
echo  - On first run it measures ambient noise for 3 seconds (stay quiet).
echo  - To start it right now without rebooting, run:
echo      wscript "%LAUNCHER%"
echo.
echo  - To uninstall: delete "%STARTUP%\dont-shout.vbs"
echo.

set /p "START_NOW=Start dont-shout now? [Y/n]: "
if /i not "%START_NOW%"=="n" (
    wscript "%LAUNCHER%"
    echo dont-shout is running in the background.
)

pause
