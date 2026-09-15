#!/bin/bash

echo "=========================================="
echo "  AI物理系统通用控制律自动设计器"
echo "  一键启动脚本 (Linux/Mac)"
echo "=========================================="
echo ""

# 关键：将项目根目录加入 PYTHONPATH
export PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
echo "[PYTHONPATH] $PYTHONPATH"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "Mac: brew install python3"
    exit 1
fi

# 检查前端构建
if [ ! -f "backend/static/index.html" ]; then
    echo "[警告] 前端未构建，尝试自动构建..."

    if ! command -v npm &> /dev/null; then
        echo "[错误] 未检测到Node.js，无法构建前端"
        echo "请安装Node.js后运行: cd web && npm install && npm run build"
        exit 1
    fi

    cd web
    echo "[1/4] 安装前端依赖..."
    npm install
    echo "[2/4] 构建前端..."
    npm run build
    cd ..
else
    echo "[1/4] 前端已构建，跳过"
fi

# 安装Python依赖
echo "[3/4] 安装/检查Python依赖..."
pip3 install -r requirements.txt -q

# 初始化数据目录
echo "[4/4] 初始化数据目录..."
mkdir -p data/projects
mkdir -p data/chroma_db

# 启动服务（不cd进backend，cwd保持根目录）
echo ""
echo "=========================================="
echo "  服务启动成功！"
echo "  请访问: http://localhost:8000"
echo "  按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python3 -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload
