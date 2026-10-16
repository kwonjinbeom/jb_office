@echo off
rem Keep this file ASCII only. cmd misreads multi-byte (Korean) text in .bat files.
setlocal
cd /d "%~dp0"

rem 1) Create the virtualenv and install Django on first run.
if not exist ".venv\Scripts\python.exe" (
    echo [setup] creating virtualenv...
    python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip || goto :fail
)
".venv\Scripts\python.exe" -c "import django" 2>nul || (
    echo [setup] installing requirements...
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt || goto :fail
)

rem 1-1) Register the daily routine 'run' link (jbroutine:) so it opens a claude terminal without this server.
call "%~dp0routine_link.bat" quiet

rem 2) Apply DB migrations.
".venv\Scripts\python.exe" manage.py migrate --noinput || goto :fail

rem 3) Start the server (127.0.0.1:8000). Ctrl+C to stop.
echo.
echo  Work server: http://127.0.0.1:8000/
echo.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
goto :eof

:fail
echo.
echo [ERROR] Failed. Check the messages above.
pause
exit /b 1
