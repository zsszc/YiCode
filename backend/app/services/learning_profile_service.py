"""
学习画像服务 — Phase 2
用户行为分析、画像聚合、自适应配额计算。
"""

import json
from datetime import date, timedelta, datetime
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user_behavior import UserBehavior
from app.models.learning_profile import LearningProfile
from app.models.progress import Progress
from app.models.problem import Problem
from app.config import get_settings

settings = get_settings()


class LearningProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: int = 1) -> LearningProfile:
        """获取或创建用户画像。"""
        profile = (
            self.db.query(LearningProfile)
            .filter(LearningProfile.user_id == user_id)
            .first()
        )
        if not profile:
            profile = LearningProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def record_behavior(
        self,
        user_id: int,
        problem_id: int,
        action_type: str,
        action_data: Optional[dict] = None,
    ) -> UserBehavior:
        """记录用户行为。"""
        behavior = UserBehavior(
            user_id=user_id,
            problem_id=problem_id,
            action_type=action_type,
            action_data=json.dumps(action_data or {}),
        )
        self.db.add(behavior)
        self.db.commit()
        return behavior

    def analyze_patterns(self, user_id: int = 1, days: int = 7) -> dict:
        """分析最近 N 天学习模式。"""
        since = datetime.now() - timedelta(days=days)
        behaviors = (
            self.db.query(UserBehavior)
            .filter(
                UserBehavior.user_id == user_id,
                UserBehavior.created_at >= since,
            )
            .all()
        )

        # 统计
        action_counts = defaultdict(int)
        hint_count = 0
        open_count = 0
        submit_count = 0
        solve_times = []
        hour_dist = defaultdict(int)

        for b in behaviors:
            action_counts[b.action_type] += 1
            hour = b.created_at.hour if b.created_at else 0
            hour_dist[hour] += 1

            if b.action_type == "hint":
                hint_count += 1
            if b.action_type == "open":
                open_count += 1
            if b.action_type == "submit":
                submit_count += 1
                try:
                    data = json.loads(b.action_data or "{}")
                    if "solve_time_ms" in data:
                        solve_times.append(data["solve_time_ms"])
                except json.JSONDecodeError:
                    pass

        # 活跃时段
        peak_hours = sorted(hour_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_start = min(h[0] for h in peak_hours) if peak_hours else 9
        peak_end = max(h[0] for h in peak_hours) if peak_hours else 22

        # 提示依赖率
        hint_dependency = hint_count / open_count if open_count > 0 else 0.0

        # 平均解题时间
        avg_solve_time = sum(solve_times) // len(solve_times) if solve_times else 0

        # 连续打卡
        streak = self._calculate_streak(user_id)

        # 进度统计
        progress_stats = self._progress_stats(user_id)

        return {
            "period_days": days,
            "action_counts": dict(action_counts),
            "hint_dependency_rate": round(hint_dependency, 2),
            "avg_solve_time_ms": avg_solve_time,
            "peak_hours": {"start": peak_start, "end": peak_end},
            "streak_days": streak["current"],
            "max_streak": streak["max"],
            **progress_stats,
        }

    def update_profile(self, user_id: int = 1) -> LearningProfile:
        """基于行为分析更新画像。"""
        profile = self.get_or_create(user_id)
        analysis = self.analyze_patterns(user_id, days=14)

        profile.hint_dependency_rate = analysis["hint_dependency_rate"]
        profile.peak_hour_start = analysis["peak_hours"]["start"]
        profile.peak_hour_end = analysis["peak_hours"]["end"]
        profile.streak_days = analysis["streak_days"]
        profile.max_streak = max(profile.max_streak or 0, analysis["streak_days"])
        profile.total_solved = analysis.get("total_solved", 0)
        profile.total_reviewed = analysis.get("total_reviewed", 0)

        # 首次尝试成功率
        progress_list = (
            self.db.query(Progress)
            .filter(Progress.user_id == user_id)
            .all()
        )
        first_tries = [p for p in progress_list if p.first_try is not None]
        if first_tries:
            profile.first_try_success_rate = round(
                sum(1 for p in first_tries if p.first_try) / len(first_tries), 2
            )

        # 按难度统计平均解题时间
        for diff, attr in [
            ("简单", "avg_solve_time_easy_ms"),
            ("中等", "avg_solve_time_medium_ms"),
            ("困难", "avg_solve_time_hard_ms"),
        ]:
            times = []
            for p in progress_list:
                if p.solve_time_ms and p.problem_id:
                    prob = self.db.query(Problem).filter(Problem.id == p.problem_id).first()
                    if prob and prob.difficulty == diff:
                        times.append(p.solve_time_ms)
            if times:
                setattr(profile, attr, sum(times) // len(times))

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def adaptive_recommendation(self, user_id: int = 1) -> dict:
        """基于画像生成自适应推荐。"""
        profile = self.get_or_create(user_id)

        base_weekday = profile.custom_quota_weekday or settings.daily_quota_weekday
        base_weekend = profile.custom_quota_weekend or settings.daily_quota_weekend

        # 连续打卡奖励
        streak_bonus = min(profile.streak_days // 7, 2)

        # 提示依赖率影响新题比例
        hdep = profile.hint_dependency_rate or 0.0
        if hdep > 0.7:
            new_ratio = 0.5
        elif hdep > 0.4:
            new_ratio = 0.7
        else:
            new_ratio = 0.8

        # 能力匹配影响困难题比例
        ftr = profile.first_try_success_rate or 0.0
        if ftr > 0.8:
            hard_ratio = 0.2
        elif ftr < 0.3:
            hard_ratio = 0.05
        else:
            hard_ratio = 0.1

        # 构建理由
        reasons = []
        if streak_bonus > 0:
            reasons.append(f"连续打卡 {profile.streak_days} 天，配额 +{streak_bonus}")
        else:
            reasons.append(f"当前连续打卡 {profile.streak_days} 天")

        if hdep > 0.7:
            reasons.append(f"提示依赖率 {hdep:.0%} 较高，降低新题比例至 {new_ratio:.0%}")
        elif hdep < 0.3:
            reasons.append(f"提示依赖率 {hdep:.0%} 较低，可尝试更多新题")
        else:
            reasons.append(f"提示依赖率 {hdep:.0%}，新题比例正常")

        if ftr > 0.8:
            reasons.append(f"首次成功率 {ftr:.0%} 优秀，增加困难题比例至 {hard_ratio:.0%}")
        elif ftr < 0.3:
            reasons.append(f"首次成功率 {ftr:.0%} 待提升，减少困难题比例至 {hard_ratio:.0%}")

        return {
            "quota_weekday": base_weekday + streak_bonus,
            "quota_weekend": base_weekend + streak_bonus,
            "new_ratio": new_ratio,
            "hard_ratio": hard_ratio,
            "adaptive_enabled": profile.adaptive_quota_enabled,
            "reasoning": "；".join(reasons),
            "profile": {
                "streak_days": profile.streak_days,
                "hint_dependency_rate": profile.hint_dependency_rate,
                "first_try_success_rate": profile.first_try_success_rate,
                "preferred_difficulty": profile.preferred_difficulty,
            },
        }

    def _calculate_streak(self, user_id: int) -> dict:
        """计算连续打卡天数。"""
        # 获取所有有活动的日期
        behaviors = (
            self.db.query(UserBehavior)
            .filter(
                UserBehavior.user_id == user_id,
                UserBehavior.action_type.in_(["submit", "review"]),
            )
            .all()
        )

        dates = sorted(set(
            b.created_at.date() if b.created_at else date.today()
            for b in behaviors
        ), reverse=True)

        if not dates:
            return {"current": 0, "max": 0}

        current_streak = 0
        today = date.today()
        for i, d in enumerate(dates):
            expected = today - timedelta(days=i)
            if d == expected:
                current_streak += 1
            else:
                break

        # 计算历史最大连续
        max_streak = 1
        curr = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                curr += 1
                max_streak = max(max_streak, curr)
            else:
                curr = 1

        return {"current": current_streak, "max": max_streak}

    def _progress_stats(self, user_id: int) -> dict:
        """进度统计。"""
        from app.services.sm2 import STATUS_SOLID, STATUS_ARCHIVED

        progress_list = (
            self.db.query(Progress)
            .filter(Progress.user_id == user_id)
            .all()
        )

        total_solved = sum(1 for p in progress_list if p.status != "todo")
        total_reviewed = sum(1 for p in progress_list if p.status in (STATUS_SOLID, STATUS_ARCHIVED))

        return {
            "total_solved": total_solved,
            "total_reviewed": total_reviewed,
            "total_in_progress": len(progress_list),
        }
