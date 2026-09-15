"""优化器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class BaseOptimizer(ABC):
    """参数优化器抽象基类。

    所有优化器（CMA-ES、遗传算法、粒子群等）必须实现此接口。
    """

    @abstractmethod
    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """执行优化。

        Args:
            objective: 目标函数，输入参数字典，返回代价值（越小越好）
            param_bounds: 参数边界 {param_name: (low, high)}
            n_trials: 优化迭代次数
            seed: 随机种子

        Returns:
            (best_params, best_value, history)
            - best_params: 最优参数字典
            - best_value: 最优代价值
            - history: 每轮优化历史 [{"params": {...}, "value": float}, ...]
        """
        ...
