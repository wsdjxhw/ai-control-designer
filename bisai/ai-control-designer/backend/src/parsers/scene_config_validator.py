"""
场景配置验证器 - 验证并补全scene_config参数
"""

from typing import Dict, Any, List


def validate_and_complete_temporal(scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并补全时间参数

    Returns:
        {
            "scene_config": {...},
            "warnings": [...]
        }
    """
    warnings: List[str] = []
    temporal = scene_config.setdefault("temporal", {})

    # 提取 T 和 dt（支持多种命名）
    T = temporal.get("t_total") or temporal.get("T") or temporal.get("total_time")
    dt = temporal.get("dt") or temporal.get("time_step")

    if T is not None and dt is not None:
        # 计算 n_steps
        try:
            n_steps = int(T / dt)
            temporal["n_steps"] = n_steps

            # 验证 n_steps 合理性
            if n_steps > 100000:
                warnings.append(f"n_steps={n_steps} 过大，建议使用多保真度优化或增加dt")
            if n_steps < 10:
                warnings.append(f"n_steps={n_steps} 过小，仿真精度可能不足")
            if dt >= T:
                warnings.append(f"dt({dt}) >= T({T})，会导致n_steps<=1")
            if dt <= 0 or T <= 0:
                warnings.append(f"非法时间参数: T={T}, dt={dt}")

        except (TypeError, ZeroDivisionError) as e:
            warnings.append(f"时间参数计算失败: {e}")

    # 验证并补全空间参数（PDE）
    if scene_config.get("detected_type") == "pde":
        space_time = scene_config.setdefault("space_time", {})
        x_length = space_time.get("x_length")
        dx = space_time.get("dx")

        if x_length and dx:
            try:
                n_spatial = int(x_length / dx)
                space_time["n_spatial"] = n_spatial

                if n_spatial > 1000:
                    warnings.append(f"n_spatial={n_spatial} 过大，PDE计算量可能过大")
                if n_spatial < 10:
                    warnings.append(f"n_spatial={n_spatial} 过小，空间离散精度不足")

            except (TypeError, ZeroDivisionError) as e:
                warnings.append(f"空间参数计算失败: {e}")

    return {
        "scene_config": scene_config,
        "warnings": warnings
    }


def validate_scene_config(scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    完整验证scene_config

    Returns:
        {
            "scene_config": {...},
            "warnings": [...],
            "is_valid": bool
        }
    """
    result = validate_and_complete_temporal(scene_config)
    warnings = result["warnings"]
    scene_config = result["scene_config"]

    # 基础字段验证
    is_valid = True

    if not scene_config.get("state_names"):
        warnings.append("缺少 state_names")
        is_valid = False

    if not scene_config.get("control_names"):
        warnings.append("缺少 control_names")
        is_valid = False

    if not scene_config.get("temporal", {}).get("t_total"):
        warnings.append("缺少 temporal.t_total")
        is_valid = False

    if not scene_config.get("temporal", {}).get("dt"):
        warnings.append("缺少 temporal.dt")
        is_valid = False

    return {
        "scene_config": scene_config,
        "warnings": warnings,
        "is_valid": is_valid
    }
