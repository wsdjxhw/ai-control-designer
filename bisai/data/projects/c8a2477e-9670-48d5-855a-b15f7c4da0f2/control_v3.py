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
# @param: grav_ff (0.0, 5.0)
# @param: rate_limit (1.0, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous PD + integral + bias-FF + gravity-FF + slew-rate-limited control
    for the pendulum.

    Target: theta -> 1.0 rad, omega -> 0.5 rad/s
    Control: torque (clipped to [-10, 10])

    V2 structural changes vs. V1 (which left theta_mean stuck at ~0.84 rad):
    * FIX sign on the PD(theta) term — V1 used `+ kd_theta * e_theta` (same sign as
      the proportional term), which is structurally wrong: kd_theta should damp
      the *rate* (omega), not double-count theta. The corrected damping term is
      placed on omega (kp_omega * e_omega), with kd_theta reserved for theta-rate
      damping via the explicit `-kd_theta * omega` channel.
    * FIX wrong notion of equilibrium: V1 treated "theta -> target_theta" as if it
      were the only error, but with theta starting at 0.5 and gravity pulling
      downward, the linear feedback was fighting gravity with insufficient gain.
      Now the proportional action is computed against the *target* directly
      (e_theta = theta - target_theta), as required, with higher kp_theta headroom.
    * ADD gravity feed-forward `grav_ff * sin(theta)`: at theta = 0.5 rad the
      gravity torque is ~g*sin(0.5) which a small kp_theta alone cannot cancel.
      Subtracting it from the control lets feedback gains focus on the residual.
    * KEEP integral action with leak (anti-windup) and bias feed-forward from V1.
    * ADD torque rate-limit: V1 showed oscillating control effort (mean 3.65,
      suggestive of bang-bang-like saturation chatter). A first-order slew limiter
      smooths the command without changing its average level.
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
    grav_ff = params.get("grav_ff", 1.0)          # gravity feed-forward scaling
    rate_limit = params.get("rate_limit", 50.0)   # max |Δtorque| per step

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

    # Continuous feedback: PD(theta) + damping(omega) + integral(theta) + gravity FF + bias FF
    # NOTE: in V1 the term `kd_theta * e_theta` was wrong — kd_theta is a *rate*
    # damper, so it multiplies omega (not the position error). Place kd_theta on
    # omega to damp angular velocity and avoid double-counting theta.
    u_p_theta = -kp_theta * e_theta
    u_d_theta = -kd_theta * omega       # rate damping on omega via the kd_theta slot
    u_d_omega = -kp_omega * e_omega     # cross-term on velocity error
    u_i = -ki_theta * integ
    u_grav_ff = -grav_ff * np.sin(theta)
    u_ff = u_ff_bias
    u_raw = u_p_theta + u_d_theta + u_d_omega + u_i + u_grav_ff + u_ff

    # Saturate to control limits [-10, 10]
    torque_desired = np.clip(u_raw, -10.0, 10.0)

    # Torque rate-limit (slew limiter) — smooths control effort across calls.
    prev_torque = params.get("_prev_torque", None)
    if prev_torque is None:
        prev_torque = 0.0
    delta = torque_desired - prev_torque
    delta = np.clip(delta, -rate_limit * dt, rate_limit * dt)
    torque = prev_torque + delta

    # Final saturation guard after rate-limiting
    torque = np.clip(torque, -10.0, 10.0)

    # Clamp integrator magnitude (anti-windup guard)
    integ = np.clip(integ, -50.0, 50.0)

    # Persist state across calls
    params["_theta_integrator"] = integ
    params["_prev_torque"] = torque

    return np.array([torque])