"""CodeCost：基于用户自定义 Python 代码的代价函数。

从 scene_config['cost'] 中读取 Python 代码字符串，
动态编译并执行以计算运行代价和终端代价。
最高灵活性，支持任意复杂逻辑（循环、条件、外部库调用等）。
"""

from __future__ import annotations

import types

import numpy as np

from core.base.base_cost import BaseCost


class CodeCost(BaseCost):
    """代码定义代价函数：通过 scene_config 提供自定义 Python 函数。

    scene_config['cost'] 格式示例:
    {
        "type": "code",
        "running_code": "def compute_running(state, control, step):\n    return 0.5*np.sum((state-1000)**2) + 0.1*np.sum(control)",
        "terminal_code": "def compute_terminal(state):\n    return 100*np.sum((state-1000)**2)"
    }

    代码字符串必须定义：
      - compute_running(state, control, step) -> float
      - compute_terminal(state) -> float
    """

    def __init__(self, scene_config: dict) -> None:
        super().__init__(scene_config)

        # 兼容两种命名：cost_function（新）或 cost（旧）
        cost_cfg = scene_config.get("cost_function") or scene_config.get("cost", {})

        # 编译运行代价函数
        running_code = cost_cfg.get("running_code", "")
        if running_code:
            namespace: dict = {"np": np}
            exec(compile(running_code, "<running_cost>", "exec"), namespace)
            self._running_func = namespace.get("compute_running")
            if self._running_func is None:
                raise ValueError("running_code 必须定义 compute_running(state, control, step) 函数")
        else:
            self._running_func = None

        # 编译终端代价函数
        terminal_code = cost_cfg.get("terminal_code", "")
        if terminal_code and cost_cfg.get("has_terminal_cost", True):
            namespace: dict = {"np": np}
            exec(compile(terminal_code, "<terminal_cost>", "exec"), namespace)
            self._terminal_func = namespace.get("compute_terminal")
            if self._terminal_func is None:
                raise ValueError("terminal_code 必须定义 compute_terminal(state) 函数")
        else:
            self._terminal_func = None

        # 时间步长
        temporal = scene_config.get("temporal", {})
        dt_val = temporal.get("dt")
        self._dt: float = float(dt_val) if dt_val is not None else 1.0

    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """调用用户定义的运行代价函数。"""
        if self._running_func is None:
            return 0.0

        cost_val = float(self._running_func(state, control, step))
        return cost_val * self._dt

    def compute_terminal(self, state: np.ndarray) -> float:
        """调用用户定义的终端代价函数。"""
        if self._terminal_func is None:
            return 0.0

        return float(self._terminal_func(state))
