# ========== VECTORIZATION SELF-CHECK ==========
# [x] 1. No float(, int(, bool( applied to any array or comparison expression.
# [x] 2. All np.where conditions use & or |, not and or or.
# [x] 3. np.max / np.min used instead of max / min.
# [x] 4. No hardcoded return shape or T constant (inferred from existing code).
# [x] 5. Return shape matches the original control_law.
# [x] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: kp (0.0, 200.0)
# @param: kd (0.0, 100.0)
# @param: feedforward (0.0, 50.0)
# @param: omega_gain (0.0, 50.0)
# @param: vel_close_thresh (0.5, 10.0)
# @param: blend_width (0.1, 5.0)
# @param: max_torque (1.0, 20.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    Two-stage continuous control with soft-blend for the pendulum.

    Motivation (from diagnostic report):
      - Previous PD + gravity compensation left omega with a large
        residual final deviation (~2.0) and a persistently negative
        mean torque (~-2.35), indicating the controller kept pushing
        one way while the state drifted the other way at the end of
        the trajectory.
      - Pure gain tuning is unlikely to fix this: the symptom is a
        *structural* mismatch between a single global PD law and the
        dual goals of (a) bringing theta to the setpoint quickly and
        (b) killing omega once near the setpoint.

    Strategy:
      1. Soft-blend between a "far" PD law (high stiffness, drives
         theta in) and a "near" law (damped velocity regulation to
         kill omega residual).
      2. Use a smooth tanh blend on the position error so the law is
         continuously differentiable (continuous control type
         preserved — no np.where on discrete branches).
      3. Add a velocity-error term scaled by an extra gain so that
         omega is actively driven to its target, not only indirectly
         via the P-derivative coupling.
      4. Gravity compensation kept (small-angle feedforward) so the
         controller behaves well away from the equilibrium.
      5. Soft saturation via tanh before hard clip on max_torque to
         avoid the "mean torque pinned at one rail" symptom.
    """
    theta = state[0]
    omega = state[1]

    # Targets (from scene context)
    theta_target = 10.0
    omega_target = 2.0

    # Tunable gains
    kp           = params.get("kp", 20.0)
    kd           = params.get("kd", 5.0)
    feedforward  = params.get("feedforward", 1.0)
    omega_gain   = params.get("omega_gain", 8.0)
    vel_close_thresh = params.get("vel_close_thresh", 3.0)
    blend_width  = params.get("blend_width", 1.0)
    max_torque   = params.get("max_torque", 10.0)

    # Tracking errors
    e_theta = theta - theta_target
    e_omega = omega - omega_target

    # ----- Two-stage soft blend (continuous, no discrete branches) -----
    # w_far  in [0,1]: how much we are in the "far / approach" regime.
    # w_near = 1 - w_far: how much we are in the "near / damp" regime.
    w_far = 0.5 * (1.0 + np.tanh(np.abs(e_theta) / blend_width - vel_close_thresh / blend_width))
    w_near = 1.0 - w_far

    # Far-mode: aggressive PD on angle to drive theta to setpoint.
    u_far = -kp * e_theta - kd * e_omega

    # Near-mode: damped velocity regulation with a softer angle pull
    # and a direct omega-to-target term (the missing piece that left
    # omega at final_dev ~ 2.0 previously).
    u_near = -0.3 * kp * e_theta - (kd + omega_gain) * e_omega

    # Smooth blend
    u = w_far * u_far + w_near * u_near

    # Gravity compensation (linearized around small angles, scaled).
    g_comp = feedforward * np.sin(theta)
    u = u + g_comp

    # Anti-windup style soft saturation: tanh squash, then hard clip.
    # Keeps the sign of the controller's intent visible (no long
    # pinned-at-rail behavior like mean torque = -2.35 before).
    u = max_torque * np.tanh(u / max_torque)
    u = np.clip(u, -max_torque, max_torque)

    return np.array([u])