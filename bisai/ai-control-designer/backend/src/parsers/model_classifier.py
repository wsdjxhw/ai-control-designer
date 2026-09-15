"""
模型类型检测器 - 基于AST分析判断ODE/PDE
三层防御：规则匹配 → LLM验证 → 用户确认
"""

import ast
from typing import Dict, Any, Literal, List

ModelType = Literal["ode", "pde", "unknown"]


def detect_model_type_from_code(model_code: str) -> Dict[str, Any]:
    """
    基于AST分析 model.py 代码，判断是ODE还是PDE

    检测依据（优先级从高到低）：
    1. rhs方法签名（最可靠）
    2. state变量维度（次可靠）
    3. 空间参数使用（辅助）

    Returns:
        {
            "model_type": "ode" | "pde" | "unknown",
            "confidence": 0.0-1.0,
            "evidence": [...],
            "rhs_signature": "def rhs(self, state, t)" | ...
        }
    """
    try:
        tree = ast.parse(model_code)
    except SyntaxError as e:
        return {
            "model_type": "unknown",
            "confidence": 0.0,
            "evidence": [f"语法错误: {e}"],
            "rhs_signature": None
        }

    evidence: List[str] = []
    model_type: ModelType = "unknown"
    confidence = 0.0
    rhs_signature = None

    for node in ast.walk(tree):
        # 检测1: rhs方法签名（最高优先级）
        if isinstance(node, ast.FunctionDef) and node.name == "rhs":
            args = [arg.arg for arg in node.args.args]
            # 跳过 self
            args = [a for a in args if a != "self"]

            rhs_signature = f"def rhs(self, {', '.join(args)})"

            if "x" in args or "spatial" in args or "grid" in args:
                model_type = "pde"
                evidence.append(f"rhs签名包含空间变量: {args}")
                confidence = 0.95
            elif len(args) >= 2 and args[0] in ["state", "y", "u"]:
                model_type = "ode"
                evidence.append(f"rhs签名仅含时间变量: {args}")
                confidence = 0.90

        # 检测2: 空间参数赋值（辅助证据）
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if target.attr in ["dx", "x_length", "spatial_grid", "n_spatial"]:
                        if model_type != "pde":
                            evidence.append(f"发现空间参数: {target.attr}")
                            if confidence < 0.7:
                                model_type = "pde"
                                confidence = 0.7

    # 兜底：如果没有找到rhs，尝试从类名/注释推断
    if model_type == "unknown":
        code_lower = model_code.lower()
        if any(kw in code_lower for kw in ["pde", "partial", "wave equation", "heat equation"]):
            model_type = "pde"
            evidence.append("类名/注释包含PDE关键词")
            confidence = 0.5
        elif any(kw in code_lower for kw in ["ode", "state space", "dx/dt", "dy/dt"]):
            model_type = "ode"
            evidence.append("类名/注释包含ODE关键词")
            confidence = 0.5

    return {
        "model_type": model_type,
        "confidence": confidence,
        "evidence": evidence,
        "rhs_signature": rhs_signature
    }


async def llm_verify_model_type(model_code: str, rule_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM二次验证（仅在规则置信度<0.8时调用）
    """
    if rule_result["confidence"] >= 0.8:
        return rule_result  # 规则已经很确定，不需要LLM

    prompt = f"""你是一个控制系统专家。请判断下面这个Python模型代码是ODE还是PDE。

只返回两个词：ODE 或 PDE

判断依据：
- 如果 rhs 方法只有 state 和 t 两个参数 → ODE
- 如果 rhs 方法有 state, x, t 三个参数，或 state 是二维数组 → PDE

代码：
```python
{model_code[:2000]}
```
"""

    try:
        from core.llm.gateway import get_llm
        llm = get_llm()
        response = llm.invoke(prompt).strip().upper()

        if response in ["ODE", "PDE"]:
            return {
                **rule_result,
                "model_type": response.lower(),
                "confidence": max(rule_result["confidence"], 0.85),
                "evidence": rule_result["evidence"] + [f"LLM验证: {response}"]
            }
    except Exception as e:
        print(f"[model_type_detector] LLM验证失败: {e}")

    return rule_result


async def classify_model_type(model_code: str) -> Dict[str, Any]:
    """
    三层防御：规则匹配 → LLM验证 → 用户确认

    Returns:
        {
            "model_type": "ode" | "pde" | "unknown",
            "confidence": 0.0-1.0,
            "evidence": [...],
            "rhs_signature": ...,
            "user_can_override": True,
            "detection_method": "rule+llm" | "llm_fallback"
        }
    """
    # 层1: 规则匹配（AST分析）
    rule_result = detect_model_type_from_code(model_code)

    # 层2: LLM验证（仅在置信度<0.8时）
    verified_result = await llm_verify_model_type(model_code, rule_result)

    # 层3: 返回结果 + 前端用户确认
    return {
        **verified_result,
        "user_can_override": True,  # 前端显示切换按钮
        "detection_method": "rule+llm" if verified_result["confidence"] >= 0.8 else "llm_fallback"
    }
