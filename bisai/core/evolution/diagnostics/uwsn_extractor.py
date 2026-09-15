"""UWSN 特化诊断提取器。

继承 BaseExtractor，添加 UWSN 特化的时间轨迹分析、切换分析、
参数逻辑分析和代价分解，对应原 diagnostic_extractor_v2.py。
"""

from __future__ import annotations

import numpy as np

from core.evolution.diagnostics.base_extractor import BaseExtractor


class UWSNExtractor(BaseExtractor):
    """UWSN 特化诊断提取器。"""

    def analyze_time_trajectory(
        self,
        state_history: np.ndarray,
        time_array: np.ndarray,
    ) -> str:
        """分析关键状态的时间轨迹特征。"""
        lines = ["=== Time Trajectory Analysis ==="]
        # 分析 Iu 和 Ia 的时空演化
        for name in ("Iu", "Ia"):
            idx = self._state_index.get(name)
            if idx is None:
                continue
            vals = state_history[:, :, idx]
            spatial_mean = np.mean(vals, axis=1)
            spatial_max = np.max(vals, axis=1)
            lines.append(
                f"  {name}: mean_start={spatial_mean[0]:.4f}, "
                f"mean_end={spatial_mean[-1]:.4f}, "
                f"max_start={spatial_max[0]:.4f}, "
                f"max_end={spatial_max[-1]:.4f}"
            )
            # 检测振荡
            if len(spatial_mean) > 10:
                diffs = np.diff(spatial_mean[-50:])
                zero_crossings = np.sum(np.diff(np.sign(diffs)) != 0)
                lines.append(
                    f"    Oscillation (last 50): {zero_crossings} zero crossings"
                )
        return "\n".join(lines)

    def analyze_switching(
        self,
        control_history: np.ndarray,
    ) -> str:
        """分析 bang-bang 控制的切换行为。"""
        lines = ["=== Switching Analysis ==="]
        for i, name in enumerate(self.control_names):
            vals = control_history[:, :, i]
            # 计算切换次数（按空间平均）
            spatial_avg = np.mean(vals, axis=1)
            switches = int(np.sum(np.abs(np.diff(np.round(spatial_avg))) > 0.1))
            lines.append(
                f"  {name}: {switches} switches, "
                f"avg_active={float(np.mean(vals)):.3f}"
            )
        return "\n".join(lines)

    def analyze_cost_breakdown(
        self,
        state_history: np.ndarray,
        control_history: np.ndarray,
        time_array: np.ndarray,
    ) -> str:
        """分析各代价分量的贡献。"""
        lines = ["=== Cost Breakdown ==="]
        dx = self.dx
        dt = time_array[1] - time_array[0] if len(time_array) > 1 else 0.01

        # 状态偏差代价
        for name, target in self.target_values.items():
            idx = self._state_index.get(name)
            if idx is None:
                continue
            deviations = state_history[:, :, idx] - target
            total = float(np.trapz(np.mean(deviations ** 2, axis=1), time_array) * dx)
            lines.append(f"  State {name} deviation cost: {total:.4f}")

        # 控制代价
        for i, name in enumerate(self.control_names):
            total = float(
                np.trapz(np.mean(control_history[:, :, i], axis=1), time_array) * dx
            )
            if total > 0.01:
                lines.append(f"  Control {name} cost: {total:.4f}")

        return "\n".join(lines)
