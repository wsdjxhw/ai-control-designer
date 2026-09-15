"""多轮需求澄清 - 纯对话式智能收集模式

核心思路：
- LLM 根据用户描述，动态判断需要收集哪些信息
- 主动追问缺失的关键信息（状态、动作、代价、时间、初始值、物理参数、约束等）
- 直到信息完整，再进入配置清单确认阶段
"""

import json
import re
import uuid
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ClarifySession:
    """澄清会话状态"""
    session_id: str
    description: str
    # 已收集的信息（动态字段）
    collected: Dict[str, Any] = field(default_factory=dict)
    # 状态机
    stage: str = "init"  # init → collecting → draft → editing → confirm → done
    history: list = field(default_factory=list)
    ready_to_create: bool = False
    scene_config: Optional[Dict] = None
    model_code: Optional[str] = None
    cost_function: Optional[Dict] = None


_sessions: Dict[str, ClarifySession] = {}


def create_session(description: str) -> ClarifySession:
    session_id = str(uuid.uuid4())
    session = ClarifySession(session_id=session_id, description=description)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[ClarifySession]:
    return _sessions.get(session_id)


def clear_session(session_id: str):
    _sessions.pop(session_id, None)


def clarify_turn(session_id: str, user_message: str) -> Dict[str, Any]:
    """
    执行一轮澄清对话（纯对话式智能收集）

    Returns:
        {
            "session_id": str,
            "stage": str,
            "message": str,
            "collected": {...},        # 已收集的信息
            "draft_config": {...},     # 阶段2配置草稿
            "missing_fields": [...],   # 阶段2缺失字段
            "ready_to_create": bool,
            "scene_config": {...}|None,
            "model_code": str|None,
            "cost_function": {...}|None
        }
    """
    from core.llm.gateway import get_llm

    session = get_session(session_id)
    if not session:
        return {"error": "会话不存在", "session_id": session_id}

    session.history.append({"role": "user", "content": user_message})

    # 根据阶段选择 Prompt
    if session.stage in ("init", "collecting"):
        prompt = _build_collecting_prompt(session, user_message)
    else:
        prompt = _build_draft_prompt(session, user_message)

    llm = get_llm()
    try:
        content = llm.invoke(prompt, temperature=0.3)
    except Exception as e:
        return {
            "session_id": session_id,
            "stage": session.stage,
            "message": f"抱歉，LLM 调用失败: {str(e)}",
            "collected": session.collected,
            "draft_config": session.collected,  # 兼容
            "missing_fields": [],
            "ready_to_create": False
        }

    result = _parse_response(content, session)
    session.history.append({"role": "assistant", "content": result.get("message", "")})

    return {
        "session_id": session_id,
        "stage": result["stage"],
        "message": result.get("message", ""),
        "collected": session.collected,
        "draft_config": session.collected,  # 兼容前端
        "missing_fields": result.get("missing_fields", []),
        "ready_to_create": result.get("ready_to_create", False),
        "scene_config": result.get("scene_config"),
        "model_code": result.get("model_code"),
        "cost_function": result.get("cost_function")
    }


