"""新手模式 - 自然语言 → scene_config + model_code + cost_function"""

import json
import re
from typing import Any, Dict

from core.llm.gateway import get_llm
from core.llm.prompts import load_prompt


def generate_scene(description: str) -> Dict[str, Any]:
    """调用 LLM 生成 scene_config + model_code + cost_function

    Args:
        description: 自然语言描述（如"简单弹簧-质量-阻尼系统"）

    Returns:
        {
            "scene_config": {...},
            "model_code": "class XXX(BaseModel): ...",
            "cost_function": {...}
        }
    """
    llm = get_llm()
    prompt = load_prompt("newbie_guide.txt", {"description": description})

    # 重试 3 次
    for attempt in range(3):
        try:
            content = llm.invoke(prompt, temperature=0.3)

            # 尝试提取 JSON
            json_str = None

            # 1. 尝试提取 ```json ... ``` 代码块
            json_block_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
            else:
                # 2. 尝试直接匹配花括号包围的内容（可能是纯 JSON）
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 3. 无法提取，尝试直接解析整个内容
                    json_str = content

            # 清理修复 JSON
            json_str = _sanitize_json(json_str)

            # 尝试解析
            result = json.loads(json_str)

            # 验证必要字段
            if "scene_config" in result and "model_code" in result:
                return result
            else:
                print(f"新手模式生成尝试 {attempt + 1}: 返回的 JSON 缺少必要字段 (scene_config 或 model_code)")

        except json.JSONDecodeError as e:
            print(f"新手模式生成尝试 {attempt + 1} JSON解析失败: {e}")
            # 打印部分内容辅助调试
            if 'json_str' in locals():
                print(f"  清理后的JSON片段: {json_str[:200]}...")
        except Exception as e:
            print(f"新手模式生成尝试 {attempt + 1} 失败: {e}")

        import time
        time.sleep(2 ** attempt)

    # 兜底：返回默认场景（通用格式）
    model_code_fallback = """import numpy as np
from core.base.base_model import BaseModel

class GenericModel(BaseModel):
    def __init__(self, scene_config):
        self.scene_config = scene_config
        params = self.scene_config.get("physical_params", {})
        self.a = params.get("a", 1.0)
        self.b = params.get("b", 1.0)

    def get_initial_state(self, x_grid=None):
        init = self.scene_config.get("initial_state", {})
        state_names = self.scene_config.get("state_names", ["x1", "x2"])
        return np.array([
            init.get(f"{name}0", 0.0) for name in state_names
        ])

    def rhs(self, t, state, control, x_grid=None):
        state_names = self.scene_config.get("state_names", ["x1", "x2"])
        x1, x2 = state
        u = control[0] if len(control) > 0 else 0.0
        dx1 = x2
        dx2 = -self.a * x1 + self.b * u
        return np.array([dx1, dx2])

    def validate_state(self, state):
        return True"""

    return {
        "scene_config": {
            "domain_name": "generic_system",
            "model_type": "generic_ode",
            "state_names": ["x1", "x2"],
            "control_names": ["u1"],
            "target_values": {"x1": 1.0, "x2": 0.0},
            "physical_params": {"a": 1.0, "b": 1.0},
            "control_type": "continuous",
            "control_limits": {"u1": [-10.0, 10.0]},
            "temporal": {"T": 2.0, "dt": 0.1},
            "initial_state": {"x1": 0.0, "x2": 0.0},
            "_model_code": model_code_fallback
        },
        "model_code": """import numpy as np
from core.base.base_model import BaseModel

class GenericModel(BaseModel):
    def __init__(self, scene_config):
        self.scene_config = scene_config
        params = self.scene_config.get("physical_params", {})
        self.a = params.get("a", 1.0)
        self.b = params.get("b", 1.0)

    def get_initial_state(self, x_grid=None):
        init = self.scene_config.get("initial_state", {})
        state_names = self.scene_config.get("state_names", ["x1", "x2"])
        return np.array([
            init.get(f"{name}0", 0.0) for name in state_names
        ])

    def rhs(self, t, state, control, x_grid=None):
        state_names = self.scene_config.get("state_names", ["x1", "x2"])
        x1, x2 = state
        u = control[0] if len(control) > 0 else 0.0
        dx1 = x2
        dx2 = -self.a * x1 + self.b * u
        return np.array([dx1, dx2])

    def validate_state(self, state):
        return True""",
        "cost_function": {
            "running_state_weight": {"x1": 1.0, "x2": 0.1},
            "control_weight": {"u1": 0.01},
            "terminal_state_weight": {"x1": 1.0, "x2": 0.1}
        }
    }


def _sanitize_json(json_str: str) -> str:
    """清理和修复 JSON 字符串中的常见问题"""
    # 移除控制字符
    json_str = re.sub(r'[\x00-\x1f\x7f]', '', json_str)

    # 修复未转义的换行符（在字符串值内部）
    # 这是一个简化的处理，实际可能需要更复杂的逻辑
    json_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

    return json_str


def refine_config(scene_config: Dict[str, Any], feedback: str) -> Dict[str, Any]:
    """根据用户反馈精炼配置"""
    description = f"用户反馈：{feedback}\n当前配置：{json.dumps(scene_config, indent=2)}\n请根据反馈修改配置，返回修改后的完整 JSON。"
    result = generate_scene(description)
    return result.get("scene_config", scene_config)
