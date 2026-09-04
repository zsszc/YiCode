"""
Phase 2 测试 — AI Tutor + Learning Profile + Feishu Bot
使用 pytest-asyncio 运行异步测试。
"""

import pytest
import asyncio
from datetime import date, datetime, timedelta

from app.models.problem import Problem
from app.models.progress import Progress
from app.models.user_behavior import UserBehavior
from app.models.learning_profile import LearningProfile
from app.models.ai_tutor_log import AITutorLog
from app.services.ai_tutor_service import AITutorService, MockLLMProvider
from app.services.learning_profile_service import LearningProfileService


# Helper to run async in sync context
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ============ AI Tutor Service Tests ============

class TestAITutorHint:
    @pytest.mark.asyncio
    async def test_hint_level_1(self, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.commit()

        service = AITutorService(db_session)
        result = await service.generate_hint(problem_id=1, level=1)
        assert result.content
        assert result.tokens_used > 0

    @pytest.mark.asyncio
    async def test_hint_level_3(self, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.commit()

        service = AITutorService(db_session)
        result = await service.generate_hint(problem_id=1, level=3)
        assert result.content
        assert len(result.content) > 10

    @pytest.mark.asyncio
    async def test_hint_invalid_level(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        service = AITutorService(db_session)
        with pytest.raises(ValueError):
            await service.generate_hint(problem_id=1, level=5)

    @pytest.mark.asyncio
    async def test_hint_records_behavior(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        service = AITutorService(db_session)
        await service.generate_hint(problem_id=1, level=1)

        # 验证行为记录
        behaviors = db_session.query(UserBehavior).all()
        assert len(behaviors) == 1
        assert behaviors[0].action_type == "hint"

        # 验证日志记录
        logs = db_session.query(AITutorLog).all()
        assert len(logs) == 1
        assert logs[0].request_type == "hint"

    @pytest.mark.asyncio
    async def test_hint_updates_progress_hint_count(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.add(Progress(problem_id=1, status="todo", hint_count=0))
        db_session.commit()

        service = AITutorService(db_session)
        await service.generate_hint(problem_id=1, level=1)

        progress = db_session.query(Progress).filter(Progress.problem_id == 1).first()
        assert progress.hint_count == 1


class TestAITutorCodeReview:
    @pytest.mark.asyncio
    async def test_review_code_basic(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        service = AITutorService(db_session)
        code = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target - num], i]
        seen[num] = i
"""
        result = await service.review_code(problem_id=1, code=code, language="python")
        assert result.rating >= 1 and result.rating <= 5
        assert result.time_complexity
        assert result.space_complexity
        assert result.overall_comment

    @pytest.mark.asyncio
    async def test_review_code_logs(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        service = AITutorService(db_session)
        await service.review_code(problem_id=1, code="print('hello')", language="python")

        logs = db_session.query(AITutorLog).all()
        assert len(logs) == 1
        assert logs[0].request_type == "review_code"

    @pytest.mark.asyncio
    async def test_review_code_not_found(self, db_session):
        service = AITutorService(db_session)
        with pytest.raises(ValueError):
            await service.review_code(problem_id=999, code="print('test')", language="python")


class TestAITutorLogs:
    def test_get_logs(self, db_session):
        db_session.add(AITutorLog(user_id=1, problem_id=1, request_type="hint", response="test"))
        db_session.add(AITutorLog(user_id=1, problem_id=2, request_type="hint", response="test2"))
        db_session.commit()

        service = AITutorService(db_session)
        logs = service.get_logs(limit=10)
        assert len(logs) == 2


# ============ Learning Profile Service Tests ============

class TestLearningProfile:
    def test_get_or_create(self, db_session):
        service = LearningProfileService(db_session)
        profile = service.get_or_create(user_id=1)
        assert profile.user_id == 1
        assert profile.streak_days == 0

    def test_get_or_create_returns_existing(self, db_session):
        db_session.add(LearningProfile(user_id=1, streak_days=5))
        db_session.commit()

        service = LearningProfileService(db_session)
        profile = service.get_or_create(user_id=1)
        assert profile.streak_days == 5

    def test_record_behavior(self, db_session):
        service = LearningProfileService(db_session)
        behavior = service.record_behavior(
            user_id=1, problem_id=1, action_type="open", action_data={"foo": "bar"}
        )
        assert behavior.action_type == "open"
        assert behavior.action_data == '{"foo": "bar"}'

    def test_analyze_patterns(self, db_session):
        now = datetime.now()
        for i in range(3):
            db_session.add(UserBehavior(
                user_id=1, problem_id=1, action_type="open",
                created_at=now - timedelta(days=i),
            ))
        for i in range(2):
            db_session.add(UserBehavior(
                user_id=1, problem_id=1, action_type="hint",
                created_at=now - timedelta(days=i),
            ))
        db_session.add(UserBehavior(
            user_id=1, problem_id=1, action_type="submit",
            created_at=now, action_data='{"solve_time_ms": 300000}',
        ))
        db_session.commit()

        service = LearningProfileService(db_session)
        analysis = service.analyze_patterns(user_id=1, days=7)

        assert analysis["period_days"] == 7
        assert analysis["action_counts"]["open"] == 3
        assert analysis["action_counts"]["hint"] == 2
        assert abs(analysis["hint_dependency_rate"] - 2 / 3) < 0.01
        assert analysis["avg_solve_time_ms"] == 300000
        assert "peak_hours" in analysis

    def test_adaptive_recommendation(self, db_session):
        db_session.add(LearningProfile(
            user_id=1, streak_days=14, hint_dependency_rate=0.2,
            first_try_success_rate=0.9, custom_quota_weekday=3,
        ))
        db_session.commit()

        service = LearningProfileService(db_session)
        rec = service.adaptive_recommendation(user_id=1)

        assert rec["quota_weekday"] == 5  # 3 + streak_bonus(2)
        assert rec["new_ratio"] == 0.8
        assert rec["hard_ratio"] == 0.2  # first_try_success_rate > 0.8
        assert "连续打卡" in rec["reasoning"]

    def test_adaptive_low_success_rate(self, db_session):
        db_session.add(LearningProfile(
            user_id=1, streak_days=0, hint_dependency_rate=0.8,
            first_try_success_rate=0.2,
        ))
        db_session.commit()

        service = LearningProfileService(db_session)
        rec = service.adaptive_recommendation(user_id=1)

        assert rec["new_ratio"] == 0.5  # hint_dependency_rate > 0.7
        assert rec["hard_ratio"] == 0.05  # first_try_success_rate < 0.3

    def test_update_profile(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.add(Progress(problem_id=1, user_id=1, status="solid", first_try=True, solve_time_ms=120000))
        db_session.add(UserBehavior(user_id=1, problem_id=1, action_type="open", created_at=datetime.now()))
        db_session.add(UserBehavior(user_id=1, problem_id=1, action_type="submit", created_at=datetime.now()))
        db_session.commit()

        service = LearningProfileService(db_session)
        profile = service.update_profile(user_id=1)

        assert profile.total_solved == 1
        assert profile.first_try_success_rate == 1.0
        assert profile.avg_solve_time_easy_ms == 120000

    def test_calculate_streak(self, db_session):
        now = datetime.now()
        db_session.add(UserBehavior(user_id=1, problem_id=1, action_type="submit", created_at=now))
        db_session.add(UserBehavior(
            user_id=1, problem_id=1, action_type="submit",
            created_at=now - timedelta(days=1),
        ))
        db_session.commit()

        service = LearningProfileService(db_session)
        streak = service._calculate_streak(user_id=1)
        assert streak["current"] == 2


# ============ API Integration Tests ============

class TestTutorAPI:
    def test_hint_api(self, client, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.commit()

        resp = client.post("/api/v1/tutor/hint", json={
            "problem_id": 1,
            "hint_level": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"]
        assert data["tokens_used"] > 0

    def test_review_code_api(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        resp = client.post("/api/v1/tutor/review-code", json={
            "problem_id": 1,
            "code": "def two_sum(nums, target):\n    return []",
            "language": "python",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] >= 1
        assert data["time_complexity"]

    def test_tutor_logs_api(self, client, db_session):
        db_session.add(AITutorLog(user_id=1, problem_id=1, request_type="hint", response="test"))
        db_session.commit()

        resp = client.get("/api/v1/tutor/logs?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestProfileAPI:
    def test_get_profile(self, client):
        resp = client.get("/api/v1/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 1
        assert "streak_days" in data

    def test_update_profile(self, client):
        resp = client.put("/api/v1/profile", json={
            "preferred_difficulty": "challenging",
            "custom_quota_weekday": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["preferred_difficulty"] == "challenging"
        assert data["custom_quota_weekday"] == 5

    def test_adaptive_recommendation(self, client):
        resp = client.get("/api/v1/profile/adaptive")
        assert resp.status_code == 200
        data = resp.json()
        assert "quota_weekday" in data
        assert "reasoning" in data

    def test_record_behavior(self, client):
        resp = client.post("/api/v1/profile/behaviors", json={
            "problem_id": 1,
            "action_type": "open",
            "action_data": {"page": "detail"},
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestFeishuAPI:
    def test_feishu_challenge(self, client):
        resp = client.post("/api/v1/feishu/webhook", json={
            "type": "url_verification",
            "challenge": "test-challenge-123",
        })
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "test-challenge-123"

    def test_feishu_dashboard(self, client, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.commit()

        resp = client.post("/api/v1/feishu/webhook", json={
            "event": {"text": "今日看板", "open_id": "user1"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["msg_type"] == "interactive"
        assert "看板" in data["card"]["header"]["title"]["content"]

    def test_feishu_help(self, client):
        resp = client.post("/api/v1/feishu/webhook", json={
            "event": {"text": "帮助", "open_id": "user1"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["msg_type"] == "interactive"
        assert "帮助" in data["card"]["header"]["title"]["content"]

    def test_feishu_unknown(self, client):
        resp = client.post("/api/v1/feishu/webhook", json={
            "event": {"text": "未知命令", "open_id": "user1"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["msg_type"] == "text"
