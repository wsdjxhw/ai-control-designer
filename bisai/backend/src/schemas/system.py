"""
Pydantic Schemas —— 系统设置相关模型
"""
from typing import Optional

from pydantic import BaseModel, Field


class LLMModelInfo(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: str
    model_name: str = ""
    base_url: str = ""
    api_key: str = ""
    is_active: bool = False
    is_fallback: bool = False
    rate_limit_rpm: Optional[int] = None


class LLMModelListResponse(BaseModel):
    active_model: Optional[LLMModelInfo] = None
    fallback_models: list[LLMModelInfo] = Field(default_factory=list)


class SystemSettings(BaseModel):
    """系统设置 —— 与前端 types/api.ts 的 SystemSettings 对齐（扁平结构）"""
    llm_model: str = Field("moonshotai/Kimi-K2.5")
    llm_base_url: str = Field("https://api-inference.modelscope.cn/v1")
    llm_api_key: str = Field("")
    llm_temperature: float = Field(0.0, ge=0.0, le=2.0)
    llm_timeout: int = Field(240, ge=10, le=600)
    optimizer_type: str = Field("cmaes")
    max_iterations: int = Field(20, ge=1, le=100)


class SystemSettingsUpdate(BaseModel):
    """系统设置更新请求 —— 只传要改的字段"""
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_timeout: Optional[int] = Field(None, ge=10, le=600)
    optimizer_type: Optional[str] = None
    max_iterations: Optional[int] = None


class TestLLMConnectionRequest(BaseModel):
    """LLM 连接测试请求"""
    model_config = {"protected_namespaces": ()}

    base_url: str = Field(..., description="LLM API Base URL")
    api_key: str = Field("", description="API Key")
    model: str = Field(..., description="模型名称")


class TestLLMConnectionResponse(BaseModel):
    """LLM 连接测试响应"""
    success: bool
    message: str
    detail: Optional[str] = None
    suggestion: Optional[str] = None
    response: Optional[str] = None


class FetchLLMModelsRequest(BaseModel):
    """获取模型列表请求"""
    model_config = {"protected_namespaces": ()}

    base_url: str = Field(..., description="LLM API Base URL")
    api_key: str = Field("", description="API Key")
    limit: int = Field(100, ge=1, le=500, description="最大返回模型数量")
