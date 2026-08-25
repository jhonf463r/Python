from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


def _timeline_event(phase: str, ms: float, **extra):
    payload = {
        'phase': phase,
        't_ms_from_start': ms,
    }
    payload.update(extra)
    return payload


class _Context:
    def __init__(self) -> None:
        self.properties: dict[str, object] = {}

    def setContextProperty(self, name: str, value: object) -> None:
        self.properties[name] = value


class _Bridge:
    def __init__(self, running: bool = False, control_vm_bound: bool = False) -> None:
        self.status = SimpleNamespace(
            running=running,
            control_vm_bound=control_vm_bound,
            shell_ready=False,
        )
        self.ready_sources: list[str] = []

    def mark_shell_ready(self, source: str) -> None:
        self.status.shell_ready = True
        self.ready_sources.append(source)


def test_startup_chat_bridge_priority_builds_only_control_vm() -> None:
    from iabv_v15.bootstrap import AppBootstrap

    app = AppBootstrap.__new__(AppBootstrap)
    app.control_center_viewmodel = None
    app.ui_bridge_server = _Bridge()
    app.mcp_bridge_service = object()
    app.chat_capability_ingestion_service = object()
    app._qml_root_context = _Context()
    app._page_loader_ready_received = True
    app._shell_loader_ready_handled = True
    app._startup_chat_bridge_ready = False
    app._timeline = MagicMock()
    app._tracer = MagicMock()
    built_routes: list[str] = []

    def _build(route: str) -> None:
        built_routes.append(route)
        app.control_center_viewmodel = object()

    app._ensure_vm_for_route = _build

    assert app._ensure_startup_chat_bridge_ready('test') is True
    assert built_routes == ['control']
    assert app._qml_root_context.properties['controlCenterViewModel'] is app.control_center_viewmodel
    assert app.ui_bridge_server.ready_sources == ['late_bridge_start_after_page_loader_ready']


def test_startup_chat_bridge_defers_until_lightweight_dependencies_exist() -> None:
    from iabv_v15.bootstrap import AppBootstrap

    app = AppBootstrap.__new__(AppBootstrap)
    app.control_center_viewmodel = None
    app._qml_root_context = _Context()
    app._timeline = MagicMock()
    app._tracer = MagicMock()
    app._ensure_vm_for_route = MagicMock()

    assert app._ensure_startup_chat_bridge_ready('shell_loader_ready') is False
    app._ensure_vm_for_route.assert_not_called()
    app._timeline.mark.assert_called_with(
        'startup_chat_bridge_deferred',
        source='shell_loader_ready',
        reason='deferred_ui_batch_1_pending',
        missing_dependencies=[
            'mcp_bridge_service',
            'ui_bridge_server',
            'chat_capability_ingestion_service',
        ],
    )


def test_build_control_center_vm_is_idempotent_when_already_built() -> None:
    from iabv_v15.bootstrap import AppBootstrap

    app = AppBootstrap.__new__(AppBootstrap)
    app.control_center_viewmodel = object()
    app._timeline = MagicMock()

    assert app._build_control_center_vm() is None
    app._timeline.mark.assert_not_called()


def test_oses_reports_missing_chat_bridge_after_page_ready(tmp_path: Path) -> None:
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )

    log_dir = tmp_path / 'data' / 'logs'
    log_dir.mkdir(parents=True)
    events = [
        _timeline_event('bootstrap_init_start', 0.0),
        _timeline_event('bootstrap_init_done', 100.0),
        _timeline_event('main_window_shown', 1800.0),
        _timeline_event('page_loader_ready', 2600.0),
        _timeline_event('deferred_metacognition_start', 5100.0),
    ]
    (log_dir / 'startup_timeline.jsonl').write_text(
        '\n'.join(json.dumps(evt) for evt in events),
        encoding='utf-8',
    )

    svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    svc.workspace_root = str(tmp_path)
    findings = svc._startup_health_findings()
    categories = {f.category for f in findings}

    assert 'startup_chat_bridge_missing' in categories
    assert 'startup_priority_inversion' in categories


def test_oses_reports_late_chat_bridge(tmp_path: Path) -> None:
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )

    log_dir = tmp_path / 'data' / 'logs'
    log_dir.mkdir(parents=True)
    events = [
        _timeline_event('bootstrap_init_start', 0.0),
        _timeline_event('bootstrap_init_done', 100.0),
        _timeline_event('main_window_shown', 1800.0),
        _timeline_event('page_loader_ready', 2600.0),
        _timeline_event('startup_chat_bridge_priority_requested', 2700.0),
        _timeline_event('startup_chat_bridge_priority_granted', 17100.0),
        _timeline_event('startup_chat_bridge_ready', 18100.0),
    ]
    (log_dir / 'startup_timeline.jsonl').write_text(
        '\n'.join(json.dumps(evt) for evt in events),
        encoding='utf-8',
    )

    svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    svc.workspace_root = str(tmp_path)
    findings = svc._startup_health_findings()

    late = [f for f in findings if f.category == 'startup_chat_bridge_late']
    assert late
    assert late[0].metadata['observed_ms'] == 18100.0
