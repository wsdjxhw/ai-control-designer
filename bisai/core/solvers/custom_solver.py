"""CustomSolver：支持用户上传自定义求解器代码。

用户可以通过 scene_config 提供自定义求解器代码，实现：
- 不同的积分方法（显式/隐式、多步法等）
- 特殊的边界条件处理
- 领域特定的优化
- 向后兼容：不影响现有内置求解器
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from core.base.base_solver import BaseSolver
from core.base.base_model import BaseModel


class CustomSolver(BaseSolver):
    """自定义求解器：通过 scene_config 加载用户提供的求解器代码。

    scene_config['solver'] 格式示例:
    {
        "solver_type": "custom",
        "custom_solver_code": '''
class MyCustomSolver(BaseSolver):
    def step(self, model, state, control, dt):
        # 自定义单步积分逻辑
        k1 = model.rhs(0, state, control)
        new_state = state + dt * k1
        return new_state

    def solve(self, model, t_span, dt, control_func):
        # 自定义完整仿真逻辑
        ...
        ''',
        "description": "用户自定义求解器说明"
    }

    代码必须定义继承 BaseSolver 的类，类名任意（自动检测第一个子类）。
    """

    def __init__(self, scene_config: dict) -> None:
        # 不调用 super().__init__()，因为 BaseSolver 没有 __init__
        # 只保存 scene_config 引用
        self.scene_config = scene_config

        solver_cfg = scene_config.get("solver", {})
        code = solver_cfg.get("custom_solver_code", "")

        if not code:
            raise ValueError("custom_solver_code 不能为空")

        # 动态编译用户代码
        namespace: dict[str, Any] = {
            "np": np,
            "BaseSolver": BaseSolver,
            "BaseModel": BaseModel,
            "Callable": Callable,
        }
        exec(compile(code, "<custom_solver>", "exec"), namespace)

        # 查找继承 BaseSolver 的类（排除 BaseSolver 本身）
        solver_cls = None
        for name, obj in namespace.items():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseSolver)
                and obj is not BaseSolver
            ):
                solver_cls = obj
                break

        if solver_cls is None:
            raise ValueError(
                "custom_solver_code 中未找到继承 BaseSolver 的类"
            )

        # 实例化用户定义的求解器
        self._inner_solver: BaseSolver = solver_cls()
        self._solver_name = solver_cls.__name__
        self._description = solver_cfg.get("description", self._solver_name)

    def step(
        self,
        model: BaseModel,
        state: np.ndarray,
        control: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """委托给用户定义的 step 方法。"""
        return self._inner_solver.step(model, state, control, dt)

    def solve(
        self,
        model: BaseModel,
        t_span: tuple[float, float],
        dt: float,
        control_func: Callable[[float, np.ndarray], np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """委托给用户定义的 solve 方法。"""
        return self._inner_solver.solve(model, t_span, dt, control_func)

    def __repr__(self) -> str:
        return f"CustomSolver({self._solver_name})"
