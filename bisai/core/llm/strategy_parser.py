"""
策略自然语言解析模块
职责：将控制律代码解析为自然语言描述
"""

import re
import json
from typing import Dict, Any

from core.config import PROJECT_ROOT
from core.llm.gateway import get_llm

PROMPTS_DIR = PROJECT_ROOT / "core" / "llm" / "prompts"


def parse_strategy(control_law_code: str) -> Dict[str, Any]:
    llm = get_llm()

    template_path = PROMPTS_DIR / "strategy_parse.txt"
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        template = """
You are a control system analyst. Explain the following control law code in plain English.

## Input
Control law code:
{{control_law_code}}

## Output Format
Return a JSON object with:
{
  "description": "Overall strategy description in 2-3 sentences",
  "key_mechanisms": ["Mechanism 1", "Mechanism 2"],
  "parameter_effects": {"param_name": "effect description"}
}
"""

    prompt = template.replace("{{control_law_code}}", control_law_code)

    for attempt in range(3):
        try:
            content = llm.invoke(prompt)
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
            if "description" in result:
                return result
        except Exception as e:
            print(f"策略解析尝试 {attempt + 1} 失败: {e}")
            import time
            time.sleep(2 ** attempt)

    # 兜底
    param_names = re.findall(r'params\.get\([\'"]([^\'"]+)[\'"]', control_law_code)
    has_where = "np.where" in control_law_code
    description = "该控制律"
    description += "采用 bang-bang 开关控制策略" if has_where else "采用连续反馈控制策略"
    if param_names:
        description += f"，包含可调参数: {', '.join(param_names[:5])}"

    return {
        "description": description,
        "key_mechanisms": [
            "根据系统状态计算控制输出",
            f"{'使用阈值开关' if has_where else '使用连续反馈'}"
        ],
        "parameter_effects": {p: "控制策略的调节参数" for p in param_names[:3]}
    }