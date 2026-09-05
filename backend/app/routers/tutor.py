"""
AI Tutor API Router — Phase 2 + Phase 4 SSE
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.dependencies import get_db
from app.services import AITutorService
from app.schemas.tutor import (
    HintRequest,
    HintResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    ChatRequest,
    ChatResponse,
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
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
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


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """AI Tutor 自由对话：携带题目上下文、历史消息与用户当前代码。"""
    service = AITutorService(db)
    try:
        result = await service.chat(
            problem_id=req.problem_id,
            message=req.message,
            history=[h.model_dump() for h in req.history],
            user_code=req.user_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "reply": result.content,
        "tokens_used": result.tokens_used,
        "latency_ms": result.latency_ms,
    }


@router.post("/chat-stream")
async def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """SSE 流式自由对话：逐段返回 AI 回复，前端打字机渲染。"""
    service = AITutorService(db)

    async def event_generator():
        try:
            async for chunk in service.chat_stream(
                problem_id=req.problem_id,
                message=req.message,
                history=[h.model_dump() for h in req.history],
                user_code=req.user_code,
            ):
                # JSON 编码避免换行/特殊字符破坏 SSE 行格式
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'AI 服务异常: {e}'}, ensure_ascii=False)}\n\n"
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


@router.get("/history/{problem_id}")
def get_chat_history(problem_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """按题目取回历史对话消息（user/assistant 交替，时间正序）。"""
    service = AITutorService(db)
    return service.get_chat_history(problem_id=problem_id, limit=limit)


@router.get("/logs", response_model=list[TutorLogItem])
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    """获取 AI Tutor 交互历史。"""
    service = AITutorService(db)
    return service.get_logs(limit=limit)
