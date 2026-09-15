# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No `float(`, `int(`, `bool(` on arrays. Use `.astype()` instead.
# [ ] 2. `np.where` uses `&` / `|`, NOT `and` / `or`.
# [ ] 3. `np.max` / `np.min` / `np.abs` used (not Python built-ins).
# [ ] 4. No `for i in range(M+1)` loops.
# [ ] 5. Return shape: `(M+1, N_control)` for PDE, `(N_control,)` for ODE.
# [ ] 6. All controls implemented (no forced zeros).
# [ ] 7. Uses `t / T` for time normalization if needed.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: threshold_Iu (0.001, 1.0)
# @param: threshold_Ia (0.001, 1.0)
# @param: threshold_LRu (0.1, 10.0)
# ========== END PARAM DECLARATION ==========

import numpy as np

def control_law(t, x, state, params):
    """
    UWSN PDE bang-bang control law.
    Returns shape (M+1, 6).
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

    th_Iu = params.get("threshold_Iu", 0.02)
    th_Ia = params.get("threshold_Ia", 0.01)
    th_LRu = params.get("threshold_LRu", 2.0)

    infected_u = Iu > th_Iu
    infected_a = Ia > th_Ia
    latent_low = LRu < th_LRu

    u1 = np.where((Su < 1.0) & infected_u, 1.0, 0.0)
    u2 = np.where((Sa < 2.0) & infected_a, 1.0, 0.0)
    u3 = np.where(latent_low & (infected_u | infected_a), 1.0, 0.0)
    u4 = np.where(infected_u, 1.0, 0.0)
    u5 = np.where(infected_a, 1.0, 0.0)
    u6 = np.where(infected_u | infected_a, 1.0, 0.0)

    return np.column_stack([u1, u2, u3, u4, u5, u6])