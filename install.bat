@echo off
setlocal

echo === dont-shout installer ===
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install it from https://python.org and re-run this script.
    pause
    exit /b 1
)

:: Install dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip >nul
python -m pip install psutil plyer pycaw
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

:: Get the directory where this script lives
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"

:: Find pythonw.exe (runs Python without a console window)
for /f "delims=" %%i in ('where pythonw 2^>nul') do set "PYTHONW=%%i"
if not defined PYTHONW (
    :: Fall back to python.exe if pythonw not found
    for /f "delims=" %%i in ('where python') do set "PYTHONW=%%i"
)

echo.
echo Creating startup shortcut...

:: Create a .vbs launcher so there's no console window flash
set "LAUNCHER=%APP_DIR%\launch.vbs"
(
    echo Set objShell = CreateObject("WScript.Shell"^)
    echo objShell.Run """" ^& "%PYTHONW%" ^& """ """ ^& "%APP_DIR%\main.py" ^& """", 0, False
) > "%LAUNCHER%"

:: Copy shortcut into Windows startup folder
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy "%LAUNCHER%" "%STARTUP%\dont-shout.vbs" >nul

echo.
echo Done!
echo.
echo  - dont-shout will now start automatically when you log in.
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
