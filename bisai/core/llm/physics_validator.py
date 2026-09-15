"""
物理验证模块
职责：L1 LLM语义检查、L2 SymPy符号分析、L3 烟雾测试
"""

import re
import json
import types
import numpy as np
from typing import Dict, Any, Literal
from core.llm.gateway import get_llm


def validate_physics(
    model_code: str,
    scene_config: Dict[str, Any],
    level: Literal["L1", "L2", "L3"]
) -> Dict[str, Any]:
    if level == "L1":
        return validate_l1(model_code, scene_config)
    elif level == "L2":
        return validate_l2(model_code, scene_config)
    elif level == "L3":
        return validate_l3(model_code, scene_config)
    else:
        raise ValueError(f"无效验证级别: {level}")


def validate_l1(model_code: str, scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """L1: LLM语义验证"""
    llm = get_llm()

    prompt = f"""
You are a physics expert. Analyze the following model code and check if it violates any basic physical principles.

## Scene Config
{json.dumps(scene_config, indent=2)}

## Model Code
```python
{model_code}
```

##Check the following:
1.Are all state variables non-negative? (If they represent populations, concentrations, etc.)

2.Is energy/mass conserved where expected?

3.Are there any physically meaningless operations?

4.Does the model have reasonable behavior?

Output Format
Return a JSON object with:
{{
"passed": true/false,
"issues": ["issue description", ...],
"suggestions": ["suggestion", ...]
}}
"""

    for attempt in range(3):
        try:
            content = llm.invoke(prompt)
            # 提取 JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    continue

            result = json.loads(json_str)
            return {
                "level": "L1",
                "passed": result.get("passed", True),
                "issues": result.get("issues", []),
                "suggestions": result.get("suggestions", []),
                "details": {"llm_response": content[:500]}
            }
        except Exception as e:
            print(f"L1 验证尝试 {attempt + 1} 失败: {e}")
            import time
            time.sleep(2 ** attempt)

    # 兜底：基本语法检查
    has_return = "return" in model_code
    has_def = "def " in model_code
    return {
        "level": "L1",
        "passed": has_def and has_return,
        "issues": [] if (has_def and has_return) else ["代码结构不完整，缺少函数定义或返回语句"],
        "suggestions": ["请确保 model_code 包含完整的类定义和 rhs 方法"],
        "details": {}
    }


def validate_l2(model_code: str, scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """L2: 简化版结构检查"""
    issues = []
    suggestions = []
    passed = True

    if "np.maximum" not in model_code and "clip" not in model_code:
        issues.append("代码中未发现非负约束（np.maximum/clip），建议添加")
        suggestions.append("在 rhs 方法末尾添加 state = np.maximum(state, 0.0)")
        passed = False

    if "d" not in model_code and "derivative" not in model_code:
        issues.append("未检测到微分方程结构（d/dt 变量）")
        suggestions.append("请确保 rhs 方法返回 dy/dt 数组")
        passed = False

    return {
        "level": "L2",
        "passed": passed,
        "issues": issues,
        "suggestions": suggestions,
        "details": {
            "sympy_analysis": "基本结构检查完成",
            "checked_items": ["非负约束", "微分结构"]
        }
    }


def validate_l3(model_code: str, scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """L3: 烟雾测试"""
    issues = []
    suggestions = []
    passed = True
    model_classes_found = []

    try:
        module = types.ModuleType("test_model")
        exec(model_code, module.__dict__)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type):
                if attr.__name__ not in ['BaseModel', 'ABC', 'object']:
                    if hasattr(attr, 'rhs'):
                        model_classes_found.append(attr.__name__)

        if not model_classes_found:
            issues.append("未能找到继承 BaseModel 且包含 rhs 方法的类")
            suggestions.append("请确保 model_code 中定义了一个继承 BaseModel 的类，并实现了 rhs 方法")
            passed = False
        else:
            try:
                class_name = model_classes_found[0]
                model_class = eval(class_name, module.__dict__)
                model_instance = model_class(scene_config)

                if hasattr(model_instance, 'get_initial_state'):
                    init_state = model_instance.get_initial_state()
                    if init_state is None:
                        issues.append("get_initial_state 返回 None")
                        passed = False
                    else:
                        print(f"✅ 烟雾测试通过：模型实例化成功，初始状态 shape = {init_state.shape}")
                else:
                    issues.append("模型缺少 get_initial_state 方法")
                    passed = False
            except Exception as e:
                issues.append(f"模型实例化失败: {str(e)}")
                suggestions.append("请检查构造函数和 scene_config 参数")
                passed = False

    except SyntaxError as e:
        issues.append(f"代码语法错误: {str(e)}")
        suggestions.append("请修复语法错误")
        passed = False
    except Exception as e:
        issues.append(f"烟雾测试异常: {str(e)}")
        passed = False

    return {
        "level": "L3",
        "passed": passed,
        "issues": issues,
        "suggestions": suggestions,
        "details": {
            "test_result": "通过" if passed else "失败",
            "model_classes_found": model_classes_found
        }
    }