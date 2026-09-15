"""
诊断报告 API 路由

实现：基于 FileStorageService 读取诊断报告文件
数据来源：data/projects/{run_id}/diagnostic_v{version}.txt
"""

import sys
from pathlib import Path

# 添加项目根路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, HTTPException

from backend.src.services.file_storage import FileStorageService
from backend.src.config import settings

router = APIRouter(tags=["diagnostics"])

# 初始化文件存储服务
file_storage = FileStorageService(projects_root=settings.projects_root)


@router.get("/evolution/{run_id}/versions/{version}/diagnosis")
async def get_diagnosis(run_id: str, version: int) -> dict:
    """
    获取指定版本的诊断报告

    数据来源：data/projects/{run_id}/diagnostic_v{version}.txt
    回退：如果文件不存在，尝试从 evolution_log.json 提取 diagnosis_summary
    """
    try:
        # 方案A：尝试读取诊断报告文件
        diagnostic_content = file_storage.load_diagnostic(run_id, version)

        if diagnostic_content is not None:
            return {
                "run_id": run_id,
                "version": version,
                "diagnosis": diagnostic_content,
                "source": "diagnostic_file",
            }

        # 方案B：回退到从演化日志提取
        log_data = file_storage.load_evolution_log(run_id)

        if log_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"项目 {run_id} 没有演化记录或诊断报告"
            )

        # 查找指定版本的记录
        record = next((r for r in log_data if r["version"] == version), None)

        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"版本 {version} 不存在"
            )

        diagnosis_summary = record.get("diagnosis_summary", "")

        if not diagnosis_summary:
            return {
                "run_id": run_id,
                "version": version,
                "diagnosis": "该版本没有生成诊断报告",
                "source": "evolution_log",
            }

        return {
            "run_id": run_id,
            "version": version,
            "diagnosis": diagnosis_summary,
            "source": "evolution_log",
            "note": "完整诊断报告文件不存在，仅显示摘要",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取诊断报告失败: {str(e)}")

