"""ExpressionCost：基于 SymPy 符号表达式的代价函数。

从 scene_config 中读取符号表达式字符串，使用 SymPy 的 lambdify 预编译为
numpy 函数，支持 ODE（一维状态）和 PDE（二维状态场）两类模型。
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from core.base.base_cost import BaseCost


class ExpressionCost(BaseCost):
    """符号表达式代价函数。

    scene_config['cost_function'] 格式示例:
    {
        "cost_type": "expression",
        "running_expr": "0.5*(S-1000)**2 + 10*I + 0.1*u1",
        "terminal_expr": "100*(S-1000)**2 + 50*I",
        "symbols": {"state": ["S", "I", "R", "Q"], "control": ["u1", "u2"]}
    }

    运行代价 J_running = ∫∫ expr dx dt
    终端代价 J_terminal = ∫ expr dx (仅在 t=T 时计算一次)
    """

    def __init__(self, scene_config: dict) -> None:
        super().__init__(scene_config)

        # 兼容两种命名：cost_function（新）或 cost（旧）
        cost_cfg = scene_config.get("cost_function") or scene_config.get("cost", {})

        # 符号定义
        symbols_cfg = cost_cfg.get("symbols", {})
        state_names = symbols_cfg.get("state", scene_config.get("state_names", []))
        control_names = symbols_cfg.get("control", scene_config.get("control_names", []))

        self._state_names = list(state_names)
        self._control_names = list(control_names)
        self._state_syms = [sp.Symbol(name) for name in self._state_names]
        self._control_syms = [sp.Symbol(name) for name in self._control_names]

        # 解析运行代价表达式并预编译
        running_expr_str = cost_cfg.get("running_expr", "")
        if running_expr_str:
            local_dict = {name: sp.Symbol(name) for name in self._state_names + self._control_names}
            self._running_expr = sp.sympify(running_expr_str, locals=local_dict)
            try:
                self._running_func = sp.lambdify(
                    self._state_syms + self._control_syms,
                    self._running_expr,
                    modules=["numpy"],
                )
            except Exception as e:
                print(f"[ExpressionCost] running_expr lambdify 失败: {e}")
                self._running_func = None
        else:
            self._running_expr = None
            self._running_func = None

        # 解析终端代价表达式并预编译
        terminal_expr_str = cost_cfg.get("terminal_expr", "")
        if terminal_expr_str and cost_cfg.get("has_terminal_cost", True):
            local_dict = {name: sp.Symbol(name) for name in self._state_names + self._control_names}
            self._terminal_expr = sp.sympify(terminal_expr_str, locals=local_dict)
            try:
                self._terminal_func = sp.lambdify(
                    self._state_syms,
                    self._terminal_expr,
                    modules=["numpy"],
                )
            except Exception as e:
                print(f"[ExpressionCost] terminal_expr lambdify 失败: {e}")
                self._terminal_func = None
        else:
            self._terminal_expr = None
            self._terminal_func = None

        # 时间/空间步长
        temporal = scene_config.get("temporal", {})
        dt_val = temporal.get("dt")
        self._dt: float = float(dt_val) if dt_val is not None else 1.0
        spatial = scene_config.get("spatial", {})
        self._dx: float = spatial.get("dx") or 1.0

    # ---------- 内部工具 ----------

    def _to_2d(self, arr: np.ndarray) -> np.ndarray:
        """把一维数组变成 (1, dim)，已经是二维则原样返回"""
        arr = np.asarray(arr, dtype=float)
        if arr.ndim == 1:
            return arr.reshape(1, -1)
        return arr

    def _state_args(self, state: np.ndarray) -> list:
        """从 state 提取每个符号对应的列向量"""
        state = self._to_2d(state)
        return [state[:, i] for i in range(len(self._state_syms))]

    def _control_args(self, control: np.ndarray) -> list:
        """从 control 提取每个符号对应的列向量"""
        control = self._to_2d(control)
        return [control[:, i] for i in range(len(self._control_syms))]

    # ---------- BaseCost 接口 ----------

    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """计算单步运行代价。

        - ODE：state = (1, state_dim)，对单点求值，乘 dt
        - PDE：state = (M+1, state_dim)，对空间场求值，乘 dx 再乘 dt
        """
        if self._running_func is None:
            return 0.0

        try:
            state_args = self._state_args(state)
            control_args = self._control_args(control)

            val = self._running_func(*state_args, *control_args)
            val = np.asarray(val, dtype=float)

            # ODE: val 是标量或 (1,)；PDE: val 是 (M+1,)
            if val.ndim == 0:
                return float(val) * self._dt
            else:
                return float(np.sum(val) * self._dx) * self._dt

        except Exception as e:
            print(f"[ExpressionCost] compute_running 异常: {type(e).__name__}: {e}")
            return 0.0

    def compute_terminal(self, state: np.ndarray) -> float:
        """计算终端代价。

        - ODE：单点求值
        - PDE：对空间场求值并积分（乘 dx）
        """
        if self._terminal_func is None:
            return 0.0

        try:
            state_args = self._state_args(state)
            val = self._terminal_func(*state_args)
            val = np.asarray(val, dtype=float)

            if val.ndim == 0:
                return float(val)
            else:
                return float(np.sum(val) * self._dx)

        except Exception as e:
            print(f"[ExpressionCost] compute_terminal 异常: {type(e).__name__}: {e}")
            return 0.0