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
    """代价函数配置 - 支持四种模式：template | expression | code | unified"""

    cost_type: str = Field(
        "template",
        description="代价函数类型: template | expression | code | unified"
    )

    # ========== Template 模式（权重驱动） ==========
    running_state_weights: dict[str, float] = Field(
        default_factory=dict,
        description="运行代价：状态偏差权重"
    )
    running_control_weights: dict[str, float] = Field(
        default_factory=dict,
        description="运行代价：控制代价系数"
    )
    terminal_state_weights: Optional[dict[str, float]] = Field(
        None,
        description="终端代价：状态偏差权重（可选，默认同 running）"
    )

    # ========== Expression 模式（符号表达式 - 分开 running/terminal） ==========
    running_expr: Optional[str] = Field(
        None,
        description="运行代价表达式（SymPy 语法），例如: '0.5*(S-1000)**2 + 10*I + 0.1*u1'"
    )
    terminal_expr: Optional[str] = Field(
        None,
        description="终端代价表达式，例如: '100*(S-1000)**2 + 50*I'"
    )

    # ========== Code 模式（自定义 Python 代码 - 分开 running/terminal） ==========
    running_code: Optional[str] = Field(
        None,
        description="运行代价函数代码，需定义 compute_running(state, control, step) -> float"
    )
    terminal_code: Optional[str] = Field(
        None,
        description="终端代价函数代码，需定义 compute_terminal(state) -> float"
    )

    # ========== Unified 模式（统一表达式 - 只写一个） ==========
    cost_expr: Optional[str] = Field(
        None,
        description="统一代价表达式（SymPy 语法），例如: '0.5*(S-0)**2 + 10*(I-0)**2 + 0.1*u1**2'"
    )
    cost_code: Optional[str] = Field(
        None,
        description="统一代价函数代码，需定义 compute_cost(state, control, step, is_terminal) -> float"
    )
    integrate_over_time: bool = Field(
        True,
        description="统一模式：是否对表达式进行时间积分（True=每步乘dt，False=只在结束时计算一次）"
    )

    # ========== 符号定义（expression/unified 共用） ==========
    symbols: Optional[dict[str, list[str]]] = Field(
        None,
        description="符号定义: {'state': ['S','I','R'], 'control': ['u1','u2']}"
    )

    # ========== 标记 ==========
    has_terminal_cost: bool = Field(
        True,
        description="是否启用终端代价（False 时忽略 terminal_expr/terminal_code）"
    )


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
