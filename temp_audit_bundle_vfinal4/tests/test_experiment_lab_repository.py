from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import EvaluationRoute, ExperimentDomain, ExperimentMetric, ExperimentRecommendation, ExperimentRun
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_experiment_lab_repository_round_trip() -> None:
    root = _workspace('experiment_lab_repository')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        repository = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), ArtifactStorage(str(root / 'evolution')))
        run = ExperimentRun(
            domain=ExperimentDomain.LANGUAGE,
            suite_name='text_understanding_suite',
            objective='Clasificar una intencion',
            subject_key='general',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='local language suite',
            success=True,
            expected_summary='clasificacion correcta',
            observed_summary='clasificacion correcta',
            metrics=ExperimentMetric(precision=0.92, execution_ms=42, operational_cost=0.05, robustness=0.81, reuse_score=0.6, total_score=0.81),
            metadata={'suite_name': 'text_understanding_suite'},
        )
        recommendation = ExperimentRecommendation(
            domain=ExperimentDomain.LANGUAGE,
            subject_key='general',
            recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            score=0.81,
            confidence=0.88,
            rationale='La comprension de lenguaje local viene dando mejores resultados.',
            supporting_run_ids=[run.run_id],
        )

        repository.save_run(run)
        repository.save_recommendation(recommendation)

        stored_runs = repository.list_runs(domain=ExperimentDomain.LANGUAGE.value, subject_key='general')
        stored_recommendations = repository.list_recommendations(domain=ExperimentDomain.LANGUAGE.value, subject_key='general')

        assert len(stored_runs) == 1
        assert stored_runs[0].metrics.total_score == 0.81
        assert stored_runs[0].route == EvaluationRoute.LANGUAGE_UNDERSTANDING
        assert len(stored_recommendations) == 1
        assert stored_recommendations[0].recommended_route == EvaluationRoute.LANGUAGE_UNDERSTANDING
        assert stored_recommendations[0].supporting_run_ids == [run.run_id]
    finally:
        shutil.rmtree(root, ignore_errors=True)
