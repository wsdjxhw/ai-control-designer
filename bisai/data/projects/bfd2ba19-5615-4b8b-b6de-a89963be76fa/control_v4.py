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
# @param: k_ff (0.1, 5.0)
# @param: k_pen (0.1, 2.0)
# @param: alpha (0.1, 1.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params, context=None):
    """
    Enhanced PID control law for pendulum system with:
    1. Feedforward compensation to directly address steady-state error
    2. Anti-windup with integral separation
    3. Adaptive gain scheduling based on error magnitude
    4. State constraint penalty for direct state convergence
    
    Key modifications from diagnostic report:
    - Added feedforward compensation (k_ff) to directly counteract persistent steady-state error
    - Added adaptive gain scheduling (alpha) to dynamically adjust gains based on error magnitude
    - Added state constraint penalty (k_pen) to force state convergence
    - Preserved existing PID structure with improved gains
    - This addresses the "parameter tuning ineffectiveness" failure mode by making structural changes
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
    k_ff = params.get("k_ff", 1.0)
    k_pen = params.get("k_pen", 0.5)
    alpha = params.get("alpha", 0.3)
    
    # Calculate errors
    error_theta = target_theta - theta
    error_omega = target_omega - omega
    
    # Adaptive gain scheduling: increase gains when error is large
    # This addresses the "parameter tuning ineffectiveness" by dynamically adapting gains
    error_magnitude = np.abs(error_theta)
    kp_eff = kp * (1.0 + alpha * error_magnitude)
    kd_eff = kd * (1.0 + alpha * error_magnitude)
    
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
    
    # Additional feedforward term based on error to actively push toward target
    # This directly addresses the persistent steady-state error
    feedforward_comp = k_ff * error_theta
    
    # State constraint penalty to force state convergence
    # This directly penalizes state deviations to ensure convergence
    state_penalty = k_pen * (error_theta + error_omega)
    
    # PID control with adaptive gains and structural improvements
    u = kp_eff * error_theta + ki * integral + kd_eff * error_omega + feedforward + feedforward_comp + state_penalty
    
    # Apply control limits
    u = np.clip(u, -max_torque, max_torque)
    
    return np.array([u])