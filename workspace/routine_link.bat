@echo off
rem 일일루틴 '실행' 링크(jbroutine:) 등록: 화면에서 '실행'을 누르면 PC 서버 없이 claude 터미널이 열린다.
rem run.bat 이 시작할 때마다 부른다. 이 파일만 한 번 더블클릭해도 된다. (관리자 권한 필요 없음, 현재 사용자에게만)
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [link] 가상환경이 없습니다. run.bat 을 먼저 한 번 실행하세요.
    if "%~1"=="" pause
    exit /b 1
)
set "KEY=HKCU\Software\Classes\jbroutine"
reg add "%KEY%" /ve /d "URL:jbroutine" /f >nul || goto :fail
reg add "%KEY%" /v "URL Protocol" /d "" /f >nul || goto :fail
reg add "%KEY%\shell\open\command" /ve /d "\"%~dp0.venv\Scripts\python.exe\" \"%~dp0manage.py\" routine_open --pause \"%%1\"" /f >nul || goto :fail
if "%~1"=="" (
    echo [link] 일일루틴 '실행' 링크를 등록했습니다. 이제 화면에서 '실행'을 누르면 claude 터미널이 열립니다.
    pause
)
exit /b 0

:fail
echo [link] 등록하지 못했습니다. 위 메시지를 확인하세요.
if "%~1"=="" pause
exit /b 1
