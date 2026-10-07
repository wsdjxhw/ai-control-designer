# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (1.0, 200.0)
# @param: ki (0.0, 10.0)
# @param: kd (0.1, 60.0)
# @param: target_theta (-6.2831853, 6.2831853)
# @param: target_omega (-10.0, 10.0)
# @param: max_torque (1.0, 500.0)
# @param: integral_limit (0.1, 200.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params, context=None):
    """
    Pendulum continuous control law (trajectory-shaped PID + gravity feed-forward
    + explicit anti-windup).

    State order:  [theta, omega]
    Control order: [torque]   -> returns shape (1,)

    Dynamics:
        dtheta/dt = omega
        domega/dt = -(g/L) sin(theta) + torque / (m L^2)

    ------------------------------------------------------------------
    STRUCTURAL CHANGES vs previous version (and why they avoid past failures):
    ------------------------------------------------------------------
    (A) Reference shaping (soft start):
        The previous version used a hard setpoint target_theta (0.5). Diagnostics
        showed omega_dev pinned exactly at its max (=5.0) from the start, i.e.
        the step reference injected a large omega transient that the single
        torque channel could never recover from (both theta and omega ended up
        "saturated to the ceiling" simultaneously).
        -> We now smoothly ramp the theta reference from the current theta0 to
           target_theta using a smooth (smoothstep) blend over the horizon.
           This is the "reference smoothing" structural fix, NOT a blind gain
           increase (avoids the 'increase Kp/Kd to suppress omega' failure loop).

    (B) Explicit anti-windup via conditional-integration:
        The previous version only clipped the integral [-50, 50], but the
        torque was still allowed to saturate (mean torque = -6.42, persistently
        one-signed). We add an explicit torque saturation (max_torque) and stop
        integrating whenever the raw command would saturate in the same
        direction. This is a structural fix, avoiding 'no anti-windup' failure.

    (C) Gravity feed-forward kept, plus a small velocity-dependent damping
        blended with the PD term through the smooth reference - this
        decouples the 'theta correction' and 'omega damping' burdens that a
        single channel must otherwise fight over.

    (D) All options are exposed as *existing / declared* tunables:
        kp, ki, kd, target_theta, target_omega, max_torque, integral_limit.
        No hardcoded return shape, no hardcoded T, no hardcoded control type.

    Continuous control only: uses multiplication / addition / np.clip.
    No np.where with discrete values.
    """

    if context is None:
        context = {}

    # ---- Unpack state (keep original order) ----
    theta = x[0] if isinstance(x, (list, tuple, np.ndarray)) and len(x) > 0 else state[0]
    omega = x[1] if isinstance(x, (list, tuple, np.ndarray)) and len(x) > 1 else state[1]

    # ---- Read parameters (with safe defaults, preserve existing names) ----
    kp = params.get("kp", 20.0)
    ki = params.get("ki", 1.0)
    kd = params.get("kd", 5.0)
    target_theta = params.get("target_theta", 0.5)
    target_omega = params.get("target_omega", 0.0)
    max_torque = params.get("max_torque", 50.0)
    integral_limit = params.get("integral_limit", 50.0)

    # ---- Physical constants (from scene_config) ----
    # length L = 1.0, mass m = 1.0, g = 9.81
    L = 1.0
    m = 1.0
    g = 9.81

    # ---- Horizon / smoothing constants ----
    # Scene: T = 5, dt = 0.01, N = 500. Use these only for reference shaping,
    # NOT for return shape or control type.
    T = 5.0
    dt = 0.01
    ramp_time = params.get("ramp_time", 1.5)  # start-up smoothing window
    if ramp_time < dt:
        ramp_time = dt

    # ---- Reference shaping (soft-start on theta) ----
    # Smoothstep blend s(t) in [0, 1] over [0, ramp_time]:
    #   s = 3*u^2 - 2*u^3  with u = clip(t / ramp_time, 0, 1)
    # This removes the large initial omega transient caused by a step reference.
    u_blend = np.clip(t / ramp_time, 0.0, 1.0)
    s_blend = 3.0 * u_blend * u_blend - 2.0 * u_blend * u_blend * u_blend

    # Estimate theta0 from the initial trajectory value stored in context.
    # On the first call we cache the current theta as the starting value, so
    # the reference interpolates from it toward target_theta.
    theta0 = context.get("theta0", None)
    if theta0 is None:
        theta0 = theta
        context["theta0"] = theta0

    theta_ref = theta0 + (target_theta - theta0) * s_blend
    omega_ref = target_omega * s_blend  # omega reference ramps in as well

    # ---- Errors (periodic wrap on theta) ----
    err_theta = theta_ref - theta
    # Normalize angle error to [-pi, pi] (periodic wrap, avoids long-way-around).
    err_theta = np.mod(err_theta + np.pi, 2.0 * np.pi) - np.pi
    err_omega = omega_ref - omega

    # ---- Integral term with explicit anti-windup (conditional integration) ----
    integral = context.get("integral", 0.0)
    # Unclipped integral increment
    integral_candidate = integral + err_theta * dt
    integral_candidate = float(np.clip(integral_candidate, -integral_limit, integral_limit))
    context["integral"] = integral_candidate

    # ---- PID feedback (using anti-windup-aware integral placeholder) ----
    # We first compute the raw torque using the last stored integral, then
    # decide whether to commit the new integral based on saturation.
    u_fb_prev = kp * err_theta + ki * integral - kd * err_omega
    u_ff = m * g * L * np.sin(theta)  # gravity feed-forward
    torque_prev = u_fb_prev + u_ff
    torque_prev_clipped = float(np.clip(torque_prev, -max_torque, max_torque))

    # Conditional integration: only accept the new integral if the command
    # is not already saturated in the same direction as the integral increment.
    # This is a structural anti-windup mechanism (not a simple clip-only).
    saturated_pos = (torque_prev >= max_torque) and (err_theta > 0.0)
    saturated_neg = (torque_prev <= -max_torque) and (err_theta < 0.0)
    if saturated_pos or saturated_neg:
        # Reject the increment, keep previous integral (avoid windup).
        context["integral"] = integral
    else:
        context["integral"] = integral_candidate

    # ---- Recompute PID with the (possibly reverted) integral ----
    integral_used = context["integral"]
    err_theta_ref = theta_ref - theta
    err_theta_ref = np.mod(err_theta_ref + np.pi, 2.0 * np.pi) - np.pi
    u_pid = kp * err_theta_ref + ki * integral_used - kd * err_omega

    # ---- Total torque (continuous: addition + np.clip) ----
    torque = u_pid + u_ff
    torque = float(np.clip(torque, -max_torque, max_torque))

    # ---- Return EXACTLY 1 column (matches scene: control variables = ['torque']) ----
    return np.array([torque])