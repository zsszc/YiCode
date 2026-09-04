from sqlalchemy import Column, Integer, String, DateTime, Date, Text, CheckConstraint, UniqueConstraint, ForeignKey
from app.core.database import Base


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    status = Column(String, nullable=False, default="todo")
    review_stage = Column(Integer, nullable=False, default=-1)
    next_review = Column(Date, nullable=True)
    last_done = Column(Date, nullable=True)
    note = Column(Text, default="", nullable=False)
    cheatsheet = Column(Text, default="", nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('todo', 'forgot', 'shaky', 'solid', 'archived')", name="ck_progress_status"),
        UniqueConstraint("user_id", "problem_id", name="uq_progress_user_problem"),
    )
