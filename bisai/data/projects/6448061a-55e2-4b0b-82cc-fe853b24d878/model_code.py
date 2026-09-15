# 示例：单摆系统 (Pendulum)
# 继承 BaseModel 并实现必需的方法
# 硬编码参数 (self.xxx = ...) 会被 LLM 自动提取

from core.base.base_model import BaseModel
import numpy as np

class Pendulum(BaseModel):
    """单摆系统"""

    def __init__(self, scene_config=None):
        if scene_config is None:
            scene_config = {}
        params = scene_config.get("model_params", {})
        self.length = params.get("length", 1.0)      # 摆长 (m)
        self.mass = params.get("mass", 1.0)          # 摆锤质量 (kg)
        self.g = params.get("g", 9.81)               # 重力加速度 (m/s²)

    def get_initial_state(self, x_grid=None):
        """返回初始状态 [θ, ω]"""
        # 默认初始状态: θ=0.5 rad, ω=0
        return np.array([0.5, 0.0])

    def rhs(self, t, x, u):
        """状态方程: dx/dt = f(x, u)"""
        theta, omega = x[0], x[1]
        torque = u[0] if len(u) > 0 else 0.0

        # 单摆动力学
        dtheta_dt = omega
        domega_dt = -(self.g / self.length) * np.sin(theta) + torque / (self.mass * self.length**2)

        return np.array([dtheta_dt, domega_dt])

    def validate_state(self, state):
        """验证状态是否有效"""
        # 单摆状态通常没有硬性约束,返回 True 表示总是有效
        return True
