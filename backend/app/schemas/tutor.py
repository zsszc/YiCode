"""
AI Tutor schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


class HintRequest(BaseModel):
    problem_id: int
    hint_level: int = Field(default=1, ge=1, le=3)
    user_code: Optional[str] = None
    language: str = "python"


class HintResponse(BaseModel):
    content: str
    tokens_used: int
    latency_ms: int


class CodeReviewRequest(BaseModel):
    problem_id: int
    code: str = Field(..., min_length=1)
    language: str = "python"


class CodeReviewResponse(BaseModel):
    time_complexity: str
    space_complexity: str
    edge_cases: list[str]
    style_suggestions: list[str]
    optimization_hints: list[str]
    rating: int
    overall_comment: str
    tokens_used: int
    latency_ms: int


class TutorLogItem(BaseModel):
    id: int
    problem_id: Optional[int]
    request_type: str
    tokens_used: Optional[int]
    latency_ms: Optional[int]
    created_at: Optional[str]


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    problem_id: Optional[int] = None
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    user_code: Optional[str] = Field(None, max_length=10000)


class ChatResponse(BaseModel):
    reply: str
    tokens_used: int
    latency_ms: int
