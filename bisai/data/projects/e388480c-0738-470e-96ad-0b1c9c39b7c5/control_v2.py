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
# @param: nonlinear_gain (0.01, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Nonlinear PD stabilization for pendulum regulation.

    Modification rationale:
    - Retains the original PD structure and parameter names.
    - Adds a bounded nonlinear restoring term based on sin(theta),
      which is more consistent with pendulum physics than a purely
      linear proportional term for larger angular deviations.
    - Uses saturation to prevent excessive control effort.
    """
    theta, omega = state

    kp = params.get("kp", 12.0)
    kd = params.get("kd", 4.0)
    torque_limit = params.get("torque_limit", 20.0)
    nonlinear_gain = params.get("nonlinear_gain", 3.0)

    theta_target = 0.0
    omega_target = 0.0

    theta_error = theta - theta_target
    omega_error = omega - omega_target

    linear_term = -kp * theta_error
    damping_term = -kd * omega_error
    nonlinear_term = -nonlinear_gain * np.sin(theta_error)

    torque = linear_term + damping_term + nonlinear_term
    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])