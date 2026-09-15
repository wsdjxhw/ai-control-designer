"""
演化监控 API 路由

依赖：C 成员的 EvolutionEngine 接口
实现：基于 FileStorageService 读取演化日志和状态
"""

import sys
from pathlib import Path

# 添加项目根路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, HTTPException
from typing import Any

from backend.src.services.file_storage import FileStorageService
from backend.src.config import settings

router = APIRouter(tags=["evolution"])

# 初始化文件存储服务
file_storage = FileStorageService(projects_root=settings.projects_root)


@router.get("/evolution/{run_id}/status")
async def get_evolution_status(run_id: str) -> dict[str, Any]:
    """
    轮询演化状态

    数据来源：data/projects/{run_id}/evolution_log.json (最新记录)
    回退：如果日志不存在，返回 idle 状态
    """
    try:
        log_data = file_storage.load_evolution_log(run_id)

        if log_data is None or len(log_data) == 0:
            # 没有演化记录，返回空闲状态
            return {
                "run_id": run_id,
                "status": "idle",
                "current_version": 0,
                "best_cost": None,
                "best_params": {},
                "iteration": 0,
                "max_iterations": 20,
                "message": "演化尚未开始",
                "error": None,
            }

        # 取最新记录
        latest = log_data[-1]

        return {
            "run_id": run_id,
            "status": "done" if latest["version"] >= 1 else "running",
            "current_version": latest["version"],
            "best_cost": latest["cost"],
            "best_params": latest["params"],
            "iteration": latest["version"],
            "max_iterations": 20,
            "message": f"已完成 {latest['version']} 轮演化",
            "error": None,
            "timestamp": latest.get("timestamp"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取演化状态失败: {str(e)}")


@router.get("/evolution/{run_id}/versions")
async def list_versions(run_id: str) -> list[dict[str, Any]]:
    """
    获取演化版本列表

    数据来源：data/projects/{run_id}/evolution_log.json
    """
    try:
        log_data = file_storage.load_evolution_log(run_id)

        if log_data is None or len(log_data) == 0:
            return []

        versions = []
        for record in log_data:
            versions.append({
                "version": record["version"],
                "cost": record["cost"],
                "params": record["params"],
                "param_count": record.get("param_count", len(record["params"])),
                "timestamp": record.get("timestamp"),
            })

        return versions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本列表失败: {str(e)}")


@router.get("/evolution/{run_id}/versions/{version}")
async def get_version_detail(run_id: str, version: int) -> dict[str, Any]:
    """
    获取指定版本详情

    数据来源：data/projects/{run_id}/evolution_log.json + best_params_v{version}.json
    """
    try:
        log_data = file_storage.load_evolution_log(run_id)

        if log_data is None:
            raise HTTPException(status_code=404, detail=f"项目 {run_id} 没有演化记录")

        # 查找指定版本
        record = next((r for r in log_data if r["version"] == version), None)

        if record is None:
            raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")

        # 尝试加载完整的最佳参数（如果存在单独文件）
        best_params = file_storage.load_best_params(run_id, version)
        if best_params is None:
            best_params = record["params"]

        return {
            "run_id": run_id,
            "version": version,
            "cost": record["cost"],
            "params": best_params,
            "param_count": record.get("param_count", len(record["params"])),
            "diagnosis_summary": record.get("diagnosis_summary", ""),
            "metrics": record.get("metrics", {}),
            "timestamp": record.get("timestamp"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本详情失败: {str(e)}")


@router.get("/evolution/{run_id}/compare")
async def compare_versions(run_id: str) -> dict[str, Any]:
    """
    获取多版本对比数据（前端 ECharts 用）

    数据来源：data/projects/{run_id}/evolution_log.json
    返回格式：适合 ECharts 的时间序列数据
    """
    try:
        log_data = file_storage.load_evolution_log(run_id)

        if log_data is None or len(log_data) == 0:
            return {
                "run_id": run_id,
                "versions": [],
                "costs": [],
                "param_counts": [],
                "timestamps": [],
            }

        versions = [r["version"] for r in log_data]
        costs = [r["cost"] for r in log_data]
        param_counts = [r.get("param_count", len(r["params"])) for r in log_data]
        timestamps = [r.get("timestamp", "") for r in log_data]

        return {
            "run_id": run_id,
            "versions": versions,
            "costs": costs,
            "param_counts": param_counts,
            "timestamps": timestamps,
            "best_cost": min(costs) if costs else None,
            "best_version": versions[costs.index(min(costs))] if costs else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对比数据失败: {str(e)}")
