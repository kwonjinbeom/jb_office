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

echo [1/6] Preparing secure GitHub authentication...
git credential-manager --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git Credential Manager is not available.
    echo Install or update Git for Windows, then run this script again.
    echo https://git-scm.com/download/win
    goto :fail
)

rem Use only Windows Credential Manager for this repository.
rem This prevents a GitHub token from being saved as plain text in the project.
git config --local --unset-all credential.helper >nul 2>&1
git config --local --add credential.helper ""
if errorlevel 1 goto :fail
git config --local --add credential.helper manager
if errorlevel 1 goto :fail

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

echo [2/6] Checking remote origin/main...
echo On a new computer, complete the GitHub sign-in window once.
git ls-remote --exit-code --heads origin refs/heads/main >nul
set "REMOTE_CHECK=%ERRORLEVEL%"

if "%REMOTE_CHECK%"=="0" (
    echo [3/6] Pulling origin/main with rebase...
    git pull --rebase --autostash origin main
    if errorlevel 1 goto :fail
) else if "%REMOTE_CHECK%"=="2" (
    echo [3/6] origin/main does not exist yet. Skipping pull for the first push.
) else (
    echo [ERROR] Could not access remote "origin".
    echo Complete GitHub sign-in if a browser window opened, then run this script again.
    goto :fail
)

echo [4/6] Staging every change with git add .
git add .
if errorlevel 1 goto :fail

git diff --cached --quiet
if errorlevel 1 (
    set "COMMIT_MSG=%~1"
    if not defined COMMIT_MSG (
        for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "STAMP=%%T"
        set "COMMIT_MSG=sync: !STAMP!"
    )
    echo [5/6] Committing all staged changes...
    git commit -m "!COMMIT_MSG!"
    if errorlevel 1 goto :fail
) else (
    echo [5/6] No local changes to commit.
)

echo [6/6] Pushing main to origin...
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
