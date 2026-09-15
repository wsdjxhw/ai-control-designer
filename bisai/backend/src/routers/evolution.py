"""
演化监控 API 路由

对接 C 的 EvolutionEngine，提供 4 个端点：
  1. GET  /evolution/{run_id}/status          — 轮询演化实时状态（前端进度条用）
  2. GET  /evolution/{run_id}/versions        — 获取版本列表
  3. GET  /evolution/{run_id}/versions/{v}    — 获取指定版本详情（含参数 + 诊断）
  4. GET  /evolution/{run_id}/compare         — 多版本对比数据（前端 ECharts 曲线图用）

数据来源：
  - 实时状态：从 EvolutionService._instances 缓存中拿引擎状态
  - 版本历史：从数据库 EvolutionRun 表 + 文件存储（最优参数、诊断报告）

为什么不用 POST：
  这些都是查操作，符合 REST 规范用 GET，
  前端直接用浏览器或 curl 就能测，不需要构造请求体。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.src.database import get_db
from backend.src.models import EvolutionRun
from backend.src.services.evolution_service import EvolutionService
from backend.src.services.file_storage import FileStorageService

router = APIRouter(tags=["evolution"])
file_storage = FileStorageService()


@router.get("/evolution/{run_id}/status")
async def get_evolution_status(run_id: str, db: Session = Depends(get_db)):
    """轮询演化状态

    前端调用时机：点击"启动演化"后，每隔 1-2 秒调用一次，更新进度条。
    返回的 status 字段取值：idle / running / optimizing / diagnosing / modifying / completed / failed

    实现逻辑：
      1. 先查数据库确认 run_id 存在
      2. 通过 run.project_id 找到对应的 EvolutionService 实例
      3. EvolutionService.get_status() 从引擎拿实时状态
      4. 补上 run_id 和 project_id 返回给前端
    """
    run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="演化运行记录不存在")

    # 获取该项目的演化服务实例（如果有正在运行的引擎，能从缓存拿到）
    service = EvolutionService.get_instance(run.project_id, db)
    status = service.get_status()

    # 补充路由参数到返回体中
    status["run_id"] = run_id
    status["project_id"] = run.project_id
    status["version"] = run.version
    return status



@router.get("/evolution/{run_id}/versions")
async def list_versions(run_id: str, db: Session = Depends(get_db)):
    """获取演化版本列表（从文件系统扫描 control_v*.py）"""
    run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="演化运行记录不存在")

    project_id = run.project_id
    work_dir = file_storage.project_dir(project_id)

    # 从 evolution_log.json 读每轮的代价
    log = file_storage.load_evolution_log(project_id) or []
    cost_map = {rec.get("version"): rec.get("cost") for rec in log}

    # 扫描所有 control_v*.py
    import re
    versions_list = []
    for f in sorted(work_dir.glob("control_v*.py")):
        m = re.match(r'control_v(\d+)\.py$', f.name)
        if not m:
            continue
        v = int(m.group(1))
        versions_list.append({
            "run_id": run_id,
            "version": v,
            "status": "completed",
            "total_cost": cost_map.get(v),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        })

    return versions_list


@router.get("/evolution/{run_id}/versions/{version}")
async def get_version_detail(run_id: str, version: int, db: Session = Depends(get_db)):
    """获取指定版本详情（从文件系统读 control_v{N}.py + best_params_v{N}.json + diagnostic_v{N}.txt）"""
    run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="演化运行记录不存在")

    project_id = run.project_id

    # 读控制律代码
    code = file_storage.load_control_law(project_id, version)
    if code is None:
        raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")

    # 读最优参数和诊断
    params = file_storage.load_best_params(project_id, version)
    diagnosis = file_storage.load_diagnostic(project_id, version)

    # 从 evolution_log 里找这轮代价
    log = file_storage.load_evolution_log(project_id) or []
    cost = None
    for rec in log:
        if rec.get("version") == version:
            cost = rec.get("cost")
            break

    return {
        "run_id": run_id,
        "project_id": project_id,
        "version": version,
        "status": "completed",
        "total_cost": cost,
        "best_params": params or {},
        "diagnosis": diagnosis or "",
        "code": code,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }




@router.get("/evolution/{run_id}/compare")
async def compare_versions(run_id: str, db: Session = Depends(get_db)):
    """多版本对比（优先读 evolution_log.json，实时更新）

    优先级：
      1. evolution_log.json（引擎每轮结束实时写入）
      2. diagnostic_v{N}.txt（兼容旧数据 / 演化结束时生成）
    """
    run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="演化运行记录不存在")

    project_id = run.project_id
    versions = file_storage.list_control_law_versions(project_id)

    # 🆕 优先从 evolution_log.json 读（实时更新，每轮结束就有）
    log = file_storage.load_evolution_log(project_id) or []
    log_cost_map = {}
    for rec in log:
        v = rec.get("version")
        c = rec.get("cost")
        if v is not None and c is not None:
            log_cost_map[v] = c

    import re
    result = []
    for v in versions:
        # 优先用 evolution_log 的实时数据
        cost = log_cost_map.get(v)

        # fallback：从 diagnostic_v{N}.txt 正则提取
        if cost is None:
            diagnosis = file_storage.load_diagnostic(project_id, v)
            if diagnosis:
                m = re.search(r'本轮代价:\s*([\d.eE+-]+)', diagnosis)
                if m:
                    try:
                        cost = float(m.group(1))
                    except ValueError:
                        pass

        result.append({
            "version": v,
            "cost": cost,
            "param_count": None,
        })

    return {
        "project_id": project_id,
        "versions": result,
    }

@router.post("/evolution/{run_id}/stop")
async def stop_evolution(run_id: str, db: Session = Depends(get_db)):
    """请求中断指定演化

    实现思路：
      1. 从 EvolutionService._instances 缓存中按 run_id 找到运行中的实例
      2. 调用 service.request_stop() 设置中断标志
      3. engine.run() 会在下一轮开始时检查标志并 break

    注意：中断不是立即生效。如果当前正在跑 CMA-ES 或调 LLM，要等当前轮结束。
    """
    # 先确认 run_id 存在于数据库
    run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="演化运行记录不存在")

    # 从缓存中找运行中的实例
    service = EvolutionService.find_by_run_id(run_id, db)
    if service is None:
        # 缓存里找不到：可能已经结束，或者后端重启过
        raise HTTPException(
            status_code=400,
            detail="该演化已结束或不在运行中，无法中断",
        )

    ok = service.request_stop()
    if not ok:
        raise HTTPException(status_code=400, detail="中断标志设置失败")

    return {
        "run_id": run_id,
        "message": "中断请求已发送，将在当前轮结束后停止",
        "note": "如果引擎正在执行 CMA-ES 或调用 LLM，需等当前轮结束",
    }