from __future__ import annotations

from iabv_v15.domain.models import ExperimentMetric


class DecisionScoringEngine:
    def score(
        self,
        *,
        precision: float,
        execution_ms: int,
        operational_cost: float,
        robustness: float,
        reuse_score: float,
        user_progress: float = 0.0,
        metadata: dict | None = None,
    ) -> ExperimentMetric:
        latency_score = max(0.0, min(1.0, 1.0 - min(float(execution_ms), 5000.0) / 5000.0))
        cost_score = max(0.0, min(1.0, 1.0 - min(float(operational_cost), 1.0)))
        user_progress_score = max(0.0, min(float(user_progress), 1.0))
        total_score = (
            max(0.0, min(float(precision), 1.0)) * 0.35
            + max(0.0, min(float(robustness), 1.0)) * 0.22
            + max(0.0, min(float(reuse_score), 1.0)) * 0.15
            + latency_score * 0.12
            + cost_score * 0.08
            + user_progress_score * 0.08
        )
        return ExperimentMetric(
            precision=max(0.0, min(float(precision), 1.0)),
            execution_ms=max(int(execution_ms), 0),
            operational_cost=max(float(operational_cost), 0.0),
            robustness=max(0.0, min(float(robustness), 1.0)),
            reuse_score=max(0.0, min(float(reuse_score), 1.0)),
            user_progress=user_progress_score,
            total_score=round(total_score, 4),
            metadata={
                **(metadata or {}),
                'latency_score': round(latency_score, 4),
                'cost_score': round(cost_score, 4),
                'user_progress_score': round(user_progress_score, 4),
            },
        )
