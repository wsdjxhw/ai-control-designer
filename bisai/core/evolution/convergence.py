"""收敛检测算法。

监控代价下降幅度和参数空间变化，连续多轮无改善则判定收敛。
"""

from __future__ import annotations


class ConvergenceDetector:
    """收敛检测器。

    同时检查代价相对改善和参数数量变化。
    连续 patience 轮无显著改善则触发收敛。
    """

    def __init__(
        self,
        improvement_threshold: float = 0.01,
        patience: int = 2,
    ) -> None:
        """
        Args:
            improvement_threshold: 相对改善阈值，低于此值视为"无改善"。
            patience: 连续无改善轮数达到此值则判定收敛。
        """
        self.improvement_threshold = improvement_threshold
        self.patience = patience
        self.counter = 0
        self.prev_cost: float | None = None
        self.prev_param_count: int | None = None

    def check(
        self,
        current_cost: float,
        current_param_count: int,
    ) -> bool:
        """检查是否收敛。

        Args:
            current_cost: 本轮最优代价。
            current_param_count: 本轮参数个数。

        Returns:
            收敛返回 True。
        """
        if self.prev_cost is None or self.prev_param_count is None:
            self.prev_cost = current_cost
            self.prev_param_count = current_param_count
            self.counter = 0
            return False

        cost_improved = False
        relative_improvement = (
            self.prev_cost - current_cost
        ) / self.prev_cost
        if relative_improvement >= self.improvement_threshold:
            cost_improved = True

        if (
            current_param_count <= self.prev_param_count
            and not cost_improved
        ):
            self.counter += 1
        else:
            self.counter = 0

        self.prev_cost = current_cost
        self.prev_param_count = current_param_count

        return self.counter >= self.patience

    def reset(self) -> None:
        self.counter = 0
        self.prev_cost = None
        self.prev_param_count = None
