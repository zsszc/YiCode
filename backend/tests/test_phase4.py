"""
Phase 4 测试 — AI Agent 自进化
"""

import pytest
from datetime import datetime, timedelta

from app.models.problem import Problem
from app.models.knowledge_graph import KnowledgeNode, ProblemKnowledge, UserKnowledgeMastery
from app.models.mistake_analysis import MistakeAnalysis
from app.services.self_evolution_service import SelfEvolutionService


class TestMistakeAnalysis:
    def test_analyze_hint_dependency(self, db_session):
        db_session.add(Problem(id=1, title="测试题", difficulty="中等", category="哈希"))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        result = service.analyze_mistake(
            user_id=1, problem_id=1, review_log_id=None,
            score="hard", hint_count=3, attempt_count=2, solve_time_ms=600000,
        )
        assert result.mistake_type == "hint_dependency"
        assert "过度依赖" in result.description

    def test_analyze_concept_gap(self, db_session):
        db_session.add(Problem(id=1, title="测试题", difficulty="困难", category="动态规划"))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        result = service.analyze_mistake(
            user_id=1, problem_id=1, review_log_id=None,
            score="hard", hint_count=0, attempt_count=5, solve_time_ms=300000,
        )
        assert result.mistake_type == "concept_gap"

    def test_analyze_time_pressure(self, db_session):
        db_session.add(Problem(id=1, title="测试题", difficulty="简单", category="数组"))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        result = service.analyze_mistake(
            user_id=1, problem_id=1, review_log_id=None,
            score="ok", hint_count=0, attempt_count=2, solve_time_ms=900000,  # 15 min for easy
        )
        assert result.mistake_type == "time_pressure"

    def test_analyze_well_reviewed(self, db_session):
        db_session.add(Problem(id=1, title="测试题", difficulty="简单", category="数组"))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        result = service.analyze_mistake(
            user_id=1, problem_id=1, review_log_id=None,
            score="easy", hint_count=0, attempt_count=1, solve_time_ms=300000,
        )
        assert result.mistake_type == "reviewed_well"


class TestKnowledgeMastery:
    def test_mastery_increases_on_success(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="哈希"))
        db_session.add(KnowledgeNode(id=1, name="哈希表", category="数据结构"))
        db_session.add(ProblemKnowledge(problem_id=1, knowledge_id=1, importance=1.0))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        service.analyze_mistake(
            user_id=1, problem_id=1, review_log_id=None, score="easy",
            hint_count=0, attempt_count=1, solve_time_ms=300000,
        )

        mastery = db_session.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.knowledge_id == 1
        ).first()
        assert mastery is not None
        assert mastery.mastery_level > 0.3

    def test_mastery_decreases_on_failure(self, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="哈希"))
        db_session.add(KnowledgeNode(id=1, name="哈希表", category="数据结构"))
        db_session.add(ProblemKnowledge(problem_id=1, knowledge_id=1, importance=1.0))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        service.analyze_mistake(
            user_id=1, problem_id=1, review_log_id=None, score="hard",
            hint_count=0, attempt_count=1, solve_time_ms=300000,
        )

        mastery = db_session.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.knowledge_id == 1
        ).first()
        assert mastery.mastery_level < 0.3

    def test_mastery_report(self, db_session):
        db_session.add(KnowledgeNode(id=1, name="哈希表", category="数据结构"))
        db_session.add(KnowledgeNode(id=2, name="双指针", category="算法"))
        db_session.add(UserKnowledgeMastery(user_id=1, knowledge_id=1, mastery_level=0.2, total_attempts=5, correct_attempts=1))
        db_session.add(UserKnowledgeMastery(user_id=1, knowledge_id=2, mastery_level=0.9, total_attempts=10, correct_attempts=9))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        report = service.get_mastery_report(user_id=1)

        assert report["total_knowledge"] == 2
        assert len(report["weak_points"]) == 1
        assert report["weak_points"][0]["name"] == "哈希表"
        assert len(report["strong_points"]) == 1
        assert report["strong_points"][0]["name"] == "双指针"
        assert report["overall_mastery"] == 0.55


