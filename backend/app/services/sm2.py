"""
简化 SM-2 遗忘曲线算法核心。

间隔: [1, 3, 7, 15, 30] 天
stage 0-4 对应上述间隔，stage >= 5 归档。
"""

from datetime import date, timedelta
from typing import Optional

from app.config import get_settings

settings = get_settings()

# 状态常量
STATUS_TODO = "todo"
STATUS_FORGOT = "forgot"
STATUS_SHAKY = "shaky"
STATUS_SOLID = "solid"
STATUS_ARCHIVED = "archived"

# 打分常量
SCORE_EASY = "easy"
SCORE_OK = "ok"
SCORE_HARD = "hard"

VALID_STATUSES = {STATUS_TODO, STATUS_FORGOT, STATUS_SHAKY, STATUS_SOLID, STATUS_ARCHIVED}
VALID_SCORES = {SCORE_EASY, SCORE_OK, SCORE_HARD}
VALID_FIRST_SOLVE_STATUSES = {STATUS_FORGOT, STATUS_SHAKY, STATUS_SOLID}


def get_intervals() -> list[int]:
    return settings.review_intervals_days


def next_review_date(stage: int, base_date: Optional[date] = None) -> Optional[str]:
    """计算 stage 对应的下次复习日期。stage 超出 intervals → None (归档)。"""
    intervals = get_intervals()
    if stage >= len(intervals):
        return None
    delta = intervals[stage]
    base = base_date or date.today()
    return (base + timedelta(days=delta)).isoformat()


def apply_first_solve(status: str, base_date: Optional[date] = None) -> tuple[int, str, str]:
    """首次刷完，返回 (stage, next_review_iso, status)。

    solid → stage=1 (+3天), forgot/shaky → stage=0 (+1天)
    """
    if status not in VALID_FIRST_SOLVE_STATUSES:
        raise ValueError(f"Invalid first-solve status: {status}")

    stage = 1 if status == STATUS_SOLID else 0
    nr = next_review_date(stage, base_date)
    if nr is None:
        # 理论上不会发生（stage=0/1 都在 intervals 内）
        stage = len(get_intervals())
        nr = None
    return stage, nr, status


def apply_review(stage: int, score: str, base_date: Optional[date] = None) -> tuple[int, Optional[str], str]:
    """复习打分，返回 (new_stage, next_review_iso, new_status)。

    easy: stage+1, solid
    ok:   保持,   shaky
    hard: 回退0,  forgot
    stage >= len(intervals) → archived
    """
    if score not in VALID_SCORES:
        raise ValueError(f"Invalid review score: {score}")

    if stage < 0:
        stage = 0

    if score == SCORE_EASY:
        new_stage = stage + 1
        new_status = STATUS_SOLID
    elif score == SCORE_OK:
        new_stage = stage
        new_status = STATUS_SHAKY
    else:  # hard
        new_stage = 0
        new_status = STATUS_FORGOT

    intervals = get_intervals()
    if new_stage >= len(intervals):
        return new_stage, None, STATUS_ARCHIVED

    nr = next_review_date(new_stage, base_date)
    return new_stage, nr, new_status


def default_progress_entry() -> dict:
    """返回默认进度条目结构。"""
    return {
        "status": STATUS_TODO,
        "note": "",
        "cheatsheet": "",
        "review_stage": -1,
        "next_review": None,
        "last_done": None,
        "history": [],
    }
