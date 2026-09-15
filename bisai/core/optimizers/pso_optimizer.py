"""PSOOptimizer：基于粒子群优化的参数优化器实现。"""

from __future__ import annotations

from typing import Callable

import numpy as np

from core.optimizers.base_optimizer import BaseOptimizer


class PSOOptimizer(BaseOptimizer):
    """粒子群优化器 (Particle Swarm Optimization)。

    算法原理：
    - 每个粒子有位置(position)和速度(velocity)
    - 位置更新: x = x + v
    - 速度更新: v = w*v + c1*r1*(pbest - x) + c2*r2*(gbest - x)
    - w: 惯性权重, c1: 个体学习因子, c2: 社会学习因子
    """

    def __init__(
        self,
        n_particles: int = 30,
        w: float = 0.7,
        c1: float = 1.5,
        c2: float = 1.5,
        max_iter: int = 100,
        **kwargs,
    ):
        """初始化 PSO 优化器。

        Args:
            n_particles: 粒子数量
            w: 惯性权重 (0.4-0.9)
            c1: 个体学习因子
            c2: 社会学习因子
            max_iter: 最大迭代次数
            **kwargs: 其他参数
        """
        self.n_particles = n_particles
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.max_iter = max_iter
        self.kwargs = kwargs

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """执行 PSO 优化。

        Args:
            objective: 目标函数
            param_bounds: 参数边界
            n_trials: 优化次数(实际使用 max_iter)
            seed: 随机种子

        Returns:
            (best_params, best_value, history)
        """
        np.random.seed(seed)

        param_names = list(param_bounds.keys())
        n_params = len(param_names)

        # 提取边界
        lowers = np.array([param_bounds[name][0] for name in param_names])
        uppers = np.array([param_bounds[name][1] for name in param_names])

        # 初始化粒子位置 (均匀分布在边界内)
        positions = np.random.uniform(lowers, uppers, (self.n_particles, n_params))
        velocities = np.zeros((self.n_particles, n_params))

        # 个体最优
        personal_best_positions = positions.copy()
        personal_best_values = np.array([objective(self._to_dict(pos, param_names)) for pos in positions])

        # 全局最优
        global_best_idx = np.argmin(personal_best_values)
        global_best_position = personal_best_positions[global_best_idx].copy()
        global_best_value = personal_best_values[global_best_idx]

        history = []

        # PSO 主循环
        actual_iter = min(n_trials, self.max_iter)
        for iter_idx in range(actual_iter):
            for i in range(self.n_particles):
                # 更新速度
                r1 = np.random.rand(n_params)
                r2 = np.random.rand(n_params)

                velocities[i] = (
                    self.w * velocities[i]
                    + self.c1 * r1 * (personal_best_positions[i] - positions[i])
                    + self.c2 * r2 * (global_best_position - positions[i])
                )

                # 更新位置
                positions[i] = positions[i] + velocities[i]

                # 边界处理 (截断到 [lower, upper])
                positions[i] = np.clip(positions[i], lowers, uppers)

                # 评估新位置
                current_value = objective(self._to_dict(positions[i], param_names))

                # 更新个体最优
                if current_value < personal_best_values[i]:
                    personal_best_values[i] = current_value
                    personal_best_positions[i] = positions[i].copy()

                    # 更新全局最优
                    if current_value < global_best_value:
                        global_best_value = current_value
                        global_best_position = positions[i].copy()

            # 记录历史
            history.append({
                "params": self._to_dict(global_best_position, param_names),
                "value": global_best_value
            })

        best_params = self._to_dict(global_best_position, param_names)
        best_value = global_best_value

        return best_params, best_value, history

    def _to_dict(self, arr: np.ndarray, names: list[str]) -> dict[str, float]:
        """将 numpy 数组转换为参数字典。"""
        return {name: float(val) for name, val in zip(names, arr)}
