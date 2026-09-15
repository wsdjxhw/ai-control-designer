"""
D模块配置文件
只服务于 D 模块（LLM/RAG），不涉及其他模块
"""

import os
from pathlib import Path

# ========== LLM 配置（ModelScope / 魔搭社区） ==========
LLM_MODEL = os.getenv("LLM_MODEL", "grok-4.3")
BASE_URL = os.getenv("BASE_URL", "https://new.xinjianya.top/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-uH3TzQzY4S1mNIIZ6sovHVMerE3RUoRabrPgNJdUK1lKF1Ij")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "30"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "240"))

# ========== 其他平台备用配置 ==========
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# ========== 路径配置 ==========
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

DATA_DIR = PROJECT_ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"
SYSTEM_SETTINGS_FILE = DATA_DIR / "system_settings.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

def print_config():
    print("=" * 40)
    print("D模块当前配置：")
    print(f"  LLM_MODEL: {LLM_MODEL}")
    print(f"  BASE_URL: {BASE_URL}")
    print(f"  OPENAI_API_KEY: {'已设置' if OPENAI_API_KEY else '未设置'}")
    print(f"  LLM_TEMPERATURE: {LLM_TEMPERATURE}")
    print(f"  LLM_MAX_RETRIES: {LLM_MAX_RETRIES}")
    print(f"  DATA_DIR: {DATA_DIR}")
    print("=" * 40)