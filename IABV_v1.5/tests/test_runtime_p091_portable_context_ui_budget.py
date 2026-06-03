from __future__ import annotations

import json
import tempfile
from pathlib import Path

from iabv_v15.domain.models import PortableContextPackage
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _service(root: Path) -> PortableContextService:
    return PortableContextService(
        workspace_root=str(root),
        storage=ArtifactStorage(str(root / "data" / "evolution")),
    )


def test_current_package_allow_stale_returns_cache_without_sync_build(tmp_path: Path):
    svc = _service(tmp_path)
    cached = PortableContextPackage(summary="cached portable context")
    svc._current_package = cached
    svc._is_fresh = lambda package, *, max_age_seconds: False  # type: ignore[method-assign]
    svc._goal_shifted = lambda package, *, task_context: False  # type: ignore[method-assign]
    scheduled: list[str] = []
    svc._schedule_package_refresh_async = (  # type: ignore[method-assign]
        lambda *, reason, **_: scheduled.append(reason)
    )

    def _forbidden_build(**_):
        raise AssertionError("UI stale path must not build portable context synchronously")

    svc.build_package = _forbidden_build  # type: ignore[method-assign]

    package = svc.current_package(refresh=False, allow_stale=True)

    assert package is cached
    assert scheduled == ["current_package_stale_allowed"]


def test_current_package_allow_stale_without_cache_returns_lightweight_package(tmp_path: Path):
    svc = _service(tmp_path)
    svc._current_package = None
    svc._load_latest_package = lambda: None  # type: ignore[method-assign]
    scheduled: list[str] = []
    svc._schedule_package_refresh_async = (  # type: ignore[method-assign]
        lambda *, reason, **_: scheduled.append(reason)
    )

    def _forbidden_build(**_):
        raise AssertionError("missing UI cache must not force full portable context build")

    svc.build_package = _forbidden_build  # type: ignore[method-assign]

    package = svc.current_package(refresh=False, allow_stale=True)

    assert package.summary.startswith("Contexto portable ligero")
    assert "UNRESOLVED:portable_context_background_refresh_pending" in package.unresolved_fields
    assert scheduled == ["current_package_missing_stale_allowed"]


def test_oses_detects_ui_portable_context_account_scan_stall():
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "data" / "logs" / "runtime_audit.jsonl"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "kind": "ui_event_loop_stall",
            "data": {
                "duration_ms": 39649.5,
                "dominant_phase": "event_loop_blocked_unknown",
                "main_thread_stack_during_stall": [
                    "portable_context_service.py, line 96, in current_package",
                    "portable_context_service.py, line 203, in build_package",
                    "portable_context_service.py, line 3256, in _canonical_work_queue_section",
                    "control_master_service.py, line 317, in current_work_queue",
                    "control_master_service.py, line 742, in _project_account_inventory",
                    "account_resource_scanner.py, line 1122, in build_inventory_snapshot",
                    "account_resource_scanner.py, line 304, in scan_browser_sessions",
                ],
            },
        }
        with audit_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")

        svc = object.__new__(OperationalSelfExaminationService)
        svc.workspace_root = tmpdir
        findings = svc._external_readiness_missing_findings()

        portable_findings = [
            f for f in findings
            if f.category == "ui_portable_context_scan_stall_repeated"
        ]
        assert portable_findings
        assert portable_findings[0].severity.value == "high"

