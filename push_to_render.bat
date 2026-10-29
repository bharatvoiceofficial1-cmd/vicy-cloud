@echo off
title Push VICY Cloud to GitHub & Render
echo ======================================================================
echo           PUSH VICY AUTONOMOUS CLOUD AGENT TO GITHUB & RENDER
echo ======================================================================
echo.
echo Step 1: Create a new (empty) repository on GitHub (e.g. named 'vicy-cloud').
echo         Link: https://github.com/new
echo.
set /p REPO_URL="Enter your GitHub Repository URL (e.g. https://github.com/yourname/vicy-cloud.git): "

if "%REPO_URL%"=="" (
    echo [ERROR] No repository URL provided. Aborting.
    pause
    exit /b 1
)

echo.
echo [1/3] Setting branch to main...
git branch -M main

echo [2/3] Adding remote origin...
git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%

echo [3/3] Pushing files to GitHub...
git push -u origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Git push failed. Please verify your GitHub credentials or repo URL.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo [SUCCESS] Code pushed to GitHub successfully!
echo.
echo Now deploy to Render in 2 clicks:
echo   1. Opening https://dashboard.render.com in your browser...
echo   2. Click 'New +' -> 'Blueprint' (or 'Web Service')
echo   3. Select your 'vicy-cloud' repository
echo   4. Click 'Apply' / 'Deploy'!
echo ======================================================================
start https://dashboard.render.com/blueprints/new
pause
