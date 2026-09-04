from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class DashboardItem(BaseModel):
    id: int
    title: str
    slug: Optional[str] = None
    difficulty: str
    category: str
    status: Optional[str] = "todo"
    next_review: Optional[str] = None
    review_stage: int = 0
    note: str = ""
    is_overdue: bool = False


class DashboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    is_weekend: bool
    quota: int
    done_today: list[int]
    solved_today: list[int]
    reviewed_today: list[int]
    due_review: list[DashboardItem]
    today_new: list[DashboardItem]
    extras_pool: list[DashboardItem]
    todo_left: int
    counts: dict[str, int]
    total: int
    finish: dict
    skipped_yesterday: Optional[dict] = None


class PreviewDay(BaseModel):
    date: str
    is_weekend: bool
    quota: int
    due_review: list[DashboardItem]
    today_new: list[DashboardItem]


class ShiftForwardResponse(BaseModel):
    shifted_count: int
    message: str
