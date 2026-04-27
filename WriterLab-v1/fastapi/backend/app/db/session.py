import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL 未设置：请在 fastapi/backend/.env 或环境变量中配置 PostgreSQL 连接字符串"
    )


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Base(DeclarativeBase):
    pass


# 把 SQL echo 由环境变量 DATABASE_ECHO 控制，避免默认在生产/测试中刷大量 SQL 日志。
engine = create_engine(DATABASE_URL, echo=_bool_env("DATABASE_ECHO", default=False))

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
