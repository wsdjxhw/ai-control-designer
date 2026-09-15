"""CustomOptimizer：支持用户上传自定义优化器代码。

用户可以通过 scene_config 提供自定义优化器代码，实现：
- 遗传算法（GA）
- 粒子群优化（PSO）
- 差分进化（DE）
- 模拟退火（SA）
- 贝叶斯优化
- 强化学习优化器
- 任意其他优化算法

不影响现有 CMA-ES 默认实现。
"""

from __future__ import annotations

from typing import Any, Callable

from core.optimizers.base_optimizer import BaseOptimizer


class CustomOptimizer(BaseOptimizer):
    """自定义优化器：通过 scene_config 加载用户提供的优化器代码。

    scene_config['optimizer'] 格式示例:
    {
        "optimizer_type": "custom",
        "custom_optimizer_code": '''
from core.optimizers.base_optimizer import BaseOptimizer
from typing import Callable
import numpy as np
import random

class GeneticAlgorithmOptimizer(BaseOptimizer):
    \"\"\"遗传算法优化器。\"\"\"

    def __init__(self, population_size=50, mutation_rate=0.1):
        self.population_size = population_size
        self.mutation_rate = mutation_rate

    def optimize(self, objective, param_bounds, n_trials, seed=42):
        # 实现遗传算法逻辑
        random.seed(seed)
        np.random.seed(seed)

        param_names = list(param_bounds.keys())

        # 初始化种群
        population = []
        for _ in range(self.population_size):
            individual = {
                name: random.uniform(low, high)
                for name, (low, high) in param_bounds.items()
            }
            population.append(individual)

        history = []
        best_value = float('inf')
        best_params = None

        for trial in range(n_trials):
            # 评估
            fitness = [objective(ind) for ind in population]

            # 记录历史
            for ind, fit in zip(population, fitness):
                history.append({"params": ind.copy(), "value": fit})

            # 找到最优
            min_idx = np.argmin(fitness)
            if fitness[min_idx] < best_value:
                best_value = fitness[min_idx]
                best_params = population[min_idx].copy()

            # 选择、交叉、变异...
            # （完整遗传算法逻辑）

        return best_params, best_value, history
        ''',
        "description": "用户自定义遗传算法优化器"
    }

    代码必须定义继承 BaseOptimizer 的类，类名任意（自动检测第一个子类）。
    """

    def __init__(self, scene_config: dict) -> None:
        self.scene_config = scene_config

        opt_cfg = scene_config.get("optimizer", {})
        code = opt_cfg.get("custom_optimizer_code", "")

        if not code:
            raise ValueError("custom_optimizer_code 不能为空")

        # 动态编译用户代码
        namespace: dict[str, Any] = {
            "np": __import__("numpy"),
            "random": __import__("random"),
            "BaseOptimizer": BaseOptimizer,
            "Callable": Callable,
        }
        exec(compile(code, "<custom_optimizer>", "exec"), namespace)

        # 查找继承 BaseOptimizer 的类（排除 BaseOptimizer 本身）
        opt_cls = None
        for name, obj in namespace.items():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseOptimizer)
                and obj is not BaseOptimizer
            ):
                opt_cls = obj
                break

        if opt_cls is None:
            raise ValueError(
                "custom_optimizer_code 中未找到继承 BaseOptimizer 的类"
            )

        # 实例化用户定义的优化器
        self._inner_optimizer: BaseOptimizer = opt_cls()
        self._optimizer_name = opt_cls.__name__
        self._description = opt_cfg.get("description", self._optimizer_name)

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """委托给用户定义的 optimize 方法。"""
        return self._inner_optimizer.optimize(
            objective, param_bounds, n_trials, seed
        )
