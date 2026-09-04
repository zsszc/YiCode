"""
数据导出路由 — Phase 3
支持导出进度、题目、学习画像为 JSON。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.progress import Progress
from app.models.problem import Problem
from app.models.learning_profile import LearningProfile
from app.models.review_log import ReviewLog

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/progress")
def export_progress(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """导出当前用户的全部进度数据。"""
    progress_list = db.query(Progress).filter(Progress.user_id == current_user.id).all()
    problems = db.query(Problem).all()
    problem_map = {p.id: {"title": p.title, "difficulty": p.difficulty, "category": p.category, "slug": p.slug} for p in problems}

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "exported_at": __import__('datetime').datetime.now().isoformat(),
        "progress": [
            {
                "problem_id": p.problem_id,
                "problem": problem_map.get(p.problem_id),
                "status": p.status,
                "review_stage": p.review_stage,
                "next_review": p.next_review.isoformat() if p.next_review else None,
                "last_done": p.last_done.isoformat() if p.last_done else None,
                "note": p.note,
                "cheatsheet": p.cheatsheet,
                "hint_count": p.hint_count,
                "attempt_count": p.attempt_count,
                "first_try": p.first_try,
            }
            for p in progress_list
        ],
    }


@router.get("/profile")
def export_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """导出学习画像。"""
    profile = db.query(LearningProfile).filter(LearningProfile.user_id == current_user.id).first()
    logs = db.query(ReviewLog).filter(ReviewLog.user_id == current_user.id).all()

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "exported_at": __import__('datetime').datetime.now().isoformat(),
        "profile": {
            "streak_days": profile.streak_days if profile else 0,
            "max_streak": profile.max_streak if profile else 0,
            "total_solved": profile.total_solved if profile else 0,
            "total_reviewed": profile.total_reviewed if profile else 0,
            "hint_dependency_rate": profile.hint_dependency_rate if profile else 0,
            "first_try_success_rate": profile.first_try_success_rate if profile else 0,
            "preferred_difficulty": profile.preferred_difficulty if profile else "balanced",
        } if profile else None,
        "review_logs": [
            {
                "problem_id": log.problem_id,
                "score": log.score,
                "from_stage": log.from_stage,
                "to_stage": log.to_stage,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
