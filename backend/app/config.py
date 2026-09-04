from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT.parent / "data"
SOLUTIONS_DIR = ROOT.parent / "solutions"


class Settings(BaseSettings):
    """应用配置，支持 .env 文件覆盖。"""

    # 数据库 (默认内存，生产通过 .env 覆盖为文件路径)
    database_url: str = "sqlite:///:memory:"

    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "YiCode"
    version: str = "2.0.0"

    # 安全
    secret_key: str = "yicode-dev-secret-change-in-production"
    access_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # SM-2 默认配置
    review_intervals_days: list[int] = [1, 3, 7, 15, 30]
    daily_quota_weekday: int = 3
    daily_quota_weekend: int = 6
    overdue_alert_days: int = 3
    day_boundary_hour: float = 0.0

    # 多语言
    languages: list[str] = ["python", "go", "cpp", "java"]
    default_language: str = "python"

    # 飞书 (Phase 2)
    feishu_webhook: str = ""
    feishu_secret: str = ""

    # LLM (Phase 3)
    llm_provider: str = "mock"  # mock | kimi | openai
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 30
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7

    class Config:
        env_file = str(ROOT.parent / ".env")
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