def _build_collecting_prompt(session: ClarifySession, user_message: str) -> str:
    """纯对话式信息收集 Prompt"""

    collected_json = json.dumps(session.collected, ensure_ascii=False, indent=2) if session.collected else "{}"
    history_summary = "\n".join([
        f"{'用户' if h['role']=='user' else '助手'}: {h['content'][:200]}"
        for h in session.history[-6:]
    ])

    if session.stage == "init":
        # 第一轮：LLM 主动分析，列出需要补充的信息
        return f"""你是一个专业的控制系统建模助手。用户用自然语言描述了控制问题，你需要**智能判断**需要收集哪些信息，并主动引导用户补充。

**用户初始描述**:
{session.description}

**用户最新消息**:
{user_message}

---

**你的任务**：

1. **分析用户描述**，判断这是一个什么领域的问题（SIR传播、电机控制、机器人、化学反应等）

2. **智能判断需要收集的关键信息**（根据领域动态决定，不用固定清单）：
   - 状态变量：个数、含义、取值范围、初始值
   - 控制动作：个数、含义、取值范围（连续/离散）
   - 代价/奖励函数：表达式（例如：cost = max(I) + 0.1 * ∫u²dt）
   - 时间配置：仿真总时长、时间步长
   - 物理参数：领域相关的参数（SIR 的 β/γ、电机的 R/L/J 等）
   - 约束条件：状态/控制的上下界（如果有）

3. **主动输出需要补充的信息列表**，用自然语言清晰列出

**输出格式**（必须是合法 JSON）：
```json
{{
  "stage": "collecting",
  "message": "好的，我理解你想建立一个水下的 SIR 传播模型。为了准确建模，我需要了解以下信息：\\n\\n1. 状态变量：有哪些状态？每个状态的含义、取值范围、初始值？\\n2. 控制动作：控制什么？动作的取值范围是多少？\\n3. 代价函数：希望优化什么？请给出表达式（例如：最小化感染峰值 → cost = max(I)）\\n4. 时间配置：仿真总时长、时间步长？\\n5. 物理参数：感染率 β、康复率 γ 等参数值（如果知道的话）\\n\\n请逐条回复，我会检查并补充缺失项。",
  "collected": {{}}
}}
```

现在分析用户描述，输出需要收集的信息：
"""

    else:
        # 后续轮次：解析用户消息，更新 collected，检查是否足够
        return f"""你是一个控制系统建模助手。用户正在提供信息。

**用户初始描述**:
{session.description}

**当前已收集信息**:
{collected_json}

**对话历史**:
{history_summary}

**用户最新消息**:
{user_message}

---

**任务**：
1. 从用户消息中提取信息，更新 `collected`
2. 判断信息是否足够生成配置清单
3. 如果信息不足，明确指出还缺什么
4. 如果信息足够，`stage` 设为 "draft"

**关键信息检查清单**（根据领域判断）：
- 状态变量（名称、含义、范围、初始值）
- 控制动作（名称、含义、范围）
- 代价函数表达式
- 时间配置（T, dt）
- 物理参数（如果适用）
- 约束条件（可选）

**输出格式**：
```json
{{
  "stage": "collecting|draft",
  "message": "收到！已记录...\\n\\n还缺少：X, Y。请补充。",
  "collected": {{更新后的信息}}
}}
```

如果信息足够：
```json
{{
  "stage": "draft",
  "message": "信息已收集完整！现在生成配置清单...",
  "collected": {{完整信息}}
}}
```

现在处理用户消息：
"""


def _build_draft_prompt(session: ClarifySession, user_message: str) -> str:
    """阶段 2: Draft 模式 Prompt"""

    collected_json = json.dumps(session.collected, ensure_ascii=False, indent=2)

    if session.stage == "draft":
        return f"""你是一个控制系统建模助手。基于用户提供的信息，生成结构化配置清单。

**用户初始描述**:
{session.description}

**已收集的完整信息**:
{collected_json}

---

**任务**：生成以下 8 个字段的配置：

1. `state_names`: 状态变量名称列表
2. `state_meanings`: 每个状态的物理含义
3. `state_ranges`: 每个状态的取值范围
4. `control_names`: 控制动作名称列表
5. `control_meanings`: 每个动作的物理含义
6. `control_ranges`: 每个动作的取值范围
7. `cost_objective`: 代价/目标函数描述
8. `solver`: 求解器类型

**输出格式**：
```json
{{
  "stage": "editing",
  "message": "已根据你的信息生成配置清单，请查看并确认或修改：",
  "draft_config": {{
    "state_names": [...],
    "state_meanings": {{...}},
    ...
  }},
  "missing_fields": []
}}
```

现在生成配置清单：
"""

    else:
        return f"""用户正在编辑配置清单。

**当前配置草稿**:
{json.dumps(session.collected, ensure_ascii=False, indent=2)}

**用户消息**:
{user_message}

**任务**：更新 draft_config。

**输出格式**：
```json
{{
  "stage": "editing|confirm",
  "message": "已更新...",
  "draft_config": {{更新后的配置}},
  "missing_fields": []
}}
```

如果用户确认：
```json
{{
  "stage": "confirm",
  "message": "配置已确认！是否生成最终项目？",
  "draft_config": {{当前配置}},
  "missing_fields": []
}}
```

现在处理：
"""


def _parse_response(content: str, session: ClarifySession) -> Dict[str, Any]:
    """解析 LLM 响应并更新会话"""
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            json_str = json_match.group(1) if json_match else content

        json_str = re.sub(r'[\x00-\x1f\x7f]', '', json_str)
        json_str = json_str.replace('\n', '\\n').replace('\r', '\\r')

        result = json.loads(json_str)

        # 更新会话
        if "stage" in result:
            session.stage = result["stage"]

        if "collected" in result and result["collected"]:
            session.collected.update(result["collected"])

        return result

    except Exception as e:
        return {
            "stage": session.stage,
            "message": f"抱歉，解析失败。能否重新描述？\n\n(错误: {str(e)})",
            "collected": session.collected,
            "missing_fields": [],
            "ready_to_create": False
        }
