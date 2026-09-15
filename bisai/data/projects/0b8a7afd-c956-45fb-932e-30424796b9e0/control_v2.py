# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float(, int(, bool( applied to any array or comparison expression.
# [ ] 2. All np.where conditions use & or |, not and or or.
# [ ] 3. np.max / np.min used instead of max / min.
# [ ] 4. No hardcoded return shape or T constant (inferred from existing code).
# [ ] 5. Return shape matches the original control_law.
# [ ] 6. Existing parameter names preserved where applicable.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: threshold_Iu (0.001, 1.0)
# @param: threshold_Ia (0.001, 1.0)
# @param: threshold_LRu (0.1, 10.0)
# @param: threshold_Su_gap (0.01, 1.0)
# @param: threshold_Sa_gap (0.01, 2.0)
# @param: early_time_ratio (0.05, 0.95)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    UWSN PDE bang-bang control law.

    Structural modification:
    - Previous version produced all-zero controls because infection thresholds
      were too restrictive relative to the observed state magnitudes.
    - This version combines target-tracking gaps and spatial infection signals.
    - Uses adaptive bang-bang activation based on local field values and
      population deficits, helping activate controls earlier instead of waiting
      for large infection levels that may never occur.
    - Maintains PDE vectorization and returns shape (M+1, 6).
    """

    Su, Iu, Ru, LSu, LIu, LRu, Sa, Ia, Ra, Sus = (
        state[:, 0],
        state[:, 1],
        state[:, 2],
        state[:, 3],
        state[:, 4],
        state[:, 5],
        state[:, 6],
        state[:, 7],
        state[:, 8],
        state[:, 9],
    )

    th_Iu = params.get("threshold_Iu", 0.005)
    th_Ia = params.get("threshold_Ia", 0.005)
    th_LRu = params.get("threshold_LRu", 0.5)

    th_Su_gap = params.get("threshold_Su_gap", 0.15)
    th_Sa_gap = params.get("threshold_Sa_gap", 0.25)
    early_time_ratio = params.get("early_time_ratio", 0.6)

    target_Su = 1.0
    target_Sa = 2.0
    target_LRu = 3.0

    max_x = np.max(x)
    time_ratio = t / (t + 1.0e-12 + max_x)

    infected_u = Iu > th_Iu
    infected_a = Ia > th_Ia

    infection_present = infected_u | infected_a
    strong_need_su = (target_Su - Su) > th_Su_gap
    strong_need_sa = (target_Sa - Sa) > th_Sa_gap
    low_lru = LRu < th_LRu
    far_from_lru_target = (target_LRu - LRu) > th_LRu

    early_phase = np.full_like(Su, time_ratio < early_time_ratio, dtype=bool)

    u1 = np.where(strong_need_su & (infection_present | early_phase), 1.0, 0.0)

    u2 = np.where(strong_need_sa & (infection_present | early_phase), 1.0, 0.0)

    u3 = np.where(far_from_lru_target & (low_lru | infection_present), 1.0, 0.0)

    u4 = np.where(
        infected_u | (strong_need_su & (Sus > 0.0)),
        1.0,
        0.0,
    )

    u5 = np.where(
        infected_a | (strong_need_sa & (Sus > 0.0)),
        1.0,
        0.0,
    )

    u6 = np.where(
        infection_present | far_from_lru_target | (Sus > 0.05),
        1.0,
        0.0,
    )

    return np.column_stack([u1, u2, u3, u4, u5, u6])