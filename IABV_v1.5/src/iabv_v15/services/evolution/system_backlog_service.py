"""SystemBacklogService — memoria de tareas pendientes del sistema.

El sistema mantiene su propia lista de tareas que necesita hacer para
mejorar (no las del usuario). Las tareas se auto-asignan desde
findings del SelfExamination, auditorias de capacidad, y deteccion
de errores recurrentes.

Contratos respetados (ver AGENTS.md):

- No es otro cerebro. No decide rutas ni ejecuta tareas autonomamente
  (eso lo hace AutonomousValidationCycleService para tareas de bajo
  riesgo). Este servicio solo registra y prioriza.
- No toca capas P1-P4.
- Persistencia en ``data/evolution/system_backlog/``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


VALID_CATEGORIES = frozenset({
    'infrastructure', 'ui', 'learning', 'audit',
    'deployment', 'error_recovery', 'optimization',
    'capability_gap', 'external_tool_fault',
})

VALID_STATUSES = frozenset({
    'pending', 'in_progress', 'completed', 'blocked',
    'auto_executed', 'dismissed',
})

VALID_PRIORITIES = frozenset({'critical', 'high', 'medium', 'low'})


class BacklogItem:
    """Una tarea que el sistema necesita hacer para mejorar."""

    __slots__ = (
        'item_id', 'title', 'description', 'category', 'priority',
        'status', 'dependencies', 'evidence', 'source',
        'created_at', 'updated_at', 'completed_at',
        'auto_executable', 'risk_level', 'metadata',
    )

    def __init__(
        self,
        title: str,
        *,
        item_id: str | None = None,
        description: str = '',
        category: str = 'infrastructure',
        priority: str = 'medium',
        status: str = 'pending',
        dependencies: list[str] | None = None,
        evidence: list[str] | None = None,
        source: str = '',
        created_at: datetime | str | None = None,
        updated_at: datetime | str | None = None,
        completed_at: datetime | str | None = None,
        auto_executable: bool = False,
        risk_level: str = 'low',
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.item_id = item_id or str(uuid4())
        self.title = title
        self.description = description
        self.category = category if category in VALID_CATEGORIES else 'infrastructure'
        self.priority = priority if priority in VALID_PRIORITIES else 'medium'
        self.status = status if status in VALID_STATUSES else 'pending'
        self.dependencies = list(dependencies or [])
        self.evidence = list(evidence or [])
        self.source = source
        now = _utc_now()
        self.created_at = _parse_dt(created_at) if created_at else now
        self.updated_at = _parse_dt(updated_at) if updated_at else now
        self.completed_at = _parse_dt(completed_at) if completed_at else None
        self.auto_executable = auto_executable
        self.risk_level = risk_level
        self.metadata = dict(metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            'item_id': self.item_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'dependencies': self.dependencies,
            'evidence': self.evidence,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'auto_executable': self.auto_executable,
            'risk_level': self.risk_level,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BacklogItem:
        return cls(
            title=data.get('title', ''),
            item_id=data.get('item_id'),
            description=data.get('description', ''),
            category=data.get('category', 'infrastructure'),
            priority=data.get('priority', 'medium'),
            status=data.get('status', 'pending'),
            dependencies=data.get('dependencies'),
            evidence=data.get('evidence'),
            source=data.get('source', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            completed_at=data.get('completed_at'),
            auto_executable=bool(data.get('auto_executable', False)),
            risk_level=data.get('risk_level', 'low'),
            metadata=data.get('metadata'),
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return _utc_now()
    return _utc_now()


class SystemBacklogService:
    """Memoria de tareas pendientes del sistema.

    Uso tipico:

        backlog = SystemBacklogService(workspace_root)
        backlog.add_item('Instalar aider_coder', category='infrastructure',
                         source='self_audit', auto_executable=True)
        pending = backlog.get_pending(category='infrastructure')
        backlog.mark_completed(item_id)
    """

    SUBDIR = Path('evolution') / 'system_backlog'
    BACKLOG_FILE = 'backlog.json'

    # Maximo de items en el backlog para evitar crecimiento infinito
    MAX_ITEMS = 500

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        clock: Any | None = None,
    ) -> None:
        self._root = Path(workspace_root) / 'data' / self.SUBDIR
        self._backlog_path = self._root / self.BACKLOG_FILE
        self._lock = threading.Lock()
        self._clock = clock or _utc_now

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_item(
        self,
        title: str,
        *,
        description: str = '',
        category: str = 'infrastructure',
        priority: str = 'medium',
        dependencies: list[str] | None = None,
        evidence: list[str] | None = None,
        source: str = '',
        auto_executable: bool = False,
        risk_level: str = 'low',
        metadata: dict[str, Any] | None = None,
    ) -> BacklogItem:
        """Agrega un item al backlog. Deduplica por titulo."""
        with self._lock:
            data = self._load_unlocked()
            items = data.get('items', [])

            # Deduplicacion: si ya existe un item con el mismo titulo y
            # esta pending o in_progress, no agregar otro
            for existing in items:
                if (
                    existing.get('title') == title
                    and existing.get('status') in ('pending', 'in_progress')
                ):
                    logger.debug('system_backlog: dedup — %r ya existe', title)
                    return BacklogItem.from_dict(existing)

            item = BacklogItem(
                title=title,
                description=description,
                category=category,
                priority=priority,
                dependencies=dependencies,
                evidence=evidence,
                source=source,
                auto_executable=auto_executable,
                risk_level=risk_level,
                metadata=metadata,
            )
            items.append(item.to_dict())

            # Evitar crecimiento infinito: si supera MAX_ITEMS, eliminar
            # los completados mas antiguos
            if len(items) > self.MAX_ITEMS:
                items = self._prune_items(items)

            data['items'] = items
            self._save_unlocked(data)

        logger.info('system_backlog: added %r (%s/%s)', title, category, priority)
        return item

    def get_pending(
        self,
        *,
        category: str | None = None,
        priority: str | None = None,
        auto_executable_only: bool = False,
    ) -> list[BacklogItem]:
        """Retorna items pendientes, opcionalmente filtrados."""
        data = self._load()
        results: list[BacklogItem] = []
        for item_dict in data.get('items', []):
            if item_dict.get('status') not in ('pending', 'in_progress'):
                continue
            if category and item_dict.get('category') != category:
                continue
            if priority and item_dict.get('priority') != priority:
                continue
            if auto_executable_only and not item_dict.get('auto_executable'):
                continue
            results.append(BacklogItem.from_dict(item_dict))

        # Ordenar por prioridad
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        results.sort(key=lambda i: priority_order.get(i.priority, 9))
        return results

    def mark_completed(self, item_id: str) -> bool:
        """Marca un item como completado."""
        return self._update_status(item_id, 'completed')

    def mark_in_progress(self, item_id: str) -> bool:
        """Marca un item como en progreso."""
        return self._update_status(item_id, 'in_progress')

    def mark_blocked(self, item_id: str, reason: str = '') -> bool:
        """Marca un item como bloqueado."""
        with self._lock:
            data = self._load_unlocked()
            for item_dict in data.get('items', []):
                if item_dict.get('item_id') == item_id:
                    item_dict['status'] = 'blocked'
                    item_dict['updated_at'] = self._clock().isoformat()
                    item_dict.setdefault('metadata', {})['blocked_reason'] = reason
                    self._save_unlocked(data)
                    return True
        return False

    def mark_auto_executed(self, item_id: str) -> bool:
        """Marca un item como auto-ejecutado por el sistema."""
        return self._update_status(item_id, 'auto_executed')

    def dismiss(self, item_id: str, reason: str = '') -> bool:
        """Descarta un item (no es relevante)."""
        with self._lock:
            data = self._load_unlocked()
            for item_dict in data.get('items', []):
                if item_dict.get('item_id') == item_id:
                    item_dict['status'] = 'dismissed'
                    item_dict['updated_at'] = self._clock().isoformat()
                    item_dict.setdefault('metadata', {})['dismiss_reason'] = reason
                    self._save_unlocked(data)
                    return True
        return False

    # ------------------------------------------------------------------
    # Ingestion desde SelfExamination findings
    # ------------------------------------------------------------------

    def ingest_from_findings(
        self, findings: list[dict[str, Any]],
    ) -> int:
        """Convierte findings del SelfExamination en items del backlog.

        Retorna la cantidad de items nuevos agregados.
        """
        added = 0
        for finding in findings:
            title = finding.get('title', '')
            if not title:
                continue
            category_map = {
                'recurring_failure': 'error_recovery',
                'repeated_stall': 'error_recovery',
                'token_rotation': 'infrastructure',
                'loop_closure': 'audit',
                'research_gap': 'learning',
                'cognitive_fixation': 'optimization',
                'cognitive_incubation': 'optimization',
                'neural_attractor': 'learning',
                'neural_ensemble': 'learning',
                'account_exhaustion': 'infrastructure',
                'tool_efficiency': 'optimization',
                'needs_custom_model': 'learning',
                'external_tool_misdiagnosis': 'external_tool_fault',
            }
            finding_cat = finding.get('category', '')
            category = category_map.get(finding_cat, 'audit')
            severity = finding.get('severity', 'medium')
            priority_map = {'critical': 'critical', 'high': 'high', 'medium': 'medium', 'low': 'low'}
            priority = priority_map.get(severity, 'medium')

            recommendation = finding.get('recommendation', '')
            auto_exec = bool(
                finding.get('metadata', {}).get('auto_executable')
                or (severity in ('low', 'medium') and 'install' in title.lower())
            )

            item = self.add_item(
                title=title,
                description=recommendation,
                category=category,
                priority=priority,
                evidence=[finding.get('finding_id', '')],
                source='self_examination',
                auto_executable=auto_exec,
                risk_level='low' if severity in ('low', 'medium') else 'medium',
                metadata={'finding_category': finding_cat},
            )
            if item:
                added += 1
        return added

    # ------------------------------------------------------------------
    # Resumen
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Resumen del backlog."""
        data = self._load()
        items = [BacklogItem.from_dict(d) for d in data.get('items', [])]

        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for item in items:
            by_status[item.status] = by_status.get(item.status, 0) + 1
            if item.status in ('pending', 'in_progress'):
                by_category[item.category] = by_category.get(item.category, 0) + 1
                by_priority[item.priority] = by_priority.get(item.priority, 0) + 1

        auto_executable_pending = [
            i for i in items
            if i.auto_executable and i.status == 'pending'
        ]

        return {
            'generated_at': self._clock().isoformat(),
            'total_items': len(items),
            'by_status': by_status,
            'pending_by_category': by_category,
            'pending_by_priority': by_priority,
            'auto_executable_count': len(auto_executable_pending),
            'top_auto_executable': [
                {'item_id': i.item_id, 'title': i.title, 'priority': i.priority}
                for i in auto_executable_pending[:5]
            ],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _update_status(self, item_id: str, new_status: str) -> bool:
        with self._lock:
            data = self._load_unlocked()
            for item_dict in data.get('items', []):
                if item_dict.get('item_id') == item_id:
                    item_dict['status'] = new_status
                    item_dict['updated_at'] = self._clock().isoformat()
                    if new_status in ('completed', 'auto_executed'):
                        item_dict['completed_at'] = self._clock().isoformat()
                    self._save_unlocked(data)
                    return True
        return False

    def _prune_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Elimina items completados/dismissed mas antiguos."""
        keep: list[dict[str, Any]] = []
        remove_candidates: list[dict[str, Any]] = []
        for item in items:
            if item.get('status') in ('completed', 'dismissed', 'auto_executed'):
                remove_candidates.append(item)
            else:
                keep.append(item)
        # Ordenar candidatos a eliminar por fecha (mas viejos primero)
        remove_candidates.sort(key=lambda x: x.get('completed_at', x.get('updated_at', '')))
        # Mantener los mas recientes hasta el limite
        space = self.MAX_ITEMS - len(keep)
        if space > 0:
            keep.extend(remove_candidates[-space:])
        return keep

    def _load(self) -> dict[str, Any]:
        try:
            if self._backlog_path.is_file():
                return json.loads(self._backlog_path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.warning('system_backlog: error loading %s: %s', self._backlog_path, exc)
        return {'items': []}

    def _load_unlocked(self) -> dict[str, Any]:
        return self._load()

    def _save_unlocked(self, data: dict[str, Any]) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            self._backlog_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.error('system_backlog: error saving %s: %s', self._backlog_path, exc)
