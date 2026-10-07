# ========== VECTORIZATION SELF-CHECK ==========
# [x] 1. No `float(`, `int(`, `bool(` on arrays. Use `.astype()` instead.
# [x] 2. `np.where` uses `&` / `|`, NOT `and` / `or`.
# [x] 3. `np.max` / `np.min` / `np.abs` used (not Python built-ins).
# [x] 4. No `for i in range(M+1)` loops.
# [x] 5. Return shape: `(N_control,)` for ODE.
# [x] 6. All controls implemented (no forced zeros).
# [x] 7. Uses `t / T` for time normalization if needed.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 200.0)
# @param: kd (0.0, 100.0)
# @param: feedforward (0.0, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Energy-shaping + linearizing continuous control for the pendulum.

    Goal: drive (theta, omega) to the upright-like target (theta=10, omega=2)
    while respecting torque limits [-10, 10].

    Strategy:
      1. Use PD on the angle/velocity error for stabilization.
      2. Add a small gravity-compensation / feed-forward term using the
         linearized model so the controller behaves well away from the
         equilibrium point.
    """
    theta = state[0]
    omega = state[1]

    # Targets
    theta_target = 10.0
    omega_target = 2.0

    # Tunable gains (declared above via @param)
    kp = params.get("kp", 20.0)
    kd = params.get("kd", 5.0)
    feedforward = params.get("feedforward", 1.0)

    # Tracking errors
    e_theta = theta - theta_target
    e_omega = omega - omega_target

    # PD control law
    u_pd = -kp * e_theta - kd * e_omega

    # Gravity compensation (linearized around small angles, scaled by feedforward)
    # For the pendulum, gravity torque ~ m*g*L*sin(theta); we add it as a
    # compensation term to counteract the destabilizing component.
    g_comp = feedforward * np.sin(theta)

    u = u_pd + g_comp

    # Saturate to physical torque limits
    u = np.clip(u, -10.0, 10.0)

    return np.array([u])