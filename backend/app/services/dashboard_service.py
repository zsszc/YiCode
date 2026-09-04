"""
每日看板服务 — 核心业务逻辑，从原项目 app.py 迁移重构。
"""

from datetime import date, timedelta
from typing import Optional
from collections import defaultdict
import random

from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.progress import Progress
from app.config import get_settings
from app.services.sm2 import (
    STATUS_TODO, STATUS_ARCHIVED, STATUS_FORGOT, STATUS_SHAKY, STATUS_SOLID,
)

settings = get_settings()

CHECKIN_BLURB_POOL = (
    "一天一点，不着急",
    "慢一点也是往前",
    "做了就是做了",
    "与 bug 和解的一天",
    "AC 一下，人生小胜",
    "稳住节奏，稳住手感",
    "保持出场率",
    "今天也守住了",
)

STREAK_FORGIVE_EVERY_DAYS = 10


def _today_with_boundary(day_boundary_hour: float = 0.0) -> date:
    """考虑日界时间的"今天"。"""
    if day_boundary_hour <= 0:
        return date.today()
    from datetime import datetime
    now = datetime.now()
    bh = int(day_boundary_hour)
    bm = int(round((day_boundary_hour - bh) * 60))
    threshold = now.replace(hour=bh, minute=bm, second=0, microsecond=0)
    if now < threshold:
        return (now - timedelta(days=1)).date()
    return now.date()


def _daily_quota(cfg: dict, today: date) -> int:
    dq = cfg.get("daily_quota", {"weekday": 3, "weekend": 6})
    return dq.get("weekend", 6) if today.weekday() >= 5 else dq.get("weekday", 3)


