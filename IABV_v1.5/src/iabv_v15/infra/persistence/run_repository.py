from __future__ import annotations

import json

from iabv_v15.domain.models import RunRecord
from iabv_v15.infra.persistence.database import AppDatabase


class RunRepository:
    def __init__(self, db: AppDatabase):
        self.db = db

    def record(self, run_record: RunRecord) -> RunRecord:
        self.db.execute(
            """
            INSERT OR REPLACE INTO run_records
            (run_id, request_json, result_json, route_json, status, created_at_utc, duration_ms, error_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_record.run_id,
                run_record.request.model_dump_json(),
                run_record.result.model_dump_json(),
                run_record.route.model_dump_json(),
                run_record.status.value,
                run_record.created_at_utc.isoformat(),
                run_record.duration_ms,
                run_record.error_summary,
            ),
        )
        return run_record

    def list_recent(self, limit: int = 30) -> list[RunRecord]:
        rows = self.db.fetchall(
            """
            SELECT run_id, request_json, result_json, route_json, status, created_at_utc, duration_ms, error_summary
            FROM run_records
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_model(row) for row in rows]

    def get(self, run_id: str) -> RunRecord | None:
        row = self.db.fetchone(
            """
            SELECT run_id, request_json, result_json, route_json, status, created_at_utc, duration_ms, error_summary
            FROM run_records
            WHERE run_id = ?
            """,
            (run_id,),
        )
        if row is None:
            return None
        return self._row_to_model(row)

    def _row_to_model(self, row) -> RunRecord:
        payload = {
            'run_id': row['run_id'],
            'request': json.loads(row['request_json']),
            'result': json.loads(row['result_json']),
            'route': json.loads(row['route_json']),
            'status': row['status'],
            'created_at_utc': row['created_at_utc'],
            'duration_ms': row['duration_ms'],
            'error_summary': row['error_summary'] or '',
        }
        return RunRecord.model_validate(payload)
