"""
系统设置 API 路由 —— 纯 B 层实现

提供：
  - GET  /system/settings        获取系统设置
  - PUT  /system/settings        更新系统设置
  - GET  /system/llm-models      获取可用 LLM 模型列表
  - POST /system/test-llm-connection  测试 LLM 连接
  - POST /system/fetch-llm-models     获取模型列表
"""
from fastapi import APIRouter, HTTPException

from backend.src.schemas.system import (
    SystemSettings,
    SystemSettingsUpdate,
    TestLLMConnectionRequest,
    TestLLMConnectionResponse,
    FetchLLMModelsRequest,
)
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


@router.post("/system/test-llm-connection", response_model=TestLLMConnectionResponse)
async def test_llm_connection(req: TestLLMConnectionRequest):
    """
    测试 LLM 连接是否正常

    尝试调用一次简单的 chat completion，验证配置是否正确
    """
    try:
        import httpx

        # 构造测试请求
        headers = {
            "Authorization": f"Bearer {req.api_key}" if req.api_key else "",
            "Content-Type": "application/json",
        }

        # 简单的测试 prompt
        payload = {
            "model": req.model,
            "messages": [
                {"role": "user", "content": "Hello, please respond with 'OK' if you receive this."}
            ],
            "max_tokens": 10,
            "temperature": 0,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{req.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return TestLLMConnectionResponse(
                    success=True,
                    message="✅ 连接成功！LLM 响应正常",
                    response=content[:100] if content else "OK",
                )
            elif response.status_code == 401:
                return TestLLMConnectionResponse(
                    success=False,
                    message="❌ 认证失败",
                    detail="API Key 无效或已过期",
                    suggestion="请检查 API Key 是否正确",
                )
            elif response.status_code == 404:
                return TestLLMConnectionResponse(
                    success=False,
                    message="❌ 模型不存在",
                    detail=f"模型 '{req.model}' 不存在或 URL 路径错误",
                    suggestion="请确认模型名称和 Base URL 是否匹配",
                )
            elif response.status_code == 405:
                return TestLLMConnectionResponse(
                    success=False,
                    message="❌ 方法不允许",
                    detail="该 API 端点不支持 POST 请求或路径错误",
                    suggestion="请检查 Base URL 是否正确（应为 OpenAI 兼容格式，如 https://api.openai.com/v1）",
                )
            else:
                return TestLLMConnectionResponse(
                    success=False,
                    message=f"❌ 请求失败 (HTTP {response.status_code})",
                    detail=response.text[:200] if response.text else None,
                )

    except httpx.TimeoutException:
        return TestLLMConnectionResponse(
            success=False,
            message="❌ 请求超时",
            detail="LLM 服务响应时间过长",
            suggestion="请检查网络连接或增加 Timeout 设置",
        )
    except Exception as e:
        return TestLLMConnectionResponse(
            success=False,
            message="❌ 连接测试失败",
            detail=str(e),
            suggestion="请检查 Base URL、API Key 和模型名称是否正确",
        )


@router.post("/system/fetch-llm-models")
async def fetch_llm_models(req: FetchLLMModelsRequest):
    """
    从指定 Base URL 获取可用模型列表

    支持 OpenAI 兼容的 /models 端点
    """
    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {req.api_key}" if req.api_key else "",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{req.base_url.rstrip('/')}/models",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])

                # 限制返回数量
                models = models[: req.limit]

                return {
                    "success": True,
                    "count": len(models),
                    "models": [{"id": m.get("id", ""), "object": m.get("object", "model")} for m in models],
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "detail": "认证失败：API Key 无效",
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "detail": "无法获取模型列表：该 API 不支持 /models 端点",
                }
            else:
                return {
                    "success": False,
                    "detail": f"请求失败 (HTTP {response.status_code}): {response.text[:200]}",
                }

    except Exception as e:
        return {
            "success": False,
            "detail": f"请求异常: {str(e)}",
        }
