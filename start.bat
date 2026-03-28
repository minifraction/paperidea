@echo off
chcp 65001 >nul
title PaperIdea - 基于论文的 Idea 发现工具

echo ==========================================
echo  PaperIdea - 基于论文的 Idea 发现工具
echo ==========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

echo [1/3] Python 版本:
python --version
echo.

:: 检查并安装依赖
echo [2/3] 检查依赖...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [警告] tkinter 未找到，尝试安装...
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo 安装依赖...
    python -m pip install requests -q
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)
echo 依赖就绪
echo.

:: 启动程序
echo [3/3] 启动 PaperIdea...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)
