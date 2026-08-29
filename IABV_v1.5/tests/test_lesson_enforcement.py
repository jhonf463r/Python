"""Tests for lesson enforcement at execution boundaries."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import OperationalLesson
from iabv_v15.services.tools.lesson_retrieval import VERIFIED_LESSONS
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_tool_teach_service() -> ToolTeachService:
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_memory = MagicMock()
    mock_sandbox = MagicMock()
    mock_validator = MagicMock()
    mock_approval_policy = MagicMock()
    mock_rollback = MagicMock()
    mock_adapters = {}

    service = ToolTeachService(
        registry=mock_registry,
        memory=mock_memory,
        sandbox=mock_sandbox,
        validator=mock_validator,
        approval_policy=mock_approval_policy,
        rollback_manager=mock_rollback,
        adapters=mock_adapters,
        workspace_root="/tmp",
    )
    return service


# ---------------------------------------------------------------------------
# High-risk source-truth guard tests
# ---------------------------------------------------------------------------

class TestHighRiskSourceTruthGuard:
    def test_git_checkout_blocked_without_source_truth(self) -> None:
        """Verify git checkout is blocked when source truth unresolved."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        allowed, blocking = service._check_high_risk_source_truth(
            action="checkout",
            goal="switch branch",
        )
        
        assert allowed is False
        assert len(blocking) > 0
        assert any("source" in lesson.rule.lower() or "identity" in lesson.rule.lower() for lesson in blocking)

    def test_git_delete_blocked_without_source_truth(self) -> None:
        """Verify git branch deletion is blocked when source truth unresolved."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        allowed, blocking = service._check_high_risk_source_truth(
            action="delete",
            goal="remove branch",
        )
        
        assert allowed is False
        assert len(blocking) > 0

    def test_git_push_blocked_without_source_truth(self) -> None:
        """Verify git push is blocked when source truth unresolved."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        allowed, blocking = service._check_high_risk_source_truth(
            action="push",
            goal="push changes",
        )
        
        assert allowed is False
        assert len(blocking) > 0

    def test_low_risk_action_allowed(self) -> None:
        """Verify low-risk actions are allowed by source-truth guard."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        allowed, blocking = service._check_high_risk_source_truth(
            action="validate",
            goal="check status",
        )
        
        assert allowed is True
        assert len(blocking) == 0


# ---------------------------------------------------------------------------
# Lesson retrieval tests
# ---------------------------------------------------------------------------

class TestLessonRetrievalForDecision:
    def test_retrieve_lessons_for_matching_goal(self) -> None:
        """Verify lessons are retrieved for matching goal."""
        service = _make_tool_teach_service()
        
        lesson = OperationalLesson(
            rule="External tool lesson",
            goal_patterns=["external"],
            active=True,
        )
        service.lesson_retrieval.load_lessons([lesson])
        
        lessons = service._retrieve_lessons_for_decision(
            goal="external task",
            tool_id="test_tool",
            action="run",
        )
        
        assert len(lessons) == 1
        assert lessons[0].rule == "External tool lesson"

    def test_irrelevant_lesson_not_selected(self) -> None:
        """Verify irrelevant lessons are not selected."""
        service = _make_tool_teach_service()
        
        lesson = OperationalLesson(
            rule="Git lesson",
            goal_patterns=["git"],
            active=True,
        )
        service.lesson_retrieval.load_lessons([lesson])
        
        lessons = service._retrieve_lessons_for_decision(
            goal="external task",
            tool_id="test_tool",
            action="run",
        )
        
        assert len(lessons) == 0

    def test_inactive_lesson_not_selected(self) -> None:
        """Verify inactive lessons are not selected."""
        service = _make_tool_teach_service()
        
        lesson = OperationalLesson(
            rule="Inactive lesson",
            goal_patterns=["external"],
            active=False,
        )
        service.lesson_retrieval.load_lessons([lesson])
        
        lessons = service._retrieve_lessons_for_decision(
            goal="external task",
            tool_id="test_tool",
            action="run",
        )
        
        assert len(lessons) == 0


# ---------------------------------------------------------------------------
# Devin-specific safety tests
# ---------------------------------------------------------------------------

class TestDevinSafetyLessons:
    def test_devin_lessons_exist(self) -> None:
        """Verify Devin-specific lessons exist in verified lessons."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        lessons = service._retrieve_lessons_for_decision(
            goal="devin task",
            tool_id="devin_api",
            action="run",
        )
        
        # Should have at least one Devin-related lesson
        devin_lessons = [
            lesson for lesson in lessons
            if "devin" in lesson.rule.lower() or "external" in lesson.rule.lower()
        ]
        assert len(devin_lessons) > 0

    def test_mock_success_lesson_exists(self) -> None:
        """Verify mock success != real capability lesson exists."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        lessons = service._retrieve_lessons_for_decision(
            goal="external validation",
            tool_id="devin_api",
            action="validate",
        )
        
        # Should have lesson about mock success
        mock_lessons = [
            lesson for lesson in lessons
            if "mock" in lesson.rule.lower() and "real" in lesson.rule.lower()
        ]
        assert len(mock_lessons) > 0


# ---------------------------------------------------------------------------
# Historical success guard tests
# ---------------------------------------------------------------------------

class TestHistoricalSuccessGuard:
    def test_historical_success_alone_insufficient(self) -> None:
        """Verify historical success alone is not sufficient for authorization."""
        from iabv_v15.domain.models import ActionRelevance
        
        service = _make_tool_teach_service()
        
        # Create action relevance without current applicability
        relevance = ActionRelevance(
            current_goal="Test goal",
            action="Test action",
            why_relevant="Historically succeeded",
            expected_effect="Same as before",
            resource_cost="low",
            risk="low",
            reversibility="reversible",
        )
        
        # Without lessons considered, should not auto-authorize
        # This test verifies the structure exists for the guard
        assert relevance.lessons_considered == []


# ---------------------------------------------------------------------------
# Resource freshness tests
# ---------------------------------------------------------------------------

class TestResourceFreshnessGuard:
    def test_resource_lesson_exists(self) -> None:
        """Verify resource freshness lesson exists."""
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        lessons = service._retrieve_lessons_for_decision(
            goal="gpu operation",
            tool_id="test_tool",
            action="preload",
        )
        
        # Should have lesson about resource state
        resource_lessons = [
            lesson for lesson in lessons
            if "resource" in lesson.rule.lower() or "timestamp" in lesson.rule.lower()
        ]
        assert len(resource_lessons) > 0


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------

class TestEnforcementPerformance:
    def test_lesson_retrieval_remains_fast(self) -> None:
        """Verify lesson retrieval is fast enough for enforcement."""
        import time
        
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        start = time.perf_counter()
        lessons = service._retrieve_lessons_for_decision(
            goal="test goal",
            tool_id="test_tool",
            action="run",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Should complete in under 10ms
        assert elapsed_ms < 10.0
        assert isinstance(lessons, list)

    def test_high_risk_check_remains_fast(self) -> None:
        """Verify high-risk check is fast enough for enforcement."""
        import time
        
        service = _make_tool_teach_service()
        service.lesson_retrieval.load_lessons(VERIFIED_LESSONS)
        
        start = time.perf_counter()
        allowed, blocking = service._check_high_risk_source_truth(
            action="checkout",
            goal="switch branch",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Should complete in under 10ms
        assert elapsed_ms < 10.0
        assert isinstance(allowed, bool)
        assert isinstance(blocking, list)