def _balanced_pick(todo_pool: list[dict], n: int) -> list[dict]:
    """从未刷池按难度均衡挑 n 道，保持原分类顺序。"""
    targets_by_n = {
        1: {"简单": 0, "中等": 1, "困难": 0},
        2: {"简单": 1, "中等": 1, "困难": 0},
        3: {"简单": 1, "中等": 1, "困难": 1},
        4: {"简单": 1, "中等": 2, "困难": 1},
        5: {"简单": 2, "中等": 2, "困难": 1},
        6: {"简单": 2, "中等": 3, "困难": 1},
    }
    target = targets_by_n.get(n, {
        "简单": max(1, n // 4),
        "中等": max(1, n // 2),
        "困难": max(1, n // 6),
    })

    by_diff: dict[str, list[dict]] = defaultdict(list)
    for p in todo_pool:
        by_diff.setdefault(p.get("difficulty", "中等"), []).append(p)

    picked_ids: set[int] = set()
    for diff, need in target.items():
        for p in by_diff.get(diff, [])[:need]:
            picked_ids.add(p["id"])

    if len(picked_ids) < n:
        for p in todo_pool:
            if len(picked_ids) >= n:
                break
            picked_ids.add(p["id"])

    return [p for p in todo_pool if p["id"] in picked_ids][:n]


def _estimate_finish(
    todo_left: int,
    weekday_q: int,
    weekend_q: int,
    done_today: int,
    quota_today: int,
    today: date,
) -> dict:
    """精确日历模拟完成日。"""
    if todo_left <= 0:
        return {"days_left": 0, "finish_date": today.isoformat(), "reachable": True}
    if weekday_q <= 0 and weekend_q <= 0:
        return {"days_left": None, "finish_date": None, "reachable": False}

    remaining = todo_left
    today_slot = max(0, quota_today - done_today)
    if today_slot > 0:
        remaining -= min(remaining, today_slot)
        if remaining <= 0:
            return {"days_left": 0, "finish_date": today.isoformat(), "reachable": True}

    d = today
    days_counted = 0
    max_iter = 3650
    while remaining > 0 and days_counted < max_iter:
        d = d + timedelta(days=1)
        days_counted += 1
        slot = weekend_q if d.weekday() >= 5 else weekday_q
        if slot <= 0:
            continue
        remaining -= min(remaining, slot)

    if remaining > 0:
        return {"days_left": None, "finish_date": None, "reachable": False}
    return {"days_left": days_counted, "finish_date": d.isoformat(), "reachable": True}


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.today = _today_with_boundary(settings.day_boundary_hour)
        self.today_str = self.today.isoformat()

    def build(self) -> dict:
        """构建今日看板。"""
        problems = self.db.query(Problem).filter(Problem.deleted == False).order_by(Problem.id).all()
        problem_ids = [p.id for p in problems]
        by_id = {p.id: p for p in problems}

        # 加载进度
        progress_map = {}
        for prog in self.db.query(Progress).filter(Progress.problem_id.in_(problem_ids)).all():
            progress_map[prog.problem_id] = prog

        # 统计今日已完成
        solved_today, reviewed_today = self._done_today(progress_map)
        done_today = solved_today | reviewed_today

        # 到期复习
        overdue_days = settings.overdue_alert_days
        due_review = []
        overdue_ids = []
        for pid, prog in progress_map.items():
            if prog.status in (STATUS_ARCHIVED, STATUS_TODO):
                continue
            if not prog.next_review:
                continue
            if pid in done_today:
                continue
            nr = prog.next_review.isoformat() if isinstance(prog.next_review, date) else str(prog.next_review)
            if nr <= self.today_str:
                p = by_id.get(pid)
                item = {
                    "id": pid,
                    "title": p.title if p else "?",
                    "slug": p.slug if p else None,
                    "difficulty": p.difficulty if p else "?",
                    "category": p.category if p else "?",
                    "status": prog.status,
                    "next_review": nr,
                    "review_stage": prog.review_stage,
                    "note": prog.note or "",
                }
                due_review.append(item)
                try:
                    if (self.today - date.fromisoformat(nr)).days > overdue_days:
                        overdue_ids.append(pid)
                except ValueError:
                    pass

        # 新题配额
        quota = _daily_quota(
            {"daily_quota": {"weekday": settings.daily_quota_weekday, "weekend": settings.daily_quota_weekend}},
            self.today,
        )
        new_slots = max(0, quota - len(solved_today))

        # 未刷池
        todo_pool = []
        for p in problems:
            prog = progress_map.get(p.id)
            if not prog or prog.status == STATUS_TODO:
                todo_pool.append({
                    "id": p.id,
                    "title": p.title,
                    "slug": p.slug,
                    "difficulty": p.difficulty,
                    "category": p.category,
                    "note": prog.note if prog else "",
                })

        today_new = _balanced_pick(todo_pool, new_slots)
        today_new_ids = {p["id"] for p in today_new}
        extras_pool = [p for p in todo_pool if p["id"] not in today_new_ids][:10]

        # 逾期标记
        overdue_set = set(overdue_ids)
        for r in due_review:
            r["is_overdue"] = r["id"] in overdue_set

        # 统计
        total = len(problems)
        counts = {
            STATUS_TODO: sum(1 for p in problems if (progress_map.get(p.id) is None or progress_map[p.id].status == STATUS_TODO)),
            STATUS_FORGOT: sum(1 for p in problems if (progress_map.get(p.id) and progress_map[p.id].status == STATUS_FORGOT)),
            STATUS_SHAKY: sum(1 for p in problems if (progress_map.get(p.id) and progress_map[p.id].status == STATUS_SHAKY)),
            STATUS_SOLID: sum(1 for p in problems if (progress_map.get(p.id) and progress_map[p.id].status == STATUS_SOLID)),
            STATUS_ARCHIVED: sum(1 for p in problems if (progress_map.get(p.id) and progress_map[p.id].status == STATUS_ARCHIVED)),
        }

        # 完成预估
        finish = _estimate_finish(
            todo_left=len(todo_pool),
            weekday_q=settings.daily_quota_weekday,
            weekend_q=settings.daily_quota_weekend,
            done_today=len(solved_today),
            quota_today=quota,
            today=self.today,
        )

        # 昨日空档检测
        skipped_yesterday = self._detect_skipped_yesterday(progress_map)

        return {
            "date": self.today_str,
            "is_weekend": self.today.weekday() >= 5,
            "quota": quota,
            "done_today": sorted(done_today),
            "solved_today": sorted(solved_today),
            "reviewed_today": sorted(reviewed_today),
            "due_review": due_review,
            "today_new": today_new,
            "extras_pool": extras_pool,
            "todo_left": len(todo_pool),
            "counts": counts,
            "total": total,
            "finish": finish,
            "skipped_yesterday": skipped_yesterday,
        }

    def _done_today(self, progress_map: dict[int, Progress]) -> tuple[set[int], set[int]]:
        """返回 (solved_today, reviewed_today)。"""
        # 简化版：基于 progress.last_done 判断
        solved: set[int] = set()
        reviewed: set[int] = set()
        for pid, prog in progress_map.items():
            if not prog.last_done:
                continue
            ld = prog.last_done.isoformat() if isinstance(prog.last_done, date) else str(prog.last_done)
            if ld == self.today_str:
                # 区分 solve 和 review：基于 review_stage 判断
                # stage -1 → 从未刷过（理论上不应该 last_done=today）
                # stage 0/1 且 status 从 todo 变来 → solve
                # 这里简化处理：用 review_logs 表来精确判断
                # 在完整实现中，应该查询 review_logs
                if prog.status == STATUS_TODO:
                    continue
                #  heuristic: stage <= 1 且 note 为空或 history 首次 → solve
                #  暂时统一视为 review（安全保守）
                reviewed.add(pid)
        return solved, reviewed

    def _detect_skipped_yesterday(self, progress_map: dict[int, Progress]) -> Optional[dict]:
        """检测昨天是否有复习到期但未做题。"""
        yesterday = (self.today - timedelta(days=1)).isoformat()
        y_pending = 0
        y_had_activity = False
        for pid, prog in progress_map.items():
            if prog.status not in (STATUS_ARCHIVED, STATUS_TODO):
                if prog.next_review:
                    nr = prog.next_review.isoformat() if isinstance(prog.next_review, date) else str(prog.next_review)
                    if nr == yesterday:
                        y_pending += 1
            if prog.last_done:
                ld = prog.last_done.isoformat() if isinstance(prog.last_done, date) else str(prog.last_done)
                if ld == yesterday:
                    y_had_activity = True
        if y_pending > 0 and not y_had_activity:
            return {"date": yesterday, "review_count": y_pending}
        return None

    def build_preview(self, target: date) -> dict:
        """预测 target 日期的看板内容。"""
        problems = self.db.query(Problem).filter(Problem.deleted == False).order_by(Problem.id).all()
        by_id = {p.id: p for p in problems}
        progress_map = {}
        for prog in self.db.query(Progress).all():
            progress_map[prog.problem_id] = prog

        target_str = target.isoformat()
        overdue_days = settings.overdue_alert_days

        due_review = []
        for pid, prog in progress_map.items():
            if prog.status in (STATUS_ARCHIVED, STATUS_TODO):
                continue
            if not prog.next_review:
                continue
            nr = prog.next_review.isoformat() if isinstance(prog.next_review, date) else str(prog.next_review)
            if nr > target_str:
                continue
            p = by_id.get(pid)
            item = {
                "id": pid,
                "title": p.title if p else "?",
                "slug": p.slug if p else None,
                "difficulty": p.difficulty if p else "?",
                "category": p.category if p else "?",
                "status": prog.status,
                "next_review": nr,
                "review_stage": prog.review_stage,
                "note": prog.note or "",
            }
            try:
                days_overdue = (target - date.fromisoformat(nr)).days
                item["is_overdue"] = days_overdue > overdue_days
            except ValueError:
                item["is_overdue"] = False
            due_review.append(item)

        quota = settings.daily_quota_weekend if target.weekday() >= 5 else settings.daily_quota_weekday
        todo_pool = []
        for p in problems:
            prog = progress_map.get(p.id)
            if not prog or prog.status == STATUS_TODO:
                todo_pool.append({
                    "id": p.id,
                    "title": p.title,
                    "slug": p.slug,
                    "difficulty": p.difficulty,
                    "category": p.category,
                    "note": prog.note if prog else "",
                })
        today_new = _balanced_pick(todo_pool, quota)

        return {
            "date": target_str,
            "is_weekend": target.weekday() >= 5,
            "quota": quota,
            "due_review": due_review,
            "today_new": today_new,
        }

    def build_preview_range(self, start: date, days: int = 30) -> list[dict]:
        """未来 days 天预告（前向模拟）。"""
        intervals = settings.review_intervals_days
        progress_map = {}
        for prog in self.db.query(Progress).all():
            progress_map[prog.problem_id] = prog
        problems = self.db.query(Problem).filter(Problem.deleted == False).all()
        by_id = {p.id: p for p in problems}
        overdue_days = settings.overdue_alert_days

        # 拷贝可推进状态
        sim: dict[int, dict] = {}
        for pid, prog in progress_map.items():
            if prog.status in (STATUS_ARCHIVED, STATUS_TODO):
                continue
            if not prog.next_review:
                continue
            nr = prog.next_review.isoformat() if isinstance(prog.next_review, date) else str(prog.next_review)
            sim[pid] = {
                "stage": prog.review_stage,
                "next": nr,
                "status": prog.status,
                "note": prog.note or "",
            }

        # 逾期题顺延到 start
        start_str = start.isoformat()
        for s in sim.values():
            if s["next"] < start_str:
                s["_original_due"] = s["next"]
                s["next"] = start_str

        out = []
        for i in range(days):
            target = start + timedelta(days=i)
            target_str = target.isoformat()

            due_ids = [pid for pid, s in sim.items() if s["next"] == target_str]
            due_review = []
            for pid in due_ids:
                s = sim[pid]
                p = by_id.get(pid)
                original = s.get("_original_due", s["next"])
                try:
                    real_overdue = (self.today - date.fromisoformat(original)).days
                    is_overdue = real_overdue > overdue_days
                except ValueError:
                    is_overdue = False
                due_review.append({
                    "id": pid,
                    "title": p.title if p else "?",
                    "slug": p.slug if p else None,
                    "difficulty": p.difficulty if p else "?",
                    "category": p.category if p else "?",
                    "status": s["status"],
                    "next_review": original,
                    "review_stage": s["stage"],
                    "note": s["note"],
                    "is_overdue": is_overdue,
                })
                # 模拟推进：秒 A → stage+1
                new_stage = s["stage"] + 1
                if new_stage >= len(intervals):
                    sim[pid]["next"] = ""
                    sim[pid]["stage"] = new_stage
                else:
                    sim[pid]["stage"] = new_stage
                    sim[pid]["next"] = (target + timedelta(days=intervals[new_stage])).isoformat()
                sim[pid].pop("_original_due", None)

            quota = settings.daily_quota_weekend if target.weekday() >= 5 else settings.daily_quota_weekday
            today_new = []
            if i == 0:
                # 第一天用 build_preview
                preview = self.build_preview(target)
                today_new = preview["today_new"]

            out.append({
                "date": target_str,
                "is_weekend": target.weekday() >= 5,
                "quota": quota,
                "due_review": due_review,
                "today_new": today_new,
            })

        return out

    def shift_forward(self) -> int:
        """将昨日到期的复习题整体后移一天。返回平移数量。"""
        yesterday = self.today - timedelta(days=1)
        yesterday_str = yesterday.isoformat()
        count = 0
        for prog in self.db.query(Progress).all():
            if prog.status in (STATUS_ARCHIVED, STATUS_TODO):
                continue
            if not prog.next_review:
                continue
            nr = prog.next_review.isoformat() if isinstance(prog.next_review, date) else str(prog.next_review)
            if nr == yesterday_str:
                prog.next_review = self.today
                count += 1
        self.db.commit()
        return count
