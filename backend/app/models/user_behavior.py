"""
用户行为日志模型 — Phase 2
记录用户在学习过程中的每个行为动作，用于画像分析。
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, CheckConstraint, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class UserBehavior(Base):
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    action_type = Column(String, nullable=False)
    # JSON 格式存储额外数据: {"hint_level": 1, "solve_time_ms": 300000, "code_length": 150}
    action_data = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('open','hint','attempt','submit','review','skip')",
            name="ck_user_behavior_action_type",
        ),
    )
