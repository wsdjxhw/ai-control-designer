"""
LLM 控制律代码修改模块
职责：基于诊断报告 + 场景上下文，调用 LLM 生成下一版本控制律代码
"""

import json
import os
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

    # ---------- 领域类型 ----------
    model_type = scene_config.get("model_type") or scene_config.get("detected_type", "unknown")
    domain = scene_config.get("domain_name", "custom")
    is_pde = model_type == "pde"
    lines.append(f"- Domain: {domain}  (model_type={model_type})")
    if is_pde:
        lines.append("  *** This is a PDE (partial differential equation) problem. ***")
        lines.append("  *** State and control are spatial fields, not scalars. ***")
    else:
        lines.append("  This is an ODE (ordinary differential equation) problem.")

    # ---------- 状态/控制 ----------
    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])
    n_states = len(state_names)
    n_controls = len(control_names)
    lines.append(f"- State variables ({n_states}): {state_names}")
    lines.append(f"- Control variables ({n_controls}): {control_names}")
    lines.append(f"  => control_law MUST return an array with EXACTLY {n_controls} column(s).")

    # ---------- 控制类型 ----------
    control_type = scene_config.get("control_type", "continuous")
    lines.append(f"- Control type: {control_type.upper()}")
    if control_type == "bang_bang":
        lines.append("  *** Bang-bang: use np.where(cond, val, 0.0) with DISCRETE values. ***")
    else:
        lines.append("  *** Continuous: use multiplication / addition / np.clip. ***")
        lines.append("  *** DO NOT use np.where with discrete values. ***")

    # ---------- 时间参数 ----------
    temporal = scene_config.get("temporal", {})
    T = temporal.get("T", 10.0)
    dt = temporal.get("dt", 0.01)
    N = temporal.get("n_steps")
    if N is None:
        N = int(T / dt) if dt > 0 else 1000
    lines.append(f"- Time: T = {T}, dt = {dt}, N = {N} steps")
    lines.append(f"  => Simulation time T = {T} (do NOT hardcode other values)")

    # ---------- PDE 空间参数 ----------
    if is_pde:
        spatial = scene_config.get("spatial", {})
        X = spatial.get("X", spatial.get("x_length", 2.0))
        dx = spatial.get("dx", 0.01)
        M_plus_1 = int(X / dx) + 1 if dx > 0 else 201
        lines.append(f"- Space: X = {X}, dx = {dx}, grid points = {M_plus_1}")
        lines.append(f"  => Return shape must be (M+1, {n_controls}) = ({M_plus_1}, {n_controls})")

    # ---------- 目标值 ----------
    targets = scene_config.get("target_values", {})
    if targets:
        lines.append(f"- Target values: {targets}")

    # ---------- 初始状态 ----------
    init_state = scene_config.get("initial_state", {})
    if init_state:
        lines.append(f"- Initial state: {init_state}")

    lines.append("")
    lines.append("*** Any modification MUST be consistent with the above context. ***")

    return "\n".join(lines)


def modify_control_law(
    current_code: str,
    diagnosis_report: str,
    history_summary: str = "",
    scene_config: Optional[dict] = None,
    vectorization_rules_path: Optional[str] = None,
    template_path: Optional[str] = None
) -> Optional[str]:
    """
    基于诊断报告 + 场景上下文修改控制律代码

    Args:
        current_code: 当前版本控制律代码
        diagnosis_report: LLM 诊断报告
        history_summary: 演化历史摘要
        scene_config: 场景配置（包含 model_type/state_names/control_names 等）
        vectorization_rules_path: 向量化规则文件路径
        template_path: 模板文件路径

    Returns:
        新版本控制律代码，失败返回 None
    """
    # 默认路径
    if template_path is None:
        template_path = str(PROMPTS_DIR / "code_modify_template.txt")
    if vectorization_rules_path is None:
        vectorization_rules_path = str(PROMPTS_DIR / "vectorization_rules.txt")

    # 1. 加载模板
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # 2. 加载向量化规则
    vectorization_rules = ""
    if os.path.exists(vectorization_rules_path):
        with open(vectorization_rules_path, 'r', encoding='utf-8') as f:
            vectorization_rules = f.read()

    # 3. 构造场景上下文
    scene_context = _build_scene_context(scene_config or {})

    # 4. 组装 Prompt
    prompt = template.replace("{{scene_context}}", scene_context)
    prompt = prompt.replace("{{history_summary}}", history_summary or "暂无历史记录")
    prompt = prompt.replace("{{current_code}}", current_code)
    prompt = prompt.replace("{{diagnosis_report}}", diagnosis_report)
    prompt = prompt.replace("{{vectorization_rules}}", vectorization_rules)

    # 5. 获取 LLM 客户端
    llm = get_llm()

    # 6. 调用 LLM（带重试）
    last_error = None
    for attempt in range(3):
        try:
            response_content = llm.invoke(prompt, max_tokens=3000)
            new_code = extract_code_from_response(response_content)
            if new_code:
                is_valid, error_msg = validate_syntax(new_code)
                if is_valid:
                    return new_code
                else:
                    print(f"语法错误: {error_msg}")
            else:
                print(f"尝试 {attempt + 1}: 未提取到代码块")
        except Exception as e:
            print(f"尝试 {attempt + 1} 失败: {e}")
            last_error = e
            time.sleep(2 ** attempt)

    print(f"代码修改失败，最后一次错误: {last_error}")
    return None