from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import ExperimentRecommendation, ExperimentRun, IATraceEntry
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
            (run_id, domain, suite_name, subject_key, route, success, score, path, metadata_json, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(run.metadata, ensure_ascii=False, default=str),
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

    def list_runs_by_scope_key(self, scope_key: str, *, limit: int = 20) -> list[ExperimentRun]:
        rows = self.db.fetchall(
            """
            SELECT run_id, path FROM experiment_runs
            WHERE json_extract(metadata_json, '$.comparison_scope_key') = ?
            ORDER BY created_at_utc DESC LIMIT ?
            """,
            (scope_key, limit),
        )
        items: list[ExperimentRun] = []
        for row in rows:
            loaded = self._load_run_optional(row['run_id'], row['path'])
            if loaded is not None:
                items.append(loaded)
        return items

    def list_candidate_traces_for_scope(self, scope_key: str, *, limit: int = 20) -> list[IATraceEntry]:
        traces: list[IATraceEntry] = []
        for run in self.list_runs_by_scope_key(scope_key, limit=limit):
            raw_trace = run.metadata.get('ia_trace_entry')
            if isinstance(raw_trace, dict):
                traces.append(IATraceEntry.model_validate(raw_trace))
                continue
            traces.append(
                IATraceEntry(
                    trace_id=str(run.metadata.get('trace_id') or run.run_id),
                    assistant_kind=str(run.assistant_kind or run.metadata.get('assistant_kind') or ''),
                    requested_assistant_kind=str(run.metadata.get('requested_assistant_kind') or run.assistant_kind or ''),
                    actual_assistant_kind=str(run.metadata.get('actual_assistant_kind') or run.assistant_kind or ''),
                    assistant_configuration=run.assistant_configuration,
                    config_signature=str(run.config_signature or run.metadata.get('config_signature') or ''),
                    comparison_scope_key=str(run.metadata.get('comparison_scope_key') or scope_key),
                    source_trace_ids=list(run.metadata.get('source_trace_ids') or []),
                    route=run.route.value,
                    tool_id=str(run.metadata.get('tool_id') or ''),
                    task_id=str(run.metadata.get('task_id') or ''),
                    result_id=str(run.metadata.get('result_id') or ''),
                    proposal_summary=str(run.metadata.get('proposal_summary') or run.objective or '')[:240],
                    outcome_summary=str(run.metadata.get('outcome_summary') or run.observed_summary or '')[:240],
                    result_label=str(run.candidate_label or run.metadata.get('result_label') or ''),
                    success=bool(run.success),
                    execution_ms=int(run.metrics.execution_ms or 0),
                    confidence=float(run.metrics.total_score or 0.0),
                    evidence_refs=list(run.evidence_refs or []),
                    reused_later=bool(run.reused_later),
                    metadata=dict(run.metadata or {}),
                )
            )
        return traces

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
