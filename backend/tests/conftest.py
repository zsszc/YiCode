import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.database as db_module
from app.core.database import Base, get_db
from app.main import app

# 内存 SQLite 用于测试
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """每个测试函数独立的 DB session。"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden DB dependency."""
    # Monkeypatch 全局 engine 和 SessionLocal，使 lifespan 和路由使用同一个数据库
    original_engine = db_module.engine
    original_sessionlocal = db_module.SessionLocal
    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

    # 恢复
    del app.dependency_overrides[get_db]
    db_module.engine = original_engine
    db_module.SessionLocal = original_sessionlocal
