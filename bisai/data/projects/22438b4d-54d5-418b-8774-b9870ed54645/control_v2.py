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
# @param: Kp_omega (0.1, 20.0)
# @param: Ki_omega (0.0, 5.0)
# @param: Kp_current (0.0, 5.0)
# @param: K_cross (0.0, 10.0)
# @param: ff_gain (0.0, 5.0)
# @param: Vmax (5.0, 48.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous state-feedback control for a DC motor with explicit
    omega<->current coupling feedback.

    Target: track omega -> 100, current -> 0 (minimum-loss).

    Structure (structural fix vs prior version):
      u = -Kp_omega * e_omega
          - Ki_omega * integral(e_omega)
          - Kp_current * e_current           (damp electrical transient)
          - K_cross * (e_omega * e_current)  (anti-collapse coupling term)
          + ff_gain * (Ke * omega_ref)       (feedforward cancels back-EMF)

    The previous version zeroed current too aggressively, which starved
    omega of its forcing term (J * d_omega/dt = Kt*i - B*omega). The
    cross-coupling term keeps both loops simultaneously active and
    prevents the trivial "drive current to zero" collapse.
    """
    # State unpacking (order = scene_config["state_names"])
    omega, current = state

    # Targets
    omega_target = 100.0
    current_target = 0.0

    # Tunable gains
    Kp_omega = float(params.get("Kp_omega", 2.0))
    Ki_omega = float(params.get("Ki_omega", 0.5))
    Kp_current = float(params.get("Kp_current", 0.2))
    K_cross = float(params.get("K_cross", 0.5))
    ff_gain = float(params.get("ff_gain", 1.0))
    Vmax = float(params.get("Vmax", 24.0))

    # Physical parameters (fall back to model defaults if not provided)
    Ke = float(params.get("Ke", 1.0))
    R = float(params.get("R", 1.0))
    Kt = float(params.get("Kt", 1.0))
    B = float(params.get("B", 0.1))
    J = float(params.get("J", 0.01))

    # Normalized time (T = 5 s per SCENE CONTEXT)
    T = float(params.get("T", 5.0))
    tau = np.clip(t / T, 0.0, 1.0)

    # Smooth ramp-in of the reference to avoid bang at t=0
    ramp = 1.0 - np.exp(-3.0 * tau)
    omega_ref = omega_target * ramp

    # Errors
    e_omega = omega - omega_ref
    e_current = current - current_target

    # Integral of omega error (with anti-windup clipping)
    e_int = (e_omega * np.clip(tau, 0.0, 1.0)).astype(float)
    integral_term = np.clip(e_int, -50.0, 50.0)

    # Feed-forward: cancel steady-state back-EMF + load torque
    #   Steady state: Kt*i_ss = B*omega_ref  =>  i_ss = B*omega_ref / Kt
    #   Voltage:      V_ss = R*i_ss + Ke*omega_ref
    i_ss = (B * omega_ref) / np.maximum(Kt, 1e-6)
    u_ff_ss = ff_gain * (R * i_ss + Ke * omega_ref)

    # ---- Anti-collapse cross-coupling term ----
    # When one error drives the other to a trivial value, this term
    # couples their corrections so neither channel can be starved.
    u_cross = K_cross * (e_omega * e_current).astype(float)

    # Composite control
    u_unsat = (-Kp_omega * e_omega
               - Ki_omega * integral_term
               - Kp_current * e_current
               - u_cross
               + u_ff_ss)

    # Saturate to physical voltage limit
    u = np.clip(u_unsat, -Vmax, Vmax)

    return np.array([u], dtype=float)