# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No `float(`, `int(`, `bool(` on arrays. Use `.astype()` instead.
# [ ] 2. `np.where` uses `&` / `|`, NOT `and` / `or`.
# [ ] 3. `np.max` / `np.min` / `np.abs` used (not Python built-ins).
# [ ] 4. No `for i in range(M+1)` loops.
# [ ] 5. Return shape: `(M+1, N_control)` for PDE, `(N_control,)` for ODE.
# [ ] 6. All controls implemented (no forced zeros).
# [ ] 7. Uses `t / T` for time normalization if needed.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 50.0)
# @param: ki (0.0, 20.0)
# @param: kd (0.0, 20.0)
# @param: target_theta (0.0, 20.0)
# @param: target_omega (0.0, 10.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params, context=None):
    """
    PID control law for pendulum system.
    
    Args:
        t: Current time
        x: State vector (if applicable)
        state: Current state [theta, omega]
        params: Dictionary of control parameters
        context: Optional context dict for integral accumulation
    
    Returns:
        Control action [torque]
    """
    if context is None:
        context = {}
    
    # Unpack state
    theta, omega = state[0], state[1]
    
    # Get parameters with defaults
    kp = params.get("kp", 10.0)
    ki = params.get("ki", 5.0)
    kd = params.get("kd", 2.0)
    target_theta = params.get("target_theta", 10.0)
    target_omega = params.get("target_omega", 2.0)
    
    # Calculate errors
    error_theta = target_theta - theta
    error_omega = target_omega - omega
    
    # Integral term with anti-windup
    dt = 0.01  # from scene_config temporal dt
    integral = context.get("integral", 0.0)
    integral += error_theta * dt
    integral = np.clip(integral, -50.0, 50.0)  # anti-windup
    context["integral"] = integral
    
    # PID control
    u = kp * error_theta + ki * integral + kd * error_omega
    
    # Apply control limits
    u = np.clip(u, -10.0, 10.0)
    
    return np.array([u])