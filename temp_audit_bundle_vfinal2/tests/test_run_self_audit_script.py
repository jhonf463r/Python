"""Tests del script `scripts/run_self_audit.py`.

No instancian `AppBootstrap` real (demasiado pesado para cada test);
monkeypatchean el import para inyectar un `AppBootstrap` fake con un
`self_audit_service.run()` controlado. Validan que el script:

- devuelve exit=0 cuando `run()` responde con un snapshot;
- formatea salida JSON parseable con las claves estables documentadas;
- formatea salida texto con las líneas esperadas;
- agrega `summary_markdown` al payload cuando se pasa `--print-md`;
- devuelve exit=1 y escribe a stderr si `run()` levanta una excepción.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "run_self_audit.py"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "scripts.run_self_audit", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script_module() -> ModuleType:
    return _load_script()


@dataclass
class _FakeToolCheck:
    tool_id: str
    available: bool


@dataclass
class _FakeEnvMatch:
    matched: bool = True
    mismatches: list[str] = field(default_factory=list)


@dataclass
class _FakeSnapshot:
    generated_at: datetime
    reason: str
    tool_checks: list[_FakeToolCheck]
    environment_match: _FakeEnvMatch
    pending_issues: list[str]
    summary_markdown: str


class _FakeService:
    def __init__(self, snapshot: _FakeSnapshot) -> None:
        self._snapshot = snapshot
        self.calls: list[str | None] = []

    def run(self, *, reason: str | None = None) -> _FakeSnapshot:
        self.calls.append(reason)
        return self._snapshot


class _FakeBootstrap:
    instances: list["_FakeBootstrap"] = []

    def __init__(self, workspace_root: str | None = None) -> None:
        self.workspace_root = workspace_root
        # Snapshot quemado con valores predecibles.
        snapshot = _FakeSnapshot(
            generated_at=datetime(2026, 4, 19, 12, 34, 56, 789000, tzinfo=timezone.utc),
            reason="test",
            tool_checks=[
                _FakeToolCheck("tool-a", True),
                _FakeToolCheck("tool-b", False),
                _FakeToolCheck("tool-c", True),
            ],
            environment_match=_FakeEnvMatch(
                matched=False,
                mismatches=["mismatch uno", "mismatch dos"],
            ),
            pending_issues=["issue-1", "issue-2"],
            summary_markdown="# Audit\n- item\n",
        )
        self.self_audit_service = _FakeService(snapshot)
        _FakeBootstrap.instances.append(self)


@pytest.fixture(autouse=True)
def _reset_fake_instances() -> None:
    _FakeBootstrap.instances.clear()
    yield
    _FakeBootstrap.instances.clear()


def _install_fake_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = SimpleNamespace(AppBootstrap=_FakeBootstrap)
    monkeypatch.setitem(sys.modules, "iabv_v15.bootstrap", fake_module)


def test_script_exit_zero_and_text_output(
    script_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_bootstrap(monkeypatch)

    exit_code = script_module.main(
        ["--workspace", str(tmp_path), "--reason", "test"]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "=== IABV v1.5 SelfAudit ===" in captured.out
    assert "tool_checks        : 2/3 available" in captured.out
    assert "pending_issues     : 2" in captured.out
    # El service debe haber recibido la razón por kwarg.
    assert _FakeBootstrap.instances[-1].self_audit_service.calls == ["test"]


def test_script_json_mode_has_stable_keys(
    script_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_bootstrap(monkeypatch)

    exit_code = script_module.main(
        ["--workspace", str(tmp_path), "--json"]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["tool_checks"] == {"total": 3, "available": 2}
    assert payload["environment_match"] == {"matched": False, "mismatches": 2}
    assert payload["pending_issues"] == 2
    assert payload["summary_markdown_chars"] == len("# Audit\n- item\n")
    assert payload["artifacts"]["latest_json"].endswith("latest.json")
    assert payload["artifacts"]["latest_md"].endswith("latest.md")
    assert payload["artifacts"]["history_file"].endswith(
        "20260419T123456789000Z.json"
    )
    assert "summary_markdown" not in payload  # sin --print-md no incluye md


def test_script_print_md_includes_markdown(
    script_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_bootstrap(monkeypatch)

    exit_code = script_module.main(
        ["--workspace", str(tmp_path), "--json", "--print-md"]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary_markdown"] == "# Audit\n- item\n"


def test_script_exit_one_on_exception(
    script_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ExplodingBootstrap:
        def __init__(self, workspace_root: str | None = None) -> None:
            raise RuntimeError("boom")

    fake_module = SimpleNamespace(AppBootstrap=_ExplodingBootstrap)
    monkeypatch.setitem(sys.modules, "iabv_v15.bootstrap", fake_module)

    exit_code = script_module.main(["--workspace", str(tmp_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
    assert "boom" in captured.err
