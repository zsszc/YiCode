from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    score = Column(String, nullable=False)
    from_stage = Column(Integer, nullable=False)
    to_stage = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("score IN ('easy', 'ok', 'hard')", name="ck_review_log_score"),
    )
