"""
PID 基线控制律生成。

生成的代码使用 P + D 两项：
  - P: 根据误差按比例输出
  - D: 根据状态变化率（第二状态）衰减

不包含 I 项，因为控制律是无状态的（每次调用独立），
无法累积历史误差。这在工程实践中是很常见的简化（PD 控制器）。
"""

from __future__ import annotations
from typing import Optional


def generate_pid_control_law(
    scene_config: dict,
    params: Optional[dict] = None,
) -> str:
    params = params or {}
    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])
    target_values = scene_config.get("target_values", {})
    control_limits = scene_config.get("control_limits", {})
    temporal = scene_config.get("temporal", {})

    primary_state = state_names[0] if state_names else "x0"
    primary_control = control_names[0] if control_names else "u"
    primary_target = float(target_values.get(primary_state, 0.0))
    dt = float(temporal.get("dt", 0.01))

    u_range = control_limits.get(primary_control, [-1e6, 1e6])
    if isinstance(u_range, list) and len(u_range) == 2:
        u_min, u_max = float(u_range[0]), float(u_range[1])
    else:
        u_min, u_max = -1e6, 1e6

    kp_default = float(params.get("kp", 5.0))
    ki_default = float(params.get("ki", 2.0))
    kd_default = float(params.get("kd", 0.5))

    has_second_state = len(state_names) >= 2
    second_state = state_names[1] if has_second_state else None

    if has_second_state:
        code = f'''import numpy as np

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 100.0)
# @param: ki (0.0, 50.0)
# @param: kd (0.0, 50.0)
# ========== END PARAM DECLARATION ==========

def control_law(t, x, state, params, context=None):
    """
    PID 基线控制律（自动生成，有状态版本）。
    通过 context 字典累积积分项。
    """
    if context is None:
        context = {{}}

    {primary_state} = state[0]
    {second_state} = state[1]

    error = {primary_target} - {primary_state}

    kp = params.get("kp", {kp_default})
    ki = params.get("ki", {ki_default})
    kd = params.get("kd", {kd_default})

    # 🆕 积分项（通过 context 累积）
    integral = context.get("integral", 0.0)
    integral += error * {dt}
    # 抗积分饱和
    integral = float(np.clip(integral, -100.0, 100.0))
    context["integral"] = integral

    u = kp * error + ki * integral - kd * {second_state}
    u = np.clip(u, {u_min}, {u_max})

    return np.array([u])
'''
    else:
        code = f'''import numpy as np

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 100.0)
# @param: ki (0.0, 50.0)
# ========== END PARAM DECLARATION ==========

def control_law(t, x, state, params, context=None):
    if context is None:
        context = {{}}

    {primary_state} = state[0]
    error = {primary_target} - {primary_state}

    kp = params.get("kp", {kp_default})
    ki = params.get("ki", {ki_default})

    integral = context.get("integral", 0.0)
    integral += error * {dt}
    integral = float(np.clip(integral, -100.0, 100.0))
    context["integral"] = integral

    u = kp * error + ki * integral
    u = np.clip(u, {u_min}, {u_max})

    return np.array([u])
'''

    return code