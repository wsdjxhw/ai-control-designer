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
# @param: theta_gain (0.01, 100.0)
# @param: omega_gain (0.01, 100.0)
# @param: torque_limit (0.1, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Pendulum stabilization control law.
    Continuous torque feedback for driving theta and omega to zero.
    """
    theta, omega = state

    theta_gain = params.get("theta_gain", 10.0)
    omega_gain = params.get("omega_gain", 3.0)
    torque_limit = params.get("torque_limit", 20.0)

    torque = -(theta_gain * theta + omega_gain * omega)
    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])