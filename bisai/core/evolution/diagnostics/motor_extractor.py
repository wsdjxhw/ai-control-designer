"""直流电机诊断指标提取器。

从电机仿真轨迹中提取关键性能指标：
  - 稳态转速、超调量、调节时间
  - 电流峰值、能量消耗
  - 跟踪误差（如果有参考信号）
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.evolution.diagnostics.base_extractor import BaseExtractor


class MotorExtractor(BaseExtractor):
    """直流电机专用指标提取器。"""

    def extract_metrics(
        self,
        state_history: np.ndarray,
        control_history: np.ndarray,
        time_array: np.ndarray,
    ) -> dict[str, Any]:
        """提取电机关键指标。

        Args:
            state_history: shape (N, M+1, 2) — omega, current
                           (ODE 时 M+1 = 1)
            control_history: shape (N, M+1, 1) — voltage
            time_array: shape (N,)

        Returns:
            包含稳态、动态响应、能耗等指标的字典。
        """
        metrics: dict[str, Any] = {}

        # 🆕 处理 3D shape (N, M+1, state_dim)，ODE 取第 0 个空间点
        if state_history.ndim == 3:
            omega = state_history[:, 0, 0]
            current = state_history[:, 0, 1]
        else:
            omega = state_history[:, 0]
            current = state_history[:, 1]

        if control_history.ndim == 3:
            voltage = control_history[:, 0, 0]
        else:
            voltage = control_history[:, 0]

        # 稳态值（最后 10% 时间平均）
        n_steady = max(1, len(omega) // 10)
        steady_omega = float(np.mean(omega[-n_steady:]))
        steady_current = float(np.mean(current[-n_steady:]))
        metrics["steady_omega"] = steady_omega
        metrics["steady_current"] = steady_current

        # 峰值电流
        peak_current = float(np.max(np.abs(current)))
        metrics["peak_current"] = peak_current

        # 超调量（假设目标转速为 100 rad/s，可从 scene_config 读取）
        target_omega = self.scene_config.get("target_values", {}).get("omega", 100.0)
        overshoot = max(0.0, (np.max(omega) - target_omega) / target_omega * 100)
        metrics["overshoot_percent"] = overshoot

        # 调节时间（进入 ±5% 带内的时间）
        band = 0.05 * target_omega
        settling_idx = np.where(np.abs(omega - target_omega) <= band)[0]
        if len(settling_idx) > 0:
            settling_time = float(time_array[settling_idx[0]])
        else:
            settling_time = float(time_array[-1])
        metrics["settling_time"] = settling_time

        # 能量消耗（∫|voltage|*current dt 的近似）
        dt = self.scene_config.get("temporal", {}).get("dt", 0.01)
        energy = float(np.sum(np.abs(voltage) * np.abs(current)) * dt)
        metrics["energy_consumption"] = energy

        # 异常检测
        anomalies: list[str] = []
        if peak_current > 50:
            anomalies.append("峰值电流过高 (>50A)")
        if overshoot > 30:
            anomalies.append("超调量过大 (>30%)")
        if settling_time > 3.0:
            anomalies.append("调节时间过长 (>3s)")
        if energy > 1000:
            anomalies.append("能耗过高")
        metrics["anomalies"] = anomalies

        return metrics

    def format_metrics_for_llm(self, metrics: dict[str, Any]) -> str:
        """格式化为 LLM 友好的文本。"""
        lines = [
            f"稳态转速: {metrics.get('steady_omega', 0):.2f} rad/s",
            f"稳态电流: {metrics.get('steady_current', 0):.2f} A",
            f"峰值电流: {metrics.get('peak_current', 0):.2f} A",
            f"超调量: {metrics.get('overshoot_percent', 0):.1f}%",
            f"调节时间: {metrics.get('settling_time', 0):.2f} s",
            f"能耗: {metrics.get('energy_consumption', 0):.1f} J",
        ]
        anomalies = metrics.get("anomalies", [])
        if anomalies:
            lines.append("异常: " + "; ".join(anomalies))
        return "\n".join(lines)