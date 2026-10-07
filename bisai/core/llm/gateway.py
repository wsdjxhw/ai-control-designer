"""
LLM Gateway - 统一 LLM 调用接口
职责：使用 OpenAI 官方库流式调用魔搭 API，提供统一的 invoke 接口
"""

import json
import os
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI
from pathlib import Path

from core.config import (
    LLM_MODEL,
    BASE_URL,
    OPENAI_API_KEY,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)


def load_llm_config_from_settings() -> Dict[str, Any]:
    """
    从 system_settings.json 加载 LLM 配置

    优先级：system_settings.json > 环境变量 > 默认值
    """
    # 配置文件路径：项目根目录 / data / system_settings.json
    config_file = Path(__file__).resolve().parent.parent.parent / "data" / "system_settings.json"

    if config_file.exists():
        try:
            settings = json.loads(config_file.read_text(encoding="utf-8"))

            # 优先使用扁平结构（用户在前端"系统设置"页面最新修改的配置）
            if "llm_model" in settings:
                model = settings.get("llm_model") or LLM_MODEL
                print(f"[gateway] 从 system_settings.json 加载 LLM 配置（扁平结构，优先级最高）")
                print(f"[gateway] 实际使用的 model: {model}")
                return {
                    "model": model,
                    "base_url": settings.get("llm_base_url") or BASE_URL,
                    "api_key": settings.get("llm_api_key") or OPENAI_API_KEY,
                    "temperature": settings.get("llm_temperature", LLM_TEMPERATURE),
                    "timeout": settings.get("llm_timeout", LLM_TIMEOUT),
                }

            # 回退到嵌套结构（llm 对象，仅当没有扁平字段时使用）
            if "llm" in settings:
                print(f"[gateway] 从 system_settings.json 加载 LLM 配置（嵌套 llm 对象，回退）")
                llm_settings = settings.get("llm", {})
                return {
                    "model": llm_settings.get("model") or LLM_MODEL,
                    "base_url": llm_settings.get("base_url") or BASE_URL,
                    "api_key": llm_settings.get("api_key") or OPENAI_API_KEY,
                    "temperature": llm_settings.get("temperature", LLM_TEMPERATURE),
                    "timeout": llm_settings.get("timeout", LLM_TIMEOUT),
                }

            print(f"[gateway] system_settings.json 格式未知，使用环境变量配置")

        except Exception as e:
            print(f"[gateway] 读取 system_settings.json 失败: {e}，使用环境变量配置")

    # 回退到环境变量
    return {
        "model": LLM_MODEL,
        "base_url": BASE_URL,
        "api_key": OPENAI_API_KEY,
        "temperature": LLM_TEMPERATURE,
        "timeout": LLM_TIMEOUT,
    }


class LLMClient:
    """
    封装 OpenAI 流式调用，提供统一的 invoke 方法
    """
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        extra_body: Optional[Dict] = None
    ):
        # 优先从 system_settings.json 加载配置
        config = load_llm_config_from_settings()

        self.model = model or config["model"]
        self.base_url = base_url or config["base_url"]
        self.api_key = api_key or config["api_key"]
        self.temperature = temperature if temperature is not None else config["temperature"]
        self.timeout = timeout if timeout is not None else config["timeout"]
        self.extra_body = extra_body or {}
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        # 对于 Qwen3 系列，默认启用思考模式（可通过 extra_body 覆盖）
        if "Qwen3" in self.model and "enable_thinking" not in self.extra_body:
            self.extra_body["enable_thinking"] = True

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用 LLM，返回完整内容（流式收集）
        """
        max_tokens = kwargs.get('max_tokens', 30000)
        temperature = kwargs.get('temperature', self.temperature)
        extra_body = {**self.extra_body, **kwargs.get('extra_body', {})}
        stop = kwargs.get('stop')

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                extra_body=extra_body,
            )
        except Exception as e:
            raise Exception(f"LLM 调用失败: {str(e)}")

        full_content = ""
        for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_content += delta.content

        if not full_content:
            raise Exception("LLM 响应内容为空")

        return full_content


# ========== 全局工厂函数 ==========
def get_llm(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = LLM_TEMPERATURE,
    timeout: int = LLM_TIMEOUT,
    extra_body: Optional[Dict] = None
) -> LLMClient:
    """
    创建 LLM 客户端实例

    优先级：显式参数 > system_settings.json > 环境变量 > 默认值
    """
    # 如果没有提供任何参数，优先从 system_settings.json 加载
    if model is None and base_url is None and api_key is None:
        config = load_llm_config_from_settings()
        return LLMClient(
            model=config["model"],
            base_url=config["base_url"],
            api_key=config["api_key"],
            temperature=config["temperature"],
            timeout=config["timeout"],
            extra_body=extra_body,
        )

    # 否则使用显式参数（部分或全部），未提供的字段回退到默认值
    return LLMClient(
        model=model or LLM_MODEL,
        base_url=base_url or BASE_URL,
        api_key=api_key or OPENAI_API_KEY,
        temperature=temperature,
        timeout=timeout,
        extra_body=extra_body,
    )


# 保留原有多平台管理器（仅用于兼容，实际不再使用）
class LLMPlatformManager:
    pass

platform_manager = LLMPlatformManager()