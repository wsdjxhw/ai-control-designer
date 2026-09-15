"""抽象基类：动力学模型接口。

所有领域模型（UWSN、SIR、直流电机等）必须实现此接口。
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseModel(ABC):
    """动力学模型抽象基类。

    子类需实现 rhs、get_initial_state、validate_state 方法。

    以下属性有默认值，子类可以在 __init__ 里直接赋值覆盖：
        self.state_dim = 2
        self.dx = 0.01
        self.x_grid = np.linspace(...)
    """

    # ---------- 默认类属性（可被子类实例属性覆盖）----------
    state_dim: int = -1
    control_dim: int = -1
    N: int = 100
    dt: float = 0.01
    dx: float = 0.0
    x_grid = None
    state_names = None
    control_names = None

    # ---------- 抽象方法（子类必须实现）----------

    @abstractmethod
    def get_initial_state(self, x_grid=None) -> np.ndarray:
        """返回初始状态向量, shape (state_dim,) 或 (M+1, state_dim)。"""
        ...

    @abstractmethod
    def rhs(self, t: float, state: np.ndarray, control: np.ndarray, x_grid=None) -> np.ndarray:
        """计算微分方程右端项。

        Args:
            t: 当前时间.
            state: 当前状态.
            control: 当前控制输入.
            x_grid: 空间网格（PDE 模型需要，ODE 模型可忽略）.

        Returns:
            状态导数, shape 与 state 相同.
        """
        ...

    # ---------- 默认实现（子类可覆写）----------

    def validate_state(self, state: np.ndarray) -> bool:
        """校验状态是否在物理允许范围内。

        默认总是返回 True，子类可重写以实现自定义校验逻辑。
        """
        return True