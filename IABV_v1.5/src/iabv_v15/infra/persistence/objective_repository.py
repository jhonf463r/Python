from __future__ import annotations

import logging
from pathlib import Path
from threading import local
from typing import Iterable

from iabv_v15.domain.models import ObjectiveNode, ObjectiveNodeKind, ObjectiveStatus
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.read_results import (
    ArtifactReadResult,
    ArtifactReadStatus,
    RepositoryReadError,
    RepositoryReadReport,
    read_model_from_paths,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage

_log = logging.getLogger(__name__)


class ObjectiveRepository:
    """JSON payload repository indexed by SQLite.

    Ordinary reads are strictly non-destructive. An unreadable/missing payload
    is reported to the caller and never causes its SQLite index row to be
    pruned. The report scope is the selected SQLite rows, not a filesystem-wide
    inventory of unindexed objective JSON files.
    """

    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage
        self._read_state = local()

    @property
    def last_read_report(self) -> RepositoryReadReport[ObjectiveNode] | None:
        """Diagnostics for the most recent read on this thread."""
        return getattr(self._read_state, "report", None)

    def _remember_report(
        self, report: RepositoryReadReport[ObjectiveNode]
    ) -> RepositoryReadReport[ObjectiveNode]:
        self._read_state.report = report
        return report

    def save(self, node: ObjectiveNode) -> ObjectiveNode:
        if not node.root_id:
            node = node.model_copy(update={'root_id': node.objective_id if node.parent_id is None else node.root_id})
        relative_path = f"objectives/{node.objective_id}.json"
        saved_path = self.storage.save_json_atomic(relative_path, node.model_dump(mode='json'))
        self.db.execute(
            """
            INSERT OR REPLACE INTO objective_nodes
            (objective_id, kind, parent_id, root_id, site_id, status, priority, progress, title, path, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node.objective_id,
                node.kind.value,
                node.parent_id,
                node.root_id,
                node.site_id,
                node.status.value,
                int(node.priority),
                float(node.progress),
                node.title,
                saved_path,
                node.updated_at_utc.isoformat(),
            ),
        )
        return node

    def get_with_diagnostics(self, objective_id: str) -> ArtifactReadResult[ObjectiveNode]:
        row = self.db.fetchone(
            """
            SELECT objective_id, path
            FROM objective_nodes
            WHERE objective_id = ?
            """,
            (objective_id,),
        )
        if row is None:
            result = ArtifactReadResult(
                artifact_id=objective_id,
                path="",
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="IndexRowNotFound",
                error_message="No objective row exists in the SQLite index.",
            )
            self._remember_report(
                RepositoryReadReport.from_results("SQLITE_INDEX_LOOKUP", [result])
            )
            return result

        result = self._load_result(row['objective_id'], row['path'])
        self._remember_report(
            RepositoryReadReport.from_results("SQLITE_INDEX_LOOKUP", [result])
        )
        return result

    def get(self, objective_id: str) -> ObjectiveNode | None:
        result = self.get_with_diagnostics(objective_id)
        if result.status == ArtifactReadStatus.FOUND:
            return result.value
        if (
            result.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND
            and result.error_type == "IndexRowNotFound"
        ):
            return None
        report = self.last_read_report
        assert report is not None
        raise RepositoryReadError(report)

    def list_recent_with_diagnostics(
        self,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> RepositoryReadReport[ObjectiveNode]:
        sql = "SELECT objective_id, path FROM objective_nodes"
        clauses: list[str] = []
        parameters: list[object] = []
        if kind is not None:
            clauses.append('kind = ?')
            parameters.append(kind.value)
        if status is not None:
            clauses.append('status = ?')
            parameters.append(status.value)
        if site_id is not None:
            clauses.append("(site_id = ? OR (? = '' AND site_id IS NULL))")
            parameters.extend([site_id or '', site_id or ''])
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY updated_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        return self._collect_with_diagnostics(rows, scope="SQLITE_INDEX_ROWS")

    def list_recent(
        self,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[ObjectiveNode]:
        report = self.list_recent_with_diagnostics(
            kind=kind, status=status, site_id=site_id, limit=limit
        )
        return report.require_complete()

    def list_children_with_diagnostics(
        self,
        parent_id: str,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        limit: int = 40,
    ) -> RepositoryReadReport[ObjectiveNode]:
        sql = 'SELECT objective_id, path FROM objective_nodes WHERE parent_id = ?'
        parameters: list[object] = [parent_id]
        if kind is not None:
            sql += ' AND kind = ?'
            parameters.append(kind.value)
        if status is not None:
            sql += ' AND status = ?'
            parameters.append(status.value)
        sql += ' ORDER BY priority ASC, updated_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        return self._collect_with_diagnostics(rows, scope="SQLITE_INDEX_ROWS")

    def list_children(
        self,
        parent_id: str,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        limit: int = 40,
    ) -> list[ObjectiveNode]:
        report = self.list_children_with_diagnostics(
            parent_id, kind=kind, status=status, limit=limit
        )
        return report.require_complete()

    def latest_active(self, *, kind: ObjectiveNodeKind | None = None, site_id: str | None = None) -> ObjectiveNode | None:
        candidates: list[ObjectiveStatus] = [ObjectiveStatus.ACTIVE, ObjectiveStatus.BLOCKED, ObjectiveStatus.PENDING, ObjectiveStatus.PAUSED]
        for status in candidates:
            items = self.list_recent(kind=kind, status=status, site_id=site_id, limit=1)
            if items:
                return items[0]
        return None

    def find_equivalent_with_diagnostics(
        self,
        *,
        kind: ObjectiveNodeKind,
        title: str,
        parent_id: str | None = None,
        root_id: str | None = None,
        site_id: str | None = None,
        limit: int = 8,
    ) -> tuple[list[ObjectiveNode], RepositoryReadReport[ObjectiveNode]]:
        probe = self._normalize_title(title)
        if not probe:
            report = self._remember_report(
                RepositoryReadReport.from_results("SQLITE_INDEX_ROWS", [])
            )
            return [], report

        sql = 'SELECT objective_id, path FROM objective_nodes WHERE kind = ?'
        parameters: list[object] = [kind.value]
        if parent_id is not None:
            sql += ' AND parent_id = ?'
            parameters.append(parent_id)
        if root_id is not None:
            sql += ' AND root_id = ?'
            parameters.append(root_id)
        if site_id is not None:
            sql += " AND (site_id = ? OR (? = '' AND site_id IS NULL))"
            parameters.extend([site_id or '', site_id or ''])
        sql += ' ORDER BY updated_at_utc DESC LIMIT ?'
        parameters.append(limit)
        rows = self.db.fetchall(sql, tuple(parameters))
        report = self._collect_with_diagnostics(rows, scope="SQLITE_INDEX_ROWS")
        matches = [
            node for node in report.items
            if self._normalize_title(node.title) == probe
        ]
        return matches, report

    def find_equivalent(
        self,
        *,
        kind: ObjectiveNodeKind,
        title: str,
        parent_id: str | None = None,
        root_id: str | None = None,
        site_id: str | None = None,
        limit: int = 8,
    ) -> list[ObjectiveNode]:
        matches, report = self.find_equivalent_with_diagnostics(
            kind=kind,
            title=title,
            parent_id=parent_id,
            root_id=root_id,
            site_id=site_id,
            limit=limit,
        )
        report.require_complete()
        return matches

    def save_many(self, nodes: Iterable[ObjectiveNode]) -> list[ObjectiveNode]:
        saved: list[ObjectiveNode] = []
        for node in nodes:
            saved.append(self.save(node))
        return saved

    def _collect_with_diagnostics(
        self,
        rows: list[dict[str, str]],
        *,
        scope: str,
    ) -> RepositoryReadReport[ObjectiveNode]:
        results = [
            self._load_result(row['objective_id'], row['path'])
            for row in rows
        ]
        return self._remember_report(RepositoryReadReport.from_results(scope, results))

    def _load_result(self, objective_id: str, path: str) -> ArtifactReadResult[ObjectiveNode]:
        candidate = Path(path)
        paths: list[Path] = []
        if candidate.is_absolute():
            paths.append(candidate)
        paths.append(self.storage.root / f"objectives/{objective_id}.json")
        result = read_model_from_paths(paths, objective_id, ObjectiveNode)
        if result.status != ArtifactReadStatus.FOUND:
            _log.warning(
                "objective read incomplete: id=%s status=%s error=%s",
                objective_id,
                result.status.value,
                result.error_type or result.error_message,
            )
        return result

    def _normalize_title(self, title: str) -> str:
        return ' '.join((title or '').strip().lower().split())
