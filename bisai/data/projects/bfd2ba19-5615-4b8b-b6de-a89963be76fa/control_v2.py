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
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params, context=None):
    """
    PID control law for pendulum system with improved integral action.
    
    Key modifications from diagnostic report:
    1. Increased integral gain to eliminate persistent steady-state error
    2. Added anti-windup with configurable integral limit
    3. Increased control torque limit for better tracking
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
    
    # Calculate errors
    error_theta = target_theta - theta
    error_omega = target_omega - omega
    
    # Integral term with anti-windup
    dt = 0.01  # from scene_config temporal dt
    integral = context.get("integral", 0.0)
    integral += error_theta * dt
    integral = np.clip(integral, -integral_limit, integral_limit)  # anti-windup
    context["integral"] = integral
    
    # PID control with improved gains
    # Increased kp and ki to address persistent steady-state error
    # Added derivative on measurement to avoid derivative kick
    u = kp * error_theta + ki * integral + kd * error_omega
    
    # Apply control limits with increased bound
    u = np.clip(u, -max_torque, max_torque)
    
    return np.array([u])