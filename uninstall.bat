@echo off
setlocal

echo === dont-shout uninstaller ===
echo.

:: Stop running instance
set "PID_FILE=%~dp0.dont-shout.pid"
if exist "%PID_FILE%" (
    echo Stopping running dont-shout instance...
    set /p OLD_PID=<"%PID_FILE%"
    taskkill /pid %OLD_PID% /f >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
) else (
    echo No running instance found.
)

:: Remove startup shortcut
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\dont-shout.vbs" (
    echo Removing startup shortcut...
    del "%STARTUP%\dont-shout.vbs" >nul
) else (
    echo No startup shortcut found.
)

:: Remove launcher
if exist "%~dp0launch.vbs" (
    del "%~dp0launch.vbs" >nul
)

echo.
echo Done! dont-shout has been removed from your system.
echo The app files are still in this folder — delete them manually if you want.
echo.

pause
