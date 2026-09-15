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
# @param: kp_schedule_gain (0.0, 20.0)
# @param: bias_gain (0.01, 20.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Pendulum regulation controller.

    Structural changes relative to earlier versions:
    - Preserves the successful PD damping core.
    - Adds smooth gain scheduling based on |theta| instead of simply increasing kp.
    - Adds a bounded low-frequency bias-cancellation term using tanh(theta),
      targeting the persistent theta offset highlighted by diagnostics.
    - Retains pendulum-aware nonlinear feedback and cubic correction.
    - Continuous control only with final saturation through np.clip.

    These changes introduce new feedback behavior rather than repeating
    unsuccessful gain-escalation strategies.
    """

    theta, omega = state

    kp = params.get("kp", 12.0)
    kd = params.get("kd", 4.0)
    torque_limit = params.get("torque_limit", 20.0)
    nonlinear_gain = params.get("nonlinear_gain", 3.0)
    theta_cubic_gain = params.get("theta_cubic_gain", 1.5)

    kp_schedule_gain = params.get("kp_schedule_gain", 4.0)
    bias_gain = params.get("bias_gain", 2.0)

    theta_error = theta
    omega_error = omega

    # Smooth gain scheduling:
    # stronger position feedback for larger angular deviations,
    # while remaining continuous and differentiable.
    scheduled_kp = kp * (1.0 + kp_schedule_gain * np.abs(theta_error) / (1.0 + np.abs(theta_error)))

    linear_term = -scheduled_kp * theta_error
    damping_term = -kd * omega_error

    # Pendulum-aware restoring action.
    nonlinear_term = -nonlinear_gain * np.sin(theta_error)

    # Stronger correction away from the origin.
    cubic_term = -theta_cubic_gain * (theta_error ** 3)

    # Bounded bias-rejection term aimed at persistent residual theta error.
    bias_cancellation_term = -bias_gain * np.tanh(theta_error)

    torque = (
        linear_term
        + damping_term
        + nonlinear_term
        + cubic_term
        + bias_cancellation_term
    )

    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])