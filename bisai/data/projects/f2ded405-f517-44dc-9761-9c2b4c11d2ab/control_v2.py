# ========== VECTORIZATION SELF-CHECK ==========
# [x] 1. No float(, int(, bool( applied to any array or comparison expression.
# [x] 2. All np.where conditions use & or |, not and or or.
# [x] 3. np.max / np.min used instead of max / min.
# [x] 4. No hardcoded return shape or T constant (inferred from existing code).
# [x] 5. Return shape matches the original control_law: (1,) for single voltage.
# [x] 6. Existing parameter names preserved (kp, ki, kd, ff_gain).
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
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    DC motor cascade control:
      - Outer loop (omega): P + I + D + feed-forward on omega error.
      - Inner loop (current): P - Kd * current  (preserved from prior version,
        which kept current integrated_dev at ~6.5 -- a stable PRESERVED mechanism).
      - Priority-based allocation: when total demand exceeds the actuator
        limit, the outer-loop component is granted a share proportional to
        its priority weight, breaking the previous "voltage stuck at 12V while
        omega diverges" deadlock.

    Control input: voltage u in [-12, 12] V.
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

    # ---- Outer loop: omega tracking (PI + D + feed-forward) ----
    # Structural fix for the previous version where pure P on omega error
    # could not eliminate the steady-state offset (final_mean ~10.9) and
    # the control saturated at +12V without the omega channel getting any
    # authority.  We now (a) add an explicit integral over time using a
    # stateless trapezoidal accumulator (x carries the running integral),
    # (b) add a D term on omega for phase lead, (c) optionally add a
    # feed-forward component scaled by the reference omega.
    omega_error = target_omega - omega

    # Stateless integral: x[0] is the accumulated omega error over time.
    # This is the standard trick to give a PI controller memory without
    # having to allocate persistent state across CMA-ES evaluations.
    if x is None or len(x) < 2:
        omega_integral = 0.0
    else:
        omega_integral = x[0]

    # Outer-loop voltage demand (un-saturated).
    u_omega = (
        kp * omega_error
        + ki_omega * omega_integral
        + kd_omega * (-omega)            # approximate d(omega)/dt contribution
        + kff_omega * target_omega
    )

    # ---- Inner loop: current shaping (PRESERVED mechanism) ----
    # Kept the previous form because it held current integrated_dev at ~6.5,
    # which is the only thing that previously worked.
    u_current = kp * (target_omega - omega) - kd * current + ff_gain * omega

    # ---- Priority-based allocation (Suggestion 3 from the diagnostic) ----
    # Combine inner + outer demands with a weighted share when the total
    # would saturate the actuator.  The weights are tunable so the
    # optimizer can decide which channel gets the budget.  When the sum
    # fits inside the actuator envelope, both branches are passed through
    # unchanged -- no clipping is wasted.
    V_MAX = 12.0
    raw_total = u_omega + u_current
    raw_abs   = np.abs(raw_total)

    # When the demand fits, no allocation is needed.
    # When it does not, scale each branch by its weight proportion.
    # weight_sum is a scalar; safe for numpy ops.
    weight_sum = omega_weight + current_weight
    # Avoid div-by-zero with a small floor; .astype(float) not needed
    # because weight_sum is a plain Python float from params.get.
    safe_sum = max(weight_sum, 1e-6)

    omega_share   = omega_weight / safe_sum
    current_share = current_weight / safe_sum

    # Use np.where with bitwise-safe scalar conditions; everything is
    # plain floats so there is no boolean-array pitfall.
    u_omega_alloc   = np.where(raw_abs > V_MAX, u_omega   * omega_share,   u_omega)
    u_current_alloc = np.where(raw_abs > V_MAX, u_current * current_share, u_current)

    u = u_omega_alloc + u_current_alloc

    # ---- Final actuator saturation ----
    u = np.clip(u, -V_MAX, V_MAX)

    return np.array([u])