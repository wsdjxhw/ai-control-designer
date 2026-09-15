"""
项目 CRUD API 路由
"""

import asyncio
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# 添加项目根路径以导入 C 模块
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.database import get_db
from backend.src.models import Project
from backend.src.schemas.project import (
    EvolutionStartRequest,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from backend.src.services.file_storage import FileStorageService

router = APIRouter(tags=["projects"])
file_storage = FileStorageService()


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(req: ProjectCreate, db: Session = Depends(get_db)):
    """创建新项目"""
    project_id = str(uuid.uuid4())
    work_dir = str(file_storage.project_dir(project_id))

    project = Project(
        project_id=project_id,
        name=req.name,
        description=req.description or "",
        mode=req.mode or "expert",
        domain_type=req.domain_type or "custom",
        status="idle",
        current_version=0,
        scene_config=req.scene_config,
        work_dir=work_dir,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    if req.scene_config:
        file_storage.save_scene_config(project_id, req.scene_config)

    return project


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """获取项目列表（直接返回数组，前端不要包装）"""
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """获取项目详情"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, req: ProjectUpdate, db: Session = Depends(get_db)):
    """更新项目"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    if "scene_config" in update_data and update_data["scene_config"] is not None:
        file_storage.save_scene_config(project_id, update_data["scene_config"])

    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """删除项目"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    db.delete(project)
    db.commit()
    file_storage.delete_project_dir(project_id)
    return {"message": "项目已删除", "project_id": project_id}


@router.post("/projects/{project_id}/evolution/start")
async def start_evolution(
    project_id: str,
    req: EvolutionStartRequest = EvolutionStartRequest(),
    db: Session = Depends(get_db),
):
    """
    启动演化

    调用 C 模块: EvolutionEngine.run()
    流程:
      1. 加载 scene_config.json
      2. 加载最新版本的 control_law 代码
      3. 实例化 EvolutionEngine
      4. 异步运行演化
      5. 返回 run_id（即 project_id）
    """
    # 验证项目存在
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 加载 scene_config
    scene_config = file_storage.load_scene_config(project_id)
    if scene_config is None:
        raise HTTPException(status_code=400, detail="项目缺少 scene_config.json")

    # 加载控制律代码（取最新版本）
    versions = file_storage.list_control_law_versions(project_id)
    if not versions:
        raise HTTPException(status_code=400, detail="项目缺少控制律代码文件 (control_v*.py)")

    latest_version = max(versions)
    control_law_code = file_storage.load_control_law(project_id, latest_version)
    if control_law_code is None:
        raise HTTPException(status_code=400, detail=f"无法加载 control_v{latest_version}.py")

    # 更新项目状态
    project.status = "running"
    project.current_version = latest_version
    db.commit()

    # 异步启动演化（后台任务）
    work_dir = str(file_storage.project_dir(project_id))

    async def _run_evolution():
        """后台运行演化任务"""
        try:
            from core.evolution.engine import EvolutionEngine

            engine = EvolutionEngine(work_dir=work_dir, scene_config=scene_config)

            result = engine.run(
                max_iterations=req.max_iterations or 20,
                control_law_code=control_law_code,
                llm_callbacks=None,  # TODO: 集成 D 模块的 LLM 回调
            )

            # 更新项目状态
            if result.get("success"):
                project.status = "done"
                project.best_cost = result.get("best_cost")
                if result.get("best_params"):
                    project.best_params = result["best_params"]
            else:
                project.status = "error"
                project.error_message = result.get("error", "演化失败")

            db.commit()

        except Exception as e:
            project.status = "error"
            project.error_message = str(e)
            db.commit()
            print(f"演化任务失败: {e}")

    # 创建后台任务
    asyncio.create_task(_run_evolution())

    return {
        "run_id": project_id,
        "project_id": project_id,
        "status": "running",
        "message": f"演化已启动，当前版本 {latest_version}",
        "max_iterations": req.max_iterations or 20,
    }

