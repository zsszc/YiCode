from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import get_settings, DATA_DIR
from app.core.database import engine, Base
from app.routers import dashboard, problems, review, auth, tutor, profile, feishu, export, evolution, code_runner, templates

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite:///") and not settings.database_url.startswith("sqlite:///:memory:"):
        db_path = settings.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_problem_columns()
    _auto_seed()
    yield


def _migrate_problem_columns():
    """轻量迁移：为已存在的 problems 表补充新增列。"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "problems" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("problems")}
    new_columns = {
        "description": "TEXT",
        "starter_code": "TEXT",
        "test_cases": "TEXT",
        "function_name": "VARCHAR",
    }
    with engine.begin() as conn:
        for col, col_type in new_columns.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE problems ADD COLUMN {col} {col_type}"))


def _auto_seed():
    """启动时自动导入题库（幂等）：表为空或内容缺失时执行。"""
    from sqlalchemy.orm import Session
    from app.models.problem import Problem

    try:
        with Session(engine) as db:
            needs_seed = (
                db.query(Problem).count() == 0
                or db.query(Problem).filter(Problem.description.is_(None)).count() > 0
            )
        if needs_seed:
            from scripts.seed_problems import seed

            seed()
    except Exception as e:  # 种子失败不应阻断服务启动
        import logging

        logging.getLogger("yicode").warning(f"自动导入题库失败: {e}")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="忆码 YiCode — AI-Powered LeetCode Hot 100 Tracker",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(problems.router, prefix=settings.api_v1_prefix)
app.include_router(review.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(tutor.router, prefix=settings.api_v1_prefix)
app.include_router(profile.router, prefix=settings.api_v1_prefix)
app.include_router(feishu.router, prefix=settings.api_v1_prefix)
app.include_router(export.router, prefix=settings.api_v1_prefix)
app.include_router(evolution.router, prefix=settings.api_v1_prefix)
app.include_router(code_runner.router, prefix=settings.api_v1_prefix)
app.include_router(templates.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.version}
