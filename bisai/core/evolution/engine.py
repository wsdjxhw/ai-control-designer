"""演化引擎主循环。

演化引擎 (EvolutionEngine) 是整个系统的核心，负责串联：
  CMA-ES 优化 → 完整仿真 → 指标提取 → LLM 诊断 → 代码修改 → 收敛检测 → 循环

接口约定 (供 B 成员调用):
  engine = EvolutionEngine(work_dir, scene_config)
  result = engine.run(max_iterations=20, control_law_code=code, llm_callbacks=cb)
  status = engine.get_status()
"""

from __future__ import annotations

import json
import os
import types
from collections.abc import Callable
from typing import Any

import numpy as np
import optuna

from core.base.base_cost import BaseCost
from core.base.base_model import BaseModel
from core.base.base_solver import BaseSolver
from core.cost_functions.factory import create_cost
from core.evolution.convergence import ConvergenceDetector
from core.evolution.diagnostics.base_extractor import BaseExtractor
from core.evolution.logger import EvolutionLogger
from core.evolution.param_bounds import ParamBounds
from core.evolution.state import EvolutionState
from core.solvers.loader import SolverLoader

# ============================================================
# 模型/求解器工厂
# ============================================================

def _create_model(scene_config: dict) -> BaseModel:
    """创建模型实例

    支持两种模式：
    1. 动态加载：如果 scene_config 包含 "_model_code" 字段，动态执行代码创建模型
    2. 注册加载：如果 scene_config 的 model_type 在已注册列表中，使用硬编码导入

    设计原则：
    - 优先尝试动态加载（支持任意新领域）
    - 动态加载失败时，尝试注册的模型类型（向后兼容）
    """
    model_type = scene_config.get("model_type", "")

    # 🆕 优先尝试动态加载（通过 scene_config 携带的 model_code）
    model_code = scene_config.get("_model_code")
    if model_code:
        try:
            namespace = {
                "np": np,
                "BaseModel": BaseModel,
            }
            exec(compile(model_code, "<model_code>", "exec"), namespace)

            # 找到继承 BaseModel 的类（排除 BaseModel 本身）
            model_cls = None
            for name, obj in namespace.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseModel)
                    and obj is not BaseModel
                ):
                    model_cls = obj
                    break

            if model_cls:
                print(f"[engine] 动态加载模型: {model_cls.__name__} (model_type={model_type})")
                return model_cls(scene_config)
            else:
                print(f"[engine] 警告: model_code 中未找到 BaseModel 子类，尝试注册加载")

        except Exception as e:
            print(f"[engine] 动态加载失败: {e}，尝试注册加载")

    # 兜底：尝试已注册的模型类型（向后兼容）
    # 兜底：尝试已注册的模型类型（向后兼容）
    if model_type == "uwsn":
        from core.models.uwsn_model import UWSNModel
        return UWSNModel(scene_config)
    elif model_type == "sir":
        from core.models.sir_model import SIRModel
        return SIRModel(scene_config)
    elif model_type == "dc_motor":
        from core.models.dc_motor_model import DCMotorModel
        return DCMotorModel(scene_config)

    # 🆕 如果 model_type 是 "ode" / "pde" / "custom"，说明用户走的是"上传 model.py"流程，
    # 但没有有效 _model_code。这是配置错误，给出明确提示。
    if model_type in ("ode", "pde", "custom"):
        raise ValueError(
            f"model_type='{model_type}' 表示用户上传模型，"
            f"但 scene_config 缺少 '_model_code' 字段。"
            f"请检查前端上传流程是否把 model_code 写入了 scene_config。"
        )

    raise ValueError(f"不支持的 model_type: {model_type}，且未提供有效的 _model_code")

