"""SIR-Q 流行病学模型。

4 维状态 (S, I, R, Q)，2 维 bang-bang 控制。
状态为 (state_dim,) 的一维 ODE 系统。

状态分量:
  0: S - 易感者
  1: I - 感染者
  2: R - 康复者
  3: Q - 隔离者

控制分量:
  0: u1 - 隔离措施（S→Q），{0, 1}
  1: u2 - 治疗措施（I→R），{0, 1}
"""

from __future__ import annotations

import numpy as np

from core.base.base_model import BaseModel


class SIRModel(BaseModel):
    """SIR-Q 流行病学 ODE 模型。"""

    def __init__(self, scene_config: dict) -> None:
        super().__init__()
        self._scene_config = scene_config

        temporal = scene_config.get("temporal", {})
        self.T: float = temporal.get("T", 30.0)
        self.dt: float = temporal.get("dt", 0.1)
        self.N: int = int(round(self.T / self.dt))

        phys = scene_config.get("physical_params", {})
        self.beta: float = phys.get("beta", 0.3)
        self.gamma: float = phys.get("gamma", 0.1)
        self.delta: float = phys.get("delta", 0.05)

        state_names = scene_config.get("state_names", [])
        self._state_dim: int = len(state_names) if state_names else 4
        self._control_dim: int = len(scene_config.get("control_names", [])) or 2

        # ODE 模型无空间网格，提供单点以兼容控制律接口
        self.x_grid: np.ndarray = np.array([0.0])
        self.dx: float = 1.0

    # ---- BaseModel 接口实现 ----

    @property
    def state_dim(self) -> int:
        return self._state_dim

    @property
    def control_dim(self) -> int:
        return self._control_dim

    def get_initial_state(self) -> np.ndarray:
        """初始状态：990 易感、10 感染、0 康复、0 隔离。"""
        init = self._scene_config.get("initial_state", {})
        return np.array([
            init.get("S0", 990.0),
            init.get("I0", 10.0),
            init.get("R0", 0.0),
            init.get("Q0", 0.0),
        ], dtype=float)

    def rhs(self, t: float, state: np.ndarray, control: np.ndarray) -> np.ndarray:
        """计算 SIR-Q 方程右端项。

        Args:
            t: 当前时间.
            state: shape (4,).
            control: shape (2,) 或 (control_dim,).

        Returns:
            shape (4,).
        """
        S, I, R, Q = state
        u1, u2 = np.asarray(control, dtype=float).reshape(-1)[:2]

        dS = -self.beta * S * I - u1 * S + self.delta * Q
        dI = self.beta * S * I - self.gamma * I - u2 * I
        dR = self.gamma * I + u2 * I
        dQ = u1 * S - self.delta * Q
        return np.array([dS, dI, dR, dQ])

    def validate_state(self, state: np.ndarray) -> bool:
        if np.isnan(state).any():
            return False
        if np.any(state > 1e6) or np.any(state < -1e3):
            return False
        return True

    @property
    def scene_config(self) -> dict:
        return self._scene_config

    def __repr__(self) -> str:
        return f"SIRModel(N={self.N}, dt={self.dt}, beta={self.beta}, gamma={self.gamma})"
