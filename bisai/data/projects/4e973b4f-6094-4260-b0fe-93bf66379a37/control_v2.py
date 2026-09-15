# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: theta_gain (0.01, 100.0)
# @param: omega_gain (0.01, 100.0)
# @param: nonlinear_gain (0.0, 100.0)
# @param: torque_limit (0.1, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Pendulum stabilization control law.
    Continuous nonlinear PD torque feedback.

    Structural modification:
    - Keeps the original theta/omega feedback structure.
    - Adds a nonlinear sin(theta) correction term to improve convergence
      when the pendulum angle is not infinitesimally small.
    - Avoids relying only on linear feedback, which left a persistent
      theta deviation in previous behavior.
    """
    theta, omega = state

    theta_gain = params.get("theta_gain", 10.0)
    omega_gain = params.get("omega_gain", 3.0)
    nonlinear_gain = params.get("nonlinear_gain", 5.0)
    torque_limit = params.get("torque_limit", 20.0)

    linear_feedback = theta_gain * theta + omega_gain * omega
    nonlinear_feedback = nonlinear_gain * np.sin(theta)

    torque = -(linear_feedback + nonlinear_feedback)
    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])