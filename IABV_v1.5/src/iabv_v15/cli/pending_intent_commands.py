"""Dedicated CLI adapter for persisting the StartUI resource-gate intent."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "startui_defer_ui"


def _validated_payload(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if payload.get("ui_requested") is not True:
        raise ValueError("ui_requested must be true")
    if payload.get("decision") != "DEFER":
        raise ValueError("decision must be DEFER")
    if not str(payload.get("evolution_dir", "")).strip():
        raise ValueError("evolution_dir is required")
    if not str(payload.get("launcher_invocation_id", "")).strip():
        raise ValueError("launcher_invocation_id is required")
    return payload


def build_startui_defer_task(payload: dict[str, Any]):
    """Build the existing pending-task model without adding schema fields."""
    from iabv_v15.domain.models import PendingTaskStatus, PlatformPendingTask

    observation = payload.get("resource_observation")
    if not isinstance(observation, dict):
        observation = {}
    timestamp = payload.get("timestamp_utc")
    metadata = {
        "source": str(payload.get("source") or "start_iabv.ps1"),
        "launcher_invocation_id": str(payload["launcher_invocation_id"]),
        "ui_requested": True,
        "decision": "DEFER",
        "timestamp_utc": str(timestamp or datetime.now(timezone.utc).isoformat()),
        "resource_observation": observation,
    }
    reason = str(payload.get("reason") or "resource_gate_deferred_ui")
    return PlatformPendingTask(
        id=TASK_ID,
        title="StartUI solicitado; creación de la UI diferida por el gate de recursos",
        description="IABV fue solicitado mediante StartUI, pero la creación de la UI fue diferida por el resource gate.",
        reason=reason,
        status=PendingTaskStatus.PENDING,
        category="startui_defer",
        metadata=metadata,
    )


def persist_startui_defer(payload: dict[str, Any]):
    """Persist the singleton intent through the existing queue authority."""
    from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue

    task = build_startui_defer_task(payload)
    queue = PlatformPendingQueue(Path(str(payload["evolution_dir"])))
    return queue.upsert(task)


def persist_startui_defer_main() -> int:
    try:
        payload = _validated_payload(sys.stdin.read())
        task = persist_startui_defer(payload)
    except Exception as exc:
        print(f"persist-startui-defer failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "task_id": task.id, "status": task.status.value}))
    return 0
