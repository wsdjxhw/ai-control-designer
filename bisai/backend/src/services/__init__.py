"""
服务层模块 —— 封装业务逻辑

分层原则：
  - routers/  ：负责 HTTP 路由、参数校验、响应序列化
  - services/ ：负责业务逻辑、跨模块编排、数据持久化

当前服务清单：
  - file_storage.py       : ✅ 已完成 — 项目文件管理系统
  - llm_config_service.py : ✅ 已完成 — LLM 系统设置(JSON)读写
  - evolution_service.py  : ✅ 已完成 — 演化引擎编排（后台线程）
"""
from backend.src.services.file_storage import FileStorageService
from backend.src.services.llm_config_service import load_settings, save_settings, SystemSettings
from backend.src.services.evolution_service import EvolutionService

__all__ = ["FileStorageService", "load_settings", "save_settings", "SystemSettings", "EvolutionService"]
