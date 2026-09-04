from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import get_settings, DATA_DIR
from app.core.database import engine, Base
from app.routers import dashboard, problems, review, auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保数据目录存在
    if settings.database_url.startswith("sqlite:///") and not settings.database_url.startswith("sqlite:///:memory:"):
        db_path = settings.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # 启动时创建表（开发便利；生产用 Alembic）
    Base.metadata.create_all(bind=engine)
    yield
    # 关闭时清理


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="忆码 YiCode — AI-Powered LeetCode Hot 100 Tracker",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(problems.router, prefix=settings.api_v1_prefix)
app.include_router(review.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.version}
