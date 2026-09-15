"""
Expert 模式模块
职责：基于用户提供的 Model Code（物理建模代码）生成初始控制律
"""

import json
import re
from typing import Dict, Any, Optional
from core.llm.gateway import get_llm
from core.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "core" / "llm" / "prompts"


def generate_initial_control_law(
    model_code: str,
    scene_config: Dict[str, Any],
    description: Optional[str] = None
) -> str:
    """
    基于 Model Code 生成初始控制律

    输入：
        model_code: 用户提供的物理建模代码（继承 BaseModel 的类）
        scene_config: 场景配置（包含 state_names, control_names, physical_params 等）
        description: 可选的自然语言描述

    输出：
        control_law_code: Python 函数字符串，签名：
            def control_law(t, x, state, params):
                ...
                return np.array([...])
    """
    llm = get_llm()

    # 加载通用模板
    template_path = PROMPTS_DIR / "control_law_generation.txt"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"[expert] 模板文件不存在: {template_path}，使用内联提示词")
        template = None

    if template:
        # 使用模板文件
        prompt = template.replace("{{model_code}}", model_code)
        prompt = prompt.replace("{{scene_config}}", json.dumps(scene_config, indent=2, ensure_ascii=False))
        prompt = prompt.replace("{{description}}", description or "（无额外描述）")
    else:
        # 兜底：使用内联提示词（简化版）
        state_names = scene_config.get("state_names", [])
        control_names = scene_config.get("control_names", [])
        physical_params = scene_config.get("physical_params", {})

        prompt = f"""You are a control system design expert. Given a physical system model code and scene configuration, generate an initial control law.

## Input

### Model Code (用户提供的物理建模代码)
```python
{model_code}
```

### Scene Configuration
- State variables: {state_names}
- Control variables: {control_names}
- Physical parameters: {physical_params}
{f"- Description: {description}" if description else ""}

## Task

Based on the model dynamics (rhs function), design an initial control law that:
1. Stabilizes the system toward target values
2. Uses reasonable control effort
3. Is simple but effective (e.g., proportional feedback, bang-bang, or PID-like)

## Output Format

Return ONLY a Python function with this exact signature:

```python
import numpy as np

def control_law(t, x, state, params):
    \"\"\"
    Control law for the physical system.

    Args:
        t: Current time (float)
        x: Spatial grid (ndarray, for PDE models; None or empty for ODE)
        state: Current state vector (ndarray, length = len(state_names))
        params: Tunable parameters dict (e.g., {{"k1": 0.5, "k2": 1.0}})

    Returns:
        control: Control input vector (ndarray, length = len(control_names))
    \"\"\"
    # Your control logic here
    return np.array([...])
```

## Guidelines
- Extract state variables from the `state` array using indices corresponding to state_names
- Use `params` dict for tunable gains (e.g., `params.get("k1", 0.5)`)
- For bang-bang control, use discrete values (e.g., 0 or 1)
- For continuous control, use proportional or PID-like terms
- Keep the logic simple (5-15 lines)
- Do NOT include the model dynamics (rhs) in the control law
- Return ONLY the code, no explanations
"""

    for attempt in range(3):
        try:
            content = llm.invoke(prompt)

            # 提取代码块
            code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', content, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                # 尝试直接提取函数定义
                func_match = re.search(r'(import numpy.*?def control_law.*)', content, re.DOTALL)
                if func_match:
                    code = func_match.group(1).strip()
                else:
                    code = content.strip()

            # 验证代码包含必要元素
            if "def control_law" in code and "return" in code:
                return code
            else:
                print(f"[expert] 生成尝试 {attempt + 1}: 代码缺少 control_law 函数或 return 语句")

        except Exception as e:
            print(f"[expert] 生成尝试 {attempt + 1} 失败: {e}")

        import time
        time.sleep(2 ** attempt)

    # ========== LLM 失败后的兜底逻辑 ==========
    control_names_fallback = scene_config.get("control_names", [])
    n_controls = len(control_names_fallback) if control_names_fallback else 1
    control_type = scene_config.get("control_type", "continuous")

    # 简单但符合模板格式的兜底代码
    if control_type == "bang_bang":
        fallback_code = f"""import numpy as np

# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float/int/bool on arrays.
# [ ] 2. np.where uses & / |.
# [ ] 3. np.max/min/abs used.
# [ ] 4. No for-loops over M.
# [ ] 5. Return shape correct.
# [ ] 6. All controls implemented.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: threshold (0.1, 10.0)
# @param: u_max (0.1, 1.0)
# ========== END PARAM DECLARATION ==========

def control_law(t, x, state, params):
    \"\"\"
    Fallback bang-bang (LLM failed).
    \"\"\"
    if len(state) > 0:
        s0 = state[0] if len(getattr(state, 'shape', [])) == 1 or (hasattr(state, 'shape') and len(state.shape) == 1) else (state[:, 0] if hasattr(state, '__getitem__') else state[0])
        # Simplified: assume 1D for fallback
        s0 = state[0] if not hasattr(state, 'shape') or len(state.shape) == 1 else state[0, 0] if len(state.shape) == 2 else state[0]
        threshold = params.get("threshold", 1.0)
        u_max = params.get("u_max", 1.0)
        u = 1.0 if s0 > threshold else 0.0
        return np.array([u] + [0.0] * ({n_controls} - 1))
    return np.zeros({n_controls})
"""
    else:
        fallback_code = f"""import numpy as np

# ========== VECTORIZATION SELF-CHECK ==========
# [ ] 1. No float/int/bool on arrays.
# [ ] 2. np.where uses & / |.
# [ ] 3. np.max/min/abs used.
# [ ] 4. No for-loops over M.
# [ ] 5. Return shape correct.
# [ ] 6. All controls implemented.
# ==============================================

# ========== PARAM DECLARATION ==========
# @param: gain (0.01, 100.0)
# @param: target (0.0, 10.0)
# ========== END PARAM DECLARATION ==========

def control_law(t, x, state, params):
    \"\"\"
    Fallback proportional (LLM failed).
    \"\"\"
    if len(state) > 0:
        s0 = state[0] if not hasattr(state, 'shape') or len(state.shape) == 1 else state[0, 0] if len(state.shape) == 2 else state[0]
        gain = params.get("gain", 0.5)
        target = params.get("target", 1.0)
        u = gain * (s0 - target)
        u = max(min(u, 1.0), -1.0)
        return np.array([u] + [0.0] * ({n_controls} - 1))
    return np.zeros({n_controls})
"""
    return fallback_code