def _create_solver(scene_config: dict) -> BaseSolver:
    """
    创建求解器实例 - 使用 SolverLoader 统一管理

    支持的 solver_type：
    - auto: 自动选择（向后兼容）
    - ode_scipy: SciPy ODE 求解器
    - pde_rk4: RK4 PDE 求解器
    - custom: 用户自定义求解器（需提供 custom_solver_path）

    Args:
        scene_config: 场景配置字典，包含 solver 配置

    Returns:
        BaseSolver 子类实例
    """
    solver_cfg = scene_config.get("solver", {})
    solver_type = solver_cfg.get("solver_type", "auto")
    model_type = scene_config.get("model_type", "")

    # ========== Custom 模式：用户自定义求解器 ==========
    if solver_type == "custom":
        custom_path = solver_cfg.get("custom_solver_path")
        if not custom_path:
            raise ValueError("solver_type='custom' 必须提供 solver.custom_solver_path")

        params = solver_cfg.get("solver_params", {})
        print(f"[engine] 加载自定义求解器: {custom_path}")
        return SolverLoader.load(
            solver_type="custom",
            custom_path=custom_path,
            params=params
        )

    # ========== 强制指定求解器类型 ==========
    if solver_type == "ode_scipy":
        params = {
            "method": solver_cfg.get("method", "RK45"),
            "rtol": solver_cfg.get("rtol", 1e-6),
            "atol": solver_cfg.get("atol", 1e-9),
            "max_step": solver_cfg.get("max_step"),
        }
        return SolverLoader.load(solver_type="ode_scipy", params=params)

    if solver_type == "pde_rk4":
        return SolverLoader.load(solver_type="pde_rk4", params={})

    # ========== Auto 模式：根据 model_type 自动选择 ==========
    # ========== Auto 模式：根据 model_type 自动选择 ==========
    if model_type in ("uwsn", "pde"):
        # PDE 类：用 PDE_RK4 求解器
        print(f"[engine] model_type='{model_type}' → 使用 PDE_RK4 求解器")
        return SolverLoader.load(solver_type="pde_rk4", params={})

    elif model_type in ("sir", "dc_motor", "ode"):
        # ODE 类：用 SciPy 求解器
        print(f"[engine] model_type='{model_type}' → 使用 ODE_Scipy 求解器")
        return SolverLoader.load(solver_type="ode_scipy", params={})

    # 未知类型 → 默认 ODE（大多数控制系统是 ODE）
    else:
        print(f"[engine] 未知 model_type '{model_type}'，默认使用 ODE 求解器")
        return SolverLoader.load(solver_type="ode_scipy", params={})

def _compile_control_law(code: str) -> Callable:
    """将控制律代码字符串编译为可调用函数。

    编译后的函数签名: control_law(t: float, x_grid: ndarray,
                                   state: ndarray, params: dict) -> ndarray
    """
    namespace: dict[str, Any] = {"np": np}
    exec(compile(code, "<control_law>", "exec"), namespace)
    func = namespace.get("control_law")
    if func is None:
        raise ValueError("控制律代码必须定义 control_law(t, x_grid, state, params) 函数")
    return func


# ============================================================
# CMA-ES 配置
# ============================================================

_CMAES_DEFAULTS = {
    "stage1_trials": 300,
    "stage2_trials": 100,
    "stage1_steps_ratio": 0.2,
    "popsize_stage1": 200,
    "popsize_stage2": 50,
    "sigma0_stage1": 0.5,
    "sigma0_stage2": 0.25,
    "n_startup_trials": 300,
    "n_top_candidates": 10,
    "n_perturbations": 3,
    "seed": 42,
}


def _ensure_6_columns(arr: np.ndarray, expected: int = 6) -> np.ndarray:
    """确保控制数组至少有 expected 列，不足则补零。
    自动处理 1D / 标量输入。
    """
    arr = np.asarray(arr, dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1, 1)
    elif arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.shape[1] < expected:
        pad = np.zeros((arr.shape[0], expected - arr.shape[1]))
        return np.concatenate([arr, pad], axis=1)
    return arr[:, :expected]


# ============================================================
# 演化引擎
# ============================================================

LLMCallbacks = dict[str, Callable[..., Any]]
"""可选的 LLM 回调函数:
  "diagnose": (metrics_text, layered_history, anomalies) -> str
  "modify":   (old_code, diagnosis, layered_history) -> str | None
  "validate": (code) -> bool
"""


