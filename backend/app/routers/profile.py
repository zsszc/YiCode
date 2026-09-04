"""
Learning Profile API Router — Phase 2
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import LearningProfileService
from app.schemas.profile import (
    ProfileOut,
    ProfileUpdate,
    AdaptiveRecommendation,
    BehaviorRecordRequest,
    PatternAnalysis,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    """获取当前用户学习画像。"""
    service = LearningProfileService(db)
    profile = service.get_or_create()
    return profile


@router.put("", response_model=ProfileOut)
def update_profile(req: ProfileUpdate, db: Session = Depends(get_db)):
    """更新学习偏好设置。"""
    service = LearningProfileService(db)
    profile = service.get_or_create()

    if req.preferred_difficulty is not None:
        profile.preferred_difficulty = req.preferred_difficulty
    if req.adaptive_quota_enabled is not None:
        profile.adaptive_quota_enabled = req.adaptive_quota_enabled
    if req.custom_quota_weekday is not None:
        profile.custom_quota_weekday = req.custom_quota_weekday
    if req.custom_quota_weekend is not None:
        profile.custom_quota_weekend = req.custom_quota_weekend

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/adaptive", response_model=AdaptiveRecommendation)
def get_adaptive_recommendation(db: Session = Depends(get_db)):
    """获取自适应推荐配置。"""
    service = LearningProfileService(db)
    return service.adaptive_recommendation()


@router.post("/analyze")
def analyze_patterns(days: int = 7, db: Session = Depends(get_db)):
    """分析学习模式。"""
    service = LearningProfileService(db)
    return service.analyze_patterns(days=days)


@router.post("/behaviors")
def record_behavior(req: BehaviorRecordRequest, db: Session = Depends(get_db)):
    """记录用户行为。"""
    service = LearningProfileService(db)
    behavior = service.record_behavior(
        user_id=1,
        problem_id=req.problem_id,
        action_type=req.action_type,
        action_data=req.action_data,
    )
    return {"ok": True, "behavior_id": behavior.id}


@router.post("/update-from-behaviors")
def update_profile_from_behaviors(db: Session = Depends(get_db)):
    """基于行为分析更新画像。"""
    service = LearningProfileService(db)
    profile = service.update_profile()
    return profile
