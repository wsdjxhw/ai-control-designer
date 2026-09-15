"""
数据库连接模块 (SQLite + SQLAlchemy 2.0)
单文件数据库，check_same_thread=False 允许多线程访问
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.src.config import settings

# ===== 创建引擎 =====
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.database_url
    else {},
    echo=False,
)

# ===== Session 工厂 =====
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ===== ORM 基类 =====
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖注入：获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表（启动时调用）"""
    Base.metadata.create_all(bind=engine)
