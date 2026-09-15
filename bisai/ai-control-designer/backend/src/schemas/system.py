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
    """系统设置 - 扁平结构（与前端和 llm_config_service 保持一致）"""
    # LLM 配置
    llm_model: str = Field("moonshotai/Kimi-K2.5")
    llm_base_url: str = Field("https://api-inference.modelscope.cn/v1")
    llm_api_key: str = Field("")
    llm_temperature: float = Field(0.0)
    llm_timeout: int = Field(240)

    # 优化器配置
    optimizer_type: str = Field("cmaes")
    max_iterations: int = Field(20)

    # CMA-ES 参数
    popsize: int = Field(50)
    sigma0: float = Field(0.25)

    # PSO 参数
    n_particles: int = Field(30)
    w: float = Field(0.7)
    c1: float = Field(1.5)
    c2: float = Field(1.5)

    # 兼容旧字段
    default_max_iterations: int = Field(20)
    coarse_fidelity_ratio: float = Field(0.2)


class SystemSettingsUpdate(BaseModel):
    """系统设置更新 - 所有字段可选"""
    # LLM 配置
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_timeout: Optional[int] = None

    # 优化器配置
    optimizer_type: Optional[str] = None
    max_iterations: Optional[int] = None

    # CMA-ES 参数
    popsize: Optional[int] = None
    sigma0: Optional[float] = None

    # PSO 参数
    n_particles: Optional[int] = None
    w: Optional[float] = None
    c1: Optional[float] = None
    c2: Optional[float] = None

    # 兼容旧字段
    default_max_iterations: Optional[int] = None
    coarse_fidelity_ratio: Optional[float] = None
