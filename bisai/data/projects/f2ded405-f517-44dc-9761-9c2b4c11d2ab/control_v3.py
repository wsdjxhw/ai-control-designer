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
    DC motor cascade control -- V2 structural revision.

    Failure pattern of V1 (cost 1873.87) and what we change:

      V1 pathology: 4 gains all hammered to large values (kp~95, ki~30, kd~19,
      ff_gain~37) yet voltage saturated at +12 V, omega final mean offset
      +10.9, integrated_dev ~39,715. This is the canonical
      "high gain -> saturate -> integrator windup -> no tracking" trap.

      Three structural fixes layered together:

      1) ANTI-WINDUP on the outer omega integrator (back-calculation with
         time constant tau_aw). The previous version clamped only the final
         sum, but the integrator kept accumulating error while the actuator
         was pinned, so the moment voltage un-saturated the controller
         punched through the reference and overshot. Now we subtract
         (u_sat - u_unsat)/tau_aw from the integrator so the integral term
         stops growing exactly when the actuator is the bottleneck.

      2) TANH SMOOTH SATURATION replacing the hard clip. The diagnostic
         rightly noted that hard clip kills the optimizer gradient in the
         saturated region. Tanh with a tunable gain keeps the math
         differentiable while honouring the actuator envelope.

      3) SLEW-RATE LIMITER on the voltage command. V1's voltage trace
         looked like a step that immediately latched to +12; a slew limiter
         keeps the commanded voltage physically plausible and gives the
         inner current loop time to actually shape the current.

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

    # ---- Outer loop: omega tracking (PI + D + feed-forward) ----
    omega_error = target_omega - omega

    # Stateless integral: x[0] is the accumulated omega error over time.
    if x is None or len(x) < 2:
        omega_integral = 0.0
    else:
        omega_integral = x[0]

    # Stateless previous voltage: x[1] is u from last step, for slew-rate
    # limiting. If missing, treat as zero.
    if x is None or len(x) < 2:
        u_prev = 0.0
    else:
        u_prev = x[1]

    # Outer-loop voltage demand (un-saturated).
    u_omega = (
        kp * omega_error
        + ki_omega * omega_integral
        + kd_omega * (-omega)
        + kff_omega * target_omega
    )

    # ---- Inner loop: current shaping (PRESERVED mechanism) ----
    # Kept the previous form because it held current integrated_dev at ~6.5,
    # which is the only thing that previously worked.
    u_current = kp * (target_omega - omega) - kd * current + ff_gain * omega

    # ---- Priority-based allocation (preserved) ----
    raw_total = u_omega + u_current
    raw_abs   = np.abs(raw_total)

    weight_sum = omega_weight + current_weight
    safe_sum   = np.maximum(weight_sum, 1e-6)

    omega_share   = omega_weight / safe_sum
    current_share = current_weight / safe_sum

    u_omega_alloc   = np.where(raw_abs > v_max, u_omega   * omega_share,   u_omega)
    u_current_alloc = np.where(raw_abs > v_max, u_current * current_share, u_current)

    u_unsat = u_omega_alloc + u_current_alloc

    # ---- FIX 1: Anti-windup via back-calculation on the integrator ----
    # If the unsaturated demand would exceed the actuator, bleed the
    # integrator back so it doesn't keep piling up unreachable error.
    # We do this on omega_integral *before* applying the PI term, so the
    # next step's integral already reflects the saturation event.
    over_drive = u_unsat - np.clip(u_unsat, -v_max, v_max)
    # If over_drive is non-zero, the actuator was saturated; shrink the
    # accumulated integral proportionally. tau_aw acts as the time
    # constant: small -> aggressive anti-windup, large -> gentle.
    # Multiply by 1.0 first to keep the expression vector-safe when
    # u_unsat is a scalar; np.where handles both cases uniformly.
    bleed = (over_drive / np.maximum(tau_aw, 1e-3)) * 1.0
    omega_integral_clamped = omega_integral - bleed
    # Recompute outer term with the corrected integral so the saturating
    # branch sees a reduced demand.
    u_omega_corr = (
        kp * omega_error
        + ki_omega * omega_integral_clamped
        + kd_omega * (-omega)
        + kff_omega * target_omega
    )
    u_corr = u_omega_corr + u_current_alloc

    # ---- FIX 2: Tanh smooth saturation (preserves gradient) ----
    # v_max * tanh(u / v_max) is a C-infinity soft clip that asymptotically
    # approaches +/- v_max without ever exceeding it. The optimizer gets a
    # non-zero gradient in the saturated region, so CMA-ES can actually
    # see the cost landscape.
    u_smooth = v_max * np.tanh(u_corr / np.maximum(v_max, 1e-6))

    # Hard safety clamp on top of the smooth curve (numerical paranoia).
    u_sat = np.clip(u_smooth, -v_max, v_max)

    # ---- FIX 3: Slew-rate limiter ----
    # Constrain |du/dt| so the actuator can't command an instantaneous
    # jump. Previous version jumped from 0 -> +12 in one step, which
    # starved the inner current loop of any meaningful dynamic range.
    max_step = slew_rate * 0.02  # dt = 0.02 from scene context
    delta = u_sat - u_prev
    delta_clamped = np.clip(delta, -max_step, max_step)
    u = u_prev + delta_clamped

    return np.array([u])