@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem 1) 가상환경이 없으면 만들고 Django 를 설치한다.
if not exist ".venv\Scripts\python.exe" (
    echo [setup] creating virtualenv...
    python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip || goto :fail
)
".venv\Scripts\python.exe" -c "import django" 2>nul || (
    echo [setup] installing requirements...
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt || goto :fail
)

rem 1-1) 일일루틴 '실행' 링크 등록 (화면의 '실행'이 PC 서버 없이 claude 터미널을 연다). 실패해도 서버는 뜬다.
call "%~dp0routine_link.bat" quiet

rem 2) DB 마이그레이션 ('내 아이디어'는 일일 아이디어에서 직접 담은 것만 두므로 초기 데이터는 넣지 않는다)
".venv\Scripts\python.exe" manage.py migrate --noinput || goto :fail

rem 3) 서버 실행 (127.0.0.1:8000). 끄려면 Ctrl+C.
echo.
echo  작업서버: http://127.0.0.1:8000/
echo.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
goto :eof

:fail
echo.
echo [ERROR] 실행에 실패했습니다. 위 메시지를 확인하세요.
pause
exit /b 1
