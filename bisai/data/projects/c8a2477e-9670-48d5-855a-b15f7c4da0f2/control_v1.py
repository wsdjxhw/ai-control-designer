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
# @param: kp_theta (0.5, 50.0)
# @param: kd_theta (0.1, 20.0)
# @param: kp_omega (0.1, 20.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous PD-style feedback control for the pendulum.

    Target: theta ->1.0 rad, omega -> 0.5 rad/s
    Control: torque (clipped to [-10, 10])
    """
    theta, omega = state[0], state[1]

    # Target values
    target_theta = params.get("target_theta", 1.0)
    target_omega = params.get("target_omega", 0.5)

    # Tunable PD gains
    kp_theta = params.get("kp_theta", 8.0)
    kd_theta = params.get("kd_theta", 3.0)
    kp_omega = params.get("kp_omega", 5.0)

    # Tracking errors
    e_theta = theta - target_theta
    e_omega = omega - target_omega

    # Continuous feedback (PD on theta + damping on omega)
    # Inertia approximation from model: m*L^2
    u_raw = -(kp_theta * e_theta + kd_theta * e_omega + kp_omega * e_omega)

    # Saturate to control limits [-10, 10]
    torque = np.clip(u_raw, -10.0, 10.0)

    return np.array([torque])