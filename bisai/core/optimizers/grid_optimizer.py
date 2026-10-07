"""GridOptimizer：基于 Optuna GridSampler 的网格搜索优化器。

适合：参数空间较小、需要穷举所有组合
注意：参数空间较大时会非常慢
"""

from __future__ import annotations

from typing import Callable

import optuna

from core.optimizers.base_optimizer import BaseOptimizer


class GridOptimizer(BaseOptimizer):
    """网格搜索优化器。

    适合：参数空间较小、需要系统性搜索
    特点：按网格均匀采样所有组合
    警告：参数空间较大时，n_trials 会非常大
    """

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """执行网格搜索。

        注意：GridSampler 需要预定义搜索空间，这里简化为均匀采样。
        实际使用时建议用 Random 或 TPE 替代。
        """

        # 🆕 先构造离散网格（移到 optuna_objective 之前）
        search_space = {}
        n_params = len(param_bounds)
        if n_params == 0:
            return {}, float("inf"), []

        n_points_per_param = max(3, int((n_trials ** (1.0 / n_params))))

        for name, (low, high) in param_bounds.items():
            search_space[name] = [
                low + (high - low) * i / (n_points_per_param - 1)
                for i in range(n_points_per_param)
            ]

        def optuna_objective(trial):
            params = {}
            for name in param_bounds.keys():
                # 🆕 用 suggest_categorical 从预先定义的离散点里选
                params[name] = trial.suggest_categorical(name, search_space[name])
            return objective(params)



        study = optuna.create_study(
            sampler=optuna.samplers.GridSampler(search_space)
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
