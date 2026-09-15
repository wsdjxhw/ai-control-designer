"""
澄清对话 API 路由
提供多轮交互式需求收集功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from core.llm.clarify import (
    create_session,
    get_session,
    clear_session,
    clarify_turn,
)

router = APIRouter(tags=["clarify"])


class ClarifyStartRequest(BaseModel):
    """启动澄清会话请求"""
    description: str = Field(..., description="用户初始的自然语言描述")


class ClarifyStartResponse(BaseModel):
    """启动澄清会话响应"""
    session_id: str
    stage: str
    message: str
    draft_config: Dict[str, Any] = {}
    missing_fields: list = []


class ClarifyTurnRequest(BaseModel):
    """澄清对话轮次请求"""
    session_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="用户消息")


class ClarifyTurnResponse(BaseModel):
    """澄清对话轮次响应"""
    session_id: str
    stage: str
    message: str
    draft_config: Dict[str, Any] = {}
    missing_fields: list = []
    ready_to_create: bool = False
    scene_config: Optional[Dict[str, Any]] = None
    model_code: Optional[str] = None
    cost_function: Optional[Dict[str, Any]] = None


class ClarifyCancelRequest(BaseModel):
    """取消会话请求"""
    session_id: str


@router.post("/clarify/start", response_model=ClarifyStartResponse)
async def start_clarify(req: ClarifyStartRequest):
    """
    启动新的澄清会话

    用户输入初始描述后，LLM 会开始引导用户逐步明确：
    - 状态变量
    - 控制动作
    - 代价/目标函数
    - 求解器类型
    """
    if not req.description or not req.description.strip():
        raise HTTPException(status_code=400, detail="描述不能为空")

    session = create_session(req.description.strip())

    # 第一轮：LLM 主动发起提问
    result = clarify_turn(session.session_id, "请开始引导我明确需求")

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return ClarifyStartResponse(
        session_id=result["session_id"],
        stage=result["stage"],
        message=result["message"],
        draft_config=result.get("draft_config", {}),
        missing_fields=result.get("missing_fields", [])
    )


@router.post("/clarify/turn", response_model=ClarifyTurnResponse)
async def clarify_dialogue(req: ClarifyTurnRequest):
    """
    执行澄清对话的一轮

    用户回复 LLM 的问题，LLM 继续追问或确认
    直到所有关键信息收集完整，ready_to_create=True
    """
    if not req.session_id or not req.message:
        raise HTTPException(status_code=400, detail="session_id 和 message 不能为空")

    result = clarify_turn(req.session_id, req.message.strip())

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return ClarifyTurnResponse(
        session_id=result["session_id"],
        stage=result["stage"],
        message=result.get("message", ""),
        draft_config=result.get("draft_config", {}),
        missing_fields=result.get("missing_fields", []),
        ready_to_create=result.get("ready_to_create", False),
        scene_config=result.get("scene_config"),
        model_code=result.get("model_code"),
        cost_function=result.get("cost_function")
    )


@router.post("/clarify/cancel")
async def cancel_clarify(req: ClarifyCancelRequest):
    """取消并清理会话"""
    clear_session(req.session_id)
    return {"message": "会话已取消", "session_id": req.session_id}
