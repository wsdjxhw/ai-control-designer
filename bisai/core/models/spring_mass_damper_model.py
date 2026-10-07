"""
专家模式测试用的弹簧-质量-阻尼系统 (Spring-Mass-Damper)

这是一个最简单的二阶线性系统，用于验证专家模式流程。

状态: [x, v] (位置, 速度)
控制: [u] (作用力)
目标: 让质量块快速回到平衡位置 x=0, v=0
"""

import numpy as np
from core.base.base_model import BaseModel


class SpringMassDamperModel(BaseModel):
    """
    弹簧-质量-阻尼系统

    物理方程:
        m * dv/dt = -k * x - c * v + u

    状态空间形式:
        dx/dt = v
        dv/dt = -(k/m) * x - (c/m) * v + (1/m) * u

    参数:
        m: 质量 (kg)
        k: 弹簧刚度 (N/m)
        c: 阻尼系数 (N·s/m)
    """

    def __init__(self, scene_config):

        super().__init__()  # 🆕 加这行
        self.scene_config = scene_config  # 🆕 加这行

        self.state_names = scene_config.get("state_names", ["x", "v"])
        self.control_names = scene_config.get("control_names", ["u"])

        params = scene_config.get("physical_params", {})
        self.m = params.get("m", 1.0)   # 质量
        self.k = params.get("k", 10.0)  # 弹簧刚度
        self.c = params.get("c", 1.0)   # 阻尼系数

        print(f"[SpringMassDamperModel] 初始化: m={self.m}, k={self.k}, c={self.c}")

    def get_initial_state(self, x_grid=None):
        """获取初始状态"""
        init = self.scene_config.get("initial_state", {})
        return np.array([
            init.get("x0", 1.0),   # 初始位置 (偏离平衡位置)
            init.get("v0", 0.0),   # 初始速度
        ])

    def rhs(self, t, state, control, x_grid=None):
        """
        状态方程右端项

        Args:
            t: 时间
            state: [x, v]
            control: [u]

        Returns:
            [dx/dt, dv/dt]
        """
        x, v = state
        u = control[0] if len(control) > 0 else 0.0

        dx = v
        dv = -(self.k / self.m) * x - (self.c / self.m) * v + (1.0 / self.m) * u

        return np.array([dx, dv])

    def validate_state(self, state):
        """状态验证（弹簧系统无约束）"""
        return True
