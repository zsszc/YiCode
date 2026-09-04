from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, CheckConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=True)
    difficulty = Column(
        String,
        nullable=False,
    )
    category = Column(String, nullable=False)
    leetcode_url = Column(String, nullable=True)
    is_custom = Column(Boolean, default=False, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("difficulty IN ('简单', '中等', '困难')", name="ck_problem_difficulty"),
    )
