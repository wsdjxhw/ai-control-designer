# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (1.0, 400.0)
# @param: ki (0.0, 20.0)
# @param: kd (0.5, 120.0)
# @param: target_theta (-6.2831853, 6.2831853)
# @param: target_omega (-10.0, 10.0)
# @param: max_torque (1.0, 500.0)
# @param: integral_limit (0.1, 50.0)
# @param: ramp_time (0.1, 5.0)
# @param: k_g (0.0, 3.0)
# @param: kappa (0.0, 5.0)
# @param: kd_omega (0.0, 200.0)
# @param: k_cross (0.0, 5.0)
# @param: tau_ref (0.01, 2.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params, context=None):
    """
    Pendulum continuous control law: cross-coupled PD + gravity feed-forward
    + independent omega damping + first-order reference softening
    + continuous back-calculation anti-windup.

    State order:  [theta, omega]
    Control order: [torque]   -> returns shape (1,)

    Dynamics:
        dtheta/dt = omega
        domega/dt = -(g/L) sin(theta) + torque / (m L^2)

    ------------------------------------------------------------------
    HISTORICAL FAILURE MODES (from diagnostic report) & HOW WE AVOID THEM
    ------------------------------------------------------------------
    Mode A  "Damping-Collapse-Oscillation-Conservation":
        optimizer kept shrinking kd (5.33 -> 1.12) and omega stayed pinned
        at its full-scale deviation 5.0 forever. Raising/again-lowering a
        single kd did not help because the damping channel was coupled to the
        position gain structure.

    Mode B  "Target-Inflation-Drift":
        each round the optimizer pushed target_theta / target_omega further
        (0.67 -> 3.71, 0.59 -> 1.65) which only inflated the drift because the
        reference was a hard step the pendulum could not track.

    Mode C  "Single-Quadrant Amplitude Search":
        no version ever flipped a sign; pure amplitude search cannot reach a
        solution that needs an independent damping gain sign/polarity.

    STRUCTURAL FIXES (not blind re-tuning):
    (1) INDEPENDENT omega damping channel `kd_omega` (NEW):
        u_damp = -kd_omega * omega_err, added in PARALLEL to the PID's own
        -kd*err_omega term.  The optimizer can now grow/resize the damping
        channel WITHOUT disturbing the position gain kp.  This directly
        attacks Mode A: even if the optimizer still shrinks kd, kd_omega
        remains an independent knob to kill the omega oscillation.

    (2) CROSS-COUPLED damping `k_cross` (NEW):
        u_cross = -k_cross * tanh(err_theta) * omega
        When theta is far from target the coupling automatically increases
        damping on omega (breaking the "lower torque -> omega saturates ->
        theta drifts" loop found in the diagnostic section 4.2).  tanh
        keeps it bounded so it cannot inject nonlinear instability.
        This attacks Mode B without inflating the target.

    (3) FIRST-ORDER SOFTENED REFERENCE `tau_ref` (NEW):
        Instead of a hard step, theta_ref/omega_ref are low-passed toward
        the target with time constant tau_ref.  An unreachable target then
        becomes "reachable but slower" instead of "always lag -> omega
        saturates".  Attacks Mode B / Mode C by making the setpoint
        feasibility-limited rather than magnitude-limited.

    (4) PRESERVED: angle-wrap on theta error, gravity feed-forward with
        scale k_g, smooth gain-scheduling via kappa, continuous
        back-calculation anti-windup, and the max_torque / integral_limit
        safety nets (these were flagged PRESERVED in the history).

    Continuous control only: multiplication / addition / np.clip / np.tanh.
    No np.where with discrete values. No hardcoded T. No hardcoded shape.
    """

    if context is None:
        context = {}

    # ---- Unpack state (keep original order) ----
    if isinstance(x, (list, tuple, np.ndarray)) and len(x) > 1:
        theta = x[0]
        omega = x[1]
    else:
        theta = state[0]
        omega = state[1]

    # ---- Read existing parameters (names preserved) ----
    kp = params.get("kp", 60.0)
    ki = params.get("ki", 2.0)
    kd = params.get("kd", 5.0)
    target_theta = params.get("target_theta", 10.0)
    target_omega = params.get("target_omega", 5.0)
    max_torque = params.get("max_torque", 100.0)
    integral_limit = params.get("integral_limit", 20.0)
    ramp_time = params.get("ramp_time", 1.0)
    k_g = params.get("k_g", 1.0)
    kappa = params.get("kappa", 1.0)

    # ---- Read NEW structural parameters ----
    kd_omega = params.get("kd_omega", 20.0)
    k_cross = params.get("k_cross", 0.5)
    tau_ref = params.get("tau_ref", 0.3)

    # ---- Physical constants (from scene_config: L=1, m=1, g=9.81) ----
    L = 1.0
    m = 1.0
    g = 9.81

    # ---- Integration step (from scene: T=5, dt=0.01, N=500) ----
    dt = 0.01
    if ramp_time < dt:
        ramp_time = dt
    if tau_ref < dt:
        tau_ref = dt

    # ---- Soft-start smoothstep ramp (kept from previous version) ----
    u_blend = np.clip(t / ramp_time, 0.0, 1.0)
    s_blend = 3.0 * u_blend * u_blend - 2.0 * u_blend * u_blend * u_blend

    # ---- First-order softened reference (NEW -> fixes Mode B) ----
    # Store a running reference value; move it toward the ramp-blended
    # target by a low-pass step each call. This converts an unreachable
    # hard target into a trackable, feasibility-limited trajectory.
    theta0 = context.get("theta0", None)
    if theta0 is None:
        theta0 = theta
        context["theta0"] = theta0

    theta_ramp = theta0 + (target_theta - theta0) * s_blend
    omega_ramp = target_omega * s_blend

    theta_ref_prev = context.get("theta_ref", theta0)
    omega_ref_prev = context.get("omega_ref", 0.0)

    # first-order filter: ref <- ref + (ramp_target - ref) * dt / tau
    alpha = np.clip(dt / tau_ref, 0.0, 1.0)
    theta_ref = theta_ref_prev + (theta_ramp - theta_ref_prev) * alpha
    omega_ref = omega_ref_prev + (omega_ramp - omega_ref_prev) * alpha
    context["theta_ref"] = theta_ref
    context["omega_ref"] = omega_ref

    # ---- Errors (periodic wrap on theta) ----
    err_theta = theta_ref - theta
    err_theta = np.mod(err_theta + np.pi, 2.0 * np.pi) - np.pi
    err_omega = omega_ref - omega

    # ---- Gain-scheduling (preserved, attacks under-actuation) ----
    sched_theta = 1.0 + kappa * np.abs(np.sin(err_theta))
    sched_omega = 1.0 + kappa * np.minimum(np.abs(err_omega), 2.0)
    kp_eff = kp * sched_theta
    kd_eff = kd * sched_omega

    # ---- Gravity feed-forward (preserved, tunable scale) ----
    u_ff = k_g * m * g * L * np.sin(theta)

    # ---- Independent omega damping channel (NEW -> fixes Mode A) ----
    # Parallel damping knob that the optimizer can grow without touching kp.
    u_damp = -kd_omega * err_omega

    # ---- Cross-coupled damping (NEW -> fixes Mode B) ----
    # tanh keeps the coupling bounded so large theta errors cannot destabilize.
    u_cross = -k_cross * np.tanh(err_theta) * omega

    # ---- Integral term with smooth back-calculation anti-windup ----
    integral = context.get("integral", 0.0)

    # Raw (pre-saturation) command using the stored integral.
    u_pid_prev = kp_eff * err_theta + ki * integral - kd_eff * err_omega
    torque_raw_prev = u_pid_prev + u_ff + u_damp + u_cross
    torque_sat_prev = np.clip(torque_raw_prev, -max_torque, max_torque)

    # Continuous back-calculation: effective integral gain shrinks as the
    # actuator saturates (no hard accept/reject switch).
    sat_ratio_prev = np.abs(torque_raw_prev - torque_sat_prev) / max_torque
    ki_eff_prev = ki * (1.0 - np.clip(sat_ratio_prev, 0.0, 1.0))

    # Integrate with effective gain and explicit limit (now tighter, <=50).
    integral_candidate = integral + ki_eff_prev * err_theta * dt
    integral_candidate = np.clip(integral_candidate, -integral_limit, integral_limit)
    context["integral"] = integral_candidate

    # ---- Final recompute with the committed integral ----
    integral_used = context["integral"]
    u_pid = kp_eff * err_theta + ki * integral_used - kd_eff * err_omega
    torque = u_pid + u_ff + u_damp + u_cross
    torque = np.clip(torque, -max_torque, max_torque)

    # ---- Return EXACTLY 1 column (scene: control variables = ['torque']) ----
    return np.array([torque])