"""
LLM 输出处理工具函数
"""

import ast
import re
from typing import Optional, Tuple


def extract_code_from_response(content: str) -> Optional[str]:
    """
    从 LLM 响应中提取 Python 代码

    支持三种格式（按优先级）：
      1. Markdown 围栏: ```python ... ``` 或 ``` ... ```
      2. 纯 Python 代码（以 import 或 def 开头）
      3. 从自然语言中提取（看是否包含 control_law 定义）

    Args:
        content: LLM 返回的原始文本

    Returns:
        提取到的代码字符串，失败返回 None
    """
    if not content or not content.strip():
        return None

    # ---------- 1. 尝试 Markdown 围栏 ----------
    pattern = r'```(?:python|py)?\s*\n(.*?)```'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        if code:
            return code

    # ---------- 2. 尝试直接当纯代码解析 ----------
    stripped = content.strip()
    if _looks_like_python_code(stripped):
        return stripped

    # ---------- 3. 尝试从文本里抓出 control_law 函数 ----------
    # 匹配 "import ... def control_law ... 直到文件末尾"
    func_match = re.search(
        r'((?:^|\n)\s*(?:import|from)\s+[\s\S]*?def\s+control_law\s*\([\s\S]*)',
        content,
    )
    if func_match:
        code = func_match.group(1).strip()
        if code and _has_control_law(code):
            return code

    # 最后兜底：只要包含 def control_law 就返回整段（去掉自然语言前缀）
    if _has_control_law(content):
        # 找第一个 "import" 或 "def control_law" 的位置
        idx_import = content.find("import ")
        idx_def = content.find("def control_law")
        start = min(x for x in [idx_import, idx_def] if x >= 0) if (idx_import >= 0 or idx_def >= 0) else 0
        return content[start:].strip()

    return None




def smoke_test_control_law(
    code: str,
    scene_config: dict,
) -> tuple[bool, str | None]:
    """
    对控制律代码做烟雾测试：
      1. 编译执行代码
      2. 用占位参数调用 control_law(0, x_dummy, state_dummy, params_dummy)
      3. 检查返回形状
    
    Returns:
        (True, None) 通过
        (False, error_msg) 失败，error_msg 是具体错误
    """
    import numpy as np

    # 1. 编译
    namespace = {"np": np}
    try:
        exec(compile(code, "<smoke_test>", "exec"), namespace)
    except Exception as e:
        return False, f"编译失败: {type(e).__name__}: {e}"

    func = namespace.get("control_law")
    if func is None:
        return False, "未定义 control_law 函数"

    # 2. 构造假输入
    state_names = scene_config.get("state_names", [])
    control_names = scene_config.get("control_names", [])
    model_type = scene_config.get("model_type", "ode")

    state_dim = len(state_names) or 2
    control_dim = len(control_names) or 1

    # PDE 用 (M+1, state_dim)，ODE 用 (state_dim,)
    spatial = scene_config.get("spatial", {})
    if model_type == "pde" and spatial:
        X = spatial.get("X", 2.0)
        dx = spatial.get("dx", 0.1)
        M_plus_1 = int(X / dx) + 1
        state = np.random.rand(M_plus_1, state_dim)
        x_grid = np.linspace(0, X, M_plus_1)
    else:
        state = np.random.rand(state_dim)
        x_grid = np.array([0.0])

    # 3. 从 # @param 提取参数名，给默认值
    params = {}
    import re
    for m in re.finditer(r'#\s*@param:?\s+(\w+)\s*\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)', code):
        name = m.group(1)
        low = float(m.group(2))
        high = float(m.group(3))
        params[name] = (low + high) / 2

    # 4. 调用
    try:
        result = func(0.0, x_grid, state, params)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        # 只取最后一行错误信息
        last_line = tb.strip().split('\n')[-1]
        return False, f"运行时错误: {last_line}"

    # 5. 检查返回值
    result = np.asarray(result)
    if result.ndim == 0:
        return False, f"返回值是标量，期望 shape 与 control_dim={control_dim} 相关"
    
    if model_type == "pde":
        if result.shape != (M_plus_1, control_dim):
            return False, f"PDE 返回值 shape={result.shape}，期望 ({M_plus_1}, {control_dim})"
    else:
        if result.size != control_dim and result.shape != (control_dim,):
            return False, f"ODE 返回值 shape={result.shape}，期望 ({control_dim},)"

    return True, None









def _looks_like_python_code(text: str) -> bool:
    """判断一段文本是否直接是可执行的 Python 代码"""
    if not text:
        return False
    # 必须包含 def control_law
    if "def control_law" not in text:
        return False
    # 尝试 AST 解析
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def _has_control_law(text: str) -> bool:
    """检查文本是否包含 control_law 函数定义"""
    return bool(re.search(r'def\s+control_law\s*\(', text or ''))


def validate_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """验证 Python 代码语法"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"行 {e.lineno}: {e.msg}"


def has_fatal_vectorization_issue(code: str) -> bool:
    """检测代码中是否存在高危向量化错误"""
    code_clean = re.sub(r'#.*', '', code)
    code_clean = re.sub(r'"""[\s\S]*?"""', '', code_clean)
    pattern = r'(?<!\w)(float|int|bool)\s*\([^)]*?[<>=&|]'
    return bool(re.search(pattern, code_clean))


def auto_fix_code(code: str) -> str:
    """自动修复常见的向量化问题（占位）"""
    return code