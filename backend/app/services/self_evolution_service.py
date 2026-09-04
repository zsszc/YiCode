"""
AI Agent 自进化服务 — Phase 4
智能路径规划 + 错题归因 + 知识图谱更新
"""

import json
from datetime import date
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.progress import Progress
from app.models.review_log import ReviewLog
from app.models.knowledge_graph import (
    KnowledgeNode, ProblemKnowledge, KnowledgeDependency, UserKnowledgeMastery,
)
from app.models.mistake_analysis import MistakeAnalysis
from app.services.learning_profile_service import LearningProfileService


class SelfEvolutionService:
    """AI Agent 自进化核心服务。
    
    职责：
    1. 错题归因分析 — 分析 review 记录，推断错误原因
    2. 知识图谱更新 — 基于用户表现更新知识点掌握度
    3. 智能路径规划 — 推荐最优学习顺序
    4. 自适应复习调度 — 超越 SM-2，考虑知识点掌握度
    """

    def __init__(self, db: Session):
        self.db = db

    # ========== 错题归因 ==========

    def analyze_mistake(
        self,
        user_id: int,
        problem_id: int,
        review_log_id: Optional[int],
        score: str,
        hint_count: int,
        attempt_count: int,
        solve_time_ms: Optional[int],
    ) -> MistakeAnalysis:
        """基于用户行为数据自动归因错题原因。"""
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        # 获取关联知识点
        pk_links = self.db.query(ProblemKnowledge).filter(
            ProblemKnowledge.problem_id == problem_id
        ).all()
        knowledge_ids = [pk.knowledge_id for pk in pk_links]
        knowledges = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id.in_(knowledge_ids)
        ).all() if knowledge_ids else []

        # 归因逻辑
        mistake_type = self._classify_mistake(
            score=score,
            hint_count=hint_count,
            attempt_count=attempt_count,
            solve_time_ms=solve_time_ms,
            difficulty=problem.difficulty,
        )

        # 生成建议
        suggested_action = self._generate_suggestion(
            mistake_type, problem, knowledges
        )

        analysis = MistakeAnalysis(
            user_id=user_id,
            problem_id=problem_id,
            review_log_id=review_log_id,
            mistake_type=mistake_type,
            description=self._describe_mistake(mistake_type, problem),
            related_knowledge=json.dumps(knowledge_ids),
            suggested_action=suggested_action,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # 更新知识点掌握度
        self._update_knowledge_mastery(user_id, knowledge_ids, score)

        return analysis

    def _classify_mistake(
        self,
        score: str,
        hint_count: int,
        attempt_count: int,
        solve_time_ms: Optional[int],
        difficulty: str,
    ) -> str:
        """分类错误原因。"""
        if score == "easy":
            return "reviewed_well"  # 不是错误

        # 过度依赖提示
        if hint_count >= 3:
            return "hint_dependency"

        # 多次尝试
        if attempt_count >= 5:
            return "concept_gap"

        # 解题时间过长（困难题>30分钟，中等>20分钟，简单>10分钟）
        if solve_time_ms:
            time_min = solve_time_ms / 60000
            thresholds = {"简单": 10, "中等": 20, "困难": 30}
            if time_min > thresholds.get(difficulty, 20):
                return "time_pressure"

        # 根据 score 判断
        if score == "hard":
            return "wrong_approach"

        if score == "ok" and hint_count >= 1:
            return "edge_case"

        return "concept_gap"

    def _describe_mistake(self, mistake_type: str, problem: Problem) -> str:
        """生成错题描述。"""
        descriptions = {
            "hint_dependency": f"在 {problem.title} 中过度依赖 AI 提示，缺乏独立思考。",
            "concept_gap": f"{problem.title} 涉及的核心概念掌握不够扎实。",
            "edge_case": f"{problem.title} 的主要逻辑正确，但遗漏了边界情况。",
            "time_pressure": f"{problem.title} 用时过长，可能是对解法不够熟练。",
            "wrong_approach": f"{problem.title} 选择了不合适的解题方法。",
            "reviewed_well": f"{problem.title} 复习效果良好。",
        }
        return descriptions.get(mistake_type, f"{problem.title} 需要进一步分析。")

    def _generate_suggestion(
        self, mistake_type: str, problem: Problem, knowledges: list
    ) -> str:
        """生成改进建议。"""
        kn_names = ", ".join([k.name for k in knowledges[:3]]) if knowledges else "相关基础"

        suggestions = {
            "hint_dependency": f"下次先做 {kn_names} 的基础练习，减少对提示的依赖。",
            "concept_gap": f"建议重新学习 {kn_names} 的核心概念，再做同类题巩固。",
            "edge_case": f"总结 {problem.title} 的边界条件，形成检查清单。",
            "time_pressure": f"多做 {kn_names} 的限时练习，提高熟练度。",
            "wrong_approach": f"分析 {problem.title} 的最优解法，理解为什么选择该方法。",
            "reviewed_well": "继续保持！",
        }
        return suggestions.get(mistake_type, "继续练习同类题目。")

    # ========== 知识图谱 ==========

    def _update_knowledge_mastery(self, user_id: int, knowledge_ids: list[int], score: str):
        """更新用户对知识点的掌握度。"""
        delta = {"easy": 0.15, "ok": 0.05, "hard": -0.10, "reviewed_well": 0.15}
        change = delta.get(score, 0.0)

        for kid in knowledge_ids:
            mastery = self.db.query(UserKnowledgeMastery).filter(
                UserKnowledgeMastery.user_id == user_id,
                UserKnowledgeMastery.knowledge_id == kid,
            ).first()

            if not mastery:
                mastery = UserKnowledgeMastery(
                    user_id=user_id,
                    knowledge_id=kid,
                    mastery_level=max(0.0, min(1.0, 0.3 + change)),
                    total_attempts=1,
                    correct_attempts=1 if score in ("easy", "ok", "reviewed_well") else 0,
                    last_practiced=date.today().isoformat(),
                )
                self.db.add(mastery)
            else:
                mastery.mastery_level = max(0.0, min(1.0, mastery.mastery_level + change))
                mastery.total_attempts += 1
                if score in ("easy", "ok", "reviewed_well"):
                    mastery.correct_attempts += 1
                mastery.last_practiced = date.today().isoformat()

        self.db.commit()

    def get_mastery_report(self, user_id: int = 1) -> dict:
        """获取用户知识点掌握度报告。"""
        masteries = self.db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == user_id
        ).all()

        result = []
        for m in masteries:
            kn = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == m.knowledge_id).first()
            if kn:
                result.append({
                    "knowledge_id": m.knowledge_id,
                    "name": kn.name,
                    "category": kn.category,
                    "mastery_level": round(m.mastery_level, 2),
                    "total_attempts": m.total_attempts,
                    "correct_rate": round(m.correct_attempts / m.total_attempts, 2) if m.total_attempts > 0 else 0,
                    "last_practiced": m.last_practiced,
                })

        # 按掌握度排序
        result.sort(key=lambda x: x["mastery_level"])

        # 分类统计
        by_category = defaultdict(list)
        for r in result:
            by_category[r["category"]].append(r)

        weak_points = [r for r in result if r["mastery_level"] < 0.4]
        strong_points = [r for r in result if r["mastery_level"] > 0.8]

        return {
            "user_id": user_id,
            "total_knowledge": len(result),
            "weak_points": weak_points[:5],
            "strong_points": strong_points[:5],
            "by_category": dict(by_category),
            "overall_mastery": round(sum(r["mastery_level"] for r in result) / len(result), 2) if result else 0,
        }

    # ========== 智能路径规划 ==========

    def generate_learning_path(self, user_id: int = 1, target_problem_id: Optional[int] = None) -> dict:
        """生成个性化学习路径。"""
        # 获取薄弱知识点
        report = self.get_mastery_report(user_id)
        weak = report["weak_points"]

        if not weak:
            return {
                "message": "基础扎实！建议挑战新题或复习巩固。",
                "path": [],
            }

        # 为每个薄弱知识点推荐题目
        path = []
        for wp in weak[:3]:
            # 找到关联该知识点的简单/中等题
            pk_links = self.db.query(ProblemKnowledge).filter(
                ProblemKnowledge.knowledge_id == wp["knowledge_id"],
            ).all()

            problem_ids = [pk.problem_id for pk in pk_links]
            problems = self.db.query(Problem).filter(
                Problem.id.in_(problem_ids),
                Problem.difficulty.in_(["简单", "中等"]),
            ).limit(3).all()

            path.append({
                "knowledge": wp["name"],
                "mastery_level": wp["mastery_level"],
                "recommended_problems": [
                    {"id": p.id, "title": p.title, "difficulty": p.difficulty}
                    for p in problems
                ],
                "reason": f"{wp['name']} 掌握度仅 {wp['mastery_level']:.0%}，需要加强练习",
            })

        return {
            "message": f"发现 {len(weak)} 个薄弱知识点，已为你规划学习路径",
            "path": path,
        }

    def get_mistake_summary(self, user_id: int = 1, days: int = 30) -> dict:
        """获取错题总结。"""
        from datetime import datetime, timedelta
        since = datetime.now() - timedelta(days=days)

        analyses = self.db.query(MistakeAnalysis).filter(
            MistakeAnalysis.user_id == user_id,
            MistakeAnalysis.created_at >= since,
        ).all()

        type_counts = defaultdict(int)
        for a in analyses:
            type_counts[a.mistake_type] += 1

        return {
            "period_days": days,
            "total_analyzed": len(analyses),
            "type_distribution": dict(type_counts),
            "top_weakness": max(type_counts, key=type_counts.get) if type_counts else None,
            "recent_mistakes": [
                {
                    "problem_id": a.problem_id,
                    "type": a.mistake_type,
                    "suggested_action": a.suggested_action,
                }
                for a in analyses[-5:]
            ],
        }
