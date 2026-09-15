"""抽象基类：控制律加载器接口。

负责从代码字符串编译控制律、提取参数名与边界、以及运行时求值。
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseControlLaw(ABC):
    """控制律抽象基类。

    子类需实现 load、extract_parameters、evaluate 三个核心方法。
    """

    @abstractmethod
    def load(self, code: str) -> None:
        """从 Python 代码字符串编译控制律。

        Args:
            code: 包含控制律函数（如 control_law(t, state, params)）的源码字符串.
        """
        ...

    @abstractmethod
    def extract_parameters(self) -> dict[str, dict]:
        """提取控制律的可调参数及边界信息。

        Returns:
            形如 {param_name: {"default": float, "lower": float, "upper": float, "declaration": str}} 的字典.
        """
        ...

    @abstractmethod
    def evaluate(self, state: np.ndarray, params: dict[str, float]) -> np.ndarray:
        """计算给定状态和参数下的控制输出。

        Args:
            state: 当前状态, shape (state_dim,).
            params: 参数名到值的映射.

        Returns:
            控制输出向量, shape (control_dim,).
        """
        ...

    @abstractmethod
    def smoke_test(self) -> bool:
        """对当前控制律运行快速烟雾测试。

        随机采样一组参数，执行 evaluate 并检查输出形状与合法性。

        Returns:
            测试通过返回 True，否则返回 False.
        """
        ...
