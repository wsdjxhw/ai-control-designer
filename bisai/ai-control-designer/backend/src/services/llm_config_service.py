"""
LLM 配置读写服务 —— B 层唯一保留的 LLM 相关服务

职责：
  - 只负责读写 system_settings.json
  - 不做任何 LLM 调用业务逻辑
  - D 的 core/llm/gateway.py 自动读取此文件获取配置

注意：B 的 router 层直接调用 D 的 core/llm/* 模块做业务逻辑，
      B 不经过中间服务层封装。

当前使用扁平结构（与 schemas/system.py 保持一致）：
{
  "llm_model": "moonshotai/Kimi-K2.5",
  "llm_base_url": "https://...",
  "llm_api_key": "...",
  "llm_temperature": 0.0,
  "llm_timeout": 240,
  "optimizer_type": "cmaes",
  "max_iterations": 20,
  ...
}
"""

import json
from pathlib import Path
from typing import Any, Dict


# 配置文件路径
CONFIG_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "system_settings.json"
)


def load_settings() -> Dict[str, Any]:
    """
    从 JSON 文件加载系统设置

    Returns:
        扁平结构的配置字典
    """
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # 确保返回的是字典
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"[llm_config_service] 读取配置文件失败: {e}，使用默认值")

    # 返回默认值
    default = get_default_settings()
    save_settings(default)
    return default


def save_settings(data: Dict[str, Any]) -> bool:
    """
    保存系统设置到 JSON 文件

    Args:
        data: 扁平结构的配置字典

    Returns:
        是否保存成功
    """
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except IOError as e:
        print(f"[llm_config_service] 保存配置文件失败: {e}")
        return False


def get_default_settings() -> Dict[str, Any]:
    """获取默认配置（扁平结构）"""
    return {
        "llm_model": "moonshotai/Kimi-K2.5",
        "llm_base_url": "https://api-inference.modelscope.cn/v1",
        "llm_api_key": "",
        "llm_temperature": 0.0,
        "llm_timeout": 240,
        "optimizer_type": "cmaes",
        "max_iterations": 20,
        "popsize": 50,
        "sigma0": 0.25,
        "n_particles": 30,
        "w": 0.7,
        "c1": 1.5,
        "c2": 1.5,
    }


def update_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    部分更新配置

    Args:
        updates: 要更新的字段（扁平结构）

    Returns:
        更新后的完整配置
    """
    current = load_settings()
    current.update(updates)
    save_settings(current)
    return current
