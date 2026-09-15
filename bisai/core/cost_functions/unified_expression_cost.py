"""UnifiedExpressionCost：统一表达式代价函数。

用户只写一个表达式，框架自动处理时间积分。
支持两种模式：
1. integrate_over_time=True：每步计算并乘 dt（运行代价）
2. integrate_over_time=False：只在结束时计算一次（终端代价）

适用于：用户不想区分 running/terminal，只想写一个简单表达式。
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from core.base.base_cost import BaseCost


class UnifiedExpressionCost(BaseCost):
    """统一表达式代价函数：用户只写一个表达式。

    scene_config['cost_function'] 格式示例:
    {
        "cost_type": "unified",
        "cost_expr": "0.5*(S-0)**2 + 10*(I-0)**2 + 0.1*u1**2",
        "integrate_over_time": true,
        "symbols": {"state": ["S", "I", "R"], "control": ["u1"]}
    }

    - integrate_over_time=True：每步调用 compute_running，乘 dt
    - integrate_over_time=False：只在结束时调用 compute_terminal
    """

    def __init__(self, scene_config: dict) -> None:
        super().__init__(scene_config)

        cost_cfg = scene_config.get("cost_function", {}) or scene_config.get("cost", {})

        # 符号定义
        symbols_cfg = cost_cfg.get("symbols", {})
        state_names: list[str] = symbols_cfg.get("state", scene_config.get("state_names", []))
        control_names: list[str] = symbols_cfg.get("control", scene_config.get("control_names", []))

        self._state_syms = {name: sp.Symbol(name) for name in state_names}
        self._control_syms = {name: sp.Symbol(name) for name in control_names}

        # 解析统一表达式
        expr_str = cost_cfg.get("cost_expr", "")
        if expr_str:
            # 构建 locals 字典，避免 SymPy 把 S/I/R 解析为单例
            local_dict = {name: sp.Symbol(name) for name in state_names + control_names}
            self._expr = sp.sympify(expr_str, locals=local_dict)
        else:
            self._expr = None

        # 是否时间积分
        self._integrate_over_time = cost_cfg.get("integrate_over_time", True)

        # 时间/空间步长
        temporal = scene_config.get("temporal", {})
        self._dt: float = temporal.get("dt", 1.0)
        spatial = scene_config.get("spatial", {})
        self._dx: float = spatial.get("dx", 1.0)

    def _eval_expr(self, state: np.ndarray, control: np.ndarray | None) -> float:
        """数值化计算表达式。"""
        if self._expr is None:
            return 0.0

        subs_dict = {}
        for i, name in enumerate(self._state_syms.keys()):
            if i < len(state):
                subs_dict[self._state_syms[name]] = float(state[i])

        if control is not None:
            for i, name in enumerate(self._control_syms.keys()):
                if i < len(control):
                    subs_dict[self._control_syms[name]] = float(control[i])
        # 如果 control 为 None 且表达式包含控制符号，尝试用 0 填充
        elif self._control_syms:
            for name in self._control_syms.keys():
                subs_dict[self._control_syms[name]] = 0.0

        cost_val = float(self._expr.evalf(subs=subs_dict))
        return cost_val

    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """计算单步运行代价。

        仅当 integrate_over_time=True 时返回非零值。
        代价 = eval(cost_expr) * dt
        """
        if not self._integrate_over_time or self._expr is None:
            return 0.0

        cost_val = self._eval_expr(state, control)
        return cost_val * self._dt

    def compute_terminal(self, state: np.ndarray) -> float:
        """计算终端代价。

        仅当 integrate_over_time=False 时返回非零值。
        """
        if self._integrate_over_time or self._expr is None:
            return 0.0

        return self._eval_expr(state, None)
