"""UnifiedExpressionCost：统一表达式代价函数。

用户只写一个表达式，框架自动处理时间积分和空间积分。
支持两种模式：
1. integrate_over_time=True：每步计算并乘 dt（运行代价）
2. integrate_over_time=False：只在结束时计算一次（终端代价）
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from core.base.base_cost import BaseCost


class UnifiedExpressionCost(BaseCost):
    """统一表达式代价函数。

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
        state_names = symbols_cfg.get("state", scene_config.get("state_names", []))
        control_names = symbols_cfg.get("control", scene_config.get("control_names", []))

        self._state_names = list(state_names)
        self._control_names = list(control_names)
        self._state_syms = [sp.Symbol(name) for name in self._state_names]
        self._control_syms = [sp.Symbol(name) for name in self._control_names]

        # 解析统一表达式并预编译
        expr_str = cost_cfg.get("cost_expr", "")
        if expr_str:
            local_dict = {name: sp.Symbol(name) for name in self._state_names + self._control_names}
            self._expr = sp.sympify(expr_str, locals=local_dict)
            try:
                # 两个 lambdify：一个带 control，一个不带
                self._expr_with_control = sp.lambdify(
                    self._state_syms + self._control_syms,
                    self._expr,
                    modules=["numpy"],
                )
                self._expr_no_control = sp.lambdify(
                    self._state_syms,
                    self._expr,
                    modules=["numpy"],
                )
            except Exception as e:
                print(f"[UnifiedExpressionCost] lambdify 失败: {e}")
                self._expr_with_control = None
                self._expr_no_control = None
        else:
            self._expr = None
            self._expr_with_control = None
            self._expr_no_control = None

        # 是否时间积分
        self._integrate_over_time = cost_cfg.get("integrate_over_time", True)

        # 时间/空间步长
        temporal = scene_config.get("temporal", {})
        dt_val = temporal.get("dt")
        self._dt: float = float(dt_val) if dt_val is not None else 1.0
        spatial = scene_config.get("spatial", {})
        self._dx: float = spatial.get("dx") or 1.0

    # ---------- 内部工具 ----------

    def _to_2d(self, arr: np.ndarray) -> np.ndarray:
        arr = np.asarray(arr, dtype=float)
        if arr.ndim == 1:
            return arr.reshape(1, -1)
        return arr

    def _state_args(self, state: np.ndarray) -> list:
        state = self._to_2d(state)
        return [state[:, i] for i in range(len(self._state_syms))]

    def _control_args(self, control: np.ndarray) -> list:
        control = self._to_2d(control)
        return [control[:, i] for i in range(len(self._control_syms))]

    # ---------- BaseCost 接口 ----------

    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """单步运行代价。

        - integrate_over_time=True: 返回 expr * dx * dt
        - integrate_over_time=False: 返回 0（终端代价时再算）
        """
        if not self._integrate_over_time or self._expr_with_control is None:
            return 0.0

        try:
            state_args = self._state_args(state)
            control_args = self._control_args(control)
            val = self._expr_with_control(*state_args, *control_args)
            val = np.asarray(val, dtype=float)

            if val.ndim == 0:
                return float(val) * self._dt
            else:
                return float(np.sum(val) * self._dx) * self._dt

        except Exception as e:
            print(f"[UnifiedExpressionCost] compute_running 异常: {type(e).__name__}: {e}")
            return 0.0

    def compute_terminal(self, state: np.ndarray) -> float:
        """终端代价。

        - integrate_over_time=False: 返回 expr（对 state 求值，不含 control）
        - integrate_over_time=True: 返回 0（运行代价时已经算了）
        """
        if self._integrate_over_time or self._expr_no_control is None:
            return 0.0

        try:
            state_args = self._state_args(state)
            val = self._expr_no_control(*state_args)
            val = np.asarray(val, dtype=float)

            if val.ndim == 0:
                return float(val)
            else:
                return float(np.sum(val) * self._dx)

        except Exception as e:
            print(f"[UnifiedExpressionCost] compute_terminal 异常: {type(e).__name__}: {e}")
            return 0.0