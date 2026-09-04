from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.services import ProblemService
from app.schemas.problem import ProblemOut, ProblemListItem, CategoryOut, ProblemCreate
from app.core.exceptions import ProblemNotFound

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("", response_model=list[ProblemListItem])
def list_problems(
    keyword: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """题目列表，支持搜索和筛选。"""
    service = ProblemService(db)
    problems = service.search(keyword=keyword, category=category, difficulty=difficulty)
    # 附加进度状态（简化：默认 todo）
    return [
        {
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "difficulty": p.difficulty,
            "category": p.category,
            "is_custom": p.is_custom,
            "status": "todo",
            "next_review": None,
            "note": "",
        }
        for p in problems
    ]


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取所有分类名。"""
    service = ProblemService(db)
    return {"categories": service.get_categories()}


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    """题目详情。"""
    service = ProblemService(db)
    problem = service.get_by_id(problem_id)
    if not problem:
        raise ProblemNotFound(problem_id)
    return problem


@router.post("", response_model=ProblemOut, status_code=201)
def create_problem(data: ProblemCreate, db: Session = Depends(get_db)):
    """添加自定义题目。"""
    service = ProblemService(db)
    return service.create(data)


@router.put("/{problem_id}", response_model=ProblemOut)
def update_problem(problem_id: int, data: ProblemCreate, db: Session = Depends(get_db)):
    """更新自定义题目。"""
    service = ProblemService(db)
    problem = service.update(problem_id, data)
    if not problem:
        raise ProblemNotFound(problem_id)
    return problem


@router.delete("/{problem_id}")
def delete_problem(problem_id: int, db: Session = Depends(get_db)):
    """软删除自定义题目。"""
    service = ProblemService(db)
    ok = service.delete(problem_id)
    if not ok:
        raise ProblemNotFound(problem_id)
    return {"ok": True, "message": f"题目 #{problem_id} 已删除"}
