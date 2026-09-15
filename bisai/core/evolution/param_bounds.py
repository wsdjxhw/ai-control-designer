"""参数边界解析。

从控制律代码中提取可调参数及其边界（声明块、动态、通用三层）。
"""

from __future__ import annotations

import re
from typing import Any


class ParamBounds:
    """参数边界管理器。

    支持三种边界来源（优先级从高到低）：
    1. 声明块边界：控制律代码中 #@param 注释声明的边界
    2. 动态边界：LLM 诊断后推荐的调整边界
    3. 通用边界：默认的宽边界 [-10, 10]
    """

    @staticmethod
    def from_code(code: str) -> dict[str, dict[str, float]]:
        """从控制律代码中解析参数声明。

        支持两种格式:
        1. 声明块格式: #@param name lower=0.0 upper=1.0 default=0.5
        2. 注释格式: # @param: name (0.1, 10.0)

        如果没有找到任何声明，自动兜底：提取 params.get() 中的参数名，
        为每个参数分配默认范围 [default*0.1, default*10] 或 [-10, 10]。

        Returns:
            {param_name: {"lower": L, "upper": U, "default": D}}
        """
        bounds: dict[str, dict[str, float]] = {}

        # 格式1: #@param name lower=0.0 upper=1.0 default=0.5
        pattern1 = re.compile(
            r"#@param\s+(\w+)\s+"
            r"lower\s*=\s*([-\d.eE+]+)\s+"
            r"upper\s*=\s*([-\d.eE+]+)"
            r"(?:\s+default\s*=\s*([-\d.eE+]+))?"
        )
        for match in pattern1.finditer(code):
            name = match.group(1)
            bounds[name] = {
                "lower": float(match.group(2)),
                "upper": float(match.group(3)),
                "default": (
                    float(match.group(4))
                    if match.group(4) is not None
                    else (float(match.group(2)) + float(match.group(3))) / 2
                ),
            }

        # 格式2: # @param: name (0.1, 10.0) 或 # @param: name (low, high)
        pattern2 = re.compile(
            r"#\s*@param:\s*(\w+)\s*\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)"
        )
        for match in pattern2.finditer(code):
            name = match.group(1)
            if name not in bounds:  # 避免重复
                lower = float(match.group(2))
                upper = float(match.group(3))
                bounds[name] = {
                    "lower": lower,
                    "upper": upper,
                    "default": (lower + upper) / 2,
                }

        # 【兜底策略】如果没有任何 @param 声明，尝试从 params.get() 提取参数名
        if not bounds:
            param_names = ParamBounds.extract_param_names(code)
            for name in param_names:
                # 尝试提取 params.get("name", default_value) 中的默认值
                default_match = re.search(
                    rf'params\.get\s*\(\s*["\']{name}["\']\s*,\s*([-\d.eE+]+)\s*\)',
                    code
                )
                if default_match:
                    default_val = float(default_match.group(1))
                    # 基于默认值生成范围：default × [0.1, 10]，至少保留 0.1 的下界
                    lower = max(0.01, default_val * 0.1)
                    upper = default_val * 10.0 if default_val > 0 else abs(default_val) * 10.0 + 1.0
                else:
                    # 没有默认值，使用通用范围
                    lower, upper = -10.0, 10.0
                    default_val = 0.0

                bounds[name] = {
                    "lower": lower,
                    "upper": upper,
                    "default": default_val,
                }

        return bounds

    @staticmethod
    def extract_param_names(code: str) -> list[str]:
        """从控制律代码中提取参数名。

        查找函数签名中的参数名（排除 t, state, x_grid 等内置参数）。
        """
        builtins = {"t", "state", "x_grid", "params", "np", "numpy"}
        names: list[str] = []
        # 匹配 control_law(t, x_grid, state, params) 函数
        func_match = re.search(
            r"def\s+control_law\s*\(([^)]+)\)", code
        )
        if func_match:
            # 匹配 params.get("xxx") 或 params["xxx"]
            param_refs = re.findall(
                r'params\.get\s*\(\s*["\'](\w+)["\']', code
            )
            param_refs += re.findall(
                r'params\[\s*["\'](\w+)["\']\s*\]', code
            )
            names = list(dict.fromkeys(param_refs))  # 去重保序
        return names

    @staticmethod
    def merge(
        declared: dict[str, dict[str, float]],
        dynamic: dict[str, list[float]] | None = None,
        generic_bounds: tuple[float, float] = (-10.0, 10.0),
    ) -> dict[str, tuple[float, float]]:
        """合并多层边界，返回 optuna 可用的 {name: (low, high)} 格式。

        优先级: declared > dynamic > generic
        """
        result: dict[str, tuple[float, float]] = {}
        all_params = set(declared.keys())
        if dynamic:
            all_params |= set(dynamic.keys())

        for name in all_params:
            if name in declared:
                low = declared[name]["lower"]
                high = declared[name]["upper"]
                # dynamic 可缩窄范围
                if dynamic and name in dynamic:
                    d_low, d_high = dynamic[name]
                    low = max(low, d_low)
                    high = min(high, d_high)
            elif dynamic and name in dynamic:
                low, high = dynamic[name]
            else:
                low, high = generic_bounds
            result[name] = (low, high)

        return result
