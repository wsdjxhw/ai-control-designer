"""
SQLAlchemy ORM 模型 —— 项目表 (projects)
"""
import uuid

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, func

from backend.src.database import Base


class Project(Base):
    """项目表"""
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, comment="项目名称")
    description = Column(String, default="", comment="项目描述")
    mode = Column(String, default="expert", comment="创建模式: expert | newbie")
    domain_type = Column(String, default="custom", comment="物理系统领域类型: uwsn | sir | dc_motor | thermal | fluid | mechanical | custom")
    status = Column(String, default="idle", comment="项目状态: idle | running | completed | failed")
    current_version = Column(Integer, default=0, comment="当前演化版本号")
    best_cost = Column(Float, nullable=True, comment="最优代价值")
    scene_config = Column(JSON, nullable=True, comment="场景配置JSON")
    work_dir = Column(String, nullable=True, comment="项目文件工作目录路径")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class EvolutionRun(Base):
    """演化运行记录表"""
    __tablename__ = "evolution_runs"

    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, comment="所属项目ID")
    version = Column(Integer, nullable=False, comment="当前运行版本号")
    status = Column(String, default="pending", comment="运行状态: pending | running | completed | failed")
    total_cost = Column(Float, nullable=True, comment="最终总代价")
    best_params = Column(JSON, nullable=True, comment="最优参数JSON")
    deviations = Column(JSON, nullable=True, comment="最终状态偏差值JSON")
    anomalies = Column(JSON, nullable=True, comment="系统检测异常列表")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")
