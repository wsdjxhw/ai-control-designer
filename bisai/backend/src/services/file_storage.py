"""
文件存储服务 —— 管理项目工作目录的文件读写

职责：
  - 在 data/projects/{project_id}/ 下创建项目工作目录
  - 提供统一的文件读写接口
  - 文件存在性检查和路径解析

对外依赖：无（纯文件操作）
"""
import json
import shutil
from pathlib import Path
from typing import Optional

from backend.src.config import settings


class FileStorageService:
    """项目文件存储管理服务"""

    def __init__(self, projects_root: Optional[str] = None):
        self.projects_root = Path(projects_root or settings.projects_root)

    # ==================== 路径解析 ====================

    def project_dir(self, project_id: str) -> Path:
        """获取项目工作目录路径，不存在则创建"""
        path = self.projects_root / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ==================== 场景配置文件 ====================

    def scene_config_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "scene_config.json"

    def save_scene_config(self, project_id: str, config: dict) -> Path:
        path = self.scene_config_path(project_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return path

    def load_scene_config(self, project_id: str) -> Optional[dict]:
        path = self.scene_config_path(project_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ==================== 模型代码文件 ====================

    def model_code_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "model_code.py"

    def save_model_code(self, project_id: str, code: str) -> Path:
        path = self.model_code_path(project_id)
        path.write_text(code, encoding="utf-8")
        return path

    def load_model_code(self, project_id: str) -> Optional[str]:
        path = self.model_code_path(project_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    # ==================== 控制律文件（多版本）====================

    def control_law_path(self, project_id: str, version: int) -> Path:
        return self.project_dir(project_id) / f"control_v{version}.py"

    def save_control_law(self, project_id: str, version: int, code: str) -> Path:
        path = self.control_law_path(project_id, version)
        path.write_text(code, encoding="utf-8")
        return path

    def load_control_law(self, project_id: str, version: int) -> Optional[str]:
        path = self.control_law_path(project_id, version)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_control_law_versions(self, project_id: str) -> list[int]:
        directory = self.project_dir(project_id)
        versions = []
        for f in directory.glob("control_v*.py"):
            try:
                v = int(f.stem.replace("control_v", ""))
                versions.append(v)
            except ValueError:
                pass
        return sorted(versions)

    # ==================== 代价函数文件 ====================

    def cost_function_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "cost_function.py"

    def save_cost_function(self, project_id: str, code: str) -> Path:
        path = self.cost_function_path(project_id)
        path.write_text(code, encoding="utf-8")
        return path

    # ==================== 最优参数文件（多版本）====================

    def best_params_path(self, project_id: str, version: int) -> Path:
        return self.project_dir(project_id) / f"best_params_v{version}.json"

    def save_best_params(self, project_id: str, version: int, params: dict) -> Path:
        path = self.best_params_path(project_id, version)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2, ensure_ascii=False)
        return path

    def load_best_params(self, project_id: str, version: int) -> Optional[dict]:
        path = self.best_params_path(project_id, version)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ==================== 诊断报告文件（多版本）====================

    def diagnostic_path(self, project_id: str, version: int) -> Path:
        return self.project_dir(project_id) / f"diagnostic_v{version}.txt"

    def save_diagnostic(self, project_id: str, version: int, content: str) -> Path:
        path = self.diagnostic_path(project_id, version)
        path.write_text(content, encoding="utf-8")
        return path

    def load_diagnostic(self, project_id: str, version: int) -> Optional[str]:
        path = self.diagnostic_path(project_id, version)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    # ==================== 演化日志文件 ====================

    def evolution_log_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "evolution_log.json"

    def save_evolution_log(self, project_id: str, log_data: list) -> Path:
        path = self.evolution_log_path(project_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return path

    def load_evolution_log(self, project_id: str) -> Optional[list]:
        path = self.evolution_log_path(project_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ==================== 通用文件操作 ====================

    def file_exists(self, project_id: str, filename: str) -> bool:
        return (self.project_dir(project_id) / filename).exists()

    def delete_project_dir(self, project_id: str) -> bool:
        path = self.project_dir(project_id)
        if path.exists():
            shutil.rmtree(path)
            return True
        return False
