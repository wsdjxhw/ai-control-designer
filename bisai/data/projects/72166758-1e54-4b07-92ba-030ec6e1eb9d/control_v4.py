# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.25, 0.75)
# @param: kd (0.4, 2.2)
# @param: capture_gain (1.2, 2.1)
# @param: theta_scale (0.65, 0.95)
# @param: omega_scale (0.6, 1.8)
# @param: capture_limit (1.55, 2.2)
# @param: max_torque (17.0, 22.0)
# @param: ki (0.001, 2.0)
# @param: integral_leak (0.0001, 0.5)
# @param: integral_limit (0.05, 5.0)
# ========== END PARAM DECLARATION ==========

import numpy as np


def control_law(t, x, state, params):
    """
    Continuous nonlinear PD control with smooth capture and bounded low-frequency
    residual-error compensation.

    Earlier versions repeatedly adjusted proportional and derivative gains but
    remained on the same cost plateau. This version therefore preserves the
    successful low-gain PD and capture structure while adding a distinct
    low-frequency correction mechanism.

    Because no persistent controller state is guaranteed by the interface, the
    integral channel uses a time-dependent leaky residual accumulator. For a
    persistent angular error it grows smoothly from zero, while leakage and
    clipping prevent unbounded windup. The final smooth actuator saturation
    provides continuous anti-windup behavior by limiting the combined command.
    """
    theta, omega = state

    kp = params.get("kp", 0.4922397013118467)
    kd = params.get("kd", 1.0844697883175172)
    capture_gain = params.get("capture_gain", 1.5616287297686076)
    theta_scale = params.get("theta_scale", 0.8019169245194575)
    omega_scale = params.get("omega_scale", 1.1985320774231654)
    capture_limit = params.get("capture_limit", 1.8675921543379028)
    max_torque = params.get("max_torque", 19.756010181630305)

    ki = params.get("ki", 0.25)
    integral_leak = params.get("integral_leak", 0.08)
    integral_limit = params.get("integral_limit", 1.5)

    theta_error = theta
    omega_error = omega

    safe_theta_scale = np.maximum(theta_scale, 1.0e-12)
    safe_omega_scale = np.maximum(omega_scale, 1.0e-12)
    safe_capture_limit = np.maximum(capture_limit, 1.0e-12)
    safe_max_torque = np.maximum(max_torque, 1.0e-12)
    safe_integral_leak = np.maximum(integral_leak, 1.0e-12)
    safe_integral_limit = np.maximum(integral_limit, 1.0e-12)

    theta_ratio = theta_error / safe_theta_scale
    omega_ratio = omega_error / safe_omega_scale

    theta_ratio_squared = theta_ratio * theta_ratio
    omega_ratio_squared = omega_ratio * omega_ratio

    # The capture term has negligible local slope near the target and therefore
    # does not duplicate the linear proportional channel. It remains responsible
    # primarily for larger angular errors.
    position_factor = theta_ratio_squared / (
        1.0 + theta_ratio_squared
    )
    velocity_modulation = 1.0 / np.sqrt(
        1.0 + omega_ratio_squared
    )
    capture_gate = position_factor * velocity_modulation

    capture_raw = -capture_gain * capture_gate * theta_error
    capture_torque = safe_capture_limit * np.tanh(
        capture_raw / safe_capture_limit
    )

    # This bounded leaky accumulator approximates the accumulated contribution
    # of a persistent residual over elapsed simulation time without assuming a
    # particular horizon or time step. It introduces the low-frequency freedom
    # that repeated kp and kd tuning could not provide.
    elapsed_time = np.maximum(np.asarray(t), 0.0)
    accumulation_factor = -np.expm1(
        -safe_integral_leak * elapsed_time
    ) / safe_integral_leak

    integral_state = np.clip(
        theta_error * accumulation_factor,
        -safe_integral_limit,
        safe_integral_limit,
    )

    # Smoothly reduce integral correction during rapid motion. This preserves
    # the existing damping behavior and concentrates the new action in the
    # quasi-static regime where the unresolved theta bias was observed.
    settle_gate = 1.0 / (
        1.0 + omega_ratio_squared
    )
    integral_torque = -ki * settle_gate * integral_state

    base_torque = -kp * theta_error - kd * omega_error
    raw_torque = base_torque + capture_torque + integral_torque

    # Smooth continuous limiting bounds the actuator command and prevents the
    # residual accumulator from producing a discontinuous saturated output.
    torque = safe_max_torque * np.tanh(
        raw_torque / safe_max_torque
    )

    return np.stack((torque,), axis=-1)