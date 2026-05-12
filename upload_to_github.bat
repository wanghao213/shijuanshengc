@echo off
setlocal enabledelayedexpansion

echo ====================================================
echo   GitHub 一键上传脚本 (Windows)
echo ====================================================
echo  ⚠️ 请确保此脚本已放在你的【代码文件夹根目录】下
echo  ⚠️ 首次使用请确保已配置 Git 用户名和邮箱
echo.

:: 1. 检查 Git 是否可用
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Git，请先安装 Git 并配置环境变量。
    pause
    exit /b 1
)

:: 2. 获取用户输入
set /p "REPO_URL=请输入 GitHub 仓库地址 (SSH 或 HTTPS): "
if "!REPO_URL!"=="" (
    echo [错误] 仓库地址不能为空。
    pause
    exit /b 1
)

set /p "COMMIT_MSG=请输入提交信息 (直接回车默认为 'Initial commit'): "
if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Initial commit"

:: 3. 初始化 Git (若尚未初始化)
if not exist ".git" (
    echo [提示] 正在初始化本地 Git 仓库...
    git init
    if !errorlevel! neq 0 (
        echo [错误] Git 初始化失败。
        pause
        exit /b 1
    )
) else (
    echo [提示] 检测到已存在 .git 目录，跳过初始化。
)

:: 4. 配置/更新远程仓库地址
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo [提示] 正在添加远程仓库 origin...
    git remote add origin !REPO_URL!
) else (
    echo [提示] 已存在 origin，正在更新仓库地址...
    git remote set-url origin !REPO_URL!
)

:: 5. 添加所有文件
echo [提示] 正在添加文件到暂存区...
git add .

:: 6. 提交 (若无变更则自动跳过)
git diff --cached --quiet
if !errorlevel! equ 0 (
    echo [提示] 没有需要提交的新更改，跳过 commit。
) else (
    echo [提示] 正在提交到本地仓库...
    git commit -m "!COMMIT_MSG!"
    if !errorlevel! neq 0 (
        echo [警告] 提交失败。请检查是否已配置用户信息：
        echo   git config --global user.name "你的用户名"
        echo   git config --global user.email "你的邮箱"
        pause
        exit /b 1
    )
)

:: 7. 统一主分支名为 main
echo [提示] 正在确保分支名为 main...
git branch -M main

:: 8. 推送到 GitHub
echo [提示] 正在推送至 GitHub (可能需要输入密码/Token)...
git push -u origin main

if !errorlevel! equ 0 (
    echo.
    echo ====================================================
    echo   ✅ 成功！代码已上传至 GitHub。
    echo ====================================================
) else (
    echo.
    echo ====================================================
    echo   ❌ 推送失败！请查看上方错误提示。
    echo   常见原因：
    echo   1. 认证失败 → 请使用 SSH 或 Personal Access Token
    echo   2. 远程仓库非空 → 请先执行: git pull --rebase origin main
    echo ====================================================
)

pause