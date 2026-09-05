"""
AI Tutor Service — 可插拔 LLM 架构

通过配置自动选择 Provider：
- llm_provider=mock (默认): 无需 API key，基于规则
- llm_provider=kimi: 调用 Moonshot AI API
- llm_provider=openai: 调用 OpenAI API
"""

import json
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.learning_profile import LearningProfile
from app.models.ai_tutor_log import AITutorLog
from app.models.user_behavior import UserBehavior
from app.services.llm_providers import get_llm_provider
from app.services.llm_providers.base import HintResult, CodeReviewResult


class AITutorService:
    """AI Tutor 服务，通过配置自动切换 LLM provider。"""

    def __init__(self, db: Session, provider=None):
        self.db = db
        # 允许测试注入 provider；否则通过工厂自动创建
        self.provider = provider or get_llm_provider()

    def _uid_or_none(self, user_id: int):
        """用户不存在时返回 None，避免外键约束失败（未注册/单用户场景）。"""
        from app.models.user import User

        exists = self.db.query(User).filter(User.id == user_id).first()
        return user_id if exists else None

    async def generate_hint(
        self,
        problem_id: int,
        level: int = 1,
        user_code: Optional[str] = None,
        user_id: int = 1,
    ) -> HintResult:
        """生成解题提示。"""
        if level not in (1, 2, 3):
            raise ValueError("hint_level must be 1, 2, or 3")

        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        profile = (
            self.db.query(LearningProfile)
            .filter(LearningProfile.user_id == user_id)
            .first()
        )

        result = await self.provider.generate_hint(problem, level, user_code, profile)

        # 记录日志
        log = AITutorLog(
            user_id=self._uid_or_none(user_id),
            problem_id=problem_id,
            request_type="hint",
            prompt=f"level={level}, code_present={bool(user_code)}",
            response=result.content[:2000],
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
        )
        self.db.add(log)

        # 记录行为
        behavior = UserBehavior(
            user_id=self._uid_or_none(user_id),
            problem_id=problem_id,
            action_type="hint",
            action_data=json.dumps({"hint_level": level}),
        )
        self.db.add(behavior)

        # 更新 progress hint_count
        from app.models.progress import Progress
        progress = (
            self.db.query(Progress)
            .filter(Progress.user_id == user_id, Progress.problem_id == problem_id)
            .first()
        )
        if progress:
            progress.hint_count = (progress.hint_count or 0) + 1

        self.db.commit()
        return result

    async def generate_hint_stream(
        self,
        problem_id: int,
        level: int = 1,
        user_code: Optional[str] = None,
        user_id: int = 1,
    ):
        """流式生成解题提示（异步生成器）。"""
        if level not in (1, 2, 3):
            raise ValueError("hint_level must be 1, 2, or 3")

        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        profile = (
            self.db.query(LearningProfile)
            .filter(LearningProfile.user_id == user_id)
            .first()
        )

        # 记录行为（不等待流结束）
        behavior = UserBehavior(
            user_id=self._uid_or_none(user_id),
            problem_id=problem_id,
            action_type="hint_stream",
            action_data=json.dumps({"hint_level": level}),
        )
        self.db.add(behavior)

        from app.models.progress import Progress
        progress = (
            self.db.query(Progress)
            .filter(Progress.user_id == user_id, Progress.problem_id == problem_id)
            .first()
        )
        if progress:
            progress.hint_count = (progress.hint_count or 0) + 1
        self.db.commit()

        async for chunk in self.provider.generate_hint_stream(problem, level, user_code, profile):
            yield chunk

    async def review_code(
        self,
        problem_id: int,
        code: str,
        language: str = "python",
        user_id: int = 1,
    ) -> CodeReviewResult:
        """审查用户代码。"""
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        result = await self.provider.review_code(problem, code, language)

        log = AITutorLog(
            user_id=self._uid_or_none(user_id),
            problem_id=problem_id,
            request_type="review_code",
            prompt=f"language={language}, code_length={len(code)}",
            response=json.dumps(result.__dict__, ensure_ascii=False)[:2000],
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
        )
        self.db.add(log)
        self.db.commit()
        return result

    async def chat(
        self,
        problem_id: Optional[int],
        message: str,
        history: list[dict],
        user_code: Optional[str] = None,
        user_id: int = 1,
    ) -> HintResult:
        """自由对话：结合题目上下文与用户当前代码回答提问。"""
        problem = None
        if problem_id is not None:
            problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
            if not problem:
                raise ValueError(f"Problem {problem_id} not found")

        result = await self.provider.chat(problem, message, history, user_code)

        log = AITutorLog(
            user_id=self._uid_or_none(user_id),
            problem_id=problem_id,
            request_type="chat",
            prompt=message[:500],
            response=result.content[:2000],
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
        )
        self.db.add(log)
        self.db.commit()
        return result

    async def chat_stream(
        self,
        problem_id: Optional[int],
        message: str,
        history: list[dict],
        user_code: Optional[str] = None,
        user_id: int = 1,
    ):
        """流式自由对话：逐段 yield 文本，结束后落库日志。"""
        problem = None
        if problem_id is not None:
            problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
            if not problem:
                raise ValueError(f"Problem {problem_id} not found")

        start = time.time()
        parts: list[str] = []
        async for chunk in self.provider.chat_stream(problem, message, history, user_code):
            parts.append(chunk)
            yield chunk

        log = AITutorLog(
            user_id=self._uid_or_none(user_id),
            problem_id=problem_id,
            request_type="chat",
            prompt=message[:500],
            response="".join(parts)[:2000],
            tokens_used=0,
            latency_ms=int((time.time() - start) * 1000),
        )
        self.db.add(log)
        self.db.commit()

    def get_logs(self, user_id: int = 1, limit: int = 20) -> list[dict]:
        """获取 AI Tutor 交互历史。"""
        logs = (
            self.db.query(AITutorLog)
            .filter(AITutorLog.user_id == user_id)
            .order_by(AITutorLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "problem_id": log.problem_id,
                "request_type": log.request_type,
                "tokens_used": log.tokens_used,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
