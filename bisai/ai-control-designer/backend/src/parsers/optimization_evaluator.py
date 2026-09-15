"""
优化评估器 - 评估模型是否需要优化，以及优化策略
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class OptimizationSuggestion:
    category: str  # "complexity" | "numerical" | "structure"
    priority: str  # "high" | "medium" | "low"
    message: str
    auto_fixable: bool = False


class OptimizationEvaluator:
    """
    评估模型是否需要优化，以及优化方向

    评估维度：
    1. 模型复杂度（状态维度、控制维度）
    2. 数值稳定性风险
    3. 结构可优化性
    """

    def evaluate(
        self,
        model_code: str,
        scene_config: Dict[str, Any],
        model_type: str
    ) -> Dict[str, Any]:
        """
        Returns:
            {
                "needs_optimization": bool,
                "complexity_score": 0-10,
                "suggestions": List[dict],
                "recommended_strategy": "standard" | "multi_fidelity" | "early_stop"
            }
        """
        suggestions: List[OptimizationSuggestion] = []
        complexity_score = 0

        # ========== 维度1: 状态空间复杂度 ==========
        n_states = len(scene_config.get("state_names", []))
        n_controls = len(scene_config.get("control_names", []))

        if n_states >= 10:
            suggestions.append(OptimizationSuggestion(
                category="complexity",
                priority="high",
                message=f"状态维度过高 (n_states={n_states})，建议使用多保真度优化",
                auto_fixable=False
            ))
            complexity_score += 3

        if n_states * n_controls >= 20:
            suggestions.append(OptimizationSuggestion(
                category="complexity",
                priority="medium",
                message=f"参数空间过大 (n_states×n_controls={n_states*n_controls})，建议早停策略",
            ))
            complexity_score += 2

        # ========== 维度2: PDE网格规模 ==========
        if model_type == "pde":
            space_time = scene_config.get("space_time", {})
            n_spatial = space_time.get("n_spatial")

            if n_spatial and n_spatial > 500:
                suggestions.append(OptimizationSuggestion(
                    category="numerical",
                    priority="high",
                    message=f"PDE空间离散点过多 (n_spatial={n_spatial})，计算量大，建议粗网格预筛选",
                ))
                complexity_score += 4

        # ========== 维度3: 时间步数 ==========
        temporal = scene_config.get("temporal", {})
        n_steps = temporal.get("n_steps")

        if n_steps and n_steps > 50000:
            suggestions.append(OptimizationSuggestion(
                category="numerical",
                priority="high",
                message=f"时间步数过多 (n_steps={n_steps})，建议自适应步长或多保真度",
            ))
            complexity_score += 3

        # ========== 维度4: 控制律复杂度（从代码分析） ==========
        if "for " in model_code and model_code.count("for ") > 3:
            suggestions.append(OptimizationSuggestion(
                category="structure",
                priority="medium",
                message="控制律包含过多循环，建议向量化改写以提升性能",
                auto_fixable=True
            ))
            complexity_score += 1

        # ========== 综合判断 ==========
        needs_optimization = complexity_score >= 4

        recommended_strategy = "standard"
        if complexity_score >= 7:
            recommended_strategy = "multi_fidelity"
        elif complexity_score >= 4:
            recommended_strategy = "early_stop"

        return {
            "needs_optimization": needs_optimization,
            "complexity_score": complexity_score,
            "suggestions": [
                {
                    "category": s.category,
                    "priority": s.priority,
                    "message": s.message,
                    "auto_fixable": s.auto_fixable
                }
                for s in suggestions[:5]
            ],
            "recommended_strategy": recommended_strategy
        }
