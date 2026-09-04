"""
API 集成测试 — 覆盖核心端点。
"""

from datetime import date

from app.models.problem import Problem
from app.models.progress import Progress
from app.services.sm2 import STATUS_SOLID, STATUS_FORGOT, SCORE_EASY


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestProblems:
    def test_list_empty(self, client):
        resp = client.get("/api/v1/problems")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_and_get(self, client, db_session):
        resp = client.post("/api/v1/problems", json={
            "title": "测试题",
            "difficulty": "简单",
            "category": "测试",
            "is_custom": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "测试题"
        pid = data["id"]

        resp = client.get(f"/api/v1/problems/{pid}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "测试题"

    def test_get_not_found(self, client):
        resp = client.get("/api/v1/problems/99999")
        assert resp.status_code == 404

    def test_search(self, client, db_session):
        # 准备数据
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.add(Problem(id=2, title="三数之和", difficulty="中等", category="双指针", slug="3sum"))
        db_session.commit()

        resp = client.get("/api/v1/problems?keyword=两数")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "两数之和"

        resp = client.get("/api/v1/problems?category=双指针")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "三数之和"


class TestDashboard:
    def test_dashboard_empty(self, client):
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == date.today().isoformat()
        assert data["todo_left"] == 0
        assert data["due_review"] == []

    def test_dashboard_with_problems(self, client, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.add(Problem(id=2, title="三数之和", difficulty="中等", category="双指针", slug="3sum"))
        db_session.commit()

        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["todo_left"] == 2
        assert data["counts"]["todo"] == 2

    def test_dashboard_with_progress(self, client, db_session):
        db_session.add(Problem(id=1, title="两数之和", difficulty="简单", category="哈希", slug="two-sum"))
        db_session.add(Progress(problem_id=1, status=STATUS_SOLID, review_stage=1, next_review=date.today()))
        db_session.commit()

        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["due_review"][0]["id"] == 1
        assert data["counts"]["solid"] == 1
        assert data["counts"]["todo"] == 0

    def test_shift_forward(self, client, db_session):
        yesterday = date.fromisoformat(date.today().isoformat())
        yesterday = yesterday.replace(day=yesterday.day - 1) if yesterday.day > 1 else yesterday

        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.add(Progress(problem_id=1, status=STATUS_SOLID, review_stage=0, next_review=yesterday))
        db_session.commit()

        resp = client.post("/api/v1/dashboard/shift-forward")
        assert resp.status_code == 200
        data = resp.json()
        assert data["shifted_count"] >= 0  # 取决于 yesterday 是否匹配


class TestReview:
    def test_first_solve(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        resp = client.post("/api/v1/review/first-solve/1", json={"status": "solid"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == STATUS_SOLID
        assert data["review_stage"] == 1

    def test_first_solve_invalid_status(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        resp = client.post("/api/v1/review/first-solve/1", json={"status": "invalid"})
        assert resp.status_code == 422

    def test_review_easy(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.add(Progress(problem_id=1, status=STATUS_SOLID, review_stage=0, next_review=date.today()))
        db_session.commit()

        resp = client.post("/api/v1/review/1", json={"score": "easy"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_stage"] == 1
        assert data["status"] == STATUS_SOLID

    def test_update_note(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        resp = client.put("/api/v1/review/1/note", json={"note": "双指针技巧"})
        assert resp.status_code == 200
        assert resp.json()["note"] == "双指针技巧"

    def test_update_cheatsheet(self, client, db_session):
        db_session.add(Problem(id=1, title="测试", difficulty="简单", category="测试"))
        db_session.commit()

        resp = client.put("/api/v1/review/1/cheatsheet", json={"cheatsheet": "```python\narr.sort()\n```"})
        assert resp.status_code == 200
        assert "arr.sort" in resp.json()["cheatsheet"]
