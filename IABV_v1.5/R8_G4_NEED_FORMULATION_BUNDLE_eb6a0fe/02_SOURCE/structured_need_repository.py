"""Structured Need Repository — R8-G4.

Persists StructuredNeed objects as JSON files in data/evolution/structured_needs/.
Follows the same pattern as PlatformPendingQueue for consistency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    StructuredNeed,
    NeedStatus,
    utc_now,
)


class StructuredNeedRepository:
    """Persistent repository for StructuredNeed objects."""

    def __init__(self, evolution_dir: str | Path) -> None:
        self._dir = Path(evolution_dir).resolve() / 'structured_needs'
        self._dir.mkdir(parents=True, exist_ok=True)

    def upsert(self, need: StructuredNeed) -> StructuredNeed:
        """Insert or update a structured need. Returns the persisted copy."""
        need = need.model_copy(update={'created_at': utc_now()})
        path = self._need_path(need.need_id)
        path.write_text(
            need.model_dump_json(indent=2),
            encoding='utf-8',
        )
        return need

    def get(self, need_id: str) -> StructuredNeed | None:
        path = self._need_path(need_id)
        if not path.exists():
            return None
        try:
            return StructuredNeed.model_validate_json(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def list_all(self) -> list[StructuredNeed]:
        """Return all structured needs sorted by created_at (newest first)."""
        needs: list[StructuredNeed] = []
        for path in sorted(self._dir.glob('need_*.json')):
            try:
                needs.append(StructuredNeed.model_validate_json(path.read_text(encoding='utf-8')))
            except Exception:
                continue
        needs.sort(key=lambda n: n.created_at, reverse=True)
        return needs

    def list_pending(self) -> list[StructuredNeed]:
        """Return needs with PENDING status."""
        return [n for n in self.list_all() if n.status == NeedStatus.PENDING]

    def update_status(self, need_id: str, status: NeedStatus) -> StructuredNeed | None:
        """Update the status of a need."""
        need = self.get(need_id)
        if need is None:
            return None
        need = need.model_copy(update={'status': status})
        return self.upsert(need)

    def summary(self) -> dict[str, Any]:
        """Return a machine-readable summary of the repository state."""
        needs = self.list_all()
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for n in needs:
            by_status[n.status.value] = by_status.get(n.status.value, 0) + 1
            by_priority[n.priority] = by_priority.get(n.priority, 0) + 1
        return {
            'total': len(needs),
            'by_status': by_status,
            'by_priority': by_priority,
            'pending': len(self.list_pending()),
        }

    def _need_path(self, need_id: str) -> Path:
        safe_id = need_id.replace('/', '_').replace('\\', '_')
        return self._dir / f'need_{safe_id}.json'

    def format_human_readable(self, need: StructuredNeed) -> str:
        """Format a need as human-readable text.

        Returns a string in the format:
        NECESITO:
          X
        PORQUE:
          Y
        EVIDENCIA:
          Z
        """
        lines = [
            "NECESITO:",
            f"  {need.capability_gap}",
            "",
            "PORQUE:",
            f"  {need.reason}",
            "",
            "EVIDENCIA:",
        ]
        if need.evidence:
            for ev in need.evidence[:3]:  # Limit to first 3 evidence items
                lines.append(f"  - {ev}")
        else:
            lines.append("  (ninguna)")
        lines.append("")
        lines.append(f"PRIORIDAD: {need.priority.upper()}")
        lines.append(f"ESTADO: {need.status.value.upper()}")
        lines.append(f"CONOCIMIENTO REQUERIDO: {need.knowledge_required}")
        return "\n".join(lines)

    def format_all_pending(self) -> str:
        """Format all pending needs as human-readable text."""
        pending = self.list_pending()
        if not pending:
            return "No hay necesidades pendientes."
        lines = [f"NECESIDADES PENDIENTES ({len(pending)}):", ""]
        for i, need in enumerate(pending, 1):
            lines.append(f"--- NECESIDAD {i} ---")
            lines.append(self.format_human_readable(need))
            lines.append("")
        return "\n".join(lines)
