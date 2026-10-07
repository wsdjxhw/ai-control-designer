"""
LLM 控制律代码修改模块
职责：基于诊断报告 + 场景上下文，调用 LLM 生成下一版本控制律代码

两级策略：
  第 1 级：完整修改（可改结构 + 参数）
  第 2 级：局部修改（只改参数边界，不改函数结构）
  都失败 → 返回 None（由 engine 复制上一版代码）
"""

import json
import os
import re
import time
from typing import Optional

from core.config import PROJECT_ROOT
from core.llm.gateway import get_llm
from core.llm.utils import extract_code_from_response, validate_syntax

PROMPTS_DIR = PROJECT_ROOT / "core" / "llm" / "prompts"


def _build_scene_context(scene_config: dict) -> str:
    """
    从 scene_config 构造 LLM 可读的场景上下文
    支持 ODE / PDE 两种领域，自动适配。
    """
    if not scene_config:
        return "(Scene context not available)"

    lines = ["[SCENE CONTEXT — MUST FOLLOW]"]

    model_type = scene_config.get("model_type") or scene_config.get("detected_type", "unknown")
    domain = scene_config.get("domain_name", "custom")
    is_pde = model_type == "pde"
    lines.append(f"- Domain: {domain}  (model_type={model_type})")
    if is_pde:
        lines.append("  *** This is a PDE (partial differential equation) problem. ***")
        lines.append("  *** State and control are spatial fields, not scalars. ***")
    else:
        lines.append("  This is an ODE (ordinary differential equation) problem.")

    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])
    n_states = len(state_names)
    n_controls = len(control_names)
    lines.append(f"- State variables ({n_states}): {state_names}")
    lines.append(f"- Control variables ({n_controls}): {control_names}")
    lines.append(f"  => control_law MUST return an array with EXACTLY {n_controls} column(s).")

    control_type = scene_config.get("control_type", "continuous")
    lines.append(f"- Control type: {control_type.upper()}")
    if control_type == "bang_bang":
        lines.append("  *** Bang-bang: use np.where(cond, val, 0.0) with DISCRETE values. ***")
    else:
        lines.append("  *** Continuous: use multiplication / addition / np.clip. ***")
        lines.append("  *** DO NOT use np.where with discrete values. ***")

    temporal = scene_config.get("temporal", {})
    T = temporal.get("T", 10.0)
    dt = temporal.get("dt", 0.01)
    N = temporal.get("n_steps")
    if N is None:
        N = int(T / dt) if dt > 0 else 1000
    lines.append(f"- Time: T = {T}, dt = {dt}, N = {N} steps")
    lines.append(f"  => Simulation time T = {T} (do NOT hardcode other values)")

    if is_pde:
        spatial = scene_config.get("spatial", {})
        X = spatial.get("X", spatial.get("x_length", 2.0))
        dx = spatial.get("dx", 0.01)
        M_plus_1 = int(X / dx) + 1 if dx > 0 else 201
        lines.append(f"- Space: X = {X}, dx = {dx}, grid points = {M_plus_1}")
        lines.append(f"  => Return shape must be (M+1, {n_controls}) = ({M_plus_1}, {n_controls})")

    targets = scene_config.get("target_values", {})
    if targets:
        lines.append(f"- Target values: {targets}")

    init_state = scene_config.get("initial_state", {})
    if init_state:
        lines.append(f"- Initial state: {init_state}")

    lines.append("")
    lines.append("*** Any modification MUST be consistent with the above context. ***")

    return "\n".join(lines)


# ============================================================
# 第 1 级：完整修改
# ============================================================

def _try_full_modify(
    current_code: str,
    diagnosis_report: str,
    history_summary: str,
    scene_config: Optional[dict],
    vectorization_rules_path: str,
    template_path: str,
) -> Optional[str]:
    """第 1 级：完整修改（3 次重试）"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"[code_modify][L1] 模板文件不存在: {template_path}")
        return None

    vectorization_rules = ""
    if os.path.exists(vectorization_rules_path):
        with open(vectorization_rules_path, 'r', encoding='utf-8') as f:
            vectorization_rules = f.read()

    scene_context = _build_scene_context(scene_config or {})

    prompt = template.replace("{{scene_context}}", scene_context)
    prompt = prompt.replace("{{history_summary}}", history_summary or "暂无历史记录")
    prompt = prompt.replace("{{current_code}}", current_code)
    prompt = prompt.replace("{{diagnosis_report}}", diagnosis_report)
    prompt = prompt.replace("{{vectorization_rules}}", vectorization_rules)

    llm = get_llm()
    last_error = None

    for attempt in range(3):
        try:
            response_content = llm.invoke(prompt, max_tokens=30000)
            new_code = extract_code_from_response(response_content)
            if new_code:
                is_valid, error_msg = validate_syntax(new_code)
                if is_valid:
                    return new_code
                else:
                    print(f"[code_modify][L1] 尝试 {attempt+1} 语法错误: {error_msg}")
            else:
                print(f"[code_modify][L1] 尝试 {attempt+1}: 未提取到代码块")
        except Exception as e:
            print(f"[code_modify][L1] 尝试 {attempt+1} 失败: {e}")
            last_error = e
            time.sleep(2 ** attempt)

    print(f"[code_modify][L1] 3 次重试全部失败，最后错误: {last_error}")
    return None


# ============================================================
# 第 2 级：局部修改（只改参数边界）
# ============================================================

def _extract_param_declarations(code: str) -> str:
    """提取代码中的 # @param 声明块（用于给 LLM 参考）"""
    pattern = re.compile(r'#\s*@param:?\s+\S+.*')
    matches = pattern.findall(code)
    if not matches:
        return "(当前代码没有任何 # @param 声明)"
    return "\n".join(matches)


