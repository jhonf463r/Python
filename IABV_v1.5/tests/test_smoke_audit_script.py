"""Tests del script standalone `scripts/smoke_audit_tools.py`.

Verifican que el script:

- no crashea con un workspace vacío (caso hostil: no hay `.git`, no hay
  `AGENTS.md`, no hay suite de tests);
- en modo `--json` emite por stdout un objeto parseable con las 5 claves
  `git_status`, `list_root`, `read_file`, `capture_screenshot`, `run_pytest`;
- cada clave trae `status` y, cuando corresponde, `detail` / `error_code`.

Estos casos son los que corren en Linux/CI, donde `capture_ui_screenshot`
degrada a `ui_not_running` y `git_status_and_log` degrada a
`not_a_git_repo` sobre un `tmp_path` limpio.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "smoke_audit_tools.py"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "scripts.smoke_audit_tools", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def smoke_module() -> ModuleType:
    return _load_script()


def test_smoke_script_runs_on_empty_workspace(
    smoke_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = smoke_module.main(["--workspace", str(tmp_path)])
    # Un workspace vacío tiene que cerrar con errors > 0 (al menos
    # `read_repo_file(AGENTS.md)` falla) → el script responde con 1 sin
    # explotar.
    assert exit_code in (0, 1)
    captured = capsys.readouterr()
    assert "of 5 ok" in captured.out


def test_smoke_script_json_mode_exposes_five_checks(
    smoke_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = smoke_module.main(["--workspace", str(tmp_path), "--json"])
    assert exit_code in (0, 1)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert isinstance(payload, dict)
    assert payload["workspace_root"] == str(tmp_path)

    for key in (
        "git_status",
        "list_root",
        "read_file",
        "capture_screenshot",
        "run_pytest",
    ):
        assert key in payload, f"falta la clave {key!r} en el JSON"
        entry = payload[key]
        assert isinstance(entry, dict)
        assert entry.get("status") in {"ok", "degraded", "error"}
        # detail / error_code son opcionales pero si están deben ser strings
        if "detail" in entry:
            assert isinstance(entry["detail"], str)
        if "error_code" in entry:
            assert isinstance(entry["error_code"], str)

    summary = payload["summary"]
    assert summary["total"] == 5
    assert summary["ok"] + summary["degraded"] + summary["errors"] == 5


def test_smoke_script_json_mode_degrades_capture_and_git(
    smoke_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_module.main(["--workspace", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    # Sin UIScreenshotProvider el helper devuelve un payload degradado;
    # el contrato del script es exponerlo con status="degraded" y
    # preservar el error_code que vino del helper.
    capture = payload["capture_screenshot"]
    assert capture["status"] == "degraded"
    assert capture.get("error_code")

    # tmp_path no es un repo git, así que el helper devuelve
    # `not_a_git_repo` y lo mostramos como degraded.
    git_status = payload["git_status"]
    assert git_status["status"] == "degraded"
    assert git_status.get("error_code") == "not_a_git_repo"


def test_detect_workspace_root_finds_pyproject(
    smoke_module: ModuleType,
    tmp_path: Path,
) -> None:
    root = tmp_path / "proj"
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")

    detected = smoke_module.detect_workspace_root(nested)
    assert detected == root.resolve()
