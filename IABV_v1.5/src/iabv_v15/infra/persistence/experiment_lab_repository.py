from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import ExperimentRecommendation, ExperimentRun
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ExperimentLabRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save_run(self, run: ExperimentRun) -> ExperimentRun:
        relative_path = f"experiment_runs/{run.run_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, run.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO experiment_runs
            (run_id, domain, suite_name, subject_key, route, success, score, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.domain.value,
                run.suite_name,
                run.subject_key,
                run.route.value,
                int(run.success),
                float(run.metrics.total_score),
                saved_path,
                run.created_at_utc.isoformat(),
            ),
        )
        return run

    def list_runs(
        self,
        *,
        domain: str | None = None,
        route: str | None = None,
        subject_key: str | None = None,
        limit: int = 20,
    ) -> list[ExperimentRun]:
        sql = 'SELECT run_id, path FROM experiment_runs'
        clauses: list[str] = []
        params: list[object] = []
        if domain:
            clauses.append('domain = ?')
            params.append(domain)
        if route:
            clauses.append('route = ?')
            params.append(route)
        if subject_key:
            clauses.append('subject_key = ?')
            params.append(subject_key)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY created_at_utc DESC LIMIT ?'
        params.append(limit)
        rows = self.db.fetchall(sql, tuple(params))
        items: list[ExperimentRun] = []
        for row in rows:
            loaded = self._load_run_optional(row['run_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def save_recommendation(self, recommendation: ExperimentRecommendation) -> ExperimentRecommendation:
        relative_path = f"experiment_recommendations/{recommendation.recommendation_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, recommendation.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO experiment_recommendations
            (recommendation_id, domain, subject_key, recommended_route, score, path, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recommendation.recommendation_id,
                recommendation.domain.value,
                recommendation.subject_key,
                recommendation.recommended_route.value,
                float(recommendation.score),
                saved_path,
                recommendation.created_at_utc.isoformat(),
            ),
        )
        return recommendation

    def list_recommendations(
        self,
        *,
        domain: str | None = None,
        subject_key: str | None = None,
        limit: int = 20,
    ) -> list[ExperimentRecommendation]:
        sql = 'SELECT recommendation_id, path FROM experiment_recommendations'
        clauses: list[str] = []
        params: list[object] = []
        if domain:
            clauses.append('domain = ?')
            params.append(domain)
        if subject_key:
            clauses.append('subject_key = ?')
            params.append(subject_key)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY created_at_utc DESC LIMIT ?'
        params.append(limit)
        rows = self.db.fetchall(sql, tuple(params))
        items: list[ExperimentRecommendation] = []
        for row in rows:
            loaded = self._load_recommendation_optional(row['recommendation_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def latest_recommendation(self, *, domain: str | None = None, subject_key: str | None = None) -> ExperimentRecommendation | None:
        items = self.list_recommendations(domain=domain, subject_key=subject_key, limit=1)
        return items[0] if items else None

    def _load_run(self, run_id: str, path: str) -> ExperimentRun:
        return ExperimentRun.model_validate(self._load_json(f'experiment_runs/{run_id}.json', path))

    def _load_recommendation(self, recommendation_id: str, path: str) -> ExperimentRecommendation:
        return ExperimentRecommendation.model_validate(self._load_json(f'experiment_recommendations/{recommendation_id}.json', path))

    def _load_run_optional(self, run_id: str, path: str) -> ExperimentRun | None:
        try:
            return self._load_run(run_id, path)
        except FileNotFoundError:
            return None

    def _load_recommendation_optional(self, recommendation_id: str, path: str) -> ExperimentRecommendation | None:
        try:
            return self._load_recommendation(recommendation_id, path)
        except FileNotFoundError:
            return None

    def _load_json(self, relative_path: str, path: str) -> dict[str, Any]:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            return json.loads(candidate.read_text(encoding='utf-8'))
        return self.storage.load_json(relative_path)
