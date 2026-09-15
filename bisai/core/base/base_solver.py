"""抽象基类：数值求解器接口。

所有数值积分方法（RK4、SciPy ODE 等）必须实现此接口。
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

import numpy as np

from core.base.base_model import BaseModel


class BaseSolver(ABC):
    """数值求解器抽象基类。"""

    @abstractmethod
    def step(
        self,
        model: BaseModel,
        state: np.ndarray,
        control: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """单步积分：从当前状态推进 dt 时间。

        Args:
            model: 动力学模型实例.
            state: 当前状态, shape (state_dim,).
            control: 当前控制输入, shape (control_dim,).
            dt: 时间步长.

        Returns:
            下一时刻状态, shape (state_dim,).
        """
        ...

    @abstractmethod
    def solve(
        self,
        model: BaseModel,
        t_span: tuple[float, float],
        dt: float,
        control_func: Callable[[float, np.ndarray], np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """完整仿真：从 t_start 到 t_end，返回时间序列、状态轨迹、控制历史。

        Args:
            model: 动力学模型实例.
            t_span: (t_start, t_end) 仿真时间区间.
            dt: 时间步长.
            control_func: 控制律函数 control(t, state) -> control_vector.

        Returns:
            (time_array, state_history, control_history)
            - time_array: shape (N,)
            - state_history: shape (N, state_dim)
            - control_history: shape (N, control_dim)
        """
        ...
