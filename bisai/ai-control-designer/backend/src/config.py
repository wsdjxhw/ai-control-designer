"""
后端配置模块 (Gateway Layer Config)
使用 Pydantic Settings 管理系统配置，所有路径使用绝对路径。

路径计算：backend/src/config.py -> 上三级到项目根目录
"""
from pathlib import Path

from pydantic_settings import BaseSettings

# 计算项目根目录：backend/src/config.py -> 上三级到根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # ===== SQLite 单文件数据库 =====
    # 绝对路径，不受启动时工作目录影响
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'app.db'}"

    # ===== ChromaDB 本地持久化路径 =====
    chroma_db_path: str = str(ROOT_DIR / "data" / "chroma_db")

    # ===== 项目文件存储根目录 =====
    projects_root: str = str(ROOT_DIR / "data" / "projects")

    # ===== 系统设置文件路径 =====
    system_settings_file: str = str(ROOT_DIR / "data" / "system_settings.json")

    # ===== LLM 默认配置 =====
    default_llm_model: str = "moonshotai/Kimi-K2.5"
    default_llm_base_url: str = "https://api-inference.modelscope.cn/v1"
    default_llm_api_key: str = ""

    # ===== 演化引擎默认参数 =====
    default_max_iterations: int = 20

    class Config:
        env_file = str(ROOT_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
