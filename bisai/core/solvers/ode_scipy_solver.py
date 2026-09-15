"""SciPy ODE 求解器，用于 ODE 模型（SIR、直流电机等）。

使用 scipy.integrate.solve_ivp（RK45 自适应步长）。
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.integrate import solve_ivp

from core.base.base_model import BaseModel
from core.base.base_solver import BaseSolver


class ODE_Scipy_Solver(BaseSolver):
    """ODE 数值求解器（solve_ivp / RK45）。

    状态 shape 为 (state_dim,) 的一维数组。
    """

    def __init__(
        self,
        method: str = "RK45",
        rtol: float = 1e-6,
        atol: float = 1e-9,
        max_step: float | None = None,
    ) -> None:
        self.method = method
        self.rtol = rtol
        self.atol = atol
        self.max_step = max_step

    def step(
        self,
        model: BaseModel,
        state: np.ndarray,
        control: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """单步积分：从当前状态推进 dt 时间。

        控制在整个 dt 区间内保持恒定。
        """
        control_vec = np.asarray(control, dtype=float).reshape(-1)

        def rhs_wrapper(t: float, y: np.ndarray) -> np.ndarray:
            return model.rhs(t, y, control_vec)

        options: dict = {
            "method": self.method,
            "rtol": self.rtol,
            "atol": self.atol,
        }
        if self.max_step is not None:
            options["max_step"] = self.max_step
        sol = solve_ivp(
            rhs_wrapper,
            (0.0, dt),
            np.asarray(state, dtype=float),
            **options,
        )
        new_state = sol.y[:, -1]
        return np.maximum(new_state, 0.0)

    def solve(
        self,
        model: BaseModel,
        t_span: tuple[float, float],
        dt: float,
        control_func: Callable[[float, np.ndarray], np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """完整仿真。

        Args:
            model: ODE 模型.
            t_span: (t_start, t_end).
            dt: 输出采样步长（solve_ivp 内部仍为自适应步长）.
            control_func: control(t, state) -> shape (control_dim,).

        Returns:
            (time_array, state_history, control_history)
            - time_array: shape (N,)
            - state_history: shape (N, state_dim)
            - control_history: shape (N, control_dim)
        """
        t0, t_end = t_span
        t_eval = np.arange(t0, t_end + dt / 2.0, dt)
        state0 = np.asarray(model.get_initial_state(), dtype=float)

        def rhs_wrapper(t: float, y: np.ndarray) -> np.ndarray:
            u = control_func(t, y)
            u = np.asarray(u, dtype=float).reshape(-1)
            return model.rhs(t, y, u)

        options: dict = {
            "method": self.method,
            "rtol": self.rtol,
            "atol": self.atol,
        }
        if self.max_step is not None:
            options["max_step"] = self.max_step
        sol = solve_ivp(
            rhs_wrapper,
            (t0, t_end),
            state0,
            t_eval=t_eval,
            **options,
        )

        state_hist = sol.y.T  # (T, state_dim)
        control_hist = np.array([
            np.asarray(control_func(t, s), dtype=float).reshape(-1)
            for t, s in zip(sol.t, state_hist)
        ])
        return sol.t, state_hist, control_hist

    def __repr__(self) -> str:
        return f"ODE_Scipy_Solver(method={self.method})"
