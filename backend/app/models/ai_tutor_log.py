"""
AI Tutor 交互日志模型 — Phase 2
记录 AI Tutor 的每次请求和响应，用于成本监控和质量优化。
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, CheckConstraint, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class AITutorLog(Base):
    __tablename__ = "ai_tutor_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)
    request_type = Column(String, nullable=False)
    prompt = Column(Text, default="", nullable=False)
    response = Column(Text, default="", nullable=False)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "request_type IN ('hint','review_code')",
            name="ck_ai_tutor_log_request_type",
        ),
    )
