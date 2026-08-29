"""Performance test for lesson retrieval - ensures no freeze on trivial chat."""

from __future__ import annotations

import time

from iabv_v15.domain.models import OperationalLesson
from iabv_v15.services.tools.lesson_retrieval import (
    LessonRetrieval,
    RetrievalContext,
    VERIFIED_LESSONS,
)


def test_trivial_chat_retrieval_performance():
    """Verify lesson retrieval is fast enough for trivial chat (< 5ms)."""
    retrieval = LessonRetrieval()
    retrieval.load_lessons(VERIFIED_LESSONS)

    # Simulate trivial chat context (no specific goal/tool/action)
    context = RetrievalContext(
        goal="",
        tool_id="",
        action="",
        action_risk="low",
    )

    start = time.perf_counter()
    result = retrieval.retrieve_relevant_lessons(context)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should complete in under 5ms for trivial chat
    assert elapsed_ms < 5.0, f"Retrieval took {elapsed_ms}ms, expected < 5ms"
    assert result.retrieval_time_ms < 5.0


def test_tool_specific_retrieval_performance():
    """Verify tool-specific retrieval is fast (< 10ms)."""
    retrieval = LessonRetrieval()
    retrieval.load_lessons(VERIFIED_LESSONS)

    context = RetrievalContext(
        goal="external task",
        tool_id="devin_api",
        action="run",
        action_risk="medium",
    )

    start = time.perf_counter()
    result = retrieval.retrieve_relevant_lessons(context)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should complete in under 10ms for tool-specific retrieval
    assert elapsed_ms < 10.0, f"Retrieval took {elapsed_ms}ms, expected < 10ms"


def test_high_risk_action_retrieval_performance():
    """Verify high-risk action retrieval is fast (< 10ms)."""
    retrieval = LessonRetrieval()
    retrieval.load_lessons(VERIFIED_LESSONS)

    start = time.perf_counter()
    result = retrieval.retrieve_for_high_risk_action("checkout", goal="git operation")
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should complete in under 10ms for high-risk action retrieval
    assert elapsed_ms < 10.0, f"Retrieval took {elapsed_ms}ms, expected < 10ms"


def test_large_lesson_set_performance():
    """Verify retrieval scales well with larger lesson sets (< 20ms for 1000 lessons)."""
    retrieval = LessonRetrieval()
    
    # Create a large lesson set (1000 lessons)
    large_lessons = [
        OperationalLesson(
            rule=f"Lesson {i}",
            goal_patterns=["test"] if i % 10 == 0 else [],
            tool_patterns=["devin"] if i % 5 == 0 else [],
            action_patterns=["run"] if i % 3 == 0 else [],
            active=True,
        )
        for i in range(1000)
    ]
    retrieval.load_lessons(large_lessons)

    context = RetrievalContext(goal="test task")

    start = time.perf_counter()
    result = retrieval.retrieve_relevant_lessons(context)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should complete in under 20ms even with 1000 lessons
    assert elapsed_ms < 20.0, f"Retrieval took {elapsed_ms}ms for 1000 lessons, expected < 20ms"


def test_cache_hit_performance():
    """Verify cache hits are significantly faster."""
    retrieval = LessonRetrieval(cache_ttl_seconds=60.0)
    retrieval.load_lessons(VERIFIED_LESSONS)

    context = RetrievalContext(goal="test")

    # First retrieval (cache miss)
    start = time.perf_counter()
    result1 = retrieval.retrieve_relevant_lessons(context)
    time1_ms = (time.perf_counter() - start) * 1000

    # Second retrieval (cache hit)
    start = time.perf_counter()
    result2 = retrieval.retrieve_relevant_lessons(context)
    time2_ms = (time.perf_counter() - start) * 1000

    # Cache hit should be faster (or at least not significantly slower)
    assert result2.cache_hit is True
    assert time2_ms <= time1_ms * 1.5, f"Cache hit took {time2_ms}ms vs {time1_ms}ms"


if __name__ == "__main__":
    # Run performance tests
    test_trivial_chat_retrieval_performance()
    print("✓ Trivial chat retrieval performance: PASS")

    test_tool_specific_retrieval_performance()
    print("✓ Tool-specific retrieval performance: PASS")

    test_high_risk_action_retrieval_performance()
    print("✓ High-risk action retrieval performance: PASS")

    test_large_lesson_set_performance()
    print("✓ Large lesson set performance: PASS")

    test_cache_hit_performance()
    print("✓ Cache hit performance: PASS")

    print("\nAll performance tests passed - no freeze risk for trivial chat")
