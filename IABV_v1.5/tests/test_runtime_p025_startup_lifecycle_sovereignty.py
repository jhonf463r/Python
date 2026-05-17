"""P0.25 focused tests: launcher/startup lifecycle sovereignty."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)
from iabv_v15.services.evolution.portable_context_service import PortableContextService


ROOT = Path(__file__).resolve().parents[1]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row))
            fh.write('\n')


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / 'workspace'
    (root / 'data' / 'logs').mkdir(parents=True, exist_ok=True)
    return root


def _startup_event(event: str, *, attempt_id: str = 'attempt-1') -> dict:
    return {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'event': event,
        'attempt_id': attempt_id,
        'pid': 1234,
        'head_commit': 'd82cd22a',
        'data': {},
    }


def test_startup_audit_snapshot_flags_attempt_without_runtime_fingerprint(tmp_path: Path) -> None:
    from iabv_v15.infra.startup_audit import startup_audit_snapshot

    root = _workspace(tmp_path)
    _write_jsonl(
        root / 'data' / 'logs' / 'startup_audit.jsonl',
        [
            _startup_event('startup_attempt'),
            _startup_event('python_launch_attempt'),
            _startup_event('python_launch_spawned'),
        ],
    )

    snap = startup_audit_snapshot(root)

    assert snap['status'] == 'needs_attention'
    assert snap['python_launch_attempted'] is True
    assert snap['python_launch_spawned'] is True
    assert 'UNRESOLVED:startup_attempt_without_runtime_fingerprint' in snap['unresolved_fields']


def test_startup_audit_snapshot_handoff_complete_with_runtime_events(tmp_path: Path) -> None:
    from iabv_v15.infra.startup_audit import startup_audit_snapshot

    root = _workspace(tmp_path)
    _write_jsonl(
        root / 'data' / 'logs' / 'startup_audit.jsonl',
        [
            _startup_event('startup_attempt'),
            _startup_event('python_launch_attempt'),
            _startup_event('python_launch_spawned'),
        ],
    )
    _write_jsonl(
        root / 'data' / 'logs' / 'runtime_audit.jsonl',
        [
            {'ts': datetime.now(timezone.utc).isoformat(), 'kind': 'startup_handoff_received'},
            {'ts': datetime.now(timezone.utc).isoformat(), 'kind': 'runtime_build_fingerprint'},
        ],
    )

    snap = startup_audit_snapshot(root)

    assert snap['status'] == 'handoff_complete'
    assert snap['bootstrap_handoff_received'] is True
    assert snap['runtime_fingerprint_received'] is True
    assert snap['unresolved_fields'] == []


def test_runtime_tracer_emits_startup_handoff_received(tmp_path: Path) -> None:
    from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

    root = _workspace(tmp_path)
    _write_jsonl(root / 'data' / 'logs' / 'startup_audit.jsonl', [_startup_event('startup_attempt')])
    tracer = RuntimeAuditTracer(log_dir=root / 'data' / 'logs')

    event = tracer.trace_startup_handoff_received(workspace=root)

    assert event['kind'] == 'startup_handoff_received'
    assert event['data']['latest_startup_event']['event'] == 'startup_attempt'
    assert 'startup_audit_summary' in event['data']


def test_oses_reports_startup_attempt_without_runtime_fingerprint(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _write_jsonl(root / 'data' / 'logs' / 'startup_audit.jsonl', [_startup_event('startup_attempt')])
    oses = OperationalSelfExaminationService(
        workspace_root=str(root),
        storage=ArtifactStorage(str(root / 'data' / 'evolution')),
    )

    findings = oses._startup_birth_audit_findings()

    assert any(f.category == 'startup_birth_blind_spot' for f in findings)
    assert any(
        'UNRESOLVED:startup_attempt_without_runtime_fingerprint' in f.unresolved_fields
        for f in findings
    )


def test_portable_context_startup_health_includes_birth_audit(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _write_jsonl(root / 'data' / 'logs' / 'startup_audit.jsonl', [_startup_event('startup_attempt')])
    svc = PortableContextService(
        workspace_root=str(root),
        storage=ArtifactStorage(str(root / 'data' / 'evolution')),
    )

    snap = svc._startup_health_snapshot()

    assert snap['birth_audit']['last_event'] == 'startup_attempt'
    section = svc._startup_health_section(status=snap, now=datetime.now(timezone.utc))
    assert any(item.get('label') == 'startup_birth_audit' for item in section.items)


def test_start_iabv_writes_startup_audit_and_releases_birth_lock() -> None:
    script = (ROOT / 'scripts' / 'start_iabv.ps1').read_text(encoding='utf-8')

    assert "Write-StartupAudit 'startup_attempt'" in script
    assert "Write-StartupAudit 'existing_ui_detected'" in script
    assert '$existingUiProcesses = @(Get-IabvUiProcesses)' in script
    assert "skip_ui_spawn" in script
    assert 'MainWindowTitle' in script
    assert '$env:IABV_WORKSPACE_ROOT = $iabvRoot' in script
    assert '$env:IABV_MCP_BIND_PORT = [string]$McpPort' in script
    assert "Write-StartupAudit 'cloudflared_zombies_removed'" in script
    assert '$startupSrcPath' in script
    assert "Write-StartupAudit 'python_launch_attempt'" in script
    assert "Write-StartupAudit 'python_launch_spawned'" in script
    assert "Write-StartupAudit 'python_launch_failed'" in script
    assert "Write-StartupAudit 'mcp_tunnel_skipped'" in script
    assert "Write-StartupAudit 'startup_lock_released'" in script
    assert "birth_phase_done_before_long_running_bridge" in script
    assert "ui_only_birth_phase_done" in script


def test_vbs_delegates_lock_decision_to_powershell() -> None:
    vbs = (ROOT / 'scripts' / 'IABV.vbs').read_text(encoding='utf-8')

    assert 'FileExists(lockPath)' not in vbs
    assert 'WScript.Quit 0' not in vbs
    assert 'start_iabv.ps1' in vbs
    assert '-UiOnly' in vbs
    assert 'PowerShell owns lock validation' in vbs


def test_run_mcp_bridge_falls_back_to_own_workspace_not_stale_absolute_path() -> None:
    bridge = (ROOT / 'scripts' / 'run_mcp_bridge.ps1').read_text(encoding='utf-8')

    assert "Split-Path -Parent $PSScriptRoot" in bridge
    assert "if (-not $workspaceRoot) { $workspaceRoot = 'C:\\Python\\IABV_v1.5' }" not in bridge


def test_platform_pending_p025_json_validates() -> None:
    from iabv_v15.domain.models import PlatformPendingTask

    path = ROOT / 'data' / 'evolution' / 'platform_pending' / 'task_runtime_startup_lifecycle_sovereignty_p025.json'
    task = PlatformPendingTask.model_validate_json(path.read_text(encoding='utf-8'))

    assert task.id == 'runtime_startup_lifecycle_sovereignty_p025'
    assert task.metadata['verification_status'] == 'LIVE_VERIFIED'
    assert task.metadata['live_proof']['duplicate_ui_guard_verified'] is True
