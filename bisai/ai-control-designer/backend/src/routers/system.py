"""
系统设置 API 路由 —— 纯 B 层实现

提供：
  - GET  /system/settings        获取系统设置
  - PUT  /system/settings        更新系统设置
  - GET  /system/llm-models      获取可用 LLM 模型列表

注：路由前缀 /api/v1 在 main.py 中通过 include_router 添加
"""
from fastapi import APIRouter

from backend.src.schemas.system import SystemSettings, SystemSettingsUpdate
from backend.src.services.llm_config_service import load_settings, save_settings

router = APIRouter(tags=["system"])


@router.get("/system/settings", response_model=SystemSettings)
async def get_settings():
    """获取系统设置"""
    return load_settings()


@router.put("/system/settings", response_model=SystemSettings)
async def update_settings(update: SystemSettingsUpdate):
    """
    更新系统设置（只更新提供的字段）
    """
    # 直接从 JSON 加载当前配置（扁平结构）
    current = load_settings()
    # 只更新用户提供的字段
    update_data = update.model_dump(exclude_unset=True)
    current.update(update_data)
    # 保存到 JSON 文件
    save_settings(current)
    # 返回更新后的配置
    return current


@router.get("/system/llm-models")
async def get_llm_models():
    """获取当前可用的 LLM 模型列表"""
    settings = SystemSettings(**load_settings())
    return {
        "active_model": {
            "model_id": settings.llm_model,
            "base_url": settings.llm_base_url,
            "api_key": "****" + settings.llm_api_key[-4:] if settings.llm_api_key else "",
            "is_active": True,
        },
        "fallback_models": [],
    }
