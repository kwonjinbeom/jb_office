@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0" || goto :fail

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not available in PATH.
    goto :fail
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This folder is not a Git repository.
    goto :fail
)

set "CURRENT_BRANCH="
for /f "delims=" %%B in ('git branch --show-current') do set "CURRENT_BRANCH=%%B"
if /i not "%CURRENT_BRANCH%"=="main" (
    echo [ERROR] Current branch is "%CURRENT_BRANCH%". This script only works on main.
    goto :fail
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Remote "origin" is not configured.
    goto :fail
)

git config user.name >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git user.name is not configured on this computer.
    echo Run: git config --global user.name "Your Name"
    goto :fail
)

git config user.email >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git user.email is not configured on this computer.
    echo Run: git config --global user.email "you@example.com"
    goto :fail
)

echo [1/5] Checking remote origin/main...
git ls-remote --exit-code --heads origin refs/heads/main >nul 2>&1
set "REMOTE_CHECK=%ERRORLEVEL%"

if "%REMOTE_CHECK%"=="0" (
    echo [2/5] Pulling origin/main with rebase...
    git pull --rebase --autostash origin main
    if errorlevel 1 goto :fail
) else if "%REMOTE_CHECK%"=="2" (
    echo [2/5] origin/main does not exist yet. Skipping pull for the first push.
) else (
    echo [ERROR] Could not access remote "origin".
    goto :fail
)

echo [3/5] Staging every change with git add .
git add .
if errorlevel 1 goto :fail

git diff --cached --quiet
if errorlevel 1 (
    set "COMMIT_MSG=%~1"
    if not defined COMMIT_MSG (
        for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "STAMP=%%T"
        set "COMMIT_MSG=sync: !STAMP!"
    )
    echo [4/5] Committing all staged changes...
    git commit -m "!COMMIT_MSG!"
    if errorlevel 1 goto :fail
) else (
    echo [4/5] No local changes to commit.
)

echo [5/5] Pushing main to origin...
git push -u origin main
if errorlevel 1 goto :fail

echo.
echo Git sync completed successfully.
goto :done

:fail
echo.
echo Git sync failed. Review the message above; no later step was run.
pause
endlocal
exit /b 1

:done
pause
endlocal
exit /b 0
