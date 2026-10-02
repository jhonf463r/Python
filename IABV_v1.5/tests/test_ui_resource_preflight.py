"""Focused tests for the shared UI RAM gate and launcher wiring."""

from __future__ import annotations

import json
import io
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from iabv_v15.services import intelligent_resource_manager as resource_manager
from iabv_v15.services.intelligent_resource_manager import evaluate_ui_ram_policy


def _snapshot(*, total: int = 16_000, available: int, used: float) -> SimpleNamespace:
    return SimpleNamespace(
        ram_total_mb=total,
        ram_available_mb=available,
        ram_used_pct=used,
    )


@pytest.mark.parametrize(
    ("snapshot", "decision", "reason"),
    [
        (_snapshot(available=4096, used=74.9), "CONTINUE", "sufficient_resources"),
        (_snapshot(available=4095, used=74.9), "DEFER", "low_free_ram"),
        (_snapshot(available=5000, used=75.0), "DEFER", "high_ram_used"),
    ],
)
def test_ui_ram_policy_boundaries(snapshot, decision: str, reason: str) -> None:
    result = evaluate_ui_ram_policy(snapshot)
    assert result["decision"] == decision
    assert result["reason"] == reason


@pytest.mark.parametrize(
    "snapshot",
    [
        None,
        _snapshot(total=0, available=0, used=0),
        _snapshot(total=-1, available=0, used=0),
        _snapshot(total=100, available=-1, used=1),
        _snapshot(total=100, available=101, used=1),
        _snapshot(total=100, available=50, used=float("nan")),
    ],
)
def test_invalid_ram_observation_defers_without_numeric_snapshot(snapshot) -> None:
    result = evaluate_ui_ram_policy(snapshot)
    assert result["decision"] == "DEFER"
    assert result["reason"] == "resource_observation_unavailable"
    assert result["ram_total_mb"] is None
    assert result["ram_available_mb"] is None
    assert result["ram_used_pct"] is None


def test_ram_snapshot_runs_only_the_ram_observer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **_kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="16000\n8000\n", stderr="")

    monkeypatch.setattr(resource_manager.Path, "exists", lambda _path: False)
    monkeypatch.setattr(resource_manager.subprocess, "run", fake_run)
    snapshot = resource_manager.take_ram_snapshot()

    assert (snapshot.ram_total_mb, snapshot.ram_available_mb, snapshot.ram_used_pct) == (
        16000,
        8000,
        50.0,
    )
    assert len(calls) == 1
    assert "Win32_OperatingSystem" in " ".join(calls[0])


