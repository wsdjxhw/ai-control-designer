"""Prompt 模板加载器"""

from pathlib import Path
from typing import Any, Dict


PROMPTS_DIR = Path(__file__).parent


def load_prompt(template_name: str, variables: Dict[str, Any] = None) -> str:
    """加载并渲染 prompt 模板

    Args:
        template_name: 模板文件名（如 "newbie_guide.txt"）
        variables: 模板变量字典

    Returns:
        渲染后的 prompt 字符串
    """
    template_path = PROMPTS_DIR / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {template_path}")

    content = template_path.read_text(encoding="utf-8")

    if variables:
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

    return content
