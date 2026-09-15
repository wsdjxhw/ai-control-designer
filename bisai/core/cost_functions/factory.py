"""代价函数工厂：根据 scene_config 中的 cost.type 创建对应的代价函数实例。
支持四种模式：template | expression | code | unified
"""

from __future__ import annotations

from core.base.base_cost import BaseCost
from core.cost_functions.template_cost import TemplateCost


def create_cost(scene_config: dict) -> BaseCost:
    """根据 scene_config 创建代价函数实例。

    支持四种代价函数类型：
    - template: 基于权重的模板代价（默认）
    - expression: 基于 SymPy 符号表达式的代价（分开 running/terminal）
    - code: 基于自定义 Python 代码的代价（分开 running/terminal）
    - unified: 统一表达式模式，用户只写一个表达式

    Args:
        scene_config: 场景配置字典，需包含 cost_function.cost_type 字段。

    Returns:
        BaseCost 子类实例。

    Raises:
        ValueError: cost_type 不被支持时抛出。
    """
    # 兼容两种命名：cost_function（新）或 cost（旧）
    cost_cfg = scene_config.get("cost_function") or scene_config.get("cost", {})
    cost_type = cost_cfg.get("cost_type") or cost_cfg.get("type", "template")

    if cost_type == "template":
        return TemplateCost(scene_config)
    elif cost_type == "expression":
        from core.cost_functions.expression_cost import ExpressionCost
        return ExpressionCost(scene_config)
    elif cost_type == "code":
        from core.cost_functions.code_cost import CodeCost
        return CodeCost(scene_config)
    elif cost_type == "unified":
        from core.cost_functions.unified_expression_cost import UnifiedExpressionCost
        return UnifiedExpressionCost(scene_config)
    else:
        raise ValueError(
            f"不支持的代价类型: {cost_type} "
            f"(可选: template, expression, code, unified)"
        )
