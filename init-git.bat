@echo off
chcp 65001 >nul 2>&1

echo ========================================
echo   Git Project Initialization
echo ========================================
echo.

if not exist .git (
    echo [1/7] Initializing Git repository...
    git init
    echo.
) else (
    echo [1/7] Git repository already exists
    echo.
)

echo [2/7] Configuring Git user name...
git config --global user.name "WangHao"
echo Done
echo.

echo [3/7] Configuring Git user email...
git config --global user.email "wanghao@test.com"
echo Done
echo.

echo [4/7] Verifying configuration...
git config user.name
git config user.email
echo.

echo [5/7] Disabling CRLF automatic conversion...
git config --global core.autocrlf false
echo Done
echo.

echo [6/7] Adding all files to Git...
git add .
echo Done
echo.

echo [7/7] Committing changes...
git commit -m "init: project initialization"
echo.

echo ========================================
echo   Verification
echo ========================================
git log --oneline
echo.

echo ========================================
echo   Initialization Complete!
echo ========================================
echo.
echo Now you can run: npx gitnexus analyze
echo.
pause