"""Fail-closed, privacy-minimised projection of the live Control Master.

The shared signal intentionally contains identifiers and prioritisation metadata
only. It never exports free-form titles, summaries, reasons, evidence paths,
logs, user content, or account inventory.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from iabv_v15.domain.models import ControlMasterState, utc_now

SCHEMA_VERSION = "iabv.control_master_signal.v1"
FRESHNESS_WINDOW_SECONDS = 900
_MAX_ITEMS = 10
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ERROR_CODE = re.compile(r"^[A-Z0-9_:-]{1,96}$")
_ALLOWED_SOURCES = {
    "objective_repository",
    "platform_pending_queue",
    "pending_issue_repository",
    "oses_finding",
    "runtime_audit",
    "tests_state",
}
_ALLOWED_PRIORITY_LABELS = {"critical", "high", "medium", "low", "info", "unknown"}
_ALLOWED_ITEM_STATUSES = {
    "active", "pending", "blocked", "unresolved", "needs_fix",
    "observed", "open", "resolved", "failed", "abandoned", "unknown",
}


def _queue_slot_id(position: int) -> str:
    """Per-snapshot reference; deliberately has no mapping to the source item ID."""
    return f"queue-item-{position + 1:02d}"


class ControlMasterSignalProjector:
    """Pure allowlist projector; no filesystem, network, or credential access."""

    @staticmethod
    def unavailable(reason: str, *, source_state_id: str = "") -> dict[str, Any]:
        observed = utc_now()
        safe_reason = reason if _ERROR_CODE.fullmatch(reason) else "SIGNAL_SOURCE_UNAVAILABLE"
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "IABV",
            "signal_status": "UNAVAILABLE",
            "signal_id": "",
            "source": {
                "component": "ControlMasterService",
                "state_id": source_state_id if _TOKEN.fullmatch(source_state_id or "") else "",
                "state_observed_at_utc": None,
            },
            "generated_at_utc": observed.astimezone(timezone.utc).isoformat(),
            "expires_at_utc": (observed + timedelta(seconds=FRESHNESS_WINDOW_SECONDS)).astimezone(timezone.utc).isoformat(),
            "freshness_window_seconds": FRESHNESS_WINDOW_SECONDS,
            "queue": {"status": "UNAVAILABLE", "item_count": None, "items": []},
            "counts": {},
            "reason_codes": [safe_reason],
            "transport": "SIGNAL_UNAVAILABLE_NOT_PUBLISHABLE",
        }
        payload["signal_id"] = "cms-" + _content_hash(payload)[:24]
        payload["content_sha256"] = _content_hash(payload)
        return payload

    @classmethod
    def project(
        cls,
        *,
        state: ControlMasterState,
        work_queue: list[dict[str, Any]] | None,
        source_errors: tuple[str, ...] | list[str] = (),
        observed_at_utc: datetime | None = None,
    ) -> dict[str, Any]:
        if work_queue is None:
            return cls.unavailable("WORK_QUEUE_NOT_AVAILABLE", source_state_id=state.state_id)
        safe_errors = sorted({
            item for item in source_errors
            if isinstance(item, str) and _ERROR_CODE.fullmatch(item)
        })
        if source_errors:
            return cls.unavailable(
                safe_errors[0] if safe_errors else "QUEUE_SOURCE_ERRORS",
                source_state_id=state.state_id,
            )
        if not isinstance(state.state_id, str) or not _TOKEN.fullmatch(state.state_id):
            return cls.unavailable("SOURCE_STATE_ID_INVALID")
        observed = observed_at_utc or utc_now()
        if observed.tzinfo is None or observed.utcoffset() is None:
            return cls.unavailable("READER_CLOCK_UNKNOWN", source_state_id=state.state_id)
        # This is when the producer observed the state/queue projection.
        # It is deliberately not ControlMasterState.last_updated, which is
        # the persisted object's modification timestamp.
        observed = observed.astimezone(timezone.utc)

        safe_items: list[dict[str, Any]] = []
        for position, item in enumerate(work_queue[:_MAX_ITEMS]):
            if not isinstance(item, dict):
                return cls.unavailable("QUEUE_ITEM_INVALID", source_state_id=state.state_id)
            item_id = item.get("id")
            source = item.get("source")
            raw_status = str(item.get("status") or "unknown").lower()
            status = raw_status if raw_status in _ALLOWED_ITEM_STATUSES else "unknown"
            label = str(item.get("priority_label") or "unknown").lower()
            score = item.get("priority_score", 0)
            if (
                not isinstance(item_id, str)
                or not _TOKEN.fullmatch(item_id)
                or not isinstance(source, str)
                or source not in _ALLOWED_SOURCES
                or not isinstance(status, str)
                or not _TOKEN.fullmatch(status)
                or label not in _ALLOWED_PRIORITY_LABELS
                or isinstance(score, bool)
                or not isinstance(score, int)
                or score < 0
                or score > 1000
            ):
                return cls.unavailable("QUEUE_ITEM_NOT_PORTABLE", source_state_id=state.state_id)
            safe_items.append({
                "item_id": _queue_slot_id(position),
                "status": status,
                "source": source,
                "priority_label": label,
                "priority_score": score,
            })

        queue_status = "EMPTY_QUEUE" if not work_queue else "NON_EMPTY_QUEUE"
        signal_status = "EMPTY_QUEUE" if not work_queue else "AVAILABLE"
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "IABV",
            "signal_status": signal_status,
            "signal_id": "",
            "source": {
                "component": "ControlMasterService",
                "state_id": state.state_id,
                "state_observed_at_utc": observed.isoformat(),
            },
            "generated_at_utc": observed.isoformat(),
            "expires_at_utc": (observed + timedelta(seconds=FRESHNESS_WINDOW_SECONDS)).isoformat(),
            "freshness_window_seconds": FRESHNESS_WINDOW_SECONDS,
            "queue": {
                "status": queue_status,
                "item_count": len(safe_items),
                "items": safe_items,
            },
            "counts": {
                "queue_items_published": len(safe_items),
            },
            "reason_codes": [],
            "transport": "READY_FOR_DEDICATED_BRANCH_PUBLICATION",
        }
        payload["signal_id"] = "cms-" + _content_hash(payload)[:24]
        payload["content_sha256"] = _content_hash(payload)
        return payload


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
