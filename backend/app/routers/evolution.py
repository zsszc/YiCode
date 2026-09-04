"""
自进化 API Router — Phase 4
错题归因 + 知识图谱 + 智能路径规划
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import SelfEvolutionService

router = APIRouter(prefix="/evolution", tags=["evolution"])


@router.post("/analyze-mistake/{problem_id}")
def analyze_mistake(
    problem_id: int,
    score: str,
    hint_count: int = 0,
    attempt_count: int = 0,
    solve_time_ms: int = None,
    db: Session = Depends(get_db),
):
    """分析错题原因。"""
    service = SelfEvolutionService(db)
    result = service.analyze_mistake(
        user_id=1,
        problem_id=problem_id,
        review_log_id=None,
        score=score,
        hint_count=hint_count,
        attempt_count=attempt_count,
        solve_time_ms=solve_time_ms,
    )
    return {
        "id": result.id,
        "mistake_type": result.mistake_type,
        "description": result.description,
        "suggested_action": result.suggested_action,
    }


@router.get("/mastery-report")
def get_mastery_report(db: Session = Depends(get_db)):
    """获取知识点掌握度报告。"""
    service = SelfEvolutionService(db)
    return service.get_mastery_report(user_id=1)


@router.get("/learning-path")
def get_learning_path(db: Session = Depends(get_db)):
    """获取个性化学习路径。"""
    service = SelfEvolutionService(db)
    return service.generate_learning_path(user_id=1)


@router.get("/mistake-summary")
def get_mistake_summary(days: int = 30, db: Session = Depends(get_db)):
    """获取错题总结。"""
    service = SelfEvolutionService(db)
    return service.get_mistake_summary(user_id=1, days=days)


@router.get("/learning-curve")
def get_learning_curve(db: Session = Depends(get_db)):
    """获取学习曲线数据（用于 ECharts 可视化）。"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    from app.models.review_log import ReviewLog
    from app.models.progress import Progress
    from app.models.knowledge_graph import UserKnowledgeMastery, KnowledgeNode

    # 最近 30 天每日复习量
    since = datetime.now() - timedelta(days=30)
    logs = db.query(ReviewLog).filter(ReviewLog.created_at >= since).all()

    daily_counts = defaultdict(int)
    for log in logs:
        day = log.created_at.strftime("%Y-%m-%d") if log.created_at else "unknown"
        daily_counts[day] += 1

    dates = sorted(daily_counts.keys())
    daily_series = [{"date": d, "count": daily_counts[d]} for d in dates]

    # 掌握度分布（按类别）
    masteries = db.query(UserKnowledgeMastery).filter(UserKnowledgeMastery.user_id == 1).all()
    category_mastery = defaultdict(list)
    for m in masteries:
        kn = db.query(KnowledgeNode).filter(KnowledgeNode.id == m.knowledge_id).first()
        if kn:
            category_mastery[kn.category].append(m.mastery_level)

    mastery_distribution = [
        {"category": cat, "avg_mastery": round(sum(vals) / len(vals), 2), "count": len(vals)}
        for cat, vals in category_mastery.items()
    ]

    # 复习状态分布
    progress_entries = db.query(Progress).filter(Progress.user_id == 1).all()
    stage_counts = defaultdict(int)
    for p in progress_entries:
        stage_counts[p.stage] += 1

    stage_distribution = [
        {"stage": stage, "count": count}
        for stage, count in sorted(stage_counts.items())
    ]

    return {
        "daily_review": daily_series,
        "mastery_by_category": mastery_distribution,
        "stage_distribution": stage_distribution,
    }
