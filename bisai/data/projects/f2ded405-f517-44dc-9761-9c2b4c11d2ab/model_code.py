"""直流电机模型。

2 维状态 (omega, current)，1 维连续控制 (voltage)。
状态为 (state_dim,) 的一维 ODE 系统。

状态分量:
  0: omega   - 转速 (rad/s)
  1: current - 电枢电流 (A)

控制分量:
  0: voltage - 电枢电压 (V)，连续 [-Vmax, Vmax]
"""

from __future__ import annotations

import numpy as np

from core.base.base_model import BaseModel


class DCMotorModel(BaseModel):
    """直流电机 ODE 模型。"""

    def __init__(self, scene_config: dict) -> None:
        super().__init__()
        self._scene_config = scene_config

        temporal = scene_config.get("temporal", {})
        self.T: float = temporal.get("T", 5.0)
        self.dt: float = temporal.get("dt", 0.01)
        self.N: int = int(round(self.T / self.dt))

        phys = scene_config.get("physical_params", {})
        self.R: float = phys.get("R", 1.0)          # 电枢电阻
        self.L: float = phys.get("L", 0.05)         # 电枢电感
        self.Kt: float = phys.get("Kt", 1.0)        # 转矩常数
        self.Ke: float = phys.get("Ke", 1.0)        # 反电动势常数
        self.J: float = phys.get("J", 0.01)         # 转动惯量
        self.B: float = phys.get("B", 0.1)          # 粘滞摩擦
        self.T_load: float = phys.get("T_load", 0.0)  # 负载转矩

        state_names = scene_config.get("state_names", [])
        self._state_dim: int = len(state_names) if state_names else 2
        self._control_dim: int = len(scene_config.get("control_names", [])) or 1

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
        """初始状态：静止（omega=0, current=0）。"""
        init = self._scene_config.get("initial_state", {})
        return np.array([
            init.get("omega", init.get("omega0", 0.0)),
            init.get("current", init.get("current0", 0.0)),
        ], dtype=float)

    def rhs(self, t: float, state: np.ndarray, control: np.ndarray) -> np.ndarray:
        """计算直流电机方程右端项。

        Args:
            t: 当前时间.
            state: shape (2,).
            control: shape (1,) 或 (control_dim,).

        Returns:
            shape (2,).
        """
        omega, current = state
        voltage = float(np.asarray(control, dtype=float).reshape(-1)[0])

        d_omega = (self.Kt * current - self.B * omega - self.T_load) / self.J
        d_current = (voltage - self.R * current - self.Ke * omega) / self.L
        return np.array([d_omega, d_current])

    def validate_state(self, state: np.ndarray) -> bool:
        if np.isnan(state).any():
            return False
        if np.any(state > 1e6) or np.any(state < -1e6):
            return False
        return True

    @property
    def scene_config(self) -> dict:
        return self._scene_config

    def __repr__(self) -> str:
        return f"DCMotorModel(N={self.N}, dt={self.dt}, J={self.J}, R={self.R})"
