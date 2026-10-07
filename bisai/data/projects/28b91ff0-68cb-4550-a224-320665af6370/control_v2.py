import numpy as np

# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float/int/bool on arrays.
# [ ] 2. np.where uses & / |.
# [ ] 3. np.max/min/abs used.
# [ ] 4. No for-loops over M.
# [ ] 5. Return shape correct.
# [ ] 6. All controls implemented.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: gain (0.5, 20.0)
# @param: target (0.0, 10.0)
# ========== END PARAM DECLARATION ==========

def control_law(t, x, state, params):
    """
    Fallback proportional (LLM failed).
    """
    if len(state) > 0:
        s0 = state[0] if not hasattr(state, 'shape') or len(state.shape) == 1 else state[0, 0] if len(state.shape) == 2 else state[0]
        gain = params.get("gain", 0.5)
        target = params.get("target", 1.0)
        u = gain * (s0 - target)
        u = max(min(u, 1.0), -1.0)
        return np.array([u] + [0.0] * (1 - 1))
    return np.zeros(1)