"""
TDD: SM-2 简化算法测试套件。

覆盖：
- next_review_date 计算
- apply_first_solve 状态流转
- apply_review 打分流转
- 边界条件（stage 越界、归档）
"""

from datetime import date
import pytest

from app.services.sm2 import (
    get_intervals,
    next_review_date,
    apply_first_solve,
    apply_review,
    default_progress_entry,
    STATUS_FORGOT,
    STATUS_SHAKY,
    STATUS_SOLID,
    STATUS_ARCHIVED,
    SCORE_EASY,
    SCORE_OK,
    SCORE_HARD,
)


class TestIntervals:
    def test_default_intervals(self):
        assert get_intervals() == [1, 3, 7, 15, 30]


class TestNextReviewDate:
    def test_stage_0(self):
        base = date(2026, 9, 4)
        assert next_review_date(0, base) == "2026-09-05"

    def test_stage_4(self):
        base = date(2026, 9, 4)
        assert next_review_date(4, base) == "2026-10-04"

    def test_stage_5_archived(self):
        assert next_review_date(5, date(2026, 9, 4)) is None

    def test_default_base_date(self):
        result = next_review_date(0)
        assert isinstance(result, str)
        # 应该是今天+1天


class TestApplyFirstSolve:
    def test_forgot(self):
        stage, nr, status = apply_first_solve(STATUS_FORGOT, date(2026, 9, 4))
        assert stage == 0
        assert status == STATUS_FORGOT
        assert nr == "2026-09-05"

    def test_shaky(self):
        stage, nr, status = apply_first_solve(STATUS_SHAKY, date(2026, 9, 4))
        assert stage == 0
        assert status == STATUS_SHAKY

    def test_solid(self):
        stage, nr, status = apply_first_solve(STATUS_SOLID, date(2026, 9, 4))
        assert stage == 1
        assert status == STATUS_SOLID
        assert nr == "2026-09-07"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            apply_first_solve("invalid")


class TestApplyReview:
    # ---- easy: stage +1 ----
    def test_easy_stage_0(self):
        stage, nr, status = apply_review(0, SCORE_EASY, date(2026, 9, 4))
        assert stage == 1
        assert status == STATUS_SOLID
        assert nr == "2026-09-07"

    def test_easy_stage_1(self):
        stage, nr, status = apply_review(1, SCORE_EASY, date(2026, 9, 4))
        assert stage == 2
        assert nr == "2026-09-11"

    def test_easy_stage_4_to_archive(self):
        stage, nr, status = apply_review(4, SCORE_EASY, date(2026, 9, 4))
        assert stage == 5
        assert status == STATUS_ARCHIVED
        assert nr is None

    # ---- ok: keep stage ----
    def test_ok_stage_2(self):
        stage, nr, status = apply_review(2, SCORE_OK, date(2026, 9, 4))
        assert stage == 2
        assert status == STATUS_SHAKY
        assert nr == "2026-09-11"

    # ---- hard: reset to 0 ----
    def test_hard_stage_3(self):
        stage, nr, status = apply_review(3, SCORE_HARD, date(2026, 9, 4))
        assert stage == 0
        assert status == STATUS_FORGOT
        assert nr == "2026-09-05"

    def test_hard_negative_stage(self):
        # stage < 0 应该被修正为 0
        stage, nr, status = apply_review(-1, SCORE_HARD, date(2026, 9, 4))
        assert stage == 0

    def test_invalid_score_raises(self):
        with pytest.raises(ValueError):
            apply_review(0, "invalid")


class TestDefaultProgressEntry:
    def test_structure(self):
        entry = default_progress_entry()
        assert entry["status"] == "todo"
        assert entry["review_stage"] == -1
        assert entry["note"] == ""
        assert entry["history"] == []
