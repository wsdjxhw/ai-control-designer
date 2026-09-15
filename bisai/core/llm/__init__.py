"""
LLM 模块（智能层核心）
"""

from core.llm.gateway import get_llm, LLMPlatformManager, platform_manager
from core.llm.diagnosis import generate_diagnostic_report, validate_diagnosis_report
from core.llm.code_modify import modify_control_law
from core.llm.newbie import generate_scene, refine_config
from core.llm.strategy_parser import parse_strategy
from core.llm.physics_validator import validate_physics
from core.llm.utils import extract_code_from_response, validate_syntax

# 从 core.config 导入配置
from core.config import (
    LLM_MODEL,
    BASE_URL,
    OPENAI_API_KEY,
    LLM_TEMPERATURE,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT,
    DATA_DIR,
    PROJECTS_DIR,
    CHROMA_DB_DIR,
    SYSTEM_SETTINGS_FILE,
)

__all__ = [
    "get_llm",
    "LLMPlatformManager",
    "platform_manager",
    "generate_diagnostic_report",
    "validate_diagnosis_report",
    "modify_control_law",
    "generate_scene",
    "refine_config",
    "parse_strategy",
    "validate_physics",
    "extract_code_from_response",
    "validate_syntax",
    "LLM_MODEL",
    "BASE_URL",
    "OPENAI_API_KEY",
    "LLM_TEMPERATURE",
    "LLM_MAX_RETRIES",
    "LLM_TIMEOUT",
    "DATA_DIR",
    "PROJECTS_DIR",
    "CHROMA_DB_DIR",
    "SYSTEM_SETTINGS_FILE",
]