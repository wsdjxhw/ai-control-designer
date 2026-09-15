"""
求解器动态加载器 - 支持内置和自定义求解器

支持两种加载模式：
1. 内置求解器：通过 solver_type 标识符加载
2. 自定义求解器：通过文件路径动态导入用户上传的求解器
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Type

from core.base.base_solver import BaseSolver


class SolverLoader:
    """
    求解器动态加载器

    用法：
        # 加载内置求解器
        solver = SolverLoader.load(solver_type="ode_scipy", params={"method": "RK45"})

        # 加载自定义求解器
        solver = SolverLoader.load(
            solver_type="custom",
            custom_path="/path/to/my_solver.py",
            params={"K1": 0.5, "K2": 1.0}
        )
    """

    # 内置求解器映射
    BUILTIN_SOLVERS = {
        "ode_scipy": "core.solvers.ode_scipy_solver.ODE_Scipy_Solver",
        "pde_rk4": "core.solvers.pde_rk4_solver.PDE_RK4_Solver",
    }

    @classmethod
    def load(
        cls,
        solver_type: str,
        params: Optional[Dict[str, Any]] = None,
        custom_path: Optional[str] = None,
    ) -> BaseSolver:
        """
        加载求解器实例

        Args:
            solver_type: 求解器类型
                - "ode_scipy": SciPy ODE 求解器
                - "pde_rk4": RK4 PDE 求解器
                - "custom": 自定义求解器（需提供 custom_path）
            params: 求解器参数字典
            custom_path: 自定义求解器文件路径（仅当 solver_type="custom" 时需要）

        Returns:
            BaseSolver 子类实例

        Raises:
            ValueError: 未知的求解器类型或自定义路径无效
            ImportError: 自定义求解器导入失败
        """
        params = params or {}

        if solver_type == "custom":
            if not custom_path:
                raise ValueError("自定义求解器必须提供 custom_path 参数")
            return cls._load_custom(custom_path, params)

        # 加载内置求解器
        return cls._load_builtin(solver_type, params)

    @classmethod
    def _load_builtin(cls, solver_type: str, params: Dict[str, Any]) -> BaseSolver:
        """加载内置求解器"""
        if solver_type not in cls.BUILTIN_SOLVERS:
            raise ValueError(
                f"未知的内置求解器类型: {solver_type}。"
                f"支持的类型: {list(cls.BUILTIN_SOLVERS.keys())}"
            )

        module_path = cls.BUILTIN_SOLVERS[solver_type]
        module_name, class_name = module_path.rsplit(".", 1)

        # 动态导入
        module = __import__(module_name, fromlist=[class_name])
        solver_cls: Type[BaseSolver] = getattr(module, class_name)

        # 实例化（传入 params）
        return solver_cls(**params)

    @classmethod
    def _load_custom(cls, custom_path: str, params: Dict[str, Any]) -> BaseSolver:
        """
        动态加载自定义求解器

        自定义求解器必须：
        1. 继承 BaseSolver
        2. 实现 step() 方法
        3. 导出名为 CustomSolver 的类
        """
        path = Path(custom_path)
        if not path.exists():
            raise ValueError(f"自定义求解器文件不存在: {custom_path}")

        if not path.suffix == ".py":
            raise ValueError(f"自定义求解器必须是 .py 文件: {custom_path}")

        # 动态导入模块
        module_name = f"custom_solver_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载自定义求解器: {custom_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 查找 CustomSolver 类
        if not hasattr(module, "CustomSolver"):
            raise ImportError(
                f"自定义求解器 {custom_path} 必须定义 CustomSolver 类"
            )

        solver_cls: Type[BaseSolver] = getattr(module, "CustomSolver")

        # 验证继承关系
        if not issubclass(solver_cls, BaseSolver):
            raise ImportError(
                f"CustomSolver 必须继承 BaseSolver: {custom_path}"
            )

        # 实例化
        return solver_cls(**params)

    @classmethod
    def validate_custom_solver(cls, custom_path: str) -> Dict[str, Any]:
        """
        验证自定义求解器文件是否有效

        Returns:
            {
                "valid": bool,
                "errors": [...],
                "warnings": [...],
                "class_name": "...",
                "methods": [...]
            }
        """
        errors = []
        warnings = []

        try:
            path = Path(custom_path)
            if not path.exists():
                return {"valid": False, "errors": [f"文件不存在: {custom_path}"], "warnings": []}

            if not path.suffix == ".py":
                return {"valid": False, "errors": [f"必须是 .py 文件"], "warnings": []}

            # 尝试加载
            module_name = f"validate_solver_{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return {"valid": False, "errors": ["无法解析文件"], "warnings": []}

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 检查 CustomSolver 类
            if not hasattr(module, "CustomSolver"):
                errors.append("必须定义 CustomSolver 类")

            else:
                solver_cls = getattr(module, "CustomSolver")

                if not issubclass(solver_cls, BaseSolver):
                    errors.append("CustomSolver 必须继承 BaseSolver")

                # 检查必要方法
                required_methods = ["step"]
                methods = [m for m in dir(solver_cls) if not m.startswith("_")]
                missing = [m for m in required_methods if not hasattr(solver_cls, m)]

                if missing:
                    errors.append(f"缺少必要方法: {missing}")

        except SyntaxError as e:
            errors.append(f"语法错误: {e}")
        except Exception as e:
            errors.append(f"加载失败: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "class_name": "CustomSolver" if "CustomSolver" in dir() else None,
            "methods": methods if "methods" in dir() else [],
        }


# 便捷函数
def load_solver(
    solver_type: str,
    params: Optional[Dict[str, Any]] = None,
    custom_path: Optional[str] = None,
) -> BaseSolver:
    """便捷函数：加载求解器"""
    return SolverLoader.load(solver_type, params, custom_path)
