"""
LLM API 路由

终版决策：B 不经过中间服务层封装 LLM 调用。
B 的 router 直接调用 D 的 core/llm/* 业务模块，只做 HTTP 请求/响应转换。
B 只保留 llm_config_service 用于读写 system_settings.json。
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import APIRouter
from pydantic import BaseModel, Field

# 导入 D 模块的 LLM 功能
from core.llm.newbie import generate_scene as newbie_generate_scene
from core.llm.physics_validator import validate_physics as llm_validate_physics
from core.llm.strategy_parser import parse_strategy as llm_parse_strategy
from core.llm.expert import generate_initial_control_law

router = APIRouter(tags=["llm"])


class GenerateSceneRequest(BaseModel):
    """新手模式：自然语言生成场景配置请求"""
    user_description: str = Field(..., description="用户用自然语言描述的物理系统")
    domain_hint: str = Field("", description="领域提示（可选）")


class ValidatePhysicsRequest(BaseModel):
    """物理验证请求"""
    model_code: str = Field(..., description="模型代码文本")
    scene_config: dict = Field(default_factory=dict, description="场景配置")
    level: str = Field("L1", description="验证级别: L1(语义) | L2(符号) | L3(烟雾测试)")


class ParseStrategyRequest(BaseModel):
    """策略解析请求"""
    control_code: str = Field(..., description="控制律代码字符串")


class GenerateControlLawRequest(BaseModel):
    """生成初始控制律请求"""
    model_code: str = Field(..., description="模型代码")
    scene_config: dict = Field(..., description="场景配置")
    description: str = Field("", description="用户描述（可选）")


@router.post("/llm/generate-scene")
async def generate_scene(req: GenerateSceneRequest):
    """
    新手模式：自然语言描述 → scene_config + model_code 草案

    调用 D 模块: core.llm.newbie.generate_scene
    """
    try:
        result = newbie_generate_scene(req.user_description)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/llm/validate-physics")
async def validate_physics(req: ValidatePhysicsRequest):
    """
    物理验证（L1 LLM语义 / L2 SymPy符号 / L3 烟雾测试）

    调用 D 模块: core.llm.physics_validator.validate_physics
    """
    try:
        result = llm_validate_physics(req.model_code, req.scene_config, req.level)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/llm/parse-strategy")
async def parse_strategy(req: ParseStrategyRequest):
    """
    控制策略自然语言解析

    调用 D 模块: core.llm.strategy_parser.parse_strategy
    """
    try:
        result = llm_parse_strategy(req.control_code)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/llm/generate-control-law")
async def generate_control_law(req: GenerateControlLawRequest):
    """
    基于 scene_config 生成初始控制律

    调用 D 模块: core.llm.expert.generate_initial_control_law

    这是独立步骤：用户先确认 scene_config，再调用此接口生成控制律
    """
    try:
        control_law_code = generate_initial_control_law(
            model_code=req.model_code,
            scene_config=req.scene_config,
            description=req.description or None
        )
        return {
            "success": True,
            "control_law_code": control_law_code
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

