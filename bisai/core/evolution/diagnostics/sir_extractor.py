"""SIR 模型诊断指标提取器。

从 SIR 仿真轨迹中提取关键流行病学指标：
  - 峰值感染数、峰值时间
  - 最终感染规模、隔离效果
  - 基本再生数估计
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.evolution.diagnostics.base_extractor import BaseExtractor


class SIRExtractor(BaseExtractor):
    """SIR 模型专用指标提取器。"""

    def extract_metrics(
        self,
        state_history: np.ndarray,
        control_history: np.ndarray,
        time_array: np.ndarray,
    ) -> dict[str, Any]:
        """提取 SIR 关键指标。

        Args:
            state_history: shape (N, M+1, 4) — S, I, R, Q
                           (ODE 时 M+1 = 1)
            control_history: shape (N, M+1, 2) — u1, u2
            time_array: shape (N,)

        Returns:
            包含峰值、最终规模、控制效果等指标的字典。
        """
        metrics: dict[str, Any] = {}

        # 🆕 处理 3D shape (N, M+1, state_dim)，ODE 取第 0 个空间点
        if state_history.ndim == 3:
            S = state_history[:, 0, 0]
            I = state_history[:, 0, 1]
            R = state_history[:, 0, 2]
            Q = state_history[:, 0, 3]
        else:
            S = state_history[:, 0]
            I = state_history[:, 1]
            R = state_history[:, 2]
            Q = state_history[:, 3]

        if control_history.ndim == 3:
            u1 = control_history[:, 0, 0]  # 隔离
            u2 = control_history[:, 0, 1]  # 治疗
        else:
            u1 = control_history[:, 0]
            u2 = control_history[:, 1]

        # 峰值感染
        peak_I = float(np.max(I))
        peak_time = float(time_array[np.argmax(I)])
        metrics["peak_infection"] = peak_I
        metrics["peak_time"] = peak_time

        # 最终规模
        final_S = float(S[-1])
        final_I = float(I[-1])
        final_R = float(R[-1])
        final_Q = float(Q[-1])
        metrics["final_susceptible"] = final_S
        metrics["final_infected"] = final_I
        metrics["final_recovered"] = final_R
        metrics["final_quarantined"] = final_Q

        # 控制效果
        total_isolation = float(np.sum(u1))
        total_treatment = float(np.sum(u2))
        metrics["total_isolation_effort"] = total_isolation
        metrics["total_treatment_effort"] = total_treatment

        # 基本再生数估计（粗略）
        # R0 ≈ β / γ（无控制时）
        beta = self.scene_config.get("physical_params", {}).get("beta", 0.3)
        gamma = self.scene_config.get("physical_params", {}).get("gamma", 0.1)
        R0_est = beta / gamma if gamma > 0 else float("inf")
        metrics["R0_estimate"] = R0_est

        # 异常检测
        anomalies: list[str] = []
        if peak_I > 500:
            anomalies.append("峰值感染数过高 (>500)")
        if final_I > 10:
            anomalies.append("最终仍有感染者未清零")
        if total_isolation < 1.0:
            anomalies.append("隔离措施几乎未使用")
        metrics["anomalies"] = anomalies

        return metrics

    def format_metrics_for_llm(self, metrics: dict[str, Any]) -> str:
        """格式化为 LLM 友好的文本。"""
        lines = [
            f"峰值感染: {metrics.get('peak_infection', 0):.1f} (t={metrics.get('peak_time', 0):.1f})",
            f"最终规模: S={metrics.get('final_susceptible', 0):.1f}, "
            f"I={metrics.get('final_infected', 0):.1f}, "
            f"R={metrics.get('final_recovered', 0):.1f}, "
            f"Q={metrics.get('final_quarantined', 0):.1f}",
            f"控制努力: 隔离={metrics.get('total_isolation_effort', 0):.1f}, "
            f"治疗={metrics.get('total_treatment_effort', 0):.1f}",
            f"R0 估计: {metrics.get('R0_estimate', 0):.2f}",
        ]
        anomalies = metrics.get("anomalies", [])
        if anomalies:
            lines.append("异常: " + "; ".join(anomalies))
        return "\n".join(lines)