def parse_expert_mode_files(
    model_code: str,
    parameters: Optional[Dict[str, Any]] = None,
    env_config: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    解析专家模式上传的 3 个文件,合并生成完整 scene_config + 控制律

    Args:
        model_code: model.py 内容
        parameters: parameters.json 内容 (可选)
        env_config: env.json 内容 (可选)
        description: 用户描述 (可选)

    Returns:
        {
            "scene_config_complete": {...},
            "control_law_code": "...",
            "warnings": [...]
        }
    """
    llm = get_llm()

    parameters_json = json.dumps(parameters, indent=2, ensure_ascii=False) if parameters else "(未提供)"
    env_json = json.dumps(env_config, indent=2, ensure_ascii=False) if env_config else "(未提供)"

    prompt = f"""你是控制系统专家。用户提供了 3 个文件,请合并生成完整的 scene_config 和初始控制律。

## 文件 1: Model Code (必须)
```python
{model_code}
```

## 文件 2: Parameters (可选)
{parameters_json}

## 文件 3: Environment Config (可选)
{env_json}

{f"## 描述: {description}" if description else ""}

## 任务

1. **合并配置**:
   - 从 model.py 提取 state_names, control_names, physical_params
   - 合并 parameters.json (如果提供,优先级更高)
   - 合并 env.json (如果提供,优先级更高)
   - 缺失字段使用合理默认值

2. **生成初始控制律** (control_law 函数)

## 输出 JSON (必须合法)
```json
{{
  "scene_config_complete": {{
    "domain_name": "...",
    "state_names": [...],
    "control_names": [...],
    "temporal": {{"T": 10.0, "dt": 0.01}},
    "initial_state": {{"x": 0.0}},
    "physical_params": {{"mass": 1.0}},
    "target_values": {{"x": 0.0}},
    "control_limits": {{"u": [-10, 10]}},
    "control_type": "continuous",
    "cost_weights": {{"x": 1.0, "u": 0.1}}
  }},
  "control_law_code": "import numpy as np\\ndef control_law(...):\\n    ...",
  "warnings": ["未提供 parameters.json,使用默认值"]
}}
```
"""

    warnings = []
    if not parameters:
        warnings.append("未提供 parameters.json,使用默认值")
    if not env_config:
        warnings.append("未提供 env.json,使用默认值")

    for attempt in range(3):
        try:
            content = llm.invoke(prompt)

            # 提取 JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(content)

            if "scene_config_complete" in result and "control_law_code" in result:
                result["warnings"] = warnings + result.get("warnings", [])
                return result

        except Exception as e:
            print(f"[expert] parse_expert_mode_files 尝试 {attempt + 1} 失败: {e}")

        import time
        time.sleep(2 ** attempt)

    # 兜底
    return {
        "scene_config_complete": {
            "domain_name": "custom",
            "state_names": ["x"],
            "control_names": ["u"],
            "temporal": {"T": 10.0, "dt": 0.01},
            "initial_state": {"x": 0.0},
            "physical_params": parameters or {},
            "target_values": {"x": 0.0},
            "control_type": "continuous",
            "cost_weights": {"x": 1.0, "u": 0.1}
        },
        "control_law_code": "# LLM 解析失败,请手动编写控制律",
        "warnings": warnings + ["LLM 解析失败"]
    }


def parse_single_model_file(
    model_code: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    【核心职责】解析单一 model.py 文件，提取 scene_config

    ⚠️ 严格职责边界：
    - ✅ 只提取 scene_config（temporal, state_names, physical_params 等）
    - ✅ 执行 ODE/PDE 自动检测
    - ✅ 自动补全 n_steps/n_spatial
    - ✅ 提供 llm_status 状态跟踪和兜底机制
    - ❌ 绝不生成 control_law_code（控制律生成改为独立步骤）

    流程变更：
    旧流程：parse_single_model_file → 自动生成 control_law
    新流程：parse_single_model_file → 用户确认 scene_config → generate_initial_control_law

    Args:
        model_code: 完整 model.py 代码
        description: 用户描述 (可选)

    Returns:
        {
            "success": bool,
            "scene_config_extracted": {...},  # 仅 scene_config，不含 control_law
            "extraction_log": [...],
            "warnings": [...],
            "detected_type": {...},
            "llm_status": {...},
            "fallback_mode": bool
        }
    """
    # 尝试从 core.parsers 导入（生产环境）
    import_success = False
    try:
        from core.parsers.model_classifier import classify_model_type
        from core.parsers.optimization_evaluator import OptimizationEvaluator
        from core.parsers.scene_config_validator import validate_and_complete_temporal
        import_success = True
    except ImportError:
        pass

    # 如果失败，尝试从 backend.src.parsers 导入（开发环境）
    if not import_success:
        try:
            from backend.src.parsers.model_classifier import classify_model_type
            from backend.src.parsers.optimization_evaluator import OptimizationEvaluator
            from backend.src.parsers.scene_config_validator import validate_and_complete_temporal
            import_success = True
        except ImportError:
            pass

    # 如果两个路径都失败，使用简化的本地实现
    if not import_success:
        print("[expert] 警告: 无法导入 parsers 模块，使用简化实现")
        classify_model_type = None  # 标记为不可用

    llm = get_llm()

    # ========== Step 0: ODE/PDE类型检测 ==========
    import asyncio
    type_detection = {
        "model_type": "unknown",
        "confidence": 0.0,
        "evidence": ["类型检测跳过（parsers 模块不可用）"],
        "user_can_override": True
    }

    if classify_model_type is not None:
        try:
            # 使用同步版本 detect_model_type_from_code（跳过 LLM 验证层）
            from core.parsers.model_classifier import detect_model_type_from_code
            type_detection = detect_model_type_from_code(model_code)
        except Exception as e:
            print(f"[expert] 类型检测失败: {e}")
            type_detection = {
                "model_type": "unknown",
                "confidence": 0.0,
                "evidence": ["类型检测异常"],
                "user_can_override": True
            }

    detected_type = type_detection.get("model_type", "unknown")
    print(f"[expert] 检测到模型类型: {detected_type} (置信度: {type_detection.get('confidence', 0)})")

    # 构建增强的prompt
    type_hint = ""
    if detected_type == "pde":
        type_hint = "\n**注意**: 此模型被检测为PDE（偏微分方程），请特别注意提取空间参数 (x_length, dx)。"
    elif detected_type == "ode":
        type_hint = "\n**注意**: 此模型被检测为ODE（常微分方程），请重点提取时间参数 (T, dt)。"

    prompt = f"""你是 Python 代码解析专家。分析用户提供的 model.py 文件,提取所有硬编码参数并生成结构化配置。{type_hint}

## 输入代码
```python
{model_code}
```

{f"## 描述: {description}" if description else ""}

## 任务

**1. 代码结构分析**:
- 找到 `class XXXModel(BaseModel)` 定义
- 找到 `__init__` 方法中的所有 `self.xxx = yyy` 赋值

**2. 参数分类提取**:
- **物理参数** → `physical_params`: mass, damping, spring_constant, beta, gamma, R, L, J 等
- **时间参数** → `temporal`: T, dt, total_time, step_size 等
- **初始状态** → `initial_state`: position=1.0, velocity=0.0 等
- **目标值** → `target_values`: 通常为 0 或稳态值（如果代码中有明确定义）
- **控制约束** → `control_limits`: force=[-10,10] 等(如果代码中有)

**3. 生成 scene_config（不生成控制律）**

**【强制要求】**:
- `control_type`: 必须从 model_code 推断或默认 "continuous"（可选值: "continuous", "bang_bang"）
- `cost_weights`: 必须包含所有 state_names 和 control_names 的权重，state 默认 1.0，control 默认 0.1
- `n_steps`: 必须从 T/dt 自动计算（不是硬编码 1000）

## 输出 JSON (必须合法)
```json
{{
  "scene_config_extracted": {{
    "domain_name": "...",
    "state_names": [...],
    "control_names": [...],
    "temporal": {{"T": 10.0, "dt": 0.01}},
    "initial_state": {{"position": 1.0}},
    "physical_params": {{"mass": 1.0}},
    "target_values": {{"position": 0.0}},
    "control_limits": {{"force": [-10.0, 10.0]}},
    "control_type": "continuous",
    "cost_weights": {{"position": 1.0, "force": 0.1}}
  }},
  "extraction_log": [
    "第 5 行: self.mass = 1.0 → physical_params.mass",
    "第 8 行: self.T = 10.0 → temporal.T"
  ],
  "warnings": []
}}
```
"""

    # LLM 调用状态跟踪
    llm_status = {
        "status": "success",
        "confidence": 1.0,
        "missing_fields": [],
        "error_message": None
    }

    for attempt in range(3):
        try:
            content = llm.invoke(prompt)

            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(content)

            if "scene_config_extracted" in result:
                # 验证必要字段
                missing = []
                extracted = result["scene_config_extracted"]

                if not extracted.get("state_names"):
                    missing.append("state_names")
                if not extracted.get("control_names"):
                    missing.append("control_names")
                if not extracted.get("temporal", {}).get("T"):
                    missing.append("temporal.T")
                if not extracted.get("temporal", {}).get("dt"):
                    missing.append("temporal.dt")

                if missing:
                    llm_status = {
                        "status": "partial",
                        "confidence": 0.5,
                        "missing_fields": missing,
                        "error_message": f"LLM 未提取到: {', '.join(missing)}"
                    }
                    result["warnings"] = result.get("warnings", []) + [f"缺失字段: {missing}"]

                # 注入 llm_status
                result["llm_status"] = llm_status
                result["success"] = True
                result["fallback_mode"] = False

                # ========== Step 4: 参数验证补全 ==========
                try:
                    result["scene_config_extracted"]["detected_type"] = detected_type

                    # 🆕 强制重算 n_steps（覆盖 LLM 给的默认值）
                    extracted = result["scene_config_extracted"]
                    temporal = extracted.get("temporal", {})
                    T_val = temporal.get("T")
                    dt_val = temporal.get("dt")
                    if T_val and dt_val and float(dt_val) > 0:
                        temporal["n_steps"] = int(round(float(T_val) / float(dt_val)))
                        extracted["temporal"] = temporal
                        print(f"[expert] 重算 n_steps = {temporal['n_steps']} (T={T_val}, dt={dt_val})")

                    validation_result = validate_and_complete_temporal(result["scene_config_extracted"])
                    result["scene_config_extracted"] = validation_result["scene_config"]
                    result["warnings"] = result.get("warnings", []) + validation_result.get("warnings", [])

                    print(f"[expert] scene_config 解析完成")

                except Exception as e:
                    print(f"[expert] 验证失败: {e}")

                return result

        except Exception as e:
            print(f"[expert] parse_single_model_file 尝试 {attempt + 1} 失败: {e}")

        import time
        time.sleep(2 ** attempt)

    # ========== LLM 完全失败的兜底 ==========
    print("[expert] LLM 调用失败，启用兜底模式")

    llm_status = {
        "status": "failed",
        "confidence": 0.0,
        "missing_fields": ["所有字段"],
        "error_message": "LLM 调用失败，请手动填写配置"
    }

    # 尝试静态提取
    static_info = extract_static_info(model_code)

    # ⚠️ 严格职责：兜底响应只包含 scene_config，不包含 control_law_code
    fallback_result = {
        "success": True,
        "scene_config_extracted": {
            "domain_name": static_info.get("domain_name", "custom"),
            "state_names": static_info.get("state_names", []),
            "control_names": static_info.get("control_names", []),
            "temporal": {"T": 10.0, "dt": 0.01, "n_steps": 1000},
            "initial_state": static_info.get("initial_state", {}),
            "physical_params": static_info.get("physical_params", {}),
            "target_values": {},
            "control_limits": {},
            "detected_type": detected_type
        },
        "extraction_log": static_info.get("extraction_log", []),
        "warnings": ["LLM 解析失败，请手动补充缺失信息"],
        "detected_type": type_detection,
        "llm_status": llm_status,
        "fallback_mode": True
        # ❌ 不包含 control_law_code - 控制律生成需单独调用 generate_initial_control_law
    }

    return fallback_result


def extract_static_info(model_code: str) -> Dict[str, Any]:
    """
    不依赖 LLM 的静态提取（基于正则和 AST）
    提取：state_names, control_names, initial_state, physical_params, domain_name

    当 LLM 调用失败时，作为兜底使用
    """
    import re
    import ast

    result: Dict[str, Any] = {
        "domain_name": "custom",
        "state_names": [],
        "control_names": [],
        "initial_state": {},
        "physical_params": {},
        "extraction_log": []
    }

    try:
        tree = ast.parse(model_code)

        # 提取 domain_name（从类名）
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if "Model" in node.name or "model" in node.name.lower():
                    result["domain_name"] = node.name.replace("Model", "").replace("model", "")
                    result["extraction_log"].append(f"从类名提取 domain_name: {result['domain_name']}")
                    break

        # 提取 state_names（从 rhs 方法的参数解包）
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "rhs":
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        if (isinstance(child.value, ast.Name) and
                            child.value.id == "state"):
                            for target in child.targets:
                                if isinstance(target, ast.Tuple):
                                    result["state_names"] = [
                                        elt.id for elt in target.elts
                                        if isinstance(elt, ast.Name)
                                    ]
                                    result["extraction_log"].append(
                                        f"从 rhs 解包提取 state_names: {result['state_names']}"
                                    )

        # 提取 physical_params 和 initial_state（从 __init__ 的 self.xxx = yyy）
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                                if target.value.id == "self":
                                    param_name = target.attr
                                    if param_name.startswith("_"):
                                        continue

                                    if isinstance(child.value, ast.Constant):
                                        value = child.value.value
                                        if isinstance(value, (int, float)):
                                            # 判断是 initial_state 还是 physical_params
                                            if param_name.startswith("initial_"):
                                                var_name = param_name.replace("initial_", "")
                                                result["initial_state"][var_name] = value
                                                result["extraction_log"].append(
                                                    f"提取 initial_state.{var_name} = {value}"
                                                )
                                            else:
                                                result["physical_params"][param_name] = value
                                                result["extraction_log"].append(
                                                    f"提取 physical_params.{param_name} = {value}"
                                                )

        # 推断 control_names
        if "def control_law" in model_code or "control" in model_code.lower():
            # 尝试从 return 语句推断
            control_match = re.search(r'return\s+np\.array\(\s*\[(.*?)\]', model_code, re.DOTALL)
            if control_match:
                # 简单假设为单控制
                result["control_names"] = ["u"]
            else:
                result["control_names"] = ["u"]
            result["extraction_log"].append(f"推断 control_names: {result['control_names']}")

    except SyntaxError as e:
        result["extraction_log"].append(f"语法错误，无法解析: {e}")
    except Exception as e:
        result["extraction_log"].append(f"静态提取异常: {e}")

    return result


def refine_control_law(
    current_code: str,
    feedback: str,
    scene_config: Dict[str, Any]
) -> str:
    """
    根据用户反馈优化控制律

    输入：
        current_code: 当前控制律代码
        feedback: 用户反馈（如 "增加控制强度"）
        scene_config: 场景配置

    输出：
        refined_code: 优化后的控制律代码
    """
    llm = get_llm()

    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])

    prompt = f"""You are a control system design expert. Refine the given control law based on user feedback.

## Current Control Law
```python
{current_code}
```

## User Feedback
{feedback}

## Scene Configuration
- State variables: {state_names}
- Control variables: {control_names}

## Task
Modify the control law according to the feedback while keeping the same function signature.

## Output Format
Return ONLY the refined Python code (no explanations).
"""

    try:
        content = llm.invoke(prompt)

        # 提取代码块
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', content, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            code = content.strip()

        if "def control_law" in code:
            return code
        else:
            return current_code  # 失败时返回原代码

    except Exception as e:
        print(f"[expert] 优化失败: {e}")
        return current_code
