@echo off
chcp 65001 >nul
echo Git Project Initialization
echo.

if not exist .git (
    echo [1/5] Initialize Git repository...
    git init
    echo.
)

echo [2/5] Configure Git user...
git config --global user.name "WangHao"
git config --global user.email "wanghao@test.com"
echo User configured
echo.

echo [3/5] Create .gitignore...
(
echo .gitnexus/
echo __pycache__/
echo *.pyc
echo .env
echo node_modules/
) > .gitignore
echo .gitignore created
echo.

echo [4/5] Disable CRLF warning...
git config core.autocrlf false
echo Done
echo.

echo [5/5] Add and commit...
git add .
git commit -m "init: project initialization"

echo.
echo Initialization complete!
echo Run: npx gitnexus analyze
echo.
pause