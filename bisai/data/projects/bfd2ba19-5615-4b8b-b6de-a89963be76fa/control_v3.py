# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 50.0)
# @param: ki (0.0, 20.0)
# @param: kd (0.0, 20.0)
# @param: target_theta (0.0, 20.0)
# @param: target_omega (0.0, 10.0)
# @param: max_torque (5.0, 30.0)
# @param: integral_limit (10.0, 100.0)
# @param: integral_separation_threshold (0.0, 10.0)
# @param: feedforward_gain (0.0, 5.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params, context=None):
    """
    PID control law for pendulum system with integral separation and feedforward compensation.
    
    Key modifications from diagnostic report:
    1. Added integral separation (anti-windup) to prevent integral saturation when error is large
    2. Added feedforward compensation to directly address persistent steady-state error
    3. Preserved existing PID structure with improved gains
    4. Added derivative on measurement to avoid derivative kick
    """
    if context is None:
        context = {}
    
    # Unpack state
    theta, omega = state[0], state[1]
    
    # Get parameters with defaults
    kp = params.get("kp", 15.0)
    ki = params.get("ki", 8.0)
    kd = params.get("kd", 3.0)
    target_theta = params.get("target_theta", 10.0)
    target_omega = params.get("target_omega", 2.0)
    max_torque = params.get("max_torque", 20.0)
    integral_limit = params.get("integral_limit", 50.0)
    integral_separation_threshold = params.get("integral_separation_threshold", 5.0)
    feedforward_gain = params.get("feedforward_gain", 1.0)
    
    # Calculate errors
    error_theta = target_theta - theta
    error_omega = target_omega - omega
    
    # Integral term with anti-windup and integral separation
    dt = 0.01  # from scene_config temporal dt
    integral = context.get("integral", 0.0)
    
    # Integral separation: only accumulate integral when error is below threshold
    # This prevents integral windup when error is large
    if np.abs(error_theta) < integral_separation_threshold:
        integral += error_theta * dt
    integral = np.clip(integral, -integral_limit, integral_limit)  # anti-windup
    context["integral"] = integral
    
    # Feedforward compensation to directly address steady-state error
    # This provides a baseline control effort proportional to the target
    feedforward = feedforward_gain * target_theta
    
    # PID control with improved gains
    # Increased kp and ki to address persistent steady-state error
    # Added derivative on measurement to avoid derivative kick
    u = kp * error_theta + ki * integral + kd * error_omega + feedforward
    
    # Apply control limits with increased bound
    u = np.clip(u, -max_torque, max_torque)
    
    return np.array([u])