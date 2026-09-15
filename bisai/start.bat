@echo off
chcp 65001 >nul
title AI Control Designer

echo ==========================================
echo   AI物理系统通用控制律自动设计器
echo   一键启动脚本 (Windows)
echo ==========================================
echo.

:: 关键：将项目根目录加入 PYTHONPATH
set "PROJECT_ROOT=%~dp0"
set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
echo [PYTHONPATH] %PYTHONPATH%

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查前端是否已构建
if not exist "backend\static\index.html" (
    echo [警告] 前端未构建，尝试自动构建...

    where npm >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未检测到Node.js，无法构建前端
        echo 请安装Node.js后运行: cd web ^&^& npm install ^&^& npm run build
        pause
        exit /b 1
    )

    cd web
    echo [1/4] 安装前端依赖...
    call npm install
    echo [2/4] 构建前端...
    call npm run build
    cd ..
) else (
    echo [1/4] 前端已构建，跳过
)

:: 安装Python依赖
echo [2/4] 安装/检查Python依赖...
pip install -r requirements.txt -q

:: 初始化数据目录
echo [3/4] 初始化数据目录...
if not exist data mkdir data
if not exist data\projects mkdir data\projects
if not exist data\chroma_db mkdir data\chroma_db

:: 启动服务（不cd进backend，cwd保持根目录）
echo.
echo ==========================================
echo  服务启动成功！
echo  请访问: http://localhost:8000
echo  按 Ctrl+C 停止服务
echo ==========================================
echo.

python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload

pause
