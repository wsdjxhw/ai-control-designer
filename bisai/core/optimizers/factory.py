"""优化器工厂：根据 scene_config 创建对应的优化器实例。

支持多种内置优化器 + 自定义优化器：
- auto/cmaes: CMA-ES 优化器（默认）
- pso: 粒子群优化 (PSO)
- tpe: TPE (Tree-structured Parzen Estimator)
- random: 随机搜索
- grid: 网格搜索
- custom: 用户自定义优化器
"""

from __future__ import annotations

from core.optimizers.base_optimizer import BaseOptimizer
from core.optimizers.cmaes_optimizer import CMAESOptimizer


def create_optimizer(scene_config: dict) -> BaseOptimizer:
    """根据 scene_config 创建优化器实例。

    Args:
        scene_config: 场景配置字典，需包含 optimizer 配置

    Returns:
        BaseOptimizer 子类实例

    Raises:
        ValueError: optimizer_type 不支持时抛出
    """
    opt_cfg = scene_config.get("optimizer", {})
    opt_type = opt_cfg.get("optimizer_type", "auto").lower()

    # ========== Custom 模式：用户自定义 ==========
    if opt_type == "custom":
        from core.optimizers.custom_optimizer import CustomOptimizer
        return CustomOptimizer(scene_config)

    # ========== 内置优化器模式 ==========
    if opt_type in ("auto", "cmaes"):
        return CMAESOptimizer(
            popsize=opt_cfg.get("popsize", 50),
            sigma0=opt_cfg.get("sigma0", 0.25),
        )

    if opt_type == "pso":
        from core.optimizers.pso_optimizer import PSOOptimizer
        return PSOOptimizer(
            n_particles=opt_cfg.get("n_particles", 30),
            w=opt_cfg.get("w", 0.7),
            c1=opt_cfg.get("c1", 1.5),
            c2=opt_cfg.get("c2", 1.5),
            max_iter=opt_cfg.get("max_iter", 100),
        )

    if opt_type == "tpe":
        from core.optimizers.tpe_optimizer import TPEOptimizer
        return TPEOptimizer(
            n_startup_trials=opt_cfg.get("n_startup_trials", 10),
            n_ei_candidates=opt_cfg.get("n_ei_candidates", 24),
        )

    if opt_type == "random":
        from core.optimizers.random_optimizer import RandomOptimizer
        return RandomOptimizer()

    if opt_type == "grid":
        from core.optimizers.grid_optimizer import GridOptimizer
        return GridOptimizer(
            n_points_per_param=opt_cfg.get("n_points_per_param", 5),
        )

    # 未知类型，报错并提示可用选项
    raise ValueError(
        f"不支持的 optimizer_type: {opt_type} "
        f"(可选: auto/cmaes, pso, tpe, random, grid, custom)"
    )
