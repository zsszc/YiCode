"""
Learning Profile schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


class ProfileOut(BaseModel):
    user_id: int
    avg_solve_time_easy_ms: int
    avg_solve_time_medium_ms: int
    avg_solve_time_hard_ms: int
    hint_dependency_rate: float
    first_try_success_rate: float
    peak_hour_start: int
    peak_hour_end: int
    preferred_difficulty: str
    streak_days: int
    max_streak: int
    total_solved: int
    total_reviewed: int
    adaptive_quota_enabled: bool
    custom_quota_weekday: Optional[int]
    custom_quota_weekend: Optional[int]

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    preferred_difficulty: Optional[str] = None
    adaptive_quota_enabled: Optional[bool] = None
    custom_quota_weekday: Optional[int] = Field(None, ge=1, le=20)
    custom_quota_weekend: Optional[int] = Field(None, ge=1, le=20)


class AdaptiveRecommendation(BaseModel):
    quota_weekday: int
    quota_weekend: int
    new_ratio: float
    hard_ratio: float
    adaptive_enabled: bool
    reasoning: str
    profile: dict


class BehaviorRecordRequest(BaseModel):
    problem_id: int
    action_type: str = Field(..., pattern="^(open|hint|attempt|submit|review|skip)$")
    action_data: Optional[dict] = None


class PatternAnalysis(BaseModel):
    period_days: int
    action_counts: dict
    hint_dependency_rate: float
    avg_solve_time_ms: int
    peak_hours: dict
    streak_days: int
    max_streak: int
    total_solved: int
    total_reviewed: int
    total_in_progress: int
