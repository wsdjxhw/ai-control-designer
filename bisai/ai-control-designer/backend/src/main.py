"""
FastAPI主入口 —— AI物理系统通用控制律自动设计器
Layer 3: 网关层 (Gateway)

保险：确保项目根目录在 sys.path 中，兼容任何启动方式。
"""
import sys
from pathlib import Path

# 保险：确保项目根目录在 sys.path 中
# backend/src/main.py -> backend/ -> 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.src.database import init_db
from backend.src.config import settings

# ===== 创建 FastAPI 应用 =====
app = FastAPI(
    title="AI物理系统通用控制律自动设计器",
    description="基于LLM与演化优化的跨领域控制律自动设计平台",
    version="1.0.0",
)

# ===== 1. API路由（必须先注册，避免被静态文件拦截）=====
from backend.src.routers import projects, evolution, diagnostics, rag, llm, system, solvers

app.include_router(projects.router, prefix="/api/v1")
app.include_router(evolution.router, prefix="/api/v1")
app.include_router(diagnostics.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(solvers.router, prefix="/api/v1")


# ===== 2. 健康检查端点 =====
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "ai-control-designer"}


# ===== 3. 静态文件挂载 =====
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ===== 4. SPA回退：所有非API路由返回index.html =====
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}

    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {
        "detail": "Frontend not built. Please run 'npm run build' in web/ directory."
    }


# ===== 5. 启动事件 =====
@app.on_event("startup")
async def startup():
    import os

    print(f"[ROOT_DIR] {ROOT_DIR}")
    print(f"[DB_PATH] {settings.database_url}")
    print(f"[PROJECTS_ROOT] {settings.projects_root}")

    # 确保数据目录存在
    os.makedirs(settings.projects_root, exist_ok=True)
    os.makedirs(settings.chroma_db_path, exist_ok=True)

    # 初始化数据库表
    init_db()
    print("[启动] 数据库表已初始化")
    print("[启动] 服务就绪，访问 http://localhost:8000")
