"""
AI Tutor API Router — Phase 2 + Phase 4 SSE
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import AITutorService
from app.schemas.tutor import (
    HintRequest,
    HintResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    TutorLogItem,
)

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/hint", response_model=HintResponse)
async def get_hint(req: HintRequest, db: Session = Depends(get_db)):
    """获取 AI 解题提示。"""
    service = AITutorService(db)
    result = await service.generate_hint(
        problem_id=req.problem_id,
        level=req.hint_level,
        user_code=req.user_code,
    )
    return {
        "content": result.content,
        "tokens_used": result.tokens_used,
        "latency_ms": result.latency_ms,
    }


@router.get("/hint-stream/{problem_id}")
async def get_hint_stream(
    problem_id: int,
    level: int = 1,
    db: Session = Depends(get_db),
):
    """SSE 流式获取 AI 解题提示。"""
    if level not in (1, 2, 3):
        raise HTTPException(status_code=422, detail="hint_level must be 1, 2, or 3")

    service = AITutorService(db)

    async def event_generator():
        async for chunk in service.generate_hint_stream(problem_id=problem_id, level=level):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/review-code", response_model=CodeReviewResponse)
async def review_code(req: CodeReviewRequest, db: Session = Depends(get_db)):
    """AI 代码审查。"""
    service = AITutorService(db)
    result = await service.review_code(
        problem_id=req.problem_id,
        code=req.code,
        language=req.language,
    )
    return {
        "time_complexity": result.time_complexity,
        "space_complexity": result.space_complexity,
        "edge_cases": result.edge_cases,
        "style_suggestions": result.style_suggestions,
        "optimization_hints": result.optimization_hints,
        "rating": result.rating,
        "overall_comment": result.overall_comment,
        "tokens_used": result.tokens_used,
        "latency_ms": result.latency_ms,
    }


@router.get("/logs", response_model=list[TutorLogItem])
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    """获取 AI Tutor 交互历史。"""
    service = AITutorService(db)
    return service.get_logs(limit=limit)
