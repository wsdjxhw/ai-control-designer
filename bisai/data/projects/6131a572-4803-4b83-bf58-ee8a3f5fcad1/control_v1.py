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
# @param: kp (0.01, 100.0)
# @param: kd (0.01, 100.0)
# @param: torque_limit (0.1, 100.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Pendulum continuous control law.
    PD feedback controller for angle stabilization.
    """
    theta, omega = state

    kp = params.get("kp", 10.0)
    kd = params.get("kd", 2.0)
    torque_limit = params.get("torque_limit", 20.0)

    target_theta = 0.0
    target_omega = 0.0

    error_theta = theta - target_theta
    error_omega = omega - target_omega

    torque = -(kp * error_theta + kd * error_omega)
    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])