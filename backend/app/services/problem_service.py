"""
题目管理服务 — 封装 Problem 模型的 CRUD 操作。
"""

from sqlalchemy.orm import Session
from typing import Optional

from app.models.problem import Problem
from app.schemas.problem import ProblemCreate


class ProblemService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, include_deleted: bool = False) -> list[Problem]:
        q = self.db.query(Problem)
        if not include_deleted:
            q = q.filter(Problem.deleted == False)
        return q.order_by(Problem.id).all()

    def get_by_id(self, problem_id: int) -> Optional[Problem]:
        return self.db.query(Problem).filter(
            Problem.id == problem_id, Problem.deleted == False
        ).first()

    def search(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> list[Problem]:
        q = self.db.query(Problem).filter(Problem.deleted == False)
        if keyword:
            q = q.filter(Problem.title.contains(keyword))
        if category:
            q = q.filter(Problem.category == category)
        if difficulty:
            q = q.filter(Problem.difficulty == difficulty)
        return q.order_by(Problem.id).all()

    def get_categories(self) -> list[str]:
        rows = self.db.query(Problem.category).filter(
            Problem.deleted == False
        ).distinct().all()
        return [r[0] for r in rows]

    def create(self, data: ProblemCreate) -> Problem:
        # 自定义题：auto id
        if data.id is None:
            max_id = self.db.query(Problem.id).filter(
                Problem.id >= 10001
            ).order_by(Problem.id.desc()).first()
            data.id = (max_id[0] + 1) if max_id else 10001

        problem = Problem(
            id=data.id,
            title=data.title,
            slug=data.slug,
            difficulty=data.difficulty,
            category=data.category,
            leetcode_url=data.leetcode_url,
            is_custom=data.is_custom,
        )
        self.db.add(problem)
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def update(self, problem_id: int, data: ProblemCreate) -> Optional[Problem]:
        problem = self.get_by_id(problem_id)
        if not problem:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            if key == "id":
                continue
            setattr(problem, key, value)
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def delete(self, problem_id: int) -> bool:
        problem = self.get_by_id(problem_id)
        if not problem or not problem.is_custom:
            return False
        problem.deleted = True
        self.db.commit()
        return True