def _try_local_modify(
    current_code: str,
    diagnosis_report: str,
    scene_config: Optional[dict],
) -> Optional[str]:
    """第 2 级：局部修改（只改参数边界），2 次重试"""
    llm = get_llm()

    param_block = _extract_param_declarations(current_code)

    scene_config = scene_config or {}
    model_type = scene_config.get("model_type", "unknown")
    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])
    targets = scene_config.get("target_values", {})

    # 用三个引号包裹 prompt；内部避免使用 markdown 代码围栏
    prompt = (
        "你是控制系统专家。请只修改参数边界，不改函数结构。\n\n"
        "## 当前控制律代码\n"
        f"{current_code}\n\n"
        "## 诊断报告摘要\n"
        f"{diagnosis_report[:1500]}\n\n"
        "## 场景信息\n"
        f"- 模型类型: {model_type}\n"
        f"- 状态变量: {state_names}\n"
        f"- 控制变量: {control_names}\n"
        f"- 目标值: {targets}\n\n"
        "## 当前参数声明\n"
        f"{param_block}\n\n"
        "---\n\n"
        "## 任务\n"
        "请只做以下修改：\n"
        "1. 调整现有 `# @param:` 声明中的 (lower, upper) 边界值\n"
        "2. 让参数搜索范围更符合诊断报告的建议\n"
        "3. 不要改函数体\n"
        "4. 不要加新参数\n"
        "5. 不要删除参数\n"
        "6. 不要改名\n\n"
        "## 输出格式（严格遵守）\n"
        "- 只输出完整的 Python 代码\n"
        "- 不要输出任何解释文字\n"
        "- 不要用 markdown 代码块包裹\n"
        "- 第一行必须是 Python 注释或 import\n"
        "- 最后一行必须是 return 语句\n\n"
        "现在直接输出修改后的完整代码：\n"
    )

    for attempt in range(2):
        try:
            response_content = llm.invoke(prompt, max_tokens=3000)
            new_code = extract_code_from_response(response_content)

            if not new_code:
                print(f"[code_modify][L2] 尝试 {attempt+1}: 未提取到代码块")
                continue

            is_valid, error_msg = validate_syntax(new_code)
            if not is_valid:
                print(f"[code_modify][L2] 尝试 {attempt+1} 语法错误: {error_msg}")
                continue

            if "def control_law" not in new_code:
                print(f"[code_modify][L2] 尝试 {attempt+1}: 缺少 control_law 函数")
                continue

            if "return" not in new_code:
                print(f"[code_modify][L2] 尝试 {attempt+1}: 缺少 return 语句")
                continue

            return new_code

        except Exception as e:
            print(f"[code_modify][L2] 尝试 {attempt+1} 失败: {e}")
            time.sleep(1)

    print(f"[code_modify][L2] 2 次重试全部失败")
    return None


# ============================================================
# 对外接口：两级策略
# ============================================================

def modify_control_law(
    current_code: str,
    diagnosis_report: str,
    history_summary: str = "",
    scene_config: Optional[dict] = None,
    vectorization_rules_path: Optional[str] = None,
    template_path: Optional[str] = None
) -> Optional[str]:
    """
    两级策略：
      第 1 级：完整修改（可改结构 + 参数）
      第 2 级：局部修改（只改参数边界）
    都失败 → 返回 None
    """
    if template_path is None:
        template_path = str(PROMPTS_DIR / "code_modify_template.txt")
    if vectorization_rules_path is None:
        vectorization_rules_path = str(PROMPTS_DIR / "vectorization_rules.txt")

    # ========== 第 1 级 ==========
    print("[code_modify] 开始第 1 级：完整修改")
    new_code = _try_full_modify(
        current_code, diagnosis_report, history_summary,
        scene_config, vectorization_rules_path, template_path,
    )
    if new_code:
        print("[code_modify] ✅ 第 1 级（完整修改）成功")
        return new_code

    # ========== 第 2 级 ==========
    print("[code_modify] ⚠️ 第 1 级失败，尝试第 2 级：局部修改")
    new_code = _try_local_modify(current_code, diagnosis_report, scene_config)
    if new_code:
        print("[code_modify] ✅ 第 2 级（局部修改）成功")
        return new_code

    # ========== 都失败 ==========
    print("[code_modify] ❌ 两级都失败，返回 None（engine 会复制上一版）")
    return None