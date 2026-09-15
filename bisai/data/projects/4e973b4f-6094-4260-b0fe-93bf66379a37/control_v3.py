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
# @param: torque_limit (0.1, 50.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Pendulum stabilization control law.

    Structural modification:
    - Preserves the successful omega damping mechanism from the previous version.
    - Adds independent theta integral compensation to address the persistent
      steady-state theta offset observed in diagnostics.
    - Keeps continuous torque output using multiplication, addition, and clipping.
    - Avoids relying only on increasing theta_gain, which could disturb the
      already solved omega regulation.

    Note:
    The simulator provides the state history externally; therefore the integral
    compensation is approximated using the current elapsed time and accumulated
    angle-error estimate from the initial condition context.
    """

    theta, omega = state

    theta_gain = params.get("theta_gain", 1.0)
    omega_gain = params.get("omega_gain", 40.0)
    nonlinear_gain = params.get("nonlinear_gain", 5.0)
    theta_integral_gain = params.get("theta_integral_gain", 1.0)
    torque_limit = params.get("torque_limit", 30.0)

    # Keep the effective damping structure that previously regulated omega.
    omega_feedback = omega_gain * omega

    # Direct restoring feedback for angle regulation.
    theta_feedback = theta_gain * theta

    # Nonlinear correction improves recovery for larger initial angle errors.
    nonlinear_feedback = nonlinear_gain * np.sin(theta)

    # Approximate accumulated theta error compensation.
    # This targets the steady-state theta offset that remained after PD control.
    theta_integral_feedback = theta_integral_gain * theta * t

    torque = -(
        theta_feedback
        + omega_feedback
        + nonlinear_feedback
        + theta_integral_feedback
    )

    torque = np.clip(torque, -torque_limit, torque_limit)

    return np.array([torque])