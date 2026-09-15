"""
场景配置验证器 - 验证和补全 temporal 参数
"""

from typing import Dict, Any, List


def validate_and_complete_temporal(scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并补全 temporal 配置

    自动推断：
    - n_steps = T / dt
    - n_spatial (如果适用)
    """
    warnings: List[str] = []

    temporal = scene_config.get("temporal", {})
    T = temporal.get("T", 10.0)
    dt = temporal.get("dt", 0.01)

    # 自动计算 n_steps
    if "n_steps" not in temporal:
        n_steps = int(T / dt)
        temporal["n_steps"] = n_steps
        warnings.append(f"自动推断 n_steps = {n_steps} (T/dt)")

    scene_config["temporal"] = temporal

    return {
        "scene_config": scene_config,
        "warnings": warnings
    }


def validate_scene_config(scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证 scene_config 的完整性
    """
    errors: List[str] = []
    warnings: List[str] = []

    required_fields = ["state_names", "control_names", "temporal"]
    for field in required_fields:
        if field not in scene_config:
            errors.append(f"缺少必需字段: {field}")

    if "temporal" in scene_config:
        temporal = scene_config["temporal"]
        if "T" not in temporal:
            errors.append("temporal 缺少 T (总时间)")
        if "dt" not in temporal:
            errors.append("temporal 缺少 dt (时间步长)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
