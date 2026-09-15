"""
Pydantic Schemas —— 项目相关请求/响应模型
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., description="项目名称", max_length=200)
    description: Optional[str] = Field("", description="项目描述")
    mode: Optional[str] = Field("expert", description="创建模式: expert | newbie")
    domain_type: Optional[str] = Field("custom", description="领域类型")
    scene_config: Optional[dict] = Field(None, description="场景配置JSON")


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scene_config: Optional[dict] = None
    domain_type: Optional[str] = None


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    description: str
    mode: str
    domain_type: str
    status: str
    current_version: int
    best_cost: Optional[float]
    scene_config: Optional[Any]
    work_dir: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

class EvolutionStartRequest(BaseModel):
    max_iterations: Optional[int] = Field(20, ge=1, le=100)


class EvolutionRunResponse(BaseModel):
    run_id: str
    project_id: str
    version: int
    status: str
    total_cost: Optional[float]
    best_params: Optional[Any]
    deviations: Optional[Any]
    anomalies: Optional[Any]
    created_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EvolutionStatusResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    current_version: int
    total_cost: Optional[float]
    message: Optional[str] = None
