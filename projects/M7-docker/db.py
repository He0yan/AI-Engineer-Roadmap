from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 连接字符串：postgresql+psycopg2://用户:密码@主机:端口/数据库名
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/device_db"
)

# 1. 创建引擎（管理连接池）
engine = create_engine(DATABASE_URL, echo=True)

# 2. 创建 Session 工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 3. 所有模型的基类
Base = declarative_base()

def get_db():
    """FastAPI 依赖注入用的数据库会话生成器。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()