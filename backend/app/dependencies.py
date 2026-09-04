from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db as _get_db
from app.config import get_settings


def get_db() -> Session:
    """FastAPI dependency: 数据库 session。"""
    yield from _get_db()


def get_settings_dep():
    """FastAPI dependency: 应用配置。"""
    return get_settings()
