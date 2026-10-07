# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.1, 50.0)
# @param: ki (0.0, 10.0)
# @param: kd (0.0, 10.0)
# @param: target_theta (0.0, 20.0)
# @param: target_omega (0.0, 5.0)
# @param: kff (0.0, 5.0)
# @param: integral_limit (1.0, 100.0)
# @param: k_ff_integral (0.1, 5.0)
# @param: k_damp (0.1, 2.0)
# @param: theta_sat (3.0, 8.0)
# @param: ki_theta (0.1, 5.0)
# @param: kff_theta (0.0, 2.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params, context=None):
    """
    PID control law for pendulum system with feedforward compensation.
    
    Args:
        t: Current time
        x: State vector (for PDE systems, may be spatial grid)
        state: Current state [theta, omega]
        params: Dictionary of control parameters
        context: Optional dictionary for stateful control (e.g., integral accumulation)
    
    Returns:
        Control action [torque]
    """
    # Initialize context if not provided
    if context is None:
        context = {}
    
    # Unpack state
    theta, omega = state[0], state[1]
    
    # Get parameters with defaults
    kp = params.get("kp", 5.0)
    ki = params.get("ki", 0.5)
    kd = params.get("kd", 0.5)
    target_theta = params.get("target_theta", 10.0)
    target_omega = params.get("target_omega", 2.0)
    kff = params.get("kff", 2.0)  # Feedforward gain
    integral_limit = params.get("integral_limit", 50.0)
    k_ff_integral = params.get("k_ff_integral", 2.0)  # Integral feedforward gain
    k_damp = params.get("k_damp", 0.5)  # Damping coefficient
    theta_sat = params.get("theta_sat", 5.0)  # Theta error saturation limit
    ki_theta = params.get("ki_theta", 1.0)  # NEW: Integral gain for theta error
    kff_theta = params.get("kff_theta", 0.5)  # NEW: Feedforward gain for theta target
    
    # Calculate errors
    error_theta = target_theta - theta
    error_omega = target_omega - omega
    
    # Apply saturation to theta error to prevent excessive control action
    error_theta_sat = np.clip(error_theta, -theta_sat, theta_sat)
    
    # Integral term (with anti-windup)
    dt = 0.01  # Time step from scene config
    integral = context.get("integral", 0.0)
    integral += error_theta * dt
    # Anti-windup: clip integral to reasonable range
    integral = np.clip(integral, -integral_limit, integral_limit)
    context["integral"] = integral
    
    # PID control with feedforward compensation
    # Feedforward term helps overcome steady-state bias by directly compensating
    # the persistent error that PID alone cannot eliminate
    u = kp * error_theta_sat + ki * integral + kd * error_omega + kff * error_theta_sat
    
    # Add integral feedforward compensation for theta steady-state error
    # This directly addresses the persistent theta bias by providing continuous correction
    u += k_ff_integral * integral
    
    # Add damping term to suppress omega oscillations
    u -= k_damp * omega
    
    # NEW: Add explicit theta integral compensation to eliminate steady-state bias
    # This directly addresses the "theta drift trap" failure mode identified in the diagnostic report.
    # The previous versions only used ki * integral which was insufficient to correct the persistent theta bias.
    # By adding a dedicated ki_theta term, we ensure the controller actively drives theta to target_theta.
    u += ki_theta * integral
    
    # NEW: Add theta feedforward compensation to directly counteract the persistent bias
    # The diagnostic report identified that the previous kff term was ineffective because it acted on
    # error_theta_sat rather than providing a direct feedforward to the target. This new term
    # provides a constant bias correction based on the target value.
    u += kff_theta * target_theta
    
    # Apply control limits
    u = np.clip(u, -10.0, 10.0)
    
    return np.array([u])