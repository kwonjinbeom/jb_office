@echo off
rem Keep this file ASCII only. cmd misreads multi-byte (Korean) text in .bat files.
rem Registers the daily routine 'run' link (jbroutine:) for the current user (no admin needed).
rem run.bat calls this on every start. Double-clicking this file alone also works.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [link] No virtualenv yet. Run run.bat once first.
    if "%~1"=="" pause
    exit /b 1
)
set "KEY=HKCU\Software\Classes\jbroutine"
reg add "%KEY%" /ve /d "URL:jbroutine" /f >nul || goto :fail
reg add "%KEY%" /v "URL Protocol" /d "" /f >nul || goto :fail
reg add "%KEY%\shell\open\command" /ve /d "\"%~dp0.venv\Scripts\python.exe\" \"%~dp0manage.py\" routine_open --pause \"%%1\"" /f >nul || goto :fail
if "%~1"=="" (
    echo [link] Registered the daily routine 'run' link. Clicking 'run' in the app now opens a claude terminal.
    pause
)
exit /b 0

:fail
echo [link] Registration failed. Check the messages above.
if "%~1"=="" pause
exit /b 1
