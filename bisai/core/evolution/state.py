"""演化状态数据类。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvolutionState:
    """演化引擎的运行状态。"""

    status: str = "idle"
    """当前状态: idle / running / optimizing / diagnosing / modifying / done / error"""

    current_version: int = 0
    best_cost: float = float("inf")
    best_params: dict = field(default_factory=dict)
    iteration: int = 0
    max_iterations: int = 20
    convergence_counter: int = 0
    error: str | None = None
    message: str = ""

    @property
    def converged(self) -> bool:
        return self.convergence_counter >= 2

    @property
    def is_running(self) -> bool:
        return self.status in ("running", "optimizing", "diagnosing", "modifying")
