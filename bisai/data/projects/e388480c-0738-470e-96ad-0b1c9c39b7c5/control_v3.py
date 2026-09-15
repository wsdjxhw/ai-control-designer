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
# @param: theta_cubic_gain (0.001, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Improved pendulum regulation controller.

    Modification relative to previous version:
    - Preserves the successful PD backbone and all existing parameter names.
    - Retains the bounded pendulum-consistent sin(theta) restoring action.
    - Adds a cubic stabilization term to increase corrective effort for
      moderate angular deviations without requiring excessively large kp.
    - Continuous control only, with final saturation through np.clip.
    """

    theta, omega = state

    kp = params.get("kp", 12.0)
    kd = params.get("kd", 4.0)
    torque_limit = params.get("torque_limit", 20.0)
    nonlinear_gain = params.get("nonlinear_gain", 3.0)
    theta_cubic_gain = params.get("theta_cubic_gain", 1.5)

    theta_error = theta
    omega_error = omega

    linear_term = -kp * theta_error
    damping_term = -kd * omega_error

    # Pendulum-aware restoring action
    nonlinear_term = -nonlinear_gain * np.sin(theta_error)

    # Structural enhancement: stronger correction away from the origin
    cubic_term = -theta_cubic_gain * (theta_error ** 3)

    torque = linear_term + damping_term + nonlinear_term + cubic_term
    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])