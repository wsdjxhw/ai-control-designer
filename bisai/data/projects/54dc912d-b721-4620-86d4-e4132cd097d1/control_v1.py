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
# @param: kp (0.1, 50.0)
# @param: ki (0.0, 10.0)
# @param: kd (0.0, 10.0)
# @param: target_theta (0.0, 20.0)
# @param: target_omega (0.0, 5.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params, context=None):
    """
    PID control law for pendulum system.
    
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
    
    # Calculate errors
    error_theta = target_theta - theta
    error_omega = target_omega - omega
    
    # Integral term (with anti-windup)
    dt = 0.01  # Time step from scene config
    integral = context.get("integral", 0.0)
    integral += error_theta * dt
    # Anti-windup: clip integral to reasonable range
    integral = np.clip(integral, -50.0, 50.0)
    context["integral"] = integral
    
    # PID control
    u = kp * error_theta + ki * integral + kd * error_omega
    
    # Apply control limits
    u = np.clip(u, -10.0, 10.0)
    
    return np.array([u])