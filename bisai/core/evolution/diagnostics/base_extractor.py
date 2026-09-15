"""通用指标提取和诊断数据准备。"""

from __future__ import annotations

from typing import Any

import numpy as np


class BaseExtractor:
    """通用指标提取器。

    从仿真结果中提取状态偏差、控制使用量、异常信号等指标，
    通过 scene_config['state_names'] 和 ['target_values'] 实现动态映射。
    """

    def __init__(self, scene_config: dict) -> None:
        self.scene_config = scene_config
        self.state_names: list[str] = scene_config.get("state_names", [])
        self.control_names: list[str] = scene_config.get("control_names", [])
        self.target_values: dict[str, float] = scene_config.get("target_values", {})
        self.spatial = scene_config.get("spatial", {})
        self.dx: float = self.spatial.get("dx") or 1.0

        self._state_index: dict[str, int] = {
            name: i for i, name in enumerate(self.state_names)
        }
        self._control_index: dict[str, int] = {
            name: i for i, name in enumerate(self.control_names)
        }

    def extract_metrics(
        self,
        state_history: np.ndarray,
        control_history: np.ndarray,
        time_array: np.ndarray,
    ) -> dict[str, Any]:
        """提取通用指标。

        Args:
            state_history: shape (T, M+1, state_dim).
            control_history: shape (T, M+1, control_dim).
            time_array: shape (T,).

        Returns:
            包含状态偏差、控制统计、异常检测的字典。
        """
        metrics: dict[str, Any] = {
            "state_stats": {},
            "control_stats": {},
            "anomalies": [],
        }

        # 状态偏差指标
        for name, target in self.target_values.items():
            idx = self._state_index.get(name)
            if idx is None:
                continue
            deviations = state_history[:, :, idx] - target
            metrics["state_stats"][name] = {
                "final_mean": float(np.mean(state_history[-1, :, idx])),
                "final_deviation": float(np.mean(np.abs(deviations[-1, :]))),
                "max_deviation": float(np.max(np.abs(deviations))),
                "integrated": float(
                    np.trapz(np.mean(deviations ** 2, axis=1), time_array)
                ),
            }

        # 控制统计
        for i, name in enumerate(self.control_names):
            control_usage = control_history[:, :, i]
            metrics["control_stats"][name] = {
                "mean_usage": float(np.mean(control_usage)),
                "max_usage": float(np.max(control_usage)),
                "total_integrated": float(
                    np.trapz(np.mean(control_usage, axis=1), time_array) * self.dx
                ),
            }

        # 异常检测
        for i, name in enumerate(self.state_names):
            vals = state_history[:, :, i]
            if np.any(np.isnan(vals)):
                metrics["anomalies"].append(f"NaN detected in state {name}")
            if np.any(vals > 1e4):
                metrics["anomalies"].append(
                    f"State explosion in {name}: max={float(np.max(vals)):.2f}"
                )

        return metrics

    def format_metrics_for_llm(self, metrics: dict[str, Any]) -> str:
        """将指标格式化为 LLM 可读的文本。"""
        lines = ["=== Evolution Metrics ==="]
        for name, stats in metrics.get("state_stats", {}).items():
            lines.append(
                f"  State {name}: final_mean={stats['final_mean']:.4f}, "
                f"final_dev={stats['final_deviation']:.4f}, "
                f"max_dev={stats['max_deviation']:.4f}, "
                f"integrated_dev={stats['integrated']:.4f}"
            )
        for name, stats in metrics.get("control_stats", {}).items():
            lines.append(
                f"  Control {name}: mean={stats['mean_usage']:.4f}, "
                f"total={stats['total_integrated']:.4f}"
            )
        if metrics.get("anomalies"):
            lines.append("Anomalies detected:")
            for a in metrics["anomalies"]:
                lines.append(f"  ⚠ {a}")
        return "\n".join(lines)
