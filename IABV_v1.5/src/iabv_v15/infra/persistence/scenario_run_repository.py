from __future__ import annotations

import json
from pathlib import Path

from iabv_v15.domain.models import ScenarioRun
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class ScenarioRunRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

    def save(self, scenario_run: ScenarioRun) -> ScenarioRun:
        relative_path = f"scenario_runs/{scenario_run.scenario_run_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, scenario_run.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO scenario_runs
            (scenario_run_id, run_id, session_id, scenario_id, mode, status, summary, path, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_run.scenario_run_id,
                scenario_run.run_id,
                scenario_run.session_id,
                scenario_run.scenario.scenario_id,
                scenario_run.mode.value,
                scenario_run.status.value,
                scenario_run.summary,
                saved_path,
                scenario_run.created_at_utc.isoformat(),
                scenario_run.updated_at_utc.isoformat(),
            ),
        )
        return scenario_run

    def list_recent(self, limit: int = 20) -> list[ScenarioRun]:
        rows = self.db.fetchall(
            """
            SELECT scenario_run_id, path
            FROM scenario_runs
            ORDER BY updated_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._load(row['scenario_run_id'], row['path']) for row in rows]

    def find_by_run(self, run_id: str) -> list[ScenarioRun]:
        rows = self.db.fetchall(
            """
            SELECT scenario_run_id, path
            FROM scenario_runs
            WHERE run_id = ?
            ORDER BY updated_at_utc DESC
            """,
            (run_id,),
        )
        return [self._load(row['scenario_run_id'], row['path']) for row in rows]

    def get(self, scenario_run_id: str) -> ScenarioRun | None:
        row = self.db.fetchone(
            """
            SELECT scenario_run_id, path
            FROM scenario_runs
            WHERE scenario_run_id = ?
            """,
            (scenario_run_id,),
        )
        if row is None:
            return None
        return self._load(row['scenario_run_id'], row['path'])

    def _load(self, scenario_run_id: str, path: str) -> ScenarioRun:
        candidate = Path(path)
        if candidate.is_absolute() and candidate.exists():
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        else:
            payload = self.storage.load_json(f'scenario_runs/{scenario_run_id}.json')
        return ScenarioRun.model_validate(payload)
