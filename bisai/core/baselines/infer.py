"""
基线类型自动推断。

当前只支持 PID（针对连续 ODE 系统）。
SIR（Bang-Bang）和 UWSN（PDE）的基线留待后续扩展。
"""

from __future__ import annotations
from typing import Optional


def infer_baseline_type(scene_config: dict) -> Optional[str]:
    """
    根据 scene_config 推断适合的基线类型。

    规则：
      - PDE 系统 → 返回 None（暂不支持）
      - Bang-Bang 控制 → 返回 None（暂不支持）
      - 连续 ODE，且有 1-2 个状态 → "pid"
      - 其他 → None

    Returns:
        "pid" | None
    """
    model_type = scene_config.get("model_type", "ode")
    control_type = scene_config.get("control_type", "continuous")
    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])

    # PDE 暂不推断基线
    if model_type == "pde":
        return None

    # Bang-Bang 暂不推断基线
    if control_type == "bang_bang":
        return None

    # 连续控制 + 至少 1 个状态 → PID
    if control_type == "continuous" and len(state_names) >= 1 and len(control_names) >= 1:
        return "pid"

    return None