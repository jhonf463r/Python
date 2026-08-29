"""Tests for lesson retrieval and decision gates."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import ActionRelevance, OperationalLesson
from iabv_v15.services.tools.lesson_retrieval import (
    LessonRetrieval,
    RetrievalContext,
    RetrievalResult,
    VERIFIED_LESSONS,
)
from iabv_v15.services.tools.tool_memory import ToolMemory


# ---------------------------------------------------------------------------
# Lesson model tests
# ---------------------------------------------------------------------------

class TestOperationalLesson:
    def test_matches_goal_with_pattern(self) -> None:
        lesson = OperationalLesson(
            rule="Test rule",
            goal_patterns=["external", "devin"],
        )
        assert lesson.matches_goal("external tool execution") is True
        assert lesson.matches_goal("devin api call") is True
        assert lesson.matches_goal("local operation") is False

    def test_matches_goal_without_pattern(self) -> None:
        lesson = OperationalLesson(rule="Test rule")
        assert lesson.matches_goal("any goal") is True

    def test_matches_tool_with_pattern(self) -> None:
        lesson = OperationalLesson(
            rule="Test rule",
            tool_patterns=["devin_api", "external"],
        )
        assert lesson.matches_tool("devin_api") is True
        assert lesson.matches_tool("external_assistant") is True
        assert lesson.matches_tool("ollama_llm") is False

    def test_matches_action_with_pattern(self) -> None:
        lesson = OperationalLesson(
            rule="Test rule",
            action_patterns=["run", "execute"],
        )
        assert lesson.matches_action("run tool") is True
        assert lesson.matches_action("execute command") is True
        assert lesson.matches_action("validate") is False

    def test_is_applicable_all_filters(self) -> None:
        lesson = OperationalLesson(
            rule="Test rule",
            goal_patterns=["external"],
            tool_patterns=["devin_api"],
            action_patterns=["run"],
            active=True,
        )
        assert lesson.is_applicable(
            goal="external task",
            tool_id="devin_api",
            action="run",
        ) is True

    def test_is_applicable_inactive(self) -> None:
        lesson = OperationalLesson(
            rule="Test rule",
            active=False,
        )
        assert lesson.is_applicable() is False

    def test_is_applicable_goal_mismatch(self) -> None:
        lesson = OperationalLesson(
            rule="Test rule",
            goal_patterns=["external"],
            active=True,
        )
        assert lesson.is_applicable(goal="local task") is False


# ---------------------------------------------------------------------------
# Lesson retrieval tests
# ---------------------------------------------------------------------------

class TestLessonRetrieval:
    def test_load_lessons(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(rule="Test 1"),
            OperationalLesson(rule="Test 2"),
        ]
        retrieval.load_lessons(lessons)
        assert retrieval.get_lesson_count() == 2

    def test_cache_validity(self) -> None:
        retrieval = LessonRetrieval(cache_ttl_seconds=1.0)
        assert retrieval.is_cache_valid() is False

        retrieval.load_lessons([OperationalLesson(rule="Test")])
        assert retrieval.is_cache_valid() is True

    def test_retrieve_relevant_lessons_filters_by_applicability(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(
                rule="External lesson",
                goal_patterns=["external"],
                active=True,
            ),
            OperationalLesson(
                rule="Local lesson",
                goal_patterns=["local"],
                active=True,
            ),
            OperationalLesson(
                rule="Inactive lesson",
                goal_patterns=["external"],
                active=False,
            ),
        ]
        retrieval.load_lessons(lessons)

        context = RetrievalContext(goal="external task")
        result = retrieval.retrieve_relevant_lessons(context)

        assert len(result.lessons) == 1
        assert result.lessons[0].rule == "External lesson"
        assert result.filtered_by_applicability is True

    def test_retrieve_relevant_lessons_filters_by_risk(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(rule="Low risk", risk_level="low", active=True),
            OperationalLesson(rule="High risk", risk_level="high", active=True),
            OperationalLesson(rule="Critical risk", risk_level="critical", active=True),
        ]
        retrieval.load_lessons(lessons)

        context = RetrievalContext()
        result = retrieval.retrieve_relevant_lessons(context, min_risk_level="high")

        assert len(result.lessons) == 2
        assert result.filtered_by_risk is True
        assert all(l.risk_level in ("high", "critical") for l in result.lessons)

    def test_retrieve_relevant_lessons_limits_results(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(rule=f"Lesson {i}", confidence=0.9, active=True)
            for i in range(10)
        ]
        retrieval.load_lessons(lessons)

        context = RetrievalContext()
        result = retrieval.retrieve_relevant_lessons(context, max_lessons=3)

        assert len(result.lessons) == 3

    def test_retrieve_relevant_lessons_bounded_execution(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(rule=f"Lesson {i}", active=True)
            for i in range(100)
        ]
        retrieval.load_lessons(lessons)

        context = RetrievalContext()
        result = retrieval.retrieve_relevant_lessons(context)

        # Should complete quickly (< 10ms for 100 lessons)
        assert result.retrieval_time_ms < 10.0

    def test_retrieve_for_tool_convenience(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(
                rule="Devin lesson",
                tool_patterns=["devin_api"],
                active=True,
            ),
            OperationalLesson(
                rule="Ollama lesson",
                tool_patterns=["ollama_llm"],
                active=True,
            ),
        ]
        retrieval.load_lessons(lessons)

        result = retrieval.retrieve_for_tool("devin_api", goal="external task")

        assert len(result) == 1
        assert result[0].rule == "Devin lesson"

    def test_retrieve_for_high_risk_action(self) -> None:
        retrieval = LessonRetrieval()
        lessons = [
            OperationalLesson(
                rule="Git lesson",
                action_patterns=["checkout"],
                risk_level="critical",
                active=True,
            ),
            OperationalLesson(
                rule="Low risk lesson",
                action_patterns=["checkout"],
                risk_level="low",
                active=True,
            ),
        ]
        retrieval.load_lessons(lessons)

        result = retrieval.retrieve_for_high_risk_action("checkout")

        # Should only return high/critical risk lessons
        assert len(result) == 1
        assert result[0].risk_level == "critical"

    def test_clear_cache(self) -> None:
        retrieval = LessonRetrieval()
        retrieval.load_lessons([OperationalLesson(rule="Test")])
        assert retrieval.get_lesson_count() == 1

        retrieval.clear_cache()
        assert retrieval.get_lesson_count() == 0


# ---------------------------------------------------------------------------
# Verified lessons tests
# ---------------------------------------------------------------------------

class TestVerifiedLessons:
    def test_verified_lessons_populated(self) -> None:
        assert len(VERIFIED_LESSONS) > 0

    def test_verified_lessons_have_required_fields(self) -> None:
        for lesson in VERIFIED_LESSONS:
            assert lesson.rule
            assert lesson.context
            assert lesson.risk_level in ("low", "medium", "high", "critical")
            assert lesson.evidence_level in ("unverified", "verified", "strong")
            assert lesson.source == "Codex cross-agent audit"

    def test_devin_specific_lessons_exist(self) -> None:
        devin_lessons = [
            lesson for lesson in VERIFIED_LESSONS
            if "devin" in lesson.rule.lower() or "devin" in str(lesson.tool_patterns).lower()
        ]
        assert len(devin_lessons) > 0

    def test_git_source_truth_lessons_exist(self) -> None:
        git_lessons = [
            lesson for lesson in VERIFIED_LESSONS
            if "git" in lesson.rule.lower() or "source" in lesson.rule.lower()
        ]
        assert len(git_lessons) > 0


# ---------------------------------------------------------------------------
# Action relevance tests
# ---------------------------------------------------------------------------

class TestActionRelevance:
    def test_action_relevance_model(self) -> None:
        relevance = ActionRelevance(
            current_goal="Fix bug",
            action="Run devin",
            why_relevant="Devin can fix bugs",
            expected_effect="Bug fixed",
            resource_cost="high",
            risk="medium",
            reversibility="reversible",
        )
        assert relevance.relevance_id
        assert relevance.current_goal == "Fix bug"

    def test_is_authorized_by_lessons_no_lessons(self) -> None:
        relevance = ActionRelevance(current_goal="Test", action="Test")
        assert relevance.is_authorized_by_lessons([]) is True

    def test_is_authorized_by_lessons_no_blocking(self) -> None:
        relevance = ActionRelevance(current_goal="Test", action="Test")
        lessons = [
            OperationalLesson(rule="Informational lesson", risk_level="low", active=True),
        ]
        assert relevance.is_authorized_by_lessons(lessons) is True

    def test_is_authorized_by_lessons_blocking(self) -> None:
        relevance = ActionRelevance(current_goal="Test", action="Test")
        lessons = [
            OperationalLesson(
                rule="BLOCK this action",
                risk_level="high",
                active=True,
            ),
        ]
        assert relevance.is_authorized_by_lessons(lessons) is False


# ---------------------------------------------------------------------------
# ToolMemory integration tests
# ---------------------------------------------------------------------------

class TestToolMemoryLessonIntegration:
    def test_record_action_relevance(self) -> None:
        mock_repo = MagicMock()
        memory = ToolMemory(repository=mock_repo)

        relevance = ActionRelevance(
            current_goal="Test goal",
            action="Test action",
        )

        result = memory.record_action_relevance(relevance)

        assert result.current_goal == "Test goal"
        mock_repo.log_execution.assert_called_once()

    def test_record_lesson_application(self) -> None:
        mock_repo = MagicMock()
        memory = ToolMemory(repository=mock_repo)

        memory.record_lesson_application(
            lesson_id="lesson-1",
            goal="Test goal",
            tool_id="devin_api",
            action="run",
            outcome="success",
            confidence_before=0.5,
            confidence_after=0.8,
        )

        mock_repo.log_execution.assert_called_once()
        call_args = mock_repo.log_execution.call_args
        assert call_args[1]['tool_id'] == "lesson_application"
        assert call_args[1]['task_id'] == "lesson-1"


# ---------------------------------------------------------------------------
# ToolTeachService integration tests
# ---------------------------------------------------------------------------

class TestToolTeachServiceLessonGate:
    def test_retrieve_lessons_for_decision(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService
        from iabv_v15.services.tools.tool_registry import ToolRegistry

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

        lessons = service._retrieve_lessons_for_decision(
            goal="external task",
            tool_id="devin_api",
            action="run",
            action_risk="medium",
        )

        # Should return lessons matching the context
        assert isinstance(lessons, list)

    def test_check_high_risk_source_truth_blocking(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService
        from iabv_v15.services.tools.tool_registry import ToolRegistry

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

        # Git checkout should be blocked by source-truth lessons
        allowed, blocking = service._check_high_risk_source_truth(
            action="checkout",
            goal="switch branch",
        )

        assert allowed is False
        assert len(blocking) > 0

    def test_check_high_risk_source_truth_allowed(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService
        from iabv_v15.services.tools.tool_registry import ToolRegistry

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

        # Non-source-truth action should be allowed
        allowed, blocking = service._check_high_risk_source_truth(
            action="validate",
            goal="check tool",
        )

        assert allowed is True
        assert len(blocking) == 0
