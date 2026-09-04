from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.dependencies import get_db, get_settings_dep
from app.services import DashboardService
from app.schemas.dashboard import DashboardOut, PreviewDay, ShiftForwardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    """获取今日看板。"""
    service = DashboardService(db)
    return service.build()


@router.get("/preview", response_model=PreviewDay)
def get_preview(target: date = Query(default_factory=lambda: date.today() + timedelta(days=1)), db: Session = Depends(get_db)):
    """预览某一天的看板内容（默认明天）。"""
    service = DashboardService(db)
    return service.build_preview(target)


@router.get("/preview-range")
def get_preview_range(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """未来 N 天预告。"""
    service = DashboardService(db)
    start = date.today() + timedelta(days=1)
    return service.build_preview_range(start, days)


@router.post("/shift-forward", response_model=ShiftForwardResponse)
def shift_forward(db: Session = Depends(get_db)):
    """将昨日到期的复习题整体后移一天。"""
    service = DashboardService(db)
    count = service.shift_forward()
    return {
        "shifted_count": count,
        "message": f"已将 {count} 道昨日到期复习题顺延到今天",
    }
