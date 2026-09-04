from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import date


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    problem_id: int
    status: str
    review_stage: int
    next_review: Optional[str] = None
    last_done: Optional[str] = None
    note: str = ""
    cheatsheet: str = ""

    @model_validator(mode="before")
    @classmethod
    def convert_dates(cls, data):
        # 处理 SQLAlchemy 模型的 date 字段
        if hasattr(data, "next_review") and isinstance(data.next_review, date):
            data.next_review = data.next_review.isoformat()
        if hasattr(data, "last_done") and isinstance(data.last_done, date):
            data.last_done = data.last_done.isoformat()
        # 也处理 dict
        if isinstance(data, dict):
            if isinstance(data.get("next_review"), date):
                data["next_review"] = data["next_review"].isoformat()
            if isinstance(data.get("last_done"), date):
                data["last_done"] = data["last_done"].isoformat()
        return data


class FirstSolveRequest(BaseModel):
    status: str = Field(..., pattern="^(forgot|shaky|solid)$")


class ReviewRequest(BaseModel):
    score: str = Field(..., pattern="^(easy|ok|hard)$")


class NoteUpdateRequest(BaseModel):
    note: str = Field(..., max_length=2000)


class CheatsheetUpdateRequest(BaseModel):
    cheatsheet: str = Field(..., max_length=5000)


class ReviewLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    score: str
    from_stage: int
    to_stage: int
    created_at: str
