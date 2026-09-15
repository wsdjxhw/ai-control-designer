"""控制律加载器：将用户提供的 Python 代码字符串编译为可调用函数。

支持从代码字符串提取参数边界、 smoke 测试等功能。
"""

from __future__ import annotations

import ast
import re
from typing import Any


def compile_control_law(code: str) -> callable:
    """将控制律代码字符串编译为可调用函数。

    编译后的函数签名应为:
        control_law(t: float, x_grid: ndarray, state: ndarray, params: dict) -> ndarray

    Args:
        code: 包含 control_law 函数定义的 Python 代码字符串。

    Returns:
        可调用函数对象。

    Raises:
        ValueError: 代码中未定义 control_law 函数。
    """
    namespace: dict[str, Any] = {"np": __import__("numpy")}
    exec(compile(code, "<control_law>", "exec"), namespace)
    func = namespace.get("control_law")
    if func is None:
        raise ValueError("控制律代码必须定义 control_law(t, x_grid, state, params) 函数")
    return func


def extract_parameters(code: str) -> dict[str, tuple[float, float]]:
    """从控制律代码中提取参数名及其建议边界。

    通过正则匹配 params.get("param_name", default) 模式，
    推断参数名列表。边界需由用户在 scene_config 或前端指定。

    Args:
        code: 控制律代码字符串。

    Returns:
        {param_name: (low, high)} 字典，初始边界可设为宽松值。
    """
    # 匹配 params["name"] 或 params.get("name", ...)
    pattern = r'params(?:\[|\.get\()[\'\"]([a-zA-Z_][a-zA-Z0-9_]*)[\'\"]'
    matches = re.findall(pattern, code)

    # 去重并返回占位边界
    param_names = sorted(set(matches))
    return {name: (-10.0, 10.0) for name in param_names}


def smoke_test(control_law_func: callable, scene_config: dict) -> bool:
    """对编译后的控制律函数进行 smoke 测试。

    使用 scene_config 中的初始状态和默认参数，
    调用一次 control_law 确保不抛出异常且返回合法形状。

    Args:
        control_law_func: 编译后的控制律函数。
        scene_config: 场景配置字典。

    Returns:
        测试通过返回 True，否则 False。
    """
    import numpy as np

    try:
        # 构造测试输入
        state_names = scene_config.get("state_names", [])
        state_dim = len(state_names) if state_names else 2
        state = np.zeros(state_dim, dtype=float)

        x_grid = np.array([0.0])  # ODE 模型单点
        t = 0.0
        params = {}  # 空参数

        result = control_law_func(t, x_grid, state, params)
        result = np.asarray(result, dtype=float)

        # 检查返回形状是否合理（至少 1 维）
        return result.ndim >= 1 and result.size > 0
    except Exception:
        return False
