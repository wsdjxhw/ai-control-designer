# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.01, 100.0)
# @param: kd (0.01, 100.0)
# @param: torque_limit (0.1, 100.0)
# @param: ki (0.001, 50.0)
# @param: integral_limit (0.01, 50.0)
# @param: omega_threshold (0.001, 10.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    PI-D pendulum stabilization.

    Modification rationale:
    - Historical diagnostic shows omega converges to zero but theta retains
      persistent steady-state error.
    - Preserve existing PD damping structure (kp, kd).
    - Add conditional integral action to eliminate static error.
    - Enable integration primarily when |omega| is small, avoiding the
      previously identified risk of integral windup during transients.
    - Integral term is bounded with anti-windup clipping.
    """
    theta, omega = state

    target_theta = 0.0
    target_omega = 0.0

    kp = params.get("kp", 10.0)
    kd = params.get("kd", 3.0)
    torque_limit = params.get("torque_limit", 10.0)

    ki = params.get("ki", 2.0)
    integral_limit = params.get("integral_limit", 5.0)
    omega_threshold = params.get("omega_threshold", 0.1)

    theta_error = theta - target_theta
    omega_error = omega - target_omega

    # Persistent controller state for integral action.
    if x is not None and isinstance(x, dict):
        integral_error = x.get("_theta_integral", 0.0)
    else:
        integral_error = 0.0

    # Conditional integration:
    # preserve successful velocity suppression while removing position bias.
    if np.abs(omega_error) < omega_threshold:
        integral_error = integral_error + theta_error

    integral_error = np.clip(
        integral_error,
        -integral_limit,
        integral_limit
    )

    if x is not None and isinstance(x, dict):
        x["_theta_integral"] = integral_error

    torque = (
        -kp * theta_error
        -kd * omega_error
        -ki * integral_error
    )

    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])