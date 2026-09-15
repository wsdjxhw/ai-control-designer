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
# @param: lru_activation_ratio (0.05, 1.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    UWSN PDE bang-bang control law.

    Structural changes relative to V1:
    - Preserve successful infection suppression branches.
    - Add explicit LRu-target tracking because LRu dominates total cost.
    - Add explicit Sa-deficit feedback because Sa is the second-largest error.
    - Reactivate u3 using LRu and Sa feedback instead of an unreachable threshold.
    - Use simple priority logic so resources are redirected toward the largest
      observed state deviations instead of focusing almost exclusively on infection.
    - Fully vectorized PDE implementation returning (M+1, 6).
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
    lru_activation_ratio = params.get("lru_activation_ratio", 0.4)

    target_Su = 1.0
    target_Sa = 2.0
    target_LRu = 3.0

    max_x = np.max(x)
    time_ratio = t / (max_x + t + 1.0e-12)

    infected_u = Iu > th_Iu
    infected_a = Ia > th_Ia
    infection_present = infected_u | infected_a

    su_gap = target_Su - Su
    sa_gap = target_Sa - Sa
    lru_gap = target_LRu - LRu

    strong_need_su = su_gap > th_Su_gap
    strong_need_sa = sa_gap > th_Sa_gap

    # Explicit LRu tracking: previous version kept u3 inactive.
    lru_far = lru_gap > (lru_activation_ratio * th_LRu)

    early_phase = np.full_like(Su, time_ratio < early_time_ratio, dtype=bool)

    # Priority indicator: focus on dominant deviations (Sa, LRu, then Su).
    major_deficit = lru_far | strong_need_sa

    u1 = np.where(
        strong_need_su & (early_phase | infection_present | major_deficit),
        1.0,
        0.0,
    )

    u2 = np.where(
        strong_need_sa,
        1.0,
        0.0,
    )

    # Reactivated channel: explicitly responds to LRu and Sa deficits.
    u3 = np.where(
        lru_far | (strong_need_sa & (sa_gap > 0.5 * lru_gap)),
        1.0,
        0.0,
    )

    # Preserve successful infection-suppression mechanism,
    # but also assist when LRu is far from target.
    u4 = np.where(
        infected_u | lru_far,
        1.0,
        0.0,
    )

    u5 = np.where(
        infected_a | strong_need_sa,
        1.0,
        0.0,
    )

    # Global coordinator: activates when any dominant error exists.
    u6 = np.where(
        infection_present
        | lru_far
        | strong_need_sa
        | (strong_need_su & (Sus > 0.0))
        | (Sus > 0.05),
        1.0,
        0.0,
    )

    return np.column_stack([u1, u2, u3, u4, u5, u6])