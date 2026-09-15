"""RandomOptimizer：基于 Optuna RandomSampler 的随机搜索优化器。

适合：快速探索参数空间、作为基线对比
"""

from __future__ import annotations

from typing import Callable

import optuna

from core.optimizers.base_optimizer import BaseOptimizer


class RandomOptimizer(BaseOptimizer):
    """随机搜索优化器。

    适合：快速探索、基线对比
    特点：均匀随机采样，不依赖历史信息
    """

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """执行随机搜索。"""

        def optuna_objective(trial):
            params = {}
            for name, (low, high) in param_bounds.items():
                params[name] = trial.suggest_float(name, low, high)
            return objective(params)

        study = optuna.create_study(
            sampler=optuna.samplers.RandomSampler(seed=seed)
        )
        study.optimize(optuna_objective, n_trials=n_trials)

        best_params = study.best_params
        best_value = study.best_value

        history = [
            {"params": t.params, "value": t.value}
            for t in study.trials
            if t.value is not None
        ]

        return best_params, best_value, history
