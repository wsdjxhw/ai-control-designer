# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.1, 60.0)
# @param: kd (0.0, 30.0)
# @param: torque_limit (0.5, 200.0)
# @param: k_theta_recover (0.1, 60.0)
# @param: k_omega_recover (5.0, 80.0)
# @param: theta_gate (0.02, 0.5)
# @param: gate_width (0.02, 0.4)
# @param: phase_width (0.001, 0.25)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous phase-plane controller with coordinated position regulation,
    direction-aware damping, and one final saturation operation.

    The previous narrow angle/speed gates and additive bias compensation are
    removed because repeated threshold and bias retuning increased complexity
    without improving cost. Instead, this controller forms its position gain
    and damping gain through smooth convex blends.

    Damping is reduced when angular velocity is already moving theta toward
    the target and increased when velocity is moving theta away from it. This
    avoids stopping useful corrective motion prematurely while preserving
    strong velocity stabilization for harmful motion.
    """
    theta, omega = state

    # Existing parameter names are retained. The meanings of the recovery
    # gains are made explicit through convex interpolation rather than through
    # additive controller paths that can compete with one another.
    kp = params.get("kp", 2.5)
    kd = params.get("kd", 8.0)
    torque_limit = params.get("torque_limit", 40.0)
    k_theta_recover = params.get("k_theta_recover", 20.0)
    k_omega_recover = params.get("k_omega_recover", 45.0)
    theta_gate = params.get("theta_gate", 0.20)
    gate_width = params.get("gate_width", 0.10)
    phase_width = params.get("phase_width", 0.04)

    theta_target = 0.0
    omega_target = 0.0

    theta_error = theta - theta_target
    omega_error = omega - omega_target

    numerical_eps = np.finfo(float).eps
    safe_gate_width = np.maximum(np.abs(gate_width), numerical_eps)
    safe_phase_width = np.maximum(np.abs(phase_width), numerical_eps)
    safe_torque_limit = np.maximum(np.abs(torque_limit), numerical_eps)

    # Smoothly increase position authority only for larger angle errors.
    # This is a convex gain schedule, not a separate gated control mode, so
    # the position-corrective action remains active for every nonzero error.
    recovery_weight = 0.5 * (
        1.0
        + np.tanh(
            (np.abs(theta_error) - np.abs(theta_gate))
            / safe_gate_width
        )
    )

    effective_kp = (
        (1.0 - recovery_weight) * np.abs(kp)
        + recovery_weight * np.abs(k_theta_recover)
    )

    # theta_error * omega_error is positive when motion increases the
    # magnitude of the position error and negative when motion reduces it.
    # A smooth phase-plane blend therefore preserves useful motion while
    # applying stronger braking to motion in the harmful direction.
    phase_product = theta_error * omega_error
    harmful_motion_weight = 0.5 * (
        1.0 + np.tanh(phase_product / safe_phase_width)
    )

    effective_kd = (
        (1.0 - harmful_motion_weight) * np.abs(kd)
        + harmful_motion_weight * np.abs(k_omega_recover)
    )

    raw_torque = (
        -effective_kp * theta_error
        - effective_kd * omega_error
    )

    # Apply actuator authority exactly once after all controller components
    # have been coordinated. Smooth saturation keeps the continuous control
    # law bounded while avoiding the low-authority failure of later versions.
    torque = safe_torque_limit * np.tanh(
        raw_torque / safe_torque_limit
    )
    torque = np.clip(
        torque,
        -safe_torque_limit,
        safe_torque_limit,
    )

    # Exactly one continuous control channel: torque.
    return np.stack((torque,), axis=-1)