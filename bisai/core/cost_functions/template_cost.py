"""TemplateCost：基于 scene_config 模板的通用代价函数。

从 scene_config['cost'] 中读取 state_terms 和 control_terms 的权重与目标值，
动态构建运行代价和终端代价，支持 UWSN、SIR、直流电机等任意领域。
"""

from __future__ import annotations

import numpy as np

from core.base.base_cost import BaseCost


class TemplateCost(BaseCost):
    """模板代价函数：通过 scene_config JSON 指定代价项。

    运行代价 J_running = Σ [ w_i * (state[i] - target_i)² ] + Σ [ c_j * control[j]² ]
    终端代价 J_terminal = Σ [ w_i * (state[i] - target_i)² ]
    所有代价按空间积分 dx 和时间积分 dt 缩放。
    """

    def __init__(self, scene_config: dict) -> None:
        super().__init__(scene_config)

        # 兼容两种命名：cost_function（新）或 cost（旧）
        cost_cfg = scene_config.get("cost_function") or scene_config.get("cost", {})
        state_names: list[str] = scene_config.get("state_names", [])
        control_names: list[str] = scene_config.get("control_names", [])

        # 构建状态名 → 索引 映射
        self._state_index: dict[str, int] = {name: i for i, name in enumerate(state_names)}
        self._control_index: dict[str, int] = {name: i for i, name in enumerate(control_names)}

        # 解析目标值
        target_vals: dict[str, float] = scene_config.get("target_values", {})

        # —— 兼容 flat cost_weights：如果没有 cost_function.running_cost 则从 cost_weights 构建 ——
        running = cost_cfg.get("running_cost", {})
        if not running.get("state_terms") and not running.get("control_terms"):
            # 尝试从顶层 cost_weights 读取 flat 格式
            flat_weights = scene_config.get("cost_weights", {})
            if flat_weights:
                # 将 flat weights 转换为 state_terms 格式
                state_terms = {name: {"weight": w, "target": name} for name, w in flat_weights.items() if name in state_names}
                control_terms = {name: {"weight": w} for name, w in flat_weights.items() if name in control_names}
                if state_terms or control_terms:
                    running = {"state_terms": state_terms, "control_terms": control_terms}
                    # 🆕 终端代价 = 运行状态代价 × 10（更有力地推动末态收敛）
                    terminal_state_terms = {
                        name: {"weight": spec["weight"] * 10, "target": spec["target"]}
                        for name, spec in state_terms.items()
                    }
                    cost_cfg = {
                        "running_cost": running,
                        "terminal_cost": {"state_terms": terminal_state_terms},
                    }

        # —— 解析运行代价 ——
        self._run_state_terms: list[tuple[int, float, float]] = []  # (idx, weight, target)
        for name, spec in running.get("state_terms", {}).items():
            idx = self._state_index.get(name)
            if idx is None:
                continue
            target_name = spec.get("target", name)
            target = target_vals.get(target_name, 0.0)
            weight = float(spec.get("weight", 1.0))
            self._run_state_terms.append((idx, weight, target))

        self._run_control_terms: list[tuple[int, float]] = []  # (idx, weight)
        for name, spec in running.get("control_terms", {}).items():
            idx = self._control_index.get(name)
            if idx is None:
                continue
            weight = float(spec.get("weight", 1.0))
            self._run_control_terms.append((idx, weight))

        # —— 解析终端代价 ——
        terminal = cost_cfg.get("terminal_cost", {})
        self._term_state_terms: list[tuple[int, float, float]] = []
        for name, spec in terminal.get("state_terms", {}).items():
            idx = self._state_index.get(name)
            if idx is None:
                continue
            target_name = spec.get("target", name)
            target = target_vals.get(target_name, 0.0)
            weight = float(spec.get("weight", 1.0))
            self._term_state_terms.append((idx, weight, target))

        # —— 空间步长 ——
        spatial = scene_config.get("spatial", {})
        self._dx: float = spatial.get("dx") or 1.0
        temporal = scene_config.get("temporal", {}) or {}  # 🆕 加这一行
        dt_val = temporal.get("dt")
        self._dt: float = float(dt_val) if dt_val is not None else 1.0

    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """计算单步运行代价。

        对 PDE 模型：state/control shape 为 (M+1, dim)，
        代价 = Σ [ w*(s - t)² ] * dx + Σ [ c * u² ] * dx，再乘以 dt。
        """
        cost = 0.0

        # 状态偏差代价
        for idx, weight, target in self._run_state_terms:
            deviation = state[:, idx] - target
            cost += weight * np.sum(deviation ** 2) * self._dx

        # 控制代价
        for idx, weight in self._run_control_terms:
            cost += weight * np.sum(control[:, idx] ** 2) * self._dx

        return cost * self._dt

    def compute_terminal(self, state: np.ndarray) -> float:
        """计算终端代价（仿真结束时调用一次）。

        仅包含状态偏差，dt = 1（终端不需要时间积分）。
        """
        cost = 0.0
        for idx, weight, target in self._term_state_terms:
            deviation = state[:, idx] - target
            cost += weight * np.sum(deviation ** 2) * self._dx
        return cost
