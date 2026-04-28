from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from iabv_v15.domain.models import ObjectiveNode, ObjectiveNodeKind, ObjectiveStatus
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage

_log = logging.getLogger(__name__)


class ObjectiveRepository:
    def __init__(self, db: AppDatabase, storage: ArtifactStorage):
        self.db = db
        self.storage = storage

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

    def get(self, objective_id: str) -> ObjectiveNode | None:
        row = self.db.fetchone(
            """
            SELECT objective_id, path
            FROM objective_nodes
            WHERE objective_id = ?
            """,
            (objective_id,),
        )
        if row is None:
            return None
        return self._load(row['objective_id'], row['path'])

    def list_recent(
        self,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[ObjectiveNode]:
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
        return self._collect(rows)

    def list_children(
        self,
        parent_id: str,
        *,
        kind: ObjectiveNodeKind | None = None,
        status: ObjectiveStatus | None = None,
        limit: int = 40,
    ) -> list[ObjectiveNode]:
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
        return self._collect(rows)

    def latest_active(self, *, kind: ObjectiveNodeKind | None = None, site_id: str | None = None) -> ObjectiveNode | None:
        candidates: list[ObjectiveStatus] = [ObjectiveStatus.ACTIVE, ObjectiveStatus.BLOCKED, ObjectiveStatus.PENDING, ObjectiveStatus.PAUSED]
        for status in candidates:
            items = self.list_recent(kind=kind, status=status, site_id=site_id, limit=1)
            if items:
                return items[0]
        return None

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
        probe = self._normalize_title(title)
        if not probe:
            return []
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
        matches: list[ObjectiveNode] = []
        for row in rows:
            node = self._load(row['objective_id'], row['path'])
            if node is not None and self._normalize_title(node.title) == probe:
                matches.append(node)
        return matches

    def save_many(self, nodes: Iterable[ObjectiveNode]) -> list[ObjectiveNode]:
        saved: list[ObjectiveNode] = []
        for node in nodes:
            saved.append(self.save(node))
        return saved

    def _collect(self, rows: list[dict[str, str]]) -> list[ObjectiveNode]:
        results: list[ObjectiveNode] = []
        orphan_ids: list[str] = []
        for row in rows:
            node = self._load(row['objective_id'], row['path'])
            if node is not None:
                results.append(node)
            else:
                orphan_ids.append(row['objective_id'])
        if orphan_ids:
            self._prune_orphans(orphan_ids)
        return results

    def _prune_orphans(self, ids: list[str]) -> None:
        if not ids:
            return
        placeholders = ','.join('?' for _ in ids)
        try:
            self.db.execute(
                f"DELETE FROM objective_nodes WHERE objective_id IN ({placeholders})",
                tuple(ids),
            )
            _log.info("objective_cleanup: pruned %d orphaned DB entries", len(ids))
        except Exception:
            pass

    def _normalize_title(self, title: str) -> str:
        return ' '.join((title or '').strip().lower().split())

    def _load(self, objective_id: str, path: str) -> ObjectiveNode | None:
        candidate = Path(path)
        try:
            if candidate.is_absolute() and candidate.exists():
                payload = json.loads(candidate.read_text(encoding='utf-8'))
            else:
                payload = self.storage.load_json(f'objectives/{objective_id}.json')
            return ObjectiveNode.model_validate(payload)
        except (FileNotFoundError, json.JSONDecodeError, OSError, Exception) as exc:
            _log.warning("objective %s: file missing or corrupt — %s", objective_id, exc)
            return None
