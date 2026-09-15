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