class EvolutionEngine:
    """演化引擎。"""

    def __init__(
        self,
        work_dir: str,
        scene_config: dict,
        cmaes_config: dict | None = None,
    ) -> None:
        self.work_dir = work_dir
        self.scene_config = scene_config

        # 核心组件
        self.model: BaseModel = _create_model(scene_config)
        self.solver: BaseSolver = _create_solver(scene_config)
        self.cost: BaseCost = create_cost(scene_config)

        # 根据模型类型选择诊断提取器
        model_type = scene_config.get("model_type", "")
        if model_type == "sir":
            from core.evolution.diagnostics.sir_extractor import SIRExtractor
            self.extractor: BaseExtractor = SIRExtractor(scene_config)
        elif model_type == "dc_motor":
            from core.evolution.diagnostics.motor_extractor import MotorExtractor
            self.extractor: BaseExtractor = MotorExtractor(scene_config)
        else:
            # UWSN 或默认使用通用提取器
            self.extractor: BaseExtractor = BaseExtractor(scene_config)

        # 辅助组件
        self.state = EvolutionState()
        self.convergence = ConvergenceDetector()
        self.logger = EvolutionLogger(
            os.path.join(work_dir, "evolution_log.json"), work_dir
        )

        # CMA-ES 参数
        self._cmaes = {**_CMAES_DEFAULTS, **(cmaes_config or {})}

        # 运行时状态
        self._current_code: str = ""
        self._param_bounds: dict[str, tuple[float, float]] = {}
        self._dynamic_bounds_file = os.path.join(work_dir, "dynamic_bounds.json")

        # 🆕 几何推断：从初始状态和 scene_config 推断模型几何
        self._geometry = self._infer_geometry(scene_config)
        print(f"[engine] 几何推断: is_pde={self._geometry['is_pde']}, "
              f"M_plus1={self._geometry['M_plus1']}, "
              f"state_dim={self._geometry['state_dim']}, "
              f"control_dim={self._geometry['control_dim']}")
        # 🆕 B-8：中断标志
        self._stop_requested: bool = False

    # ---------- 辅助方法：状态维度归一化 ----------

    def _infer_geometry(self, scene_config: dict) -> dict:
        """从初始状态和 scene_config 推断模型几何"""
        initial = self.model.get_initial_state()

        if initial.ndim == 1:
            # ODE：state = (state_dim,)
            is_pde = False
            M_plus1 = 1
            state_dim = initial.shape[0]
        else:
            # PDE：state = (M+1, state_dim)
            is_pde = True
            M_plus1 = initial.shape[0]
            state_dim = initial.shape[1]

        # control_dim 从 scene_config 推断，不信任 model.control_dim
        control_names = scene_config.get("control_names", [])
        control_dim = len(control_names) if control_names else 1

        # 🆕 从 scene_config 读取 temporal 配置，计算 N/dt
        temporal = scene_config.get("temporal", {})
        T_cfg = float(temporal.get("T") or 5.0)
        dt_cfg = float(temporal.get("dt") or 0.02)
        N_cfg = max(1, int(round(T_cfg / dt_cfg)))

        return {
            "is_pde": is_pde,
            "M_plus1": M_plus1,
            "state_dim": state_dim,
            "control_dim": control_dim,
            "N": N_cfg,
            "dt": dt_cfg,
        }

    def _to_internal(self, state: np.ndarray) -> np.ndarray:
        """外部 state → 引擎内部统一 2D 表示 (M+1, s_dim)"""
        if state.ndim == 1:
            return state.reshape(1, -1)   # (s_dim,) → (1, s_dim)
        return state

    def _to_internal_control(self, control: np.ndarray) -> np.ndarray:
        """control 归一化为 2D (M+1, c_dim)"""
        control = np.asarray(control, dtype=float)
        if control.ndim == 1:
            return control.reshape(1, -1)   # (c_dim,) → (1, c_dim)
        return control

    # ---------- 公开 API ----------

    def run(
        self,
        max_iterations: int = 20,
        control_law_code: str | None = None,
        llm_callbacks: LLMCallbacks | None = None,
        start_version: int = 1,
    ) -> dict[str, Any]:
        """运行演化循环。

        Args:
            max_iterations: 最大演化迭代次数。
            control_law_code: D 成员生成的初始控制律代码字符串。
            llm_callbacks: LLM 诊断/修改/验证回调 (D 成员提供)。

        Returns:
            {
                "success": bool,
                "final_version": int,
                "best_cost": float,
                "best_params": dict,
                "history": [每轮摘要],
                "error": str | None,
            }
        """
        self.state.status = "running"
        self.state.max_iterations = max_iterations
        self.state.current_version = 0
        self.state.best_cost = float("inf")

        if control_law_code is None:
            return self._error_result("未提供 control_law_code")

        self._current_code = control_law_code
        # 确保工作目录存在
        os.makedirs(self.work_dir, exist_ok=True)

        # 提取参数名和边界
        declared_bounds = ParamBounds.from_code(control_law_code)
        self._load_dynamic_bounds()
        self._param_bounds = ParamBounds.merge(
            declared_bounds, self._dynamic_bounds
        )

        version = start_version - 1
        end_version = start_version - 1 + max_iterations
        history: list[dict[str, Any]] = []

        while version < end_version:
            # 🆕 B-8：每轮开始前检查中断标志
            if self._stop_requested:
                print(f"[engine] 收到中断请求，停止演化（已完成 {version - start_version + 1} 轮）")
                self.state.status = "done"
                self.state.message = f"用户中断，完成 {version - start_version + 1} 轮"
                break

            version += 1
            self.state.current_version = version
            self.state.iteration = version
            self.state.message = f"迭代 {version}/{max_iterations}"

            # ---- 1. CMA-ES 优化 ----
            self.state.status = "optimizing"
            try:
                best_params, best_cost = self._optimize()
                self.state.best_cost = best_cost
                self.state.best_params = best_params
            except Exception as e:
                return self._error_result(
                    f"CMA-ES 优化失败 (V{version}): {e}"
                )
            # 🆕 保存本轮最优参数
            self._save_best_params(version, best_params)

            # ---- 2. 完整仿真 ----
            ctrl_func = _compile_control_law(self._current_code)
            t_arr, s_hist, c_hist = self._simulate(ctrl_func, best_params)

            # ---- 3. 提取指标 ----
            metrics = self.extractor.extract_metrics(s_hist, c_hist, t_arr)
            metrics_text = self.extractor.format_metrics_for_llm(metrics)
            anomalies = metrics.get("anomalies", [])

            # ---- 4. LLM 诊断与修改 (如果提供了回调) ----
            if llm_callbacks and "diagnose" in llm_callbacks:
                self.state.status = "diagnosing"
                layered_history = self.logger.get_layered_history()
                try:
                    raw_diagnosis = llm_callbacks["diagnose"](
                        metrics_text, layered_history, anomalies
                    )
                except Exception as e:
                    raw_diagnosis = f"LLM 诊断异常: {e}"
            else:
                raw_diagnosis = metrics_text

            # 记录日志
            self.logger.log_iteration(
                version=version,
                params=best_params,
                cost=best_cost,
                diagnosis=raw_diagnosis,
                metrics=metrics,
                param_count=len(self._param_bounds),
            )

            # 提取 LLM 推荐的参数边界 (简版)
            self._update_dynamic_bounds(raw_diagnosis, best_params)

            # ---- 5. LLM 代码修改 ----
            # ---- 5. LLM 代码修改 ----
            if llm_callbacks and "modify" in llm_callbacks:
                self.state.status = "modifying"
                try:
                    new_code = llm_callbacks["modify"](
                        self._current_code, raw_diagnosis, layered_history, self.scene_config
                    )
                    if new_code is not None:
                        self._current_code = new_code
                        # 保存下一版本代码 control_v{version+1}.py
                        self._save_control_law(version + 1, new_code)
                        # 重解析参数
                        declared_bounds = ParamBounds.from_code(new_code)
                        self._param_bounds = ParamBounds.merge(
                            declared_bounds, self._dynamic_bounds
                        )
                        print(f"[engine] V{version + 1} 控制律已更新（LLM 修改成功）")
                    else:
                        # 🆕 LLM 修改失败：复制上一版代码，保证版本号连续
                        print(f"[engine] ⚠️ LLM 修改返回 None，复制 V{version} 代码作为 V{version + 1}")
                        self._save_control_law(version + 1, self._current_code)
                except Exception as e:
                    print(f"[engine] ⚠️ LLM 修改异常: {e}，复制上一版代码")
                    # 🆕 异常时也复制上一版，不让整个演化崩
                    self._save_control_law(version + 1, self._current_code)

            # ---- 6. 收敛检测 ----
            if self.convergence.check(
                best_cost, len(self._param_bounds)
            ):
                self.state.message += " [收敛]"
                break

            # 保存结果摘要
            history.append({
                "version": version,
                "cost": best_cost,
                "params": best_params,
                "param_count": len(self._param_bounds),
            })

        # 完成
        self.state.status = "done"
        self.state.message = f"演化完成，共 {version} 轮"

        return {
            "success": True,
            "final_version": version,
            "best_cost": self.state.best_cost,
            "best_params": self.state.best_params,
            "history": history,
            "error": None,
        }

    def get_status(self) -> EvolutionState:
        return self.state


    def request_stop(self) -> None:
        """请求停止演化（下一轮开始时生效）"""
        self._stop_requested = True
        print("[engine] 已设置中断标志，将在当前轮结束后停止")

    # ---------- 内部方法 ----------

    def _optimize(self) -> tuple[dict[str, float], float]:
        """使用优化器工厂选择优化器（统一入口）。

        通过 scene_config.optimizer.optimizer_type 选择：
          - cmaes/auto: CMA-ES（默认）
          - pso: 粒子群
          - tpe: TPE
          - random: 随机搜索
          - grid: 网格搜索
          - custom: 用户自定义

        所有优化器统一调用 core.optimizers.factory.create_optimizer()
        """
        from core.optimizers.factory import create_optimizer

        opt_cfg = self.scene_config.get("optimizer", {})
        opt_type = (opt_cfg.get("optimizer_type") or "cmaes").lower()
        print(f"[engine] 优化器类型: {opt_type}")

        # 创建优化器
        try:
            optimizer = create_optimizer(self.scene_config)
        except Exception as e:
            print(f"[engine] 创建优化器失败: {e}，回退到默认 CMA-ES")
            from core.optimizers.cmaes_optimizer import CMAESOptimizer
            optimizer = CMAESOptimizer()

        # 编译控制律
        ctrl_func = _compile_control_law(self._current_code)

        # 目标函数（全精度仿真）
        def objective_fn(params: dict) -> float:
            return self._objective(params, ctrl_func, n_steps=None, trial=None)

        # 试验次数（默认 500）
        n_trials = int(opt_cfg.get("n_trials", 500))
        seed = int(self._cmaes.get("seed", 42))

        print(f"[engine] 使用 {type(optimizer).__name__}，n_trials={n_trials}")
        best_params, best_cost, _ = optimizer.optimize(
            objective=objective_fn,
            param_bounds=self._param_bounds,
            n_trials=n_trials,
            seed=seed,
        )
        print(f"[engine] {type(optimizer).__name__} 完成: best_cost={best_cost:.4f}")

        return best_params, best_cost

    def _objective(
        self,
        params: dict[str, float],
        ctrl_func: Callable,
        n_steps: int | None = None,
        trial: optuna.Trial | None = None,
    ) -> float:
        """多保真度目标函数。

        用给定参数运行仿真（部分步数或全精度），计算总代价。
        """
        state = self._to_internal(self.model.get_initial_state())
        dt = self._geometry["dt"]
        dx = self.model.dx
        N = self._geometry["N"]
        actual_steps = N if n_steps is None else min(n_steps, N)
        cumulative = 0.0
        step_costs: list[float] = []

        for step in range(actual_steps):
            try:
                state_for_control = state.reshape(-1) if not self._geometry["is_pde"] else state
                control = ctrl_func(step * dt, self.model.x_grid, state_for_control, params)
                control = self._to_internal_control(control)
                control = _ensure_6_columns(control, self._geometry["control_dim"])
                # 校验 bang-bang 控制
                if not self.cost.validate_control(control[0]):
                    return 1e10
                # 计算这一步的代价
                step_cost = self.cost.compute_running(state, control, step)
                cumulative += step_cost
                step_costs.append(step_cost)
                # 单步积分
                state_for_solver = state.reshape(-1) if not self._geometry["is_pde"] else state
                state = self.solver.step(self.model, state_for_solver, control, dt)
                state = self._to_internal(np.maximum(state, 0.0))
                # Optuna 剪枝
                if trial is not None and step > 0 and step % 5000 == 0:
                    avg = cumulative / (step + 1)
                    trial.report(avg * N, step)
                    if trial.should_prune():
                        raise optuna.TrialPruned()
                # 发散检测
                if not self.model.validate_state(state):
                    return 1e10 * (1.0 + (N - step) / N)
            except optuna.TrialPruned:
                raise
            except Exception as e:
                # 🆕 打印异常，避免再被静默吞掉
                if step < 3:   # 只打印前几步，避免刷屏
                    import traceback
                    print(f"[objective] step={step} 异常: {type(e).__name__}: {e}")
                    traceback.print_exc()
                return 1e10

        # 终端代价
        if actual_steps == N:
            total = cumulative + self.cost.compute_terminal(state)
        else:
            # 外推
            recent = step_costs[-min(20, len(step_costs)):]
            avg_recent = float(np.mean(recent)) if recent else 0.0
            remaining = N - actual_steps
            projected = avg_recent * remaining * 1.5
            terminal = self.cost.compute_terminal(state)
            roughness = 1.0 + 0.05 * (1.0 - actual_steps / N)
            total = (cumulative + projected + terminal) * roughness

        return float(total)

    def _simulate(
        self,
        ctrl_func: Callable,
        params: dict[str, float],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """用最优参数运行完整仿真并采集快照。"""
        state = self._to_internal(self.model.get_initial_state())
        dt = self._geometry["dt"]
        N = self._geometry["N"]
        save_interval = max(1, N // 1000)
        n_saved = N // save_interval + 1
        M_plus1 = self._geometry["M_plus1"]
        s_dim = self._geometry["state_dim"]
        c_dim = self._geometry["control_dim"]

        t_arr = np.zeros(n_saved)
        s_hist = np.zeros((n_saved, M_plus1, s_dim))
        c_hist = np.zeros((n_saved, M_plus1, c_dim))

        idx = 0
        t_arr[0] = 0.0
        s_hist[0] = state
        state_for_control = state.reshape(-1) if not self._geometry["is_pde"] else state
        c_hist[0] = self._to_internal_control(ctrl_func(0.0, self.model.x_grid, state_for_control, params))

        for step in range(1, N + 1):
            t = step * dt
            state_for_control = state.reshape(-1) if not self._geometry["is_pde"] else state
            control = self._to_internal_control(ctrl_func(t, self.model.x_grid, state_for_control, params))
            control = _ensure_6_columns(control, c_dim)
            state_for_solver = state.reshape(-1) if not self._geometry["is_pde"] else state
            state = self.solver.step(self.model, state_for_solver, control, dt)
            state = self._to_internal(np.maximum(state, 0.0))
            if step % save_interval == 0 or step == N:
                idx += 1
                t_arr[idx] = t
                s_hist[idx] = state
                c_hist[idx] = control

        return t_arr[: idx + 1], s_hist[: idx + 1], c_hist[: idx + 1]

    def _load_dynamic_bounds(self) -> None:
        self._dynamic_bounds: dict[str, list[float]] = {}
        if os.path.exists(self._dynamic_bounds_file):
            try:
                with open(self._dynamic_bounds_file, "r", encoding="utf-8") as f:
                    self._dynamic_bounds = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._dynamic_bounds = {}

    def _update_dynamic_bounds(
        self, diagnosis: str, params: dict
    ) -> None:
        """简版：暂不自动更新，保留接口供后续 LLM 集成。"""
        pass

    def _save_control_law(self, version: int, code: str) -> None:
        """保存控制律到 work_dir/control_v{version}.py"""
        import os
        path = os.path.join(self.work_dir, f"control_v{version}.py")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"[engine] 已保存 control_v{version}.py ({len(code)} 字符)")
        except Exception as e:
            print(f"[engine] 保存 control_v{version}.py 失败: {e}")

    def _save_best_params(self, version: int, params: dict) -> None:
        """保存最优参数到 work_dir/best_params_v{version}.json"""
        import os, json
        path = os.path.join(self.work_dir, f"best_params_v{version}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(params, f, indent=2, ensure_ascii=False)
            print(f"[engine] 已保存 best_params_v{version}.json")
        except Exception as e:
            print(f"[engine] 保存 best_params_v{version}.json 失败: {e}")

    def _error_result(self, msg: str) -> dict[str, Any]:
        self.state.status = "error"
        self.state.error = msg
        return {
            "success": False,
            "final_version": self.state.current_version,
            "best_cost": self.state.best_cost,
            "best_params": self.state.best_params,
            "history": [],
            "error": msg,
        }
