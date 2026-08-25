"""MCP tool: ``compare_perception_vs_ground_truth``.

Delgado wrapper sobre ``PerceptionGroundTruthComparator`` para exponerlo
como tool de auditoría. Fail-closed por governance (la lógica de gate
vive en ``server.py``). Este módulo es puro (no importa FastMCP) y se
puede testear con fakes.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


# Factoría tipo "late bind": si el caller no pasa un comparator,
# llamamos a una fábrica que lo construya sobre pedido. Mantiene el
# módulo libre de dependencias concretas.
ComparatorFactory = Callable[[], Any]


def _iso(dt: datetime | None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _mismatches_to_json(mismatches: Any) -> list[dict[str, Any]]:
    if not mismatches:
        return []
    out: list[dict[str, Any]] = []
    for m in mismatches:
        if isinstance(m, dict):
            out.append(dict(m))
            continue
        try:
            out.append(asdict(m))
        except TypeError:
            out.append(
                {
                    "field": getattr(m, "field", ""),
                    "perceived": getattr(m, "perceived", None),
                    "actual": getattr(m, "actual", None),
                    "severity": getattr(m, "severity", "info"),
                    "detail": getattr(m, "detail", ""),
                }
            )
    return out


def _result_to_payload(
    result: Any,
    *,
    window_title: str,
    checked_at: datetime,
) -> dict[str, Any]:
    if result is None:
        return {
            "window_title": window_title,
            "mismatches": [],
            "error": "comparator_returned_none",
            "checked_at_iso": _iso(checked_at),
        }

    def _get(name: str, default: Any = None) -> Any:
        if isinstance(result, dict):
            return result.get(name, default)
        return getattr(result, name, default)

    mismatches_json = _mismatches_to_json(_get("mismatches"))

    payload: dict[str, Any] = {
        "tool_id": str(_get("tool_id") or ""),
        "window_title": str(_get("window_title") or window_title),
        "perception_json": dict(_get("perception_json") or {}),
        "ground_truth_json": dict(_get("ground_truth_json") or {}),
        "mismatches": mismatches_json,
        "mismatch_count": len(mismatches_json),
        "severity_counts": _count_severities(mismatches_json),
        "evidence": dict(_get("evidence") or {}),
        "error": _get("error"),
        "detail": str(_get("detail") or ""),
        "duration_ms": int(_get("duration_ms") or 0),
        "checked_at_iso": _iso(checked_at),
    }
    return payload


def _count_severities(mismatches: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"critical": 0, "warning": 0, "info": 0}
    for m in mismatches:
        sev = str(m.get("severity") or "").lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def compare_perception_vs_ground_truth(
    window_title: str,
    *,
    tool_id: str = "",
    assistant_kind: str = "",
    site_id: str = "",
    comparator: Any | None = None,
    comparator_factory: ComparatorFactory | None = None,
    now_utc: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Compara perception de IABV vs ground truth local para una ventana.

    Parameters
    ----------
    window_title:
        título (o substring) de la ventana objetivo; obligatorio.
    tool_id, assistant_kind, site_id:
        pistas opcionales para ``UniversalPerceptionService.build_signal``.
    comparator:
        instancia ya construida de ``PerceptionGroundTruthComparator``;
        si es ``None``, se invoca ``comparator_factory``.
    comparator_factory:
        callable opcional que devuelve el comparator cuando ``comparator``
        no se pasó directo. Si también es ``None`` o falla, la tool
        devuelve ``{error: "comparator_unavailable"}``.
    now_utc:
        inyectable para tests.
    """

    _now = now_utc or (lambda: datetime.now(timezone.utc))
    checked_at = _now()

    title = (window_title or "").strip()
    if not title:
        return {
            "window_title": str(window_title or ""),
            "error": "invalid_window_title",
            "detail": "`window_title` no puede estar vacío.",
            "checked_at_iso": _iso(checked_at),
        }

    resolved = comparator
    if resolved is None and comparator_factory is not None:
        try:
            resolved = comparator_factory()
        except Exception as exc:
            logger.exception("comparator_factory falló")
            return {
                "window_title": title,
                "error": "comparator_init_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "checked_at_iso": _iso(checked_at),
            }

    if resolved is None:
        return {
            "window_title": title,
            "error": "comparator_unavailable",
            "detail": "No hay PerceptionGroundTruthComparator wireado.",
            "checked_at_iso": _iso(checked_at),
        }

    try:
        result = resolved.compare(
            title,
            tool_id=tool_id,
            assistant_kind=assistant_kind,
            site_id=site_id,
        )
    except Exception as exc:
        logger.exception("comparator.compare falló")
        return {
            "window_title": title,
            "error": "comparison_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "checked_at_iso": _iso(checked_at),
        }

    return _result_to_payload(
        result,
        window_title=title,
        checked_at=checked_at,
    )


__all__ = [
    "compare_perception_vs_ground_truth",
]
