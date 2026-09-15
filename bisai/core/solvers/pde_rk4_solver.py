"""RK4 数值求解器，专为 PDE 空间离散系统设计。

在标准 RK4 的每个阶段调用 model.rhs() 获取完整 RHS，
步末执行 Neumann 边界条件赋值。

同时提供 Numba 加速版本用于大规模仿真。
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from core.base.base_solver import BaseSolver
from core.base.base_model import BaseModel


def _apply_neumann_bc(state: np.ndarray) -> None:
    """就地应用 Neumann 边界条件（复制相邻内点值）。"""
    state[0, :] = state[1, :]
    state[-1, :] = state[-2, :]


class PDE_RK4_Solver(BaseSolver):
    """显式 RK4 求解器，用于空间离散 PDE 的时间积分。

    在每步中调用 model.rhs() 四次（RK4 四个阶段），
    每次调用时 Laplacian 基于当前阶段的中间状态重新计算。
    """

    def step(
        self,
        model: BaseModel,
        state: np.ndarray,
        control: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """单步 RK4 积分。

        Args:
            model: 动力学模型，其 rhs() 接收 (t, state, control) 并返回导数。
            state: 当前状态, shape (M+1, state_dim).
            control: 当前控制输入, shape (M+1, control_dim).
            dt: 时间步长。

        Returns:
            下一时刻状态, shape (M+1, state_dim).
        """
        k1 = model.rhs(0.0, state, control)
        k2 = model.rhs(0.5 * dt, state + 0.5 * dt * k1, control)
        k3 = model.rhs(0.5 * dt, state + 0.5 * dt * k2, control)
        k4 = model.rhs(dt, state + dt * k3, control)

        new_state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        new_state = np.maximum(new_state, 0.0)
        _apply_neumann_bc(new_state)
        return new_state

    def solve(
        self,
        model: BaseModel,
        t_span: tuple[float, float],
        dt: float,
        control_func: Callable[[float, np.ndarray], np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """完整仿真。

        Args:
            model: 动力学模型.
            t_span: (t_start, t_end).
            dt: 时间步长.
            control_func: control(t, state) -> shape (M+1, control_dim).

        Returns:
            (time_array, state_history, control_history)
            - time_array: shape (N,)
            - state_history: shape (N, M+1, state_dim)
            - control_history: shape (N, M+1, control_dim)
        """
        t0, t_end = t_span
        n_steps = int(round((t_end - t0) / dt))
        state = model.get_initial_state().copy()

        save_interval = max(1, n_steps // 1000)
        n_saved = n_steps // save_interval + 1
        M_plus1 = state.shape[0]
        state_dim = state.shape[1]
        control_dim = control_func(t0, state).shape[1]

        time_arr = np.zeros(n_saved)
        state_hist = np.zeros((n_saved, M_plus1, state_dim))
        control_hist = np.zeros((n_saved, M_plus1, control_dim))

        save_idx = 0
        time_arr[0] = t0
        state_hist[0] = state
        control_hist[0] = control_func(t0, state)

        for step in range(1, n_steps + 1):
            t = t0 + step * dt
            control = control_func(t, state)
            state = self.step(model, state, control, dt)

            if step % save_interval == 0 or step == n_steps:
                save_idx += 1
                time_arr[save_idx] = t
                state_hist[save_idx] = state
                control_hist[save_idx] = control

        time_arr = time_arr[: save_idx + 1]
        state_hist = state_hist[: save_idx + 1]
        control_hist = control_hist[: save_idx + 1]

        return time_arr, state_hist, control_hist

    def __repr__(self) -> str:
        return "PDE_RK4_Solver(explicit RK4, Neumann BC)"
