"""
Pydantic Schemas —— 场景配置模型 (Scene Config)
跨领域通用，描述任何物理系统的控制律设计问题。
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class DomainConfig(BaseModel):
    domain_type: str = Field(..., description="领域类型")
    domain_name: str = Field("", description="领域显示名称")
    description: str = Field("", description="领域描述")


class SpaceTimeConfig(BaseModel):
    x_length: float = Field(2.0, description="空间区域总长度")
    dx: float = Field(0.01, description="空间步长")
    t_total: float = Field(3.0, description="总仿真时间")
    dt: float = Field(5e-5, description="时间步长")


class StateConfig(BaseModel):
    name: str = Field(..., description="状态变量名")
    index: int = Field(..., description="state数组中的列索引(0-based)")
    description: str = Field("", description="物理含义")
    target_value: Optional[float] = Field(None, description="期望目标值")
    unit: str = Field("", description="物理单位")


class ControlConfig(BaseModel):
    name: str = Field(..., description="控制变量名")
    index: int = Field(..., description="control数组中的列索引(0-based)")
    control_type: str = Field("bang-bang", description="控制类型: bang-bang | continuous")
    values: list[float] = Field(default_factory=list, description="离散取值列表")
    cost_coefficient: float = Field(1.0, description="控制代价系数")
    description: str = Field("", description="物理含义")
    unit: str = Field("", description="物理单位")


class CostFunctionConfig(BaseModel):
    cost_type: str = Field("template", description="代价函数类型: template | expression | code")
    running_state_weights: dict[str, float] = Field(default_factory=dict)
    running_control_weights: dict[str, float] = Field(default_factory=dict)
    terminal_state_weights: Optional[dict[str, float]] = None


class SceneConfig(BaseModel):
    model_config = {"protected_namespaces": ()}

    domain: DomainConfig = Field(default_factory=DomainConfig)
    space_time: SpaceTimeConfig = Field(default_factory=SpaceTimeConfig)
    states: list[StateConfig] = Field(default_factory=list)
    controls: list[ControlConfig] = Field(default_factory=list)
    cost_function: CostFunctionConfig = Field(default_factory=CostFunctionConfig)
    physics_params: dict[str, float] = Field(default_factory=dict)
    control_limits: Optional[list[float]] = None
    diffusion_coefficients: Optional[dict[str, float]] = None
    coupling_functions: Optional[dict[str, Any]] = None
    initial_state: Optional[dict[str, Any]] = None
    model_code_path: Optional[str] = None
    control_code_path: Optional[str] = None
