"""
诊断报告 API 路由

从文件系统读取由演化引擎（evolution_service.py）写入的诊断报告。

为什么用 GET + 路径参数：
  诊断报告是"查"操作，符合 REST 规范用 GET。
  路径 /evolution/{run_id}/versions/{version}/diagnosis 和前端的路由设计一致。

为什么需要查数据库：
  run_id 是路由层的概念，文件存储用的 project_id。
  需要通过 EvolutionRun 表把 run_id 映射到 project_id。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.src.database import get_db
from backend.src.models import EvolutionRun
from backend.src.services.file_storage import FileStorageService

router = APIRouter(tags=["diagnostics"])
file_storage = FileStorageService()


@router.get("/evolution/{run_id}/versions/{version}/diagnosis")
async def get_diagnosis(run_id: str, version: int, db: Session = Depends(get_db)):
    """获取指定版本的诊断报告

    实现逻辑：
      1. 用 run_id 查 EvolutionRun 表，拿到 project_id
      2. 用 project_id + version 构造路径：data/projects/{project_id}/diagnostic_v{version}.txt
      3. FileStorageService.load_diagnostic() 读文件内容
      4. 如果文件不存在，返回 404

    Args:
        run_id: 演化运行记录的 UUID
        version: 版本号（对应 control_v{N}.py 的 N）

    Returns:
        {
            "run_id": "...",
            "project_id": "...",
            "version": 1,
            "diagnosis": "诊断报告文本内容..."
        }
    """
    # 1. 查数据库获取 project_id
    run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="演化运行记录不存在")

    # 2. 从文件读诊断报告
    diagnosis = file_storage.load_diagnostic(run.project_id, version)
    if diagnosis is None:
        raise HTTPException(status_code=404, detail="该版本的诊断报告不存在")

    # 3. 返回
    return {
        "run_id": run_id,
        "project_id": run.project_id,
        "version": version,
        "diagnosis": diagnosis,
    }
