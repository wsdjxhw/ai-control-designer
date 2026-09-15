"""抽象基类：代价函数接口。

所有代价计算方式（模板、表达式、代码）必须实现此接口。
同时包含统一的 bang-bang 离散值校验逻辑。
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseCost(ABC):
    """代价函数抽象基类。

    子类需实现 compute_running 和 compute_terminal。
    validate_control 提供默认的 bang-bang 离散值检查，子类可覆写。
    """

    def __init__(self, scene_config: dict) -> None:
        """初始化代价函数。

        Args:
            scene_config: 场景配置字典，包含代价权重、目标值、控制类型与上下限等。
        """
        self.scene_config = scene_config

    @abstractmethod
    def compute_running(
        self,
        state: np.ndarray,
        control: np.ndarray,
        step: int,
    ) -> float:
        """计算单步运行代价（每步积分调用一次）。

        Args:
            state: 当前状态, shape (state_dim,).
            control: 当前控制输入, shape (control_dim,).
            step: 当前积分步序号.

        Returns:
            标量代价.
        """
        ...

    @abstractmethod
    def compute_terminal(self, state: np.ndarray) -> float:
        """计算终端代价（仿真结束后调用一次）。

        Args:
            state: 终端状态, shape (state_dim,).

        Returns:
            标量终端代价.
        """
        ...

    def validate_control(self, control: np.ndarray) -> bool:
        """校验控制输入是否合法。

        默认实现：检查 bang-bang 离散控制是否在允许的离散值集合内。
        支持 control_limits 的两种格式：
          - dict: {"u1": [0, 1], "u2": [0, 1], ...}  （新格式，按 control_names 匹配）
          - list: [[0, 1], [0, 1], ...]              （旧格式，按索引匹配）
        """
        control_type = self.scene_config.get("control_type", "continuous")
        if control_type != "bang_bang":
            return True

        control_limits = self.scene_config.get("control_limits", {})
        control_names = self.scene_config.get("control_names", [])

        # 归一化：把 control_limits 转成 {index: allowed} 的映射
        allowed_by_idx: dict[int, list] = {}
        if isinstance(control_limits, dict):
            for i, name in enumerate(control_names):
                if name in control_limits:
                    allowed_by_idx[i] = control_limits[name]
        elif isinstance(control_limits, list):
            for i, allowed in enumerate(control_limits):
                allowed_by_idx[i] = allowed
        else:
            return True  # 未知格式，放过

        # 逐个校验
        for i, val in enumerate(control):
            allowed = allowed_by_idx.get(i)
            if allowed is None:
                continue
            if not isinstance(allowed, list):
                continue
            # allowed 是离散值集合（如 [0, 1] 或 [0, 0.5]）
            # 用容差判断，避免浮点误差
            if not any(abs(val - a) < 1e-6 for a in allowed):
                return False

        return True
