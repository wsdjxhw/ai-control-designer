from core.base.base_model import BaseModel
import numpy as np


class UWSNModel(BaseModel):
    """UWSN 10 维反应-扩散 PDE

    状态变量 (10 维):
        0: Su, 1: Iu, 2: Ru, 3: LSu, 4: LIu, 5: LRu,
        6: Sa, 7: Ia, 8: Ra, 9: Sus

    控制变量 (6 维):
        0: u1, 1: u2, 2: u3, 3: u4, 4: u5, 5: u6

    ⚠️ 调试用参数（N=50 步，M+1=21 网格），演示时改大
    """

    def __init__(self, scene_config=None):
        if scene_config is None:
            scene_config = {}
        params = scene_config.get("physical_params", {})

        # 时间/空间（调试值）
        self.T = params.get("T", 1.0)
        self.dt = params.get("dt", 0.02)
        self.X = params.get("X", 2.0)
        self.dx = params.get("dx", 0.1)

        # 物理参数
        self.Du = params.get("Du", 0.001)
        self.Da = params.get("Da", 0.001)
        self.LA1 = params.get("LA1", 0.08)
        self.LA2 = params.get("LA2", 0.02)
        self.alpha1 = params.get("alpha1", 0.4)
        self.alpha2 = params.get("alpha2", 0.6)
        self.beta1 = params.get("beta1", 0.2)
        self.beta2 = params.get("beta2", 0.5)
        self.d1 = params.get("d1", 0.0005)
        self.d2 = params.get("d2", 0.0005)
        self.gamma1 = params.get("gamma1", 0.1)
        self.gamma3 = params.get("gamma3", 0.3)
        self.gamma4 = params.get("gamma4", 0.3)

        # 空间网格
        self.M = int(round(self.X / self.dx))
        self.x_grid = np.linspace(0, self.X, self.M + 1)

    def get_initial_state(self, x_grid=None):
        """返回 shape (M+1, 10) 的高斯脉冲初始状态"""
        M_plus1 = self.M + 1
        state = np.zeros((M_plus1, 10))
        xc = self.X * 0.25
        sigma = self.X * 0.05
        state[:, 0] = 0.5
        state[:, 1] = 0.1 * np.exp(-((self.x_grid - xc) ** 2) / (2 * sigma ** 2))
        state[:, 7] = 0.05 * np.exp(-((self.x_grid - xc) ** 2) / (2 * sigma ** 2))
        return state

    def rhs(self, t, state, control, x_grid=None):
        """10 维 PDE 的右端项"""
        # 拉普拉斯
        def lap(U):
            L = np.zeros_like(U)
            L[1:-1] = (U[:-2] - 2 * U[1:-1] + U[2:]) / (self.dx ** 2)
            L[0] = L[1]
            L[-1] = L[-2]
            return L

        ds = np.zeros_like(state)
        for i in range(10):
            ds[:, i] = (self.Du if i < 6 else self.Da) * lap(state[:, i])

        Su, Iu, Ru = state[:, 0], state[:, 1], state[:, 2]
        LSu, LIu, LRu = state[:, 3], state[:, 4], state[:, 5]
        Sa, Ia, Ra, Sus = state[:, 6], state[:, 7], state[:, 8], state[:, 9]

        # 控制（可能是 2D 或 1D）
        c = control
        if c.ndim == 1:
            c = np.tile(c, (state.shape[0], 1))
        u1, u2, u3, u4, u5, u6 = (c[:, j] for j in range(6))

        # 传播率（简化常数）
        K1, K2, K12, K21 = 0.0515, 0.061, 0.0034, 0.00064

        ds[:, 0] += (self.LA1 - K1 * Su * Iu - K21 * Su * Ia
                      - self.gamma1 * Su + self.alpha2 * Ru + u3 * LSu
                      - self.d1 * Su - u1 * Su - self.gamma3 * Su - u6 * Su + self.gamma4 * Sus)
        ds[:, 1] += (K1 * Su * Iu + K21 * Su * Ia
                      - self.gamma1 * Iu + u3 * LIu - self.alpha1 * Iu - u4 * Iu - self.d1 * Iu)
        ds[:, 2] += (self.alpha1 * Iu + u4 * Iu - self.alpha2 * Ru
                      - self.gamma1 * Ru + u3 * LRu - self.d1 * Ru + u1 * Su)
        ds[:, 3] += self.gamma1 * Su - u3 * LSu - self.d1 * LSu
        ds[:, 4] += self.gamma1 * Iu - u3 * LIu - self.d1 * LIu
        ds[:, 5] += self.gamma1 * Ru - u3 * LRu - self.d1 * LRu
        ds[:, 6] += (self.LA2 - K2 * Sa * Ia - K12 * Sa * Iu
                      + self.beta2 * Ra - self.d2 * Sa - u2 * Sa)
        ds[:, 7] += (K2 * Sa * Ia + K12 * Sa * Iu
                      - self.beta1 * Ia - u5 * Ia - self.d2 * Ia)
        ds[:, 8] += (self.beta1 * Ia + u5 * Ia - self.beta2 * Ra
                      - self.d2 * Ra + u2 * Sa)
        ds[:, 9] += self.gamma3 * Su + u6 * Su - self.gamma4 * Sus - self.d1 * Sus
        return np.array(ds)

    def validate_state(self, state):
        if np.isnan(state).any():
            return False
        if np.any(state > 1e5) or np.any(state < -1e3):
            return False
        return True