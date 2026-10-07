# ========== VECTORIZATION SELF-CHECK ==========
# [x] 1. No `float(`, `int(`, `bool(` on arrays. Use `.astype()` instead.
# [x] 2. `np.where` uses `&` / `|`, NOT `and` / `or`.
# [x] 3. `np.max` / `np.min` / `np.abs` used (not Python built-ins).
# [x] 4. No `for i in range(M+1)` loops.
# [x] 5. Return shape: `(M+1, N_control)` for PDE, `(N_control,)` for ODE.
# [x] 6. All controls implemented (no forced zeros).
# [x] 7. Uses `t / T` for time normalization if needed.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: Kp_omega (0.01, 10.0)
# @param: Ki_omega (0.0, 5.0)
# @param: Kd_current (0.0, 1.0)
# @param: ff_gain (0.0, 5.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous state-feedback control for a DC motor.

    Target: track omega -> omega_target, current -> 0 (minimum-loss).
    Strategy: PD on speed error + feed-forward from target/back-EMF,
    with a light proportional on current to damp electrical transients.
    """
    # State unpacking (order = scene_config["state_names"])
    omega, current = state

    # Targets (read once; cost_function targets are authoritative)
    omega_target = 100.0
    current_target = 0.0

    # Tunable gains
    Kp_omega = float(params.get("Kp_omega", 0.5))
    Ki_omega = float(params.get("Ki_omega", 0.1))
    Kd_current = float(params.get("Kd_current", 0.05))
    ff_gain = float(params.get("ff_gain", 1.0))

    # Physical parameters (fall back to model defaults if not provided)
    R = float(params.get("R", 1.0))
    Ke = float(params.get("Ke", 1.0))
    B = float(params.get("B", 0.1))
    Kt = float(params.get("Kt", 1.0))
    J = float(params.get("J", 0.01))

    # Normalized time (T = 5 s)
    T = float(params.get("T", 5.0))
    tau = np.clip(t / T, 0.0, 1.0)

    # Smooth ramp-in of the reference to avoid bang at t=0
    ramp = 1.0 - np.exp(-3.0 * tau)
    omega_ref = omega_target * ramp

    # Errors
    e_omega = omega - omega_ref
    e_current = current - current_target

    # Integral-like correction (with anti-windup clipping)
    e_int = (e_omega * np.clip(tau, 0.0, 1.0)).astype(float)
    integral_term = np.clip(e_int, -50.0, 50.0)

    # Feed-forward: compensate back-EMF + friction + load to hold reference
    u_ff = ff_gain * (Ke * omega_ref + R * (B * omega_ref / np.maximum(Kt, 1e-6))) \
           * (current_target + 1.0) / 2.0
    # Simpler robust feed-forward: cancel steady-state back-EMF
    u_ff = ff_gain * (Ke * omega_ref)

    # PD on speed + light P on current
    u_unsat = (Kp_omega * e_omega
               + Ki_omega * integral_term
               + Kd_current * e_current
               + u_ff)

    # Saturate to physical voltage limit [-Vmax, Vmax] = [-24, 24]
    Vmax = 24.0
    u = np.clip(u_unsat, -Vmax, Vmax)

    return np.array([u], dtype=float)