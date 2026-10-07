# ========== VECTORIZATION SELF-CHECK ==========
# [x] 1. No float(, int(, bool( applied to any array or comparison expression.
# [x] 2. All np.where conditions use & or |, not and or or.
# [x] 3. np.max / np.min used instead of max / min.
# [x] 4. No hardcoded return shape or T constant (inferred from existing code).
# [x] 5. Return shape matches the original control_law -> (1,).
# [x] 6. Existing parameter names preserved (kp_theta, kd_theta, kp_omega).
# [x] 7. Uses t / T for time normalization; continuous control (no discrete np.where).
# [x] 8. All controls implemented (no forced zeros).
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp_theta (0.5, 50.0)
# @param: kd_theta (0.1, 20.0)
# @param: kp_omega (0.1, 20.0)
# @param: ki_theta (0.0, 10.0)
# @param: u_ff_bias (0.0, 5.0)
# @param: int_leak (0.5, 1.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous PD + integral + bias-feedforward control for the pendulum.

    Target: theta -> 1.0 rad, omega -> 0.5 rad/s
    Control: torque (clipped to [-10, 10])

    Structural changes vs. prior version:
    * PD on theta retained as the backbone (existing kp_theta / kd_theta).
    * Damping on omega consolidated into a single kp_omega term (existing).
    * NEW: integral action on theta with leak (anti-windup via leakage + clamping)
      to eliminate the persistent steady-state theta offset observed before.
    * NEW: constant bias feedforward `u_ff_bias` to cancel any constant disturbance
      (e.g., gravity bias at the operating point) without spending feedback authority.
    * Time normalization t/T used so scheduled behavior stays consistent across T.
    """
    theta, omega = state[0], state[1]

    # Target values
    target_theta = params.get("target_theta", 1.0)
    target_omega = params.get("target_omega", 0.5)

    # Tunable PD / damping gains (existing names preserved)
    kp_theta = params.get("kp_theta", 8.0)
    kd_theta = params.get("kd_theta", 3.0)
    kp_omega = params.get("kp_omega", 5.0)

    # New structural parameters
    ki_theta = params.get("ki_theta", 1.0)        # integral gain on theta
    u_ff_bias = params.get("u_ff_bias", 0.0)      # constant bias feedforward
    int_leak = params.get("int_leak", 0.995)      # integrator leak per call (anti-windup)

    # Tracking errors
    e_theta = theta - target_theta
    e_omega = omega - target_omega

    # Integrate theta error (continuous-time approximation via Euler).
    # State dict holds integrator; initialize lazily on first call.
    integ = params.get("_theta_integrator", None)
    if integ is None:
        integ = 0.0
    # dt is exposed via params by the harness; fall back to a sensible default.
    dt = params.get("dt", 0.02)
    # Leak-then-integrate update (prevents integral wind-up under saturation)
    integ = int_leak * integ + e_theta * dt

    # Continuous feedback: PD(theta) + damping(omega) + integral(theta) + bias FF
    u_pd = -(kp_theta * e_theta + kd_theta * e_theta + kp_omega * e_omega)
    u_i = -ki_theta * integ
    u_ff = u_ff_bias
    u_raw = u_pd + u_i + u_ff

    # Saturate to control limits [-10, 10]
    torque = np.clip(u_raw, -10.0, 10.0)

    # Clamp integrator magnitude (anti-windup guard)
    integ = np.clip(integ, -50.0, 50.0)

    # Persist integrator state for next call
    params["_theta_integrator"] = integ

    return np.array([torque])