def test_resource_preflight_cli_is_local_and_returns_structured_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Run the actual command path with Python network entrypoints denied."""
    def deny_network(*_args, **_kwargs):
        raise AssertionError("resource preflight attempted a network operation")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    original_run = subprocess.run

    def local_observation_only(args, *call_args, **kwargs):
        executable = str(args[0]).lower()
        assert Path(executable).name in {"powershell", "powershell.exe", "wmic", "wmic.exe"}
        return original_run(args, *call_args, **kwargs)

    monkeypatch.setattr(subprocess, "run", local_observation_only)
    modules_before = set(sys.modules)
    from iabv_v15.__main__ import main

    exit_code = main(["resource-preflight"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code in (0, 2)
    assert result["decision"] in {"CONTINUE", "DEFER"}
    assert result["reason"]
    newly_imported = set(sys.modules) - modules_before
    for forbidden in (
        "iabv_v15.bootstrap",
        "iabv_v15.services.evolution",
        "iabv_v15.services.adaptive",
        "iabv_v15.services.tools",
        "httpx",
        "requests",
        "urllib3",
    ):
        assert not any(
            name == forbidden or name.startswith(forbidden + ".")
            for name in newly_imported
        )
    assert "iabv_v15.cli.pending_intent_commands" not in newly_imported
    assert "iabv_v15.services.evolution.platform_pending_queue" not in newly_imported


@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        (_snapshot(available=4096, used=74.9), None),
        (_snapshot(available=4095, used=74.9), "low_free_ram:4095mb"),
        (_snapshot(available=5000, used=75.0), "high_ram_used:75.0%"),
    ],
)
def test_startup_evolution_consumes_the_shared_ram_policy(
    snapshot, expected, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("IABV_DISABLE_STARTUP_EVOLUTION", raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap_state = SimpleNamespace(
        ui_heartbeat_watchdog=None,
        _PREBUILD_SNAPSHOT_MAX_AGE_S=60.0,
        _get_cached_snapshot=lambda: (snapshot, 0.0),
    )
    result = AppBootstrap._startup_evolution_defer_reason(bootstrap_state)
    assert result == expected


def test_launcher_gates_only_new_ui_and_skips_health_checks_on_defer() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts" / "start_iabv.ps1").read_text(encoding="utf-8")

    preflight = source.index("Invoke-UIResourcePreflight")
    health = source.index("# Health checks opcionales")
    health_requests = source.index("https://api.github.com/repos/jhonf463r/Python")
    ui_presence = source.index("if ($StartUI) {", health_requests)
    existing_check = source.index("$existingUI = Find-ExistingUIProcess", ui_presence)
    defer_branch = source.index("if ($uiResourceGateDefers)", existing_check)
    spawn = source.index("[System.Diagnostics.Process]::Start($psi)", defer_branch)
    bridge = source.rindex("& powershell -ExecutionPolicy Bypass -File $bridge")

    assert preflight < health < health_requests < ui_presence
    assert existing_check < defer_branch < spawn < bridge
    assert "elseif (-not $SkipHealthChecks)" in source
    assert "Health checks opcionales omitidos: UI diferida" in source
    assert "ui_launch_skipped_resource_gate" in source
    assert "action = 'ui_not_started'" in source
    assert "[switch]$StartUI" in source


def test_launcher_runs_preflight_with_project_source_and_never_duplicates_thresholds() -> None:
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "scripts" / "start_iabv.ps1").read_text(encoding="utf-8")
    manager = (root / "src" / "iabv_v15" / "services" / "intelligent_resource_manager.py").read_text(encoding="utf-8")
    bootstrap = (root / "src" / "iabv_v15" / "bootstrap.py").read_text(encoding="utf-8")
    entrypoint = (root / "src" / "iabv_v15" / "__main__.py").read_text(encoding="utf-8")

    assert "-m iabv_v15 resource-preflight" in launcher
    assert "$uiSrcPath = Join-Path $iabvRoot 'src'" in launcher
    assert "RESOURCE_GATE_MIN_FREE_RAM_MB = 4096.0" in manager
    assert "RESOURCE_GATE_MAX_RAM_USED_PCT = 75.0" in manager
    assert "4096.0" not in launcher and "75.0" not in launcher
    assert "evaluate_ui_ram_policy" in bootstrap
    assert "evaluate_ui_ram_policy" in entrypoint


def test_natural_defer_branch_invokes_dedicated_persistence_command() -> None:
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "scripts" / "start_iabv.ps1").read_text(encoding="utf-8")
    defer_branch = launcher.index("if ($uiResourceGateDefers) {", launcher.index("$existingUI = Find-ExistingUIProcess"))
    persistence = launcher.index("persist-startui-defer", defer_branch)
    no_ui = launcher.index("ui_launch_skipped_resource_gate", persistence)
    spawn = launcher.index("[System.Diagnostics.Process]::Start($psi)", no_ui)
    assert defer_branch < persistence < no_ui < spawn
    assert "launcher_invocation_id = $launcherInvocationId" in launcher
    assert "UTF8Encoding]::new($false).GetBytes($deferPayloadJson)" in launcher
    assert "startui_defer_persistence_failed" in launcher


def test_startui_defer_task_contract_and_singleton_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from iabv_v15.cli import pending_intent_commands as command
    from iabv_v15.domain.models import PendingTaskStatus
    from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue

    payload = {
        "evolution_dir": str(tmp_path / "evolution"),
        "launcher_invocation_id": "invocation-1",
        "ui_requested": True,
        "decision": "DEFER",
        "timestamp_utc": "2026-10-02T12:00:00Z",
        "reason": "low_free_ram",
        "resource_observation": {"ram_available_mb": 1200, "threshold_free_mb": 4096},
        "source": "start_iabv.ps1",
    }
    task = command.build_startui_defer_task(command._validated_payload(json.dumps(payload)))
    assert task.id == "startui_defer_ui"
    assert task.category == "startui_defer"
    assert task.status == PendingTaskStatus.PENDING
    assert "StartUI" in task.description and "resource gate" in task.description
    assert task.reason == "low_free_ram"
    assert task.next_action == ""
    assert task.metadata["launcher_invocation_id"] == "invocation-1"
    assert task.metadata["resource_observation"]["ram_available_mb"] == 1200

    def invoke(invocation_id: str) -> int:
        repeated = dict(payload, launcher_invocation_id=invocation_id)
        monkeypatch.setattr(command.sys, "stdin", io.StringIO(json.dumps(repeated)))
        return command.persist_startui_defer_main()

    assert invoke("invocation-1") == 0
    first_updated_at = PlatformPendingQueue(payload["evolution_dir"]).get(task.id).updated_at
    assert invoke("invocation-2") == 0
    output = capsys.readouterr().out
    assert output.count('"ok": true') == 2
    queue_dir = Path(payload["evolution_dir"]) / "platform_pending"
    files = list(queue_dir.glob("task_*.json"))
    assert [path.name for path in files] == ["task_startui_defer_ui.json"]
    persisted = PlatformPendingQueue(payload["evolution_dir"]).get(task.id)
    assert persisted is not None
    assert persisted.metadata["launcher_invocation_id"] == "invocation-2"
    assert persisted.updated_at >= first_updated_at


@pytest.mark.parametrize(
    ("field", "value"),
    [("decision", "CONTINUE"), ("ui_requested", False)],
)
def test_startui_defer_cli_rejects_non_defer_payload(
    field: str,
    value,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from iabv_v15.cli import pending_intent_commands as command

    payload = {
        "evolution_dir": ".",
        "launcher_invocation_id": "invocation-1",
        "ui_requested": True,
        "decision": "DEFER",
        field: value,
    }
    monkeypatch.setattr(command.sys, "stdin", io.StringIO(json.dumps(payload)))
    assert command.persist_startui_defer_main() != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "failed" in captured.err


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"ui_requested": True, "decision": "DEFER", "launcher_invocation_id": "id"},
        {"ui_requested": True, "decision": "DEFER", "evolution_dir": "."},
    ],
)
def test_startui_defer_cli_rejects_invalid_shape_or_missing_identity(
    payload,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from iabv_v15.cli import pending_intent_commands as command

    monkeypatch.setattr(command.sys, "stdin", io.StringIO(json.dumps(payload)))
    assert command.persist_startui_defer_main() != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "failed" in captured.err


def test_startui_defer_cli_storage_failure_returns_nonzero_without_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from iabv_v15.cli import pending_intent_commands as command
    from iabv_v15.services.evolution import platform_pending_queue

    payload = {
        "evolution_dir": str(tmp_path / "evolution"),
        "launcher_invocation_id": "invocation-1",
        "ui_requested": True,
        "decision": "DEFER",
    }
    monkeypatch.setattr(command.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(platform_pending_queue.PlatformPendingQueue, "upsert", lambda *_args: (_ for _ in ()).throw(OSError("disk full")))
    assert command.persist_startui_defer_main() != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "disk full" in captured.err
