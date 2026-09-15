"""
LLM 配置读写服务 —— B 层唯一保留的 LLM 相关服务

职责：
  - 只负责读写 system_settings.json
  - 不做任何 LLM 调用业务逻辑
  - D 的 core/llm/gateway.py 自动读取此文件获取配置

注意：B 的 router 层直接调用 D 的 core/llm/* 模块做业务逻辑，
      B 不经过中间服务层封装。
"""
import json
from pathlib import Path

from pydantic import BaseModel

# 配置文件路径
CONFIG_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "system_settings.json"
)


class LLMConfig(BaseModel):
    """LLM 配置"""
    model: str = "moonshotai/Kimi-K2.5"
    api_key: str = ""
    base_url: str = "https://api-inference.modelscope.cn/v1"
    temperature: float = 0.0
    max_retries: int = 30


class OptimizerDefaults(BaseModel):
    """优化器默认配置"""
    type: str = "cmaes"
    trials: int = 1000
    seed: int = 42


class SystemSettings(BaseModel):
    """系统设置顶层模型（JSON 存储格式）"""
    llm: LLMConfig = LLMConfig()
    optimizer_defaults: OptimizerDefaults = OptimizerDefaults()
    # 前端系统设置里的默认最大迭代次数（start_evolution 未指定时使用）
    max_iterations: int = 20


def load_settings() -> dict:
    """从 JSON 文件加载系统设置"""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    # 返回默认值
    default = SystemSettings()
    save_settings(default)
    return default.model_dump()


def save_settings(data) -> bool:
    """
    保存系统设置到 JSON 文件

    Args:
        data: 可以是 SystemSettings 对象 或 dict（扁平结构）

    Returns:
        是否保存成功
    """
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 如果是 Pydantic 对象，转换为 dict
    if hasattr(data, 'model_dump'):
        data = data.model_dump()
    # 如果是 dict，直接使用

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return True
