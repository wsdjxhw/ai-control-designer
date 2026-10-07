# ========== VECTORIZATION SELF-CHECK ==========
# [x] 1. No float(, int(, bool( applied to any array or comparison expression.
# [x] 2. All np.where conditions use & or |, not and or or.
# [x] 3. np.max / np.min used instead of max / min.
# [x] 4. No hardcoded return shape or T constant (inferred from existing code).
# [x] 5. Return shape matches the original control_law: (1,) for single voltage.
# [x] 6. Existing parameter names preserved (kp, ki, kd, ff_gain) + new ones clearly added.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 100.0)
# @param: ki (0.0, 50.0)
# @param: kd (0.0, 50.0)
# @param: ff_gain (0.0, 50.0)
# @param: kd_omega (0.0, 50.0)
# @param: ki_omega (0.0, 50.0)
# @param: kff_omega (0.0, 50.0)
# @param: omega_weight (0.0, 10.0)
# @param: current_weight (0.0, 10.0)
# @param: v_max (1.0, 24.0)
# @param: tau_aw (0.01, 2.0)
# @param: slew_rate (1.0, 200.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    DC motor cascade control -- V3 structural revision.

    Failure pattern of V1/V2 (both cost 1873.87) and what we change:

      V1/V2 pathology: 4-9 gains all hammered to large values, yet omega
      completely diverges (final_dev=100, integrated_dev=50000). The cost is
      stuck at 1873.87 across versions -- a clear sign that adding more
      knobs in the same structural form does not help. The diagnostic also
      showed cross-channel parameter reuse (kd_omega == V1_ki) and near-
      symmetric omega_weight/current_weight, which lets the optimizer
      satisfy current at the expense of omega.

      Three structural fixes layered together:

      1) ASYMMETRIC PRIORITY WEIGHTING (hard). omega_weight and
         current_weight were stuck near 1.56 each -- a symmetric optimum
         where current is over-served and omega is starved. We compute an
         effective weight pair (omega_w_eff, current_w_eff) that is
         explicitly asymmetric in proportion to current error magnitude,
         so the optimizer can break the symmetry without renaming params.

      2) DECOUPLED CHANNEL ALLOCATION. Previously, raw_total = u_omega +
         u_current and we scaled both by a global share. That meant
         omega's command was always riding on top of current's. We
         restructure into two independent sub-demands, each clipped to
         its own channel envelope, then summed. This directly addresses
         the "kff_omega drowned by ff_gain" structural complaint.

      3) TWO-STAGE ANTI-WINDUP. Stage one: clamping-aware integrator
         reset on the omega integral (back-calculation). Stage two: a
         separate integral cap on the current-side integral (held in
         x[2] if provided, else 0) to prevent the inner loop from
         re-saturating when omega is still off. dt is inferred from the
         scene (0.02) but used only as a scaling constant; no T is
         hardcoded.

    Control input: voltage u in [-v_max, +v_max] V.
    State: [omega, current], target omega = 100 rad/s, current -> 0.
    """
    omega = state[0]
    current = state[1]

    target_omega = 100.0

    # ---- Tunable parameters ----
    kp            = params.get("kp", 5.0)
    ki            = params.get("ki", 2.0)
    kd            = params.get("kd", 0.5)
    ff_gain       = params.get("ff_gain", 1.0)

    kd_omega      = params.get("kd_omega", 0.05)
    ki_omega      = params.get("ki_omega", 0.5)
    kff_omega     = params.get("kff_omega", 0.0)

    omega_weight  = params.get("omega_weight", 1.0)
    current_weight = params.get("current_weight", 1.0)

    v_max         = params.get("v_max", 12.0)
    tau_aw        = params.get("tau_aw", 0.1)
    slew_rate     = params.get("slew_rate", 120.0)

    dt = 0.02  # scene context

    # ---- Stateless memory from x (if provided) ----
    if x is None or len(x) < 1:
        omega_integral = 0.0
    else:
        omega_integral = x[0]

    if x is None or len(x) < 2:
        u_prev = 0.0
    else:
        u_prev = x[1]

    if x is None or len(x) < 3:
        current_integral = 0.0
    else:
        current_integral = x[2]

    # ---- Outer loop: omega tracking ----
    omega_error = target_omega - omega

    # FIX 1: Asymmetric effective weights. Force omega to dominate when
    # its error is large relative to current's. The asymmetry is computed
    # from the live errors, not from a static pair, so even if the
    # optimizer leaves omega_weight == current_weight (V2 pathology), the
    # effective allocation still favors omega.
    omega_err_abs   = np.abs(omega_error)
    current_err_abs = np.abs(current)
    # Softmax-style scaling: ratio in (0, +inf), then map to (0, 1) for omega share.
    # +1 inside the log keeps the ratio finite when current_err_abs is tiny.
    err_ratio = omega_err_abs / (current_err_abs + 1.0)
    # Convert to a [0,1] priority for omega. log(1 + r) in [0, +inf) is
    # bounded by a smooth saturation so priority stays in (0, 1).
    omega_priority = err_ratio / (1.0 + err_ratio)
    # current priority is the complement.
    current_priority = 1.0 - omega_priority

    # Effective weights blend the user-tunable pair with the live priority.
    # This breaks the V2 symmetric-weight trap: even if both params stay
    # at 1.56, the runtime allocation is asymmetric whenever the errors
    # are asymmetric -- which is the entire 5-second simulation.
    omega_w_eff   = omega_weight   * (0.5 + omega_priority)
    current_w_eff = current_weight * (0.5 + current_priority)

    # ---- Outer sub-demand: omega PD + I + FF ----
    u_omega = (
        kp * omega_error
        + ki_omega * omega_integral
        + kd_omega * (-omega)
        + kff_omega * target_omega
    )

    # ---- Inner sub-demand: current shaping (preserved structure) ----
    u_current = kp * (target_omega - omega) - kd * current + ff_gain * omega
    # Add a small current-side integral term, anti-windup capped, so the
    # inner loop can actually drive current to zero (V1/V2 had no current
    # integral -- it relied entirely on ff_gain, which is the structural
    # reason current_weight is stuck near omega_weight).
    u_current = u_current + ki * current_integral

    # ---- FIX 2: Decoupled channel allocation ----
    # Each sub-demand is scaled by its own effective weight and clipped
    # to its own channel envelope. Then we sum. This stops u_current
    # from drowning u_omega at the actuator, which was the V2 issue.
    omega_env   = v_max * omega_w_eff   / np.maximum(omega_w_eff   + current_w_eff, 1e-6)
    current_env = v_max * current_w_eff / np.maximum(omega_w_eff   + current_w_eff, 1e-6)

    # Half-envelopes (each channel can use at most this much of v_max).
    u_omega_clipped   = np.clip(u_omega,   -omega_env,   omega_env)
    u_current_clipped = np.clip(u_current, -current_env, current_env)

    u_unsat = u_omega_clipped + u_current_clipped

    # ---- FIX 3a: Omega anti-windup via back-calculation ----
    over_drive = u_unsat - np.clip(u_unsat, -v_max, v_max)
    bleed = over_drive / np.maximum(tau_aw, 1e-3)
    omega_integral_clamped = omega_integral - bleed * dt

    # ---- FIX 3b: Current integral cap (prevents inner-loop windup) ----
    # Bound the current-side integral to a small fraction of v_max so it
    # can't push the inner loop into saturation on its own.
    current_integral_cap = v_max * 0.25
    current_integral_clamped = np.clip(
        current_integral,
        -current_integral_cap,
        current_integral_cap,
    )

    # ---- Recompute outer demand with corrected omega integral ----
    u_omega_corr = (
        kp * omega_error
        + ki_omega * omega_integral_clamped
        + kd_omega * (-omega)
        + kff_omega * target_omega
    )
    # Recompute inner demand with capped current integral
    u_current_corr = (
        kp * (target_omega - omega)
        - kd * current
        + ff_gain * omega
        + ki * current_integral_clamped
    )

    # Re-apply the decoupled allocation
    u_omega_c   = np.clip(u_omega_corr,   -omega_env,   omega_env)
    u_current_c = np.clip(u_current_corr, -current_env, current_env)
    u_corr = u_omega_c + u_current_c

    # ---- Smooth saturation (preserved from V2) ----
    u_smooth = v_max * np.tanh(u_corr / np.maximum(v_max, 1e-6))
    u_sat = np.clip(u_smooth, -v_max, v_max)

    # ---- Slew-rate limiter (preserved from V2) ----
    max_step = slew_rate * dt
    delta = u_sat - u_prev
    delta_clamped = np.clip(delta, -max_step, max_step)
    u = u_prev + delta_clamped

    return np.array([u])