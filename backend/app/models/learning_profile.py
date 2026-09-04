"""
学习画像模型 — Phase 2
聚合用户学习行为，形成自适应学习画像。
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class LearningProfile(Base):
    __tablename__ = "learning_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1, unique=True)

    # 能力评估
    avg_solve_time_easy_ms = Column(Integer, default=0)
    avg_solve_time_medium_ms = Column(Integer, default=0)
    avg_solve_time_hard_ms = Column(Integer, default=0)
    hint_dependency_rate = Column(Float, default=0.0)
    first_try_success_rate = Column(Float, default=0.0)

    # 习惯模式
    peak_hour_start = Column(Integer, default=9)
    peak_hour_end = Column(Integer, default=22)
    preferred_difficulty = Column(String, default="balanced")
    streak_days = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    total_solved = Column(Integer, default=0)
    total_reviewed = Column(Integer, default=0)

    # 自适应配置
    adaptive_quota_enabled = Column(Boolean, default=True)
    custom_quota_weekday = Column(Integer, nullable=True)
    custom_quota_weekend = Column(Integer, nullable=True)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
