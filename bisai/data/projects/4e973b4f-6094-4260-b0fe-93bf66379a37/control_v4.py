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
# @param: theta_integral_gain (0.0, 20.0)
# @param: theta_feedforward_gain (0.0, 20.0)
# @param: torque_limit (0.1, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Pendulum continuous stabilization controller.

    Structural changes:
    - Keeps the effective omega damping path because omega regulation was already solved.
    - Adds nonlinear feedforward compensation for theta dynamics instead of only
      increasing theta_gain, avoiding the previous gain escalation failure mode.
    - Keeps integral compensation bounded by elapsed-time scaling to address the
      persistent theta offset without relying on actuator restriction.
    - Uses continuous torque output through addition, multiplication, and clipping.
    """

    theta, omega = state

    theta_gain = params.get("theta_gain", 20.0)
    omega_gain = params.get("omega_gain", 40.0)
    nonlinear_gain = params.get("nonlinear_gain", 20.0)
    theta_integral_gain = params.get("theta_integral_gain", 2.0)
    theta_feedforward_gain = params.get("theta_feedforward_gain", 5.0)
    torque_limit = params.get("torque_limit", 10.0)

    # Preserve the previously successful angular velocity damping mechanism.
    omega_feedback = omega_gain * omega

    # Proportional theta restoring term.
    theta_feedback = theta_gain * theta

    # Nonlinear compensation:
    # Previous versions increased nonlinear_gain alone without structural change.
    # This term now acts as a smooth feedforward correction rather than just
    # another high-gain feedback path.
    theta_feedforward = theta_feedforward_gain * np.sin(theta)

    # Retain nonlinear parameter as an additional smooth restoring contribution.
    nonlinear_feedback = nonlinear_gain * (np.sin(theta) - theta)

    # Integral-like bias correction for persistent theta offset.
    # The elapsed time t is provided by the simulator; no simulation constants
    # are assumed here.
    theta_integral_feedback = theta_integral_gain * theta * t

    torque = -(
        theta_feedback
        + omega_feedback
        + theta_feedforward
        + nonlinear_feedback
        + theta_integral_feedback
    )

    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])