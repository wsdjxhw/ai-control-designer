"""
项目 CRUD API 路由

提供项目的增删改查 + 启动演化入口。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.src.database import get_db
from backend.src.models import Project
from backend.src.schemas.project import (
    EvolutionStartRequest,
    EvolutionStatusResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from backend.src.services.evolution_service import EvolutionService
from backend.src.services.file_storage import FileStorageService
from backend.src.services.llm_config_service import (
    load_settings as load_sys_settings,
)

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
        scene_config=None,  # 先设为 None，后面再更新
        work_dir=work_dir,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # 🆕 DEBUG: 打印接收到的字段
    print(f"[create_project] DEBUG: req.model_code is None: {req.model_code is None}")
    print(f"[create_project] DEBUG: req.model_code 类型: {type(req.model_code)}")
    if req.model_code:
        print(f"[create_project] DEBUG: req.model_code 长度: {len(req.model_code)}")
        print(f"[create_project] DEBUG: req.model_code 前100字符: {req.model_code[:100]}")

    # 🆕 1. 保存 scene_config，同时把 model_code 注入到 _model_code
    if req.scene_config:
        config = dict(req.scene_config)

        print(f"[create_project] DEBUG: scene_config keys: {list(config.keys())}")

        # 🆕 兜底 1：确保 model_type 一定有值
        if not config.get("model_type"):
            config["model_type"] = config.get("detected_type") or "ode"
            print(f"[create_project] 补齐 model_type = {config['model_type']}")

        # 🆕 兜底 2：重算 n_steps（覆盖 LLM 给的 null 或错误值）
        temporal = config.get("temporal", {})
        T_val = temporal.get("T")
        dt_val = temporal.get("dt")
        if T_val and dt_val:
            try:
                dt_f = float(dt_val)
                if dt_f > 0:
                    temporal["n_steps"] = int(round(float(T_val) / dt_f))
                    config["temporal"] = temporal
                    print(f"[create_project] 重算 n_steps = {temporal['n_steps']} (T={T_val}, dt={dt_val})")
            except (ValueError, TypeError) as e:
                print(f"[create_project] n_steps 重算失败: {e}")

        # 🆕 关键：把 model_code 注入到 scene_config["_model_code"]
        if req.model_code and len(req.model_code.strip()) > 0:
            config["_model_code"] = req.model_code
            print(f"[create_project] 已注入 _model_code，长度: {len(req.model_code)}")

        # 🆕 保存 optimizer_config 到 scene_config
        if req.optimizer_config:
            config["optimizer"] = req.optimizer_config
            print(f"[create_project] 已保存 optimizer_config")

        project.scene_config = config
        file_storage.save_scene_config(project_id, config)
        db.commit()
        db.refresh(project)

    # 🆕 2. 保存 model_code 到文件（供专家模式自动生成控制律用）
    if req.model_code:
        file_storage.save_model_code(project_id, req.model_code)
        print(f"[create_project] 已保存 model_code ({len(req.model_code)} 字符)")

    # 🆕 3. 保存初始控制律为 v1
    if req.control_v1_code:
        file_storage.save_control_law(project_id, 1, req.control_v1_code)
        print(f"[create_project] 已保存 control_v1_code ({len(req.control_v1_code)} 字符)")

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


@router.post("/projects/{project_id}/evolution/start", response_model=EvolutionStatusResponse)
async def start_evolution(
    project_id: str,
    req: EvolutionStartRequest = EvolutionStartRequest(),
    db: Session = Depends(get_db),
):
    """启动演化（异步执行，立即返回状态）

    这是"演化的入口"，接收前端点击按钮的请求，流程如下：

    1. 校验项目存在 && 状态不为 running（防止重复触发）
    2. 尝试从文件系统加载控制律代码
       - 优先加载当前版本的 control_v{version}.py
       - 如果没有，试 control_v1.py
       - 如果都没有，传给 engine 的 code=None，engine 会报错"未提供控制律代码"
    3. 创建 EvolutionService 实例，调用 start_evolution()
       - 这个方法内部会创建 EvolutionRun 记录、开线程执行演化
       - 立即返回 run_id（不等待演化结束）
    4. 返回 {run_id, project_id, status="running", ...}
       - 前端收到 run_id 后，开始轮询 /evolution/{run_id}/status

    为什么返回值里有 current_version：
      因为演化还没真正开始跑，version 已经 +1 了（在 start_evolution 中更新），
      所以这里直接取 project.current_version 就是新版本号。

    Args:
        project_id: 项目 UUID
        req: {max_iterations: 演化轮数，默认 20}

    Returns:
        EvolutionStatusResponse:
          run_id: 本次演化运行记录的 UUID
          project_id: 项目 UUID
          status: 固定为 "running"
          current_version: 本次演化的版本号
          total_cost: 演化完成前为 None
          message: "演化已启动"
    """
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status == "running":
        raise HTTPException(status_code=400, detail="该项目已有演化在运行中")

    # 尝试从文件加载最新的控制律代码
    # 🆕 从文件系统扫描最新控制律版本，加载对应代码
    # 🆕 加载控制律代码：如果用户指定了 start_version，从该版本加载；否则从最新版
    existing_versions = file_storage.list_control_law_versions(project_id)
    if req.start_version is not None:
        load_version = req.start_version
        print(f"[start_evolution] 用户指定从 v{load_version} 加载（已有: {existing_versions}）")
    else:
        load_version = max(existing_versions) if existing_versions else 1
        print(f"[start_evolution] 从最新版 v{load_version} 加载（已有: {existing_versions}）")

    control_code = file_storage.load_control_law(project_id, load_version)
    if not control_code:
        # 极端兜底
        control_code = file_storage.load_control_law(project_id, 1)
    print(f"[start_evolution] 已加载 control_v{load_version}.py (找到代码: {bool(control_code)})")
    # 🆕 新手模式自动生成：如果没有控制律且是 newbie 模式，调用 LLM 生成
    if not control_code and project.mode == "newbie":
        try:
            from core.llm.newbie import generate_scene

            # 构造自然语言描述（优先用 description，否则用 domain_type 构造）
            description = project.description
            if not description:
                domain = project.domain_type or "custom"
                description = f"请为 {domain} 领域的物理系统设计控制策略。"

            print(f"[newbie] 项目 {project_id} 触发新手模式自动生成，描述: {description[:50]}...")

            # 调用 LLM 生成 scene_config + model_code + cost_function
            result = generate_scene(description)

            # 🆕 直接使用 generate_scene 返回的 scene_config（不要从文件加载覆盖！）
            if "scene_config" in result:
                scene_config = result["scene_config"].copy()

                # 🆕 将 model_code 嵌入 scene_config 以支持动态加载
                if "model_code" in result:
                    scene_config["_model_code"] = result["model_code"]

                project.scene_config = scene_config

                # 同时保存到文件系统（供后续查询使用）
                file_storage.save_scene_config(project_id, scene_config)

                db.commit()
                db.refresh(project)
                print(f"[newbie] 已直接使用 generate_scene 返回的 scene_config (model_type={scene_config.get('model_type')}, 包含 _model_code={bool(scene_config.get('_model_code'))})")
                print(f"[newbie] DEBUG: scene_config keys after commit: {list(project.scene_config.keys()) if project.scene_config else None}")

            # 🆕 生成初始控制律（Newbie 模式需要 LLM 生成控制律，而不是模型定义！）
            # model_code 是模型定义，不能直接用作控制律
            # 这里需要调用 LLM 基于 model_code 生成一个简单的初始控制律
            if "model_code" in result and not control_code:
                try:
                    from core.llm.expert import generate_initial_control_law

                    model_code = result["model_code"]
                    scene_config_for_control = result["scene_config"].copy()

                    print(f"[newbie] 基于 model_code 生成初始控制律...")

                    control_code = generate_initial_control_law(
                        model_code=model_code,
                        scene_config=scene_config_for_control,
                        description=description
                    )

                    # 保存为 v1 版本
                    file_storage.save_control_law(project_id, 1, control_code)
                    print(f"[newbie] 已生成并保存初始控制律 (v1, {len(control_code)} 字符)")

                except Exception as e:
                    print(f"[newbie] 控制律生成失败: {e}，使用零控制律兜底")
                    import traceback
                    traceback.print_exc()

                    # 兜底：生成一个简单的零控制律
                    state_names = result["scene_config"].get("state_names", [])
                    control_names = result["scene_config"].get("control_names", [])
                    n_controls = len(control_names) if control_names else 1

                    control_code = f'''import numpy as np

def control_law(t, x_grid, state, params):
    """初始零控制律"""
    n_controls = {n_controls}
    return np.zeros(n_controls)
'''
                    file_storage.save_control_law(project_id, 1, control_code)
                    print(f"[newbie] 已保存零控制律兜底 (v1)")

        except Exception as e:
            print(f"[newbie] 自动生成失败: {e}")
            import traceback
            traceback.print_exc()
            # 继续尝试启动演化（可能会失败，但不阻塞流程）

    # 🆕 专家模式自动生成：如果有 model_code 但没有 control_law，调用 LLM 生成初始控制律
    if not control_code and project.mode == "expert":
        try:
            from core.llm.expert import generate_initial_control_law

            # 尝试加载用户提供的 model_code
            model_code = file_storage.load_model_code(project_id)
            if model_code:
                print(f"[expert] 项目 {project_id} 触发专家模式自动生成控制律...")

                scene_config = project.scene_config or {}
                description = project.description or ""

                # 调用 LLM 基于 Model Code 生成初始控制律
                control_code = generate_initial_control_law(
                    model_code=model_code,
                    scene_config=scene_config,
                    description=description if description else None
                )

                # 保存为 v1 版本
                file_storage.save_control_law(project_id, 1, control_code)
                print(f"[expert] 已基于 Model Code 生成并保存初始控制律 (v1, {len(control_code)} 字符)")

                # 🆕 直接使用 scene_config（Expert 模式已有 scene_config，无需重新加载）
                print(f"[expert] Expert 模式 scene_config.model_type: {repr(project.scene_config.get('model_type') if project.scene_config else None)}")

            else:
                print(f"[expert] 项目 {project_id} 为 expert 模式，但未找到 model_code 文件")

        except Exception as e:
            print(f"[expert] 自动生成失败: {e}")
            import traceback
            traceback.print_exc()
            # 继续尝试启动演化（可能会失败，但不阻塞流程）

    service = EvolutionService(project_id, db)
    try:
        # 未指定迭代次数时，用系统设置里的默认值（前端设置页可改）
        default_max_iter = load_sys_settings().get("max_iterations", 20)
        run_id = await service.start_evolution(
            max_iterations=req.max_iterations or default_max_iter,
            control_law_code=control_code,
            start_version_override=req.start_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "run_id": run_id,
        "project_id": project_id,
        "status": "running",
        "current_version": project.current_version,
        "total_cost": None,
        "message": "演化已启动",
    }


@router.get("/projects/{project_id}/versions")
async def list_project_versions(project_id: str, db: Session = Depends(get_db)):
    """列出项目下所有历史控制律版本（从文件系统扫描）"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 从文件系统扫描
    versions = file_storage.list_control_law_versions(project_id)

    # 从 evolution_log.json 读每轮代价
    log = file_storage.load_evolution_log(project_id) or []
    cost_map = {rec.get("version"): rec.get("cost") for rec in log}

    result = []
    for v in versions:
        result.append({
            "version": v,
            "cost": cost_map.get(v),
            "has_params": file_storage.load_best_params(project_id, v) is not None,
            "has_diagnosis": file_storage.load_diagnostic(project_id, v) is not None,
        })

    return {
        "project_id": project_id,
        "current_version": project.current_version,
        "versions": result,
    }


@router.get("/projects/{project_id}/active-run")
async def get_active_run(project_id: str, db: Session = Depends(get_db)):
    """查询项目当前是否有正在运行的演化，返回其 run_id"""
    from backend.src.models import EvolutionRun

    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.status != "running":
        return {"active": False, "run_id": None}

    run = (
        db.query(EvolutionRun)
        .filter(EvolutionRun.project_id == project_id)
        .filter(EvolutionRun.status == "running")
        .order_by(EvolutionRun.created_at.desc())
        .first()
    )

    return {
        "active": run is not None,
        "run_id": run.run_id if run else None,
    }

@router.get("/projects/{project_id}/versions/{version}")
async def get_project_version_detail(
    project_id: str,
    version: int,
    db: Session = Depends(get_db),
):
    """按 project_id + version 直接取版本详情（不需要 run_id）"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    code = file_storage.load_control_law(project_id, version)
    if code is None:
        raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")

    params = file_storage.load_best_params(project_id, version)
    diagnosis = file_storage.load_diagnostic(project_id, version)

    log = file_storage.load_evolution_log(project_id) or []
    cost = None
    for rec in log:
        if rec.get("version") == version:
            cost = rec.get("cost")
            break

    return {
        "project_id": project_id,
        "version": version,
        "best_params": params or {},
        "diagnosis": diagnosis or "",
        "code": code,
        "total_cost": cost,
    }