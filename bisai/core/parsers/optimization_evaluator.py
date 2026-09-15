"""
优化评估器 - 评估优化器配置的合理性
"""

from typing import Dict, Any, List


class OptimizationEvaluator:
    """
    评估优化配置（CMA-ES, PSO, TPE等）的参数合理性
    """

    @staticmethod
    def evaluate_optimizer_config(optimizer_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估优化器配置

        Returns:
            {
                "valid": bool,
                "warnings": [...],
                "suggestions": [...]
            }
        """
        warnings: List[str] = []
        suggestions: List[str] = []

        optimizer_type = optimizer_config.get("optimizer_type", "cmaes")

        if optimizer_type == "cmaes":
            popsize = optimizer_config.get("popsize", 50)
            if popsize < 10:
                warnings.append(f"CMA-ES 种群大小过小 ({popsize})，建议至少 20-50")
            elif popsize > 200:
                suggestions.append(f"CMA-ES 种群较大 ({popsize})，收敛可能较慢但更稳定")

        elif optimizer_type == "pso":
            n_particles = optimizer_config.get("n_particles", 30)
            if n_particles < 20:
                warnings.append(f"PSO 粒子数过少 ({n_particles})，建议 30-100")

        elif optimizer_type == "tpe":
            n_startup = optimizer_config.get("n_startup_trials", 10)
            if n_startup < 5:
                suggestions.append("TPE 随机采样次数较少，建议至少 10 次以建立先验")

        return {
            "valid": len(warnings) == 0,
            "warnings": warnings,
            "suggestions": suggestions
        }
