"""UWSN (Underwater Wireless Sensor Network) 动力学模型。

10 维反应-扩散 PDE 模型，6 维 bang-bang 控制输入。
状态定义为 (M+1, 10) 的时空网格，其中 M+1 是空间离散点数。

状态分量:
  0: Su   - UWSN 易感节点
  1: Iu   - UWSN 感染节点
  2: Ru   - UWSN 恢复节点
  3: LSu  - UWSN 低能量易感节点
  4: LIu  - UWSN 低能量感染节点
  5: LRu  - UWSN 低能量恢复节点
  6: Sa   - AUV 易感节点
  7: Ia   - AUV 感染节点
  8: Ra   - AUV 恢复节点
  9: Sus  - UWSN 睡眠节点

控制分量:
  0: u1 (α3) - Su→Ru 预防性治疗, {0, 1}
  1: u2 (β3) - Sa→Ra AUV 治疗, {0, 1}
  2: u3 (γ2) - 低能量节点唤醒, {0, 1}
  3: u4      - Iu→Ru 强化治疗, {0, 0.5}
  4: u5      - Ia→Ra AUV 强化治疗, {0, 0.5}
  5: u6      - Su→Sus 强制休眠, {0, 0.5}
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.base.base_model import BaseModel


# ===================== 辅助函数 =====================

def laplacian(U: np.ndarray, dx: float) -> np.ndarray:
    """一维拉普拉斯算子（二阶中心差分），Neumann 边界条件。"""
    lap = np.zeros_like(U, dtype=np.float64)
    lap[1:-1] = (U[:-2] - 2 * U[1:-1] + U[2:]) / (dx * dx)
    lap[0] = lap[1]
    lap[-1] = lap[-2]
    return lap


def compute_propagation_rates(
    x: np.ndarray,
    scene_config: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """计算传播率 K1, K2, K12, K21 的空间分布。"""
    rates_cfg = scene_config.get("propagation_rates", {})

    def _make_rate(key: str) -> np.ndarray:
        cfg = rates_cfg.get(key, {"base": 0.0, "modulation": 0.0, "phase": 0})
        base = cfg["base"]
        mod = cfg.get("modulation", 0.0)
        phase = np.pi if cfg.get("phase") == "pi" else 0.0
        return base + base * mod * np.cos(x + phase)

    return (
        _make_rate("K1"),
        _make_rate("K2"),
        _make_rate("K12"),
        _make_rate("K21"),
    )


# ===================== UWSN Model =====================

class UWSNModel(BaseModel):
    """UWSN 反应-扩散 PDE 模型。"""

    def __init__(self, scene_config: dict) -> None:
        super().__init__()
        self._scene_config = scene_config

        spatial = scene_config.get("spatial", {})
        self.X: float = spatial.get("X", 2.0)
        self.dx: float = spatial.get("dx", 0.01)
        self.M: int = int(round(self.X / self.dx))

        temporal = scene_config.get("temporal", {})
        self.T: float = temporal.get("T", 3.0)
        self.dt: float = temporal.get("dt", 5e-5)
        self.N: int = int(round(self.T / self.dt))

        phys = scene_config.get("physical_params", {})
        self.Du: float = phys.get("Du", 0.001)
        self.Da: float = phys.get("Da", 0.001)
        self.LA1: float = phys.get("LA1", 0.08)
        self.LA2: float = phys.get("LA2", 0.02)
        self.alpha1: float = phys.get("alpha1", 0.4)
        self.alpha2: float = phys.get("alpha2", 0.6)
        self.beta1: float = phys.get("beta1", 0.2)
        self.beta2: float = phys.get("beta2", 0.5)
        self.d1: float = phys.get("d1", 0.0005)
        self.d2: float = phys.get("d2", 0.0005)
        self.gamma1: float = phys.get("gamma1", 0.1)
        self.gamma3: float = phys.get("gamma3", 0.3)
        self.gamma4: float = phys.get("gamma4", 0.3)

        self.x_grid: np.ndarray = np.linspace(0, self.X, self.M + 1)
        self.K1, self.K2, self.K12, self.K21 = compute_propagation_rates(
            self.x_grid, scene_config
        )

        state_names = scene_config.get("state_names", [])
        self._state_dim: int = len(state_names) if state_names else 10
        self._control_dim: int = len(scene_config.get("control_names", [])) or 6

    # ---- BaseModel 接口实现 ----

    @property
    def state_dim(self) -> int:
        return self._state_dim

    @property
    def control_dim(self) -> int:
        return self._control_dim

    def get_initial_state(self) -> np.ndarray:
        """生成高斯脉冲初始状态，shape (M+1, 10)."""
        init_cfg = self._scene_config.get("initial_state", {}).get("params", {})
        M_plus1 = self.M + 1
        state = np.zeros((M_plus1, 10))
        Su_bg = init_cfg.get("Su_background", 0.5)
        Iu_amp = init_cfg.get("Iu_amplitude", 0.1)
        Ia_amp = init_cfg.get("Ia_amplitude", 0.05)
        xc = self.X * init_cfg.get("pulse_center_ratio", 0.25)
        sigma = self.X * init_cfg.get("pulse_width_ratio", 0.05)
        state[:, 0] = Su_bg
        state[:, 1] = Iu_amp * np.exp(-((self.x_grid - xc) ** 2) / (2 * sigma ** 2))
        state[:, 7] = Ia_amp * np.exp(-((self.x_grid - xc) ** 2) / (2 * sigma ** 2))
        return state

    def rhs(self, t: float, state: np.ndarray, control: np.ndarray) -> np.ndarray:
        """计算 10 维 PDE 右端项。

        Args:
            t: 当前时间（未使用但遵循接口）。
            state: shape (M+1, 10).
            control: shape (M+1, 6).

        Returns:
            shape (M+1, 10).
        """
        ds = np.zeros_like(state)
        for i in range(10):
            lap = laplacian(state[:, i], self.dx)
            ds[:, i] = (self.Du if i < 6 else self.Da) * lap

        Su, Iu, Ru = state[:, 0], state[:, 1], state[:, 2]
        LSu, LIu, LRu = state[:, 3], state[:, 4], state[:, 5]
        Sa, Ia, Ra, Sus = state[:, 6], state[:, 7], state[:, 8], state[:, 9]
        u1, u2, u3, u4, u5, u6 = (control[:, j] for j in range(6))
        K1, K2, K12, K21 = self.K1, self.K2, self.K12, self.K21

        ds[:, 0] += (self.LA1 - K1 * Su * Iu - K21 * Su * Ia
                      - self.gamma1 * Su + self.alpha2 * Ru + u3 * LSu
                      - self.d1 * Su - u1 * Su - self.gamma3 * Su - u6 * Su + self.gamma4 * Sus)
        ds[:, 1] += (K1 * Su * Iu + K21 * Su * Ia
                      - self.gamma1 * Iu + u3 * LIu - self.alpha1 * Iu - u4 * Iu - self.d1 * Iu)
        ds[:, 2] += (self.alpha1 * Iu + u4 * Iu - self.alpha2 * Ru
                      - self.gamma1 * Ru + u3 * LRu - self.d1 * Ru + u1 * Su)
        ds[:, 3] += self.gamma1 * Su - u3 * LSu - self.d1 * LSu
        ds[:, 4] += self.gamma1 * Iu - u3 * LIu - self.d1 * LIu
        ds[:, 5] += self.gamma1 * Ru - u3 * LRu - self.d1 * LRu
        ds[:, 6] += (self.LA2 - K2 * Sa * Ia - K12 * Sa * Iu
                      + self.beta2 * Ra - self.d2 * Sa - u2 * Sa)
        ds[:, 7] += (K2 * Sa * Ia + K12 * Sa * Iu
                      - self.beta1 * Ia - u5 * Ia - self.d2 * Ia)
        ds[:, 8] += (self.beta1 * Ia + u5 * Ia - self.beta2 * Ra
                      - self.d2 * Ra + u2 * Sa)
        ds[:, 9] += self.gamma3 * Su + u6 * Su - self.gamma4 * Sus - self.d1 * Sus
        return ds

    def validate_state(self, state: np.ndarray) -> bool:
        if np.isnan(state).any():
            return False
        if np.any(state > 1e5) or np.any(state < -1e3):
            return False
        return True

    @property
    def scene_config(self) -> dict:
        return self._scene_config

    @property
    def n_grid(self) -> int:
        return self.M + 1

    def __repr__(self) -> str:
        return f"UWSNModel(M={self.M}, N={self.N}, dx={self.dx}, dt={self.dt})"
