import numpy as np

def control_law(t, x_grid, state, params):
    """
    Control law for the physical system.

    Args:
        t: Current time (float)
        x_grid: Spatial grid (ndarray, for PDE models; None or empty for ODE)
        state: Current state vector (ndarray, length = len(state_names))
        params: Tunable parameters dict (e.g., {"k1": 0.5, "k2": 1.0})

    Returns:
        control: Control input vector (ndarray, length = len(control_names))
    """
    position, velocity = state
    target_position = params.get("target_position", 0.0)
    target_velocity = params.get("target_velocity", 0.0)
    
    kp = params.get("kp", 4.0)
    kd = params.get("kd", 2.0)
    
    force = kp * (target_position - position) + kd * (target_velocity - velocity)
    
    return np.array([force])