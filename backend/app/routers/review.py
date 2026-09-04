from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import ReviewService
from app.schemas.review import (
    FirstSolveRequest,
    ReviewRequest,
    NoteUpdateRequest,
    CheatsheetUpdateRequest,
    ProgressOut,
)
from app.core.exceptions import ProblemNotFound, InvalidReviewScore, InvalidFirstSolveStatus

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/first-solve/{problem_id}", response_model=ProgressOut)
def first_solve(problem_id: int, req: FirstSolveRequest, db: Session = Depends(get_db)):
    """首次刷完题目。"""
    service = ReviewService(db)
    # 验证题目存在
    from app.services import ProblemService
    ps = ProblemService(db)
    if not ps.get_by_id(problem_id):
        raise ProblemNotFound(problem_id)
    return service.first_solve(problem_id, req.status)


@router.post("/{problem_id}", response_model=ProgressOut)
def review(problem_id: int, req: ReviewRequest, db: Session = Depends(get_db)):
    """复习打分。"""
    service = ReviewService(db)
    from app.services import ProblemService
    ps = ProblemService(db)
    if not ps.get_by_id(problem_id):
        raise ProblemNotFound(problem_id)
    return service.review(problem_id, req.score)


@router.put("/{problem_id}/note", response_model=ProgressOut)
def update_note(problem_id: int, req: NoteUpdateRequest, db: Session = Depends(get_db)):
    """更新笔记。"""
    service = ReviewService(db)
    return service.update_note(problem_id, req.note)


@router.put("/{problem_id}/cheatsheet", response_model=ProgressOut)
def update_cheatsheet(problem_id: int, req: CheatsheetUpdateRequest, db: Session = Depends(get_db)):
    """更新 cheatsheet。"""
    service = ReviewService(db)
    return service.update_cheatsheet(problem_id, req.cheatsheet)


@router.get("/{problem_id}/logs")
def get_logs(problem_id: int, db: Session = Depends(get_db)):
    """获取复习历史日志。"""
    service = ReviewService(db)
    logs = service.get_logs(problem_id)
    return {"logs": logs}
