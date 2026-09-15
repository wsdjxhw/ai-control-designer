"""
求解器管理 API 路由

提供自定义求解器的上传、验证和管理功能
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
import tempfile
import os

from backend.src.schemas.solver import (
    SolverValidationResult,
    SolverUploadResponse,
    SolverConfig,
)
from core.solvers.loader import SolverLoader

router = APIRouter(prefix="/solvers", tags=["solvers"])


@router.post("/validate", response_model=SolverValidationResult)
async def validate_custom_solver(file: UploadFile = File(...)):
    """
    验证上传的自定义求解器文件

    要求：
    - 必须是 .py 文件
    - 必须定义 CustomSolver 类
    - CustomSolver 必须继承 BaseSolver
    - 必须实现 step() 和 integrate() 方法
    """
    if not file.filename or not file.filename.endswith('.py'):
        raise HTTPException(status_code=400, detail="只支持 .py 文件")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        content = await file.read()
        tmp.write(content.decode('utf-8'))
        tmp_path = tmp.name

    try:
        # 使用 SolverLoader 验证
        result = SolverLoader.validate_custom_solver(tmp_path)
        return SolverValidationResult(**result)
    finally:
        # 清理临时文件
        os.unlink(tmp_path)


@router.post("/upload", response_model=SolverUploadResponse)
async def upload_custom_solver(file: UploadFile = File(...)):
    """
    上传并保存自定义求解器

    上传后会：
    1. 验证文件有效性
    2. 保存到项目数据目录
    3. 返回保存路径供后续使用
    """
    if not file.filename or not file.filename.endswith('.py'):
        raise HTTPException(status_code=400, detail="只支持 .py 文件")

    # 验证文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        content = await file.read()
        tmp.write(content.decode('utf-8'))
        tmp_path = tmp.name

    try:
        validation = SolverLoader.validate_custom_solver(tmp_path)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"求解器验证失败: {validation['errors']}"
            )
    finally:
        os.unlink(tmp_path)

    # TODO: 实际保存到项目数据目录
    # 这里简化处理，返回文件名
    saved_path = f"custom_solvers/{file.filename}"

    return SolverUploadResponse(
        success=True,
        filename=file.filename,
        saved_path=saved_path,
        validation=validation,
    )


@router.get("/builtin")
async def list_builtin_solvers() -> Dict[str, Any]:
    """列出所有内置求解器"""
    return {
        "solvers": [
            {
                "type": "ode_scipy",
                "name": "SciPy ODE 求解器",
                "description": "基于 SciPy 的常微分方程求解器，支持多种数值方法",
                "params": ["method", "rtol", "atol", "max_step"],
            },
            {
                "type": "pde_rk4",
                "name": "RK4 PDE 求解器",
                "description": "基于 RK4 的偏微分方程求解器",
                "params": [],
            },
        ]
    }
