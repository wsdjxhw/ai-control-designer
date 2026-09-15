"""CMAESOptimizer：基于 Optuna CMA-ES 的优化器实现（当前默认）。"""

from __future__ import annotations

from typing import Callable

import optuna

from core.optimizers.base_optimizer import BaseOptimizer


class CMAESOptimizer(BaseOptimizer):
    """CMA-ES 优化器（当前默认实现，通过 Optuna）。"""

    def __init__(self, popsize: int = 50, sigma0: float = 0.25, **kwargs):
        """初始化 CMA-ES 优化器。

        Args:
            popsize: 种群大小
            sigma0: 初始步长
            **kwargs: 其他传递给 CmaEsSampler 的参数
        """
        self.popsize = popsize
        self.sigma0 = sigma0
        self.kwargs = kwargs

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """执行 CMA-ES 优化。

        Args:
            objective: 目标函数
            param_bounds: 参数边界
            n_trials: 优化次数
            seed: 随机种子

        Returns:
            (best_params, best_value, history)
        """

        def optuna_objective(trial):
            params = {}
            for name, (low, high) in param_bounds.items():
                params[name] = trial.suggest_float(name, low, high)
            return objective(params)

        study = optuna.create_study(
            sampler=optuna.samplers.CmaEsSampler(
                seed=seed,
                popsize=self.popsize,
                sigma0=self.sigma0,
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
