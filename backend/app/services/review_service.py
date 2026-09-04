"""
复习/进度管理服务 — 封装 Progress 和 ReviewLog 的 CRUD。
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.progress import Progress
from app.models.review_log import ReviewLog
from app.models.problem import Problem
from app.services.sm2 import (
    apply_first_solve,
    apply_review,
    default_progress_entry,
    STATUS_TODO,
    STATUS_ARCHIVED,
)


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_progress(self, problem_id: int, user_id: int = 1) -> Progress:
        prog = self.db.query(Progress).filter(
            Progress.problem_id == problem_id,
            Progress.user_id == user_id,
        ).first()
        if not prog:
            prog = Progress(
                user_id=user_id,
                problem_id=problem_id,
                status=STATUS_TODO,
                review_stage=-1,
            )
            self.db.add(prog)
            self.db.commit()
            self.db.refresh(prog)
        return prog

    def first_solve(self, problem_id: int, status: str, user_id: int = 1) -> Progress:
        """首次刷完题目。"""
        prog = self.get_or_create_progress(problem_id, user_id)
        stage, next_review, new_status = apply_first_solve(status, date.today())
        prog.status = new_status
        prog.review_stage = stage
        prog.next_review = date.fromisoformat(next_review) if next_review else None
        prog.last_done = date.today()
        self.db.commit()
        self.db.refresh(prog)
        return prog

    def review(self, problem_id: int, score: str, user_id: int = 1) -> Progress:
        """复习打分。"""
        prog = self.get_or_create_progress(problem_id, user_id)
        from_stage = max(0, prog.review_stage)
        new_stage, next_review, new_status = apply_review(from_stage, score, date.today())

        # 记录日志
        log = ReviewLog(
            user_id=user_id,
            problem_id=problem_id,
            score=score,
            from_stage=from_stage,
            to_stage=new_stage,
        )
        self.db.add(log)

        # 更新进度
        prog.status = new_status
        prog.review_stage = new_stage
        prog.next_review = date.fromisoformat(next_review) if next_review else None
        prog.last_done = date.today()
        self.db.commit()
        self.db.refresh(prog)
        return prog

    def update_note(self, problem_id: int, note: str, user_id: int = 1) -> Progress:
        prog = self.get_or_create_progress(problem_id, user_id)
        prog.note = note
        self.db.commit()
        self.db.refresh(prog)
        return prog

    def update_cheatsheet(self, problem_id: int, cheatsheet: str, user_id: int = 1) -> Progress:
        prog = self.get_or_create_progress(problem_id, user_id)
        prog.cheatsheet = cheatsheet
        self.db.commit()
        self.db.refresh(prog)
        return prog

    def get_logs(self, problem_id: int, user_id: int = 1) -> list[ReviewLog]:
        return self.db.query(ReviewLog).filter(
            ReviewLog.problem_id == problem_id,
            ReviewLog.user_id == user_id,
        ).order_by(ReviewLog.created_at.desc()).all()
