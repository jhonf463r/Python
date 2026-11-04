"""Regression contract for Space-Time recommendation provenance."""

from __future__ import annotations

from datetime import datetime, timezone

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
)
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler


class _RecommendationRepository:
    def __init__(self, recommendation: ExperimentRecommendation) -> None:
        self.recommendation = recommendation

    def list_recommendations(self, *, domain: str, subject_key: str, limit: int):
        assert domain == self.recommendation.domain.value
        assert subject_key == self.recommendation.subject_key
        assert limit == 3
        return [self.recommendation]


class _RecommendationProbeAssembler(TaskContextAssembler):
    def _inferred_experiment_domains(self, user_goal: str):
        return [ExperimentDomain.ALGORITHM]

    def _experiment_subject_keys(self, *, site_id, goal_context, user_goal):
        return ["space-time-scope"]


def test_recent_experiment_insight_preserves_original_creation_time() -> None:
    created_at = datetime(2026, 10, 1, 12, 30, tzinfo=timezone.utc)
    recommendation = ExperimentRecommendation(
        domain=ExperimentDomain.ALGORITHM,
        subject_key="space-time-scope",
        recommended_route=EvaluationRoute.LOCAL,
        created_at_utc=created_at,
    )
    assembler = object.__new__(_RecommendationProbeAssembler)
    assembler.experiment_lab_repository = _RecommendationRepository(recommendation)
    insights = assembler._recent_experiment_insights(
        site_id="site-1",
        user_goal="algorithm optimization",
        goal_context=None,
    )

    assert len(insights) == 1
    assert insights[0]["created_at_utc"] == created_at.isoformat()
