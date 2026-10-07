"""
基线控制律生成模块

根据 scene_config 自动推断适合的基线类型，并生成对应的控制律代码。
"""

from core.baselines.infer import infer_baseline_type
from core.baselines.pid import generate_pid_control_law

__all__ = ["infer_baseline_type", "generate_pid_control_law"]
