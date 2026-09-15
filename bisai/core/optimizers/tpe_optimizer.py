"""TPEOptimizer：基于 Optuna TPE (Tree-structured Parzen Estimator) 的优化器。

TPE 适合超参数优化，通过构建两个分布（好/坏）来指导采样。
"""

from __future__ import annotations

from typing import Callable

import optuna

from core.optimizers.base_optimizer import BaseOptimizer


class TPEOptimizer(BaseOptimizer):
    """TPE 优化器（Tree-structured Parzen Estimator）。

    适合：超参数优化、黑盒优化
    特点：通过构建两个分布模型（表现好/差）来指导采样
    """

    def __init__(self, n_startup_trials: int = 10, n_ei_candidates: int = 24, **kwargs):
        """初始化 TPE 优化器。

        Args:
            n_startup_trials: 随机采样启动次数
            n_ei_candidates: EI 候选点数量
            **kwargs: 其他传递给 TPESampler 的参数
        """
        self.n_startup_trials = n_startup_trials
        self.n_ei_candidates = n_ei_candidates
        self.kwargs = kwargs

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """执行 TPE 优化。"""

        def optuna_objective(trial):
            params = {}
            for name, (low, high) in param_bounds.items():
                params[name] = trial.suggest_float(name, low, high)
            return objective(params)

        study = optuna.create_study(
            sampler=optuna.samplers.TPESampler(
                seed=seed,
                n_startup_trials=self.n_startup_trials,
                n_ei_candidates=self.n_ei_candidates,
                **self.kwargs,
            )
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
