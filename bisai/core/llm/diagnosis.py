"""
LLM 诊断报告生成模块
职责：基于C模块提供的指标，调用LLM生成结构化诊断报告
"""

import os
import time
from typing import Optional, List

from core.config import PROJECT_ROOT
from core.llm.gateway import get_llm

PROMPTS_DIR = PROJECT_ROOT / "core" / "llm" / "prompts"


def generate_diagnostic_report(
    metrics_text: str,
    history_summary: str = "",
    anomalies: Optional[List[str]] = None,
    physics_prior_path: Optional[str] = None,
    template_path: Optional[str] = None
) -> str:
    anomalies = anomalies or []

    if template_path is None:
        template_path = str(PROMPTS_DIR / "diagnosis_template.txt")

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    physics_prior = ""
    if physics_prior_path and os.path.exists(physics_prior_path):
        with open(physics_prior_path, 'r', encoding='utf-8') as f:
            physics_prior = f.read()
        physics_prior = f"\n\n## Physics Prior Knowledge\n{physics_prior}"

    history_section = ""
    if history_summary:
        history_section = f"\n\n## Evolution History Summary\n{history_summary}\n"

    anomalies_section = ""
    if anomalies:
        anomalies_section = "\n## System-Annotated Anomalies\n" + "\n".join(f"- {a}" for a in anomalies)

    history_skip_note = ""
    if not history_summary:
        history_skip_note = """
**Note**: No Evolution History is provided (this is the first version). 
Skip Sections 5 and 6. Focus on Sections 2, 3, 4, and 7 based solely on 
the current version metrics.
"""

    prompt = template.replace("{{history_section}}", history_section)
    prompt = prompt.replace("{{metrics_text}}", metrics_text)
    prompt = prompt.replace("{{history_skip_note}}", history_skip_note)
    prompt = prompt.replace("{{anomalies_section}}", anomalies_section)
    prompt = prompt + physics_prior

    llm = get_llm()
    last_error = None
    for attempt in range(3):
        try:
            response_content = llm.invoke(prompt, max_tokens=20000)
            if response_content and len(response_content.strip()) > 0:
                return validate_diagnosis_report(response_content, anomalies)
        except Exception as e:
            print(f"诊断生成尝试 {attempt + 1} 失败: {e}")
            last_error = e
            time.sleep(2 ** attempt)

    fallback = f"## System Automatic Diagnosis (LLM service temporarily unavailable)\n\n"
    fallback += f"**Current Metrics**:\n{metrics_text}\n\n"
    fallback += "**Structural Modification Suggestions**:\n"
    fallback += "- Check if parameters are hitting bounds; consider adjusting parameter ranges.\n"
    if anomalies:
        fallback += f"\n**Anomaly Reminder**: {', '.join(anomalies)}\n"
    if last_error:
        fallback += f"\n**Error**: {str(last_error)[:200]}\n"
    return fallback


def validate_diagnosis_report(report: str, anomalies: List[str]) -> str:
    missing = [a for a in anomalies if a not in report]
    if missing:
        report += f"\n\n[System Supplement] The following anomalies were not mentioned:\n- " + "\n- ".join(missing)
    return report