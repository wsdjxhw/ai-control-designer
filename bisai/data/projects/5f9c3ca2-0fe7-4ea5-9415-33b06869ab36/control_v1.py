import numpy as np


def control_law(t, x, state, params, context=None):
    """
    Pendulum continuous control law (PID with integral + gravity compensation).

    State order:  [theta, omega]
    Control order: [torque]

    Dynamics:
        dtheta/dt = omega
        domega/dt = -(g/L) sin(theta) + torque / (m L^2)

    Strategy:
        - PD feedback drives (theta -> target_theta, omega -> target_omega)
        - Integral term eliminates steady-state error to a setpoint
        - Gravity feed-forward term compensates pendulum nonlinearity
        - Anti-windup via clipping the accumulated integral
    """
    if context is None:
        context = {}

    # ---- Unpack state ----
    theta = state[0]
    omega = state[1]

    # ---- Read parameters (with safe defaults) ----
    kp = params.get("kp", 20.0)
    ki = params.get("ki", 1.0)
    kd = params.get("kd", 5.0)
    target_theta = params.get("target_theta", 0.5)
    target_omega = params.get("target_omega", 0.0)

    # ---- Physical constants (from scene_config) ----
    # length L = 1.0, mass m = 1.0, g = 9.81
    L = 1.0
    m = 1.0
    g = 9.81

    # ---- Errors ----
    # Use a periodic error to avoid the pendulum "wrapping" the long way around
    err_theta = target_theta - theta
    # Normalize angle error to [-pi, pi] using tanh-free wrapping via modulo
    err_theta = np.mod(err_theta + np.pi, 2.0 * np.pi) - np.pi
    err_omega = target_omega - omega

    # ---- Integral term (anti-windup) ----
    dt = 0.01  # matches scene_config.temporal.dt
    integral = context.get("integral", 0.0)
    integral = integral + err_theta * dt
    # Anti-windup: clamp integral contribution
    integral = float(np.clip(integral, -50.0, 50.0))
    context["integral"] = integral

    # ---- PID feedback ----
    u_pid = kp * err_theta + ki * integral - kd * err_omega

    # ---- Gravity feed-forward (compensate m g L sin(theta)) ----
    # Adding it makes the linearized closed-loop behave like a linear system
    u_ff = m * g * L * np.sin(theta)

    # ---- Total torque ----
    torque = u_pid + u_ff

    return np.array([torque])