class TestLearningPath:
    def test_learning_path_with_weak_points(self, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希"))
        db_session.add(KnowledgeNode(id=1, name="哈希表", category="数据结构"))
        db_session.add(ProblemKnowledge(problem_id=1, knowledge_id=1))
        db_session.add(UserKnowledgeMastery(user_id=1, knowledge_id=1, mastery_level=0.2, total_attempts=3, correct_attempts=0))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        path = service.generate_learning_path(user_id=1)

        assert "薄弱" in path["message"] or "weak" in path["message"].lower()
        assert len(path["path"]) > 0
        assert path["path"][0]["knowledge"] == "哈希表"

    def test_learning_path_all_strong(self, db_session):
        db_session.add(KnowledgeNode(id=1, name="哈希表", category="数据结构"))
        db_session.add(UserKnowledgeMastery(user_id=1, knowledge_id=1, mastery_level=0.95, total_attempts=10, correct_attempts=9))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        path = service.generate_learning_path(user_id=1)

        assert "扎实" in path["message"] or "挑战" in path["message"]


class TestMistakeSummary:
    def test_summary(self, db_session):
        db_session.add(MistakeAnalysis(user_id=1, problem_id=1, mistake_type="concept_gap"))
        db_session.add(MistakeAnalysis(user_id=1, problem_id=2, mistake_type="edge_case"))
        db_session.add(MistakeAnalysis(user_id=1, problem_id=3, mistake_type="concept_gap"))
        db_session.commit()

        service = SelfEvolutionService(db_session)
        summary = service.get_mistake_summary(user_id=1, days=30)

        assert summary["total_analyzed"] == 3
        assert summary["type_distribution"]["concept_gap"] == 2
        assert summary["top_weakness"] == "concept_gap"


class TestEvolutionAPI:
    def test_analyze_mistake_api(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        resp = client.post("/api/v1/evolution/analyze-mistake/1?score=hard&hint_count=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mistake_type"] == "hint_dependency"

    def test_mastery_report_api(self, client):
        resp = client.get("/api/v1/evolution/mastery-report")
        assert resp.status_code == 200
        assert "total_knowledge" in resp.json()

    def test_learning_path_api(self, client):
        resp = client.get("/api/v1/evolution/learning-path")
        assert resp.status_code == 200
        assert "path" in resp.json()

    def test_mistake_summary_api(self, client):
        resp = client.get("/api/v1/evolution/mistake-summary?days=30")
        assert resp.status_code == 200
        assert "type_distribution" in resp.json()

    def test_learning_curve_api(self, client, db_session):
        db_session.add(KnowledgeNode(id=1, name="哈希表", category="数据结构"))
        db_session.add(UserKnowledgeMastery(user_id=1, knowledge_id=1, mastery_level=0.5, total_attempts=3, correct_attempts=2))
        db_session.commit()

        resp = client.get("/api/v1/evolution/learning-curve")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_review" in data
        assert "mastery_by_category" in data
        assert "stage_distribution" in data
        assert len(data["mastery_by_category"]) > 0


class TestTutorStreamAPI:
    def test_hint_stream_api(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="哈希"))
        db_session.commit()

        resp = client.get("/api/v1/tutor/hint-stream/1?level=1")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.content.decode("utf-8")
        assert "data:" in body
        assert "[DONE]" in body

    def test_hint_stream_invalid_level(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="哈希"))
        db_session.commit()

        resp = client.get("/api/v1/tutor/hint-stream/1?level=5")
        assert resp.status_code == 422


class TestCodeRunnerAPI:
    def test_run_code_success(self, client):
        resp = client.post("/api/v1/code/run", json={
            "code": "print('Hello, YiCode!')\nprint(2 + 3)",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Hello, YiCode!" in data["stdout"]
        assert "5" in data["stdout"]
        assert data["exit_code"] == 0
        assert data["timed_out"] is False

    def test_run_code_with_stdin(self, client):
        resp = client.post("/api/v1/code/run", json={
            "code": "name = input('name: ')\nprint(f'Hello {name}')",
            "stdin": "YiCode",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Hello YiCode" in data["stdout"]

    def test_run_code_syntax_error(self, client):
        resp = client.post("/api/v1/code/run", json={
            "code": "print('missing paren",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["exit_code"] != 0
        assert "SyntaxError" in data["stderr"] or "EOF" in data["stderr"]

    def test_run_code_timeout(self, client):
        resp = client.post("/api/v1/code/run", json={
            "code": "while True:\n    pass",
            "timeout": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["timed_out"] is True

    def test_run_code_banned_builtin(self, client):
        resp = client.post("/api/v1/code/run", json={
            "code": "eval('1+1')",
        })
        assert resp.status_code == 200
        data = resp.json()
        # eval 被删除后会报 NameError
        assert "NameError" in data["stderr"] or data["exit_code"] != 0

    def test_run_code_banned_import(self, client):
        resp = client.post("/api/v1/code/run", json={
            "code": "import os\nprint(os.getcwd())",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ImportError" in data["stderr"] or data["exit_code"] != 0
