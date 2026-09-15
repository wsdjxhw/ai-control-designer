"""ExpressionCost：基于 SymPy 符号表达式的代价函数。

从 scene_config['cost'] 中读取符号表达式字符串，
使用 SymPy 解析并数值化计算运行代价和终端代价。
支持任意代数表达式，灵活性介于 TemplateCost 和 CodeCost 之间。
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from core.base.base_cost import BaseCost


class ExpressionCost(BaseCost):
    """符号表达式代价函数：通过 SymPy 解析 scene_config 中的表达式。

    scene_config['cost'] 格式示例:
    {
        "type": "expression",
        "running_expr": "0.5*(S-1000)**2 + 10*I + 0.1*u1",
        "terminal_expr": "100*(S-1000)**2 + 50*I",
        "symbols": {"state": ["S", "I", "R", "Q"], "control": ["u1", "u2"]}
    }

    运行代价 J_running = eval(running_expr) * dt
    终端代价 J_terminal = eval(terminal_expr)
    """

    def __init__(self, scene_config: dict) -> None:
        super().__init__(scene_config)

        # 兼容两种命名：cost_function（新）或 cost（旧）
        cost_cfg = scene_config.get("cost_function") or scene_config.get("cost", {})

        # 符号定义
        symbols_cfg = cost_cfg.get("symbols", {})
        state_names: list[str] = symbols_cfg.get("state", scene_config.get("state_names", []))
        control_names: list[str] = symbols_cfg.get("control", scene_config.get("control_names", []))

        # 创建 SymPy 符号
        self._state_syms = {name: sp.Symbol(name) for name in state_names}
        self._control_syms = {name: sp.Symbol(name) for name in control_names}

        # 解析运行代价表达式
        running_expr_str = cost_cfg.get("running_expr", "")
        if running_expr_str:
            local_dict = {name: sp.Symbol(name) for name in state_names + control_names}
            self._running_expr = sp.sympify(running_expr_str, locals=local_dict)
        else:
            self._running_expr = None

        # 解析终端代价表达式
        terminal_expr_str = cost_cfg.get("terminal_expr", "")
        if terminal_expr_str and cost_cfg.get("has_terminal_cost", True):
            local_dict = {name: sp.Symbol(name) for name in state_names + control_names}
            self._terminal_expr = sp.sympify(terminal_expr_str, locals=local_dict)
        else:
            self._terminal_expr = None

        # 时间/空间步长
        temporal = scene_config.get("temporal", {})
        self._dt: float = temporal.get("dt", 1.0)
        spatial = scene_config.get("spatial", {})
        self._dx: float = spatial.get("dx", 1.0)

    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """计算单步运行代价。

        对 ODE 模型：state/control 为 1D 数组，shape (state_dim,) / (control_dim,)
        代价 = eval(running_expr) * dt
        """
        if self._running_expr is None:
            return 0.0

        # 构建符号→数值的映射
        subs_dict = {}
        for i, name in enumerate(self._state_syms.keys()):
            if i < len(state):
                subs_dict[self._state_syms[name]] = float(state[i])
        for i, name in enumerate(self._control_syms.keys()):
            if i < len(control):
                subs_dict[self._control_syms[name]] = float(control[i])

        # 数值化计算
        cost_val = float(self._running_expr.evalf(subs=subs_dict))
        return cost_val * self._dt

    def compute_terminal(self, state: np.ndarray) -> float:
        """计算终端代价。

        仅包含状态符号，无时间积分。
        """
        if self._terminal_expr is None:
            return 0.0

        subs_dict = {self._state_syms[name]: float(state[i]) for i, name in enumerate(self._state_syms.keys()) if i < len(state)}
        cost_val = float(self._terminal_expr.evalf(subs=subs_dict))
        return cost_val
