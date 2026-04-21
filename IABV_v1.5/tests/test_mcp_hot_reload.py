"""Tests para ``scripts/mcp_hot_reload.py``.

Cobrimos las partes puras (deteccion de cambios, iteracion de archivos,
snapshot de mtimes). No arrancamos el server real; esas ramas dependen
de subprocess y quedan fuera de unit tests.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


# El directorio ``scripts`` no es un paquete instalado; cargamos el modulo
# por path directo para no obligar a convertirlo en package.
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "mcp_hot_reload.py"


@pytest.fixture(scope="module")
def hot_reload():
    spec = importlib.util.spec_from_file_location("iabv_mcp_hot_reload", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["iabv_mcp_hot_reload"] = module
    spec.loader.exec_module(module)
    return module


def test_changed_paths_detects_new_file(hot_reload):
    previous = {"/a.py": 1.0}
    current = {"/a.py": 1.0, "/b.py": 2.0}
    assert hot_reload.changed_paths(previous, current) == ["/b.py"]


def test_changed_paths_detects_deleted_file(hot_reload):
    previous = {"/a.py": 1.0, "/b.py": 2.0}
    current = {"/a.py": 1.0}
    assert hot_reload.changed_paths(previous, current) == ["/b.py"]


def test_changed_paths_detects_mtime_bump(hot_reload):
    previous = {"/a.py": 1.0}
    current = {"/a.py": 2.0}
    assert hot_reload.changed_paths(previous, current) == ["/a.py"]


def test_changed_paths_empty_when_equal(hot_reload):
    previous = {"/a.py": 1.0, "/b.py": 2.0}
    current = dict(previous)
    assert hot_reload.changed_paths(previous, current) == []


def test_iter_watch_files_skips_pycache(hot_reload, tmp_path):
    (tmp_path / "mod.py").write_text("# file")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "mod.cpython-312.pyc").write_text("bytes")
    (tmp_path / "sub" / "__pycache__").mkdir(parents=True)
    (tmp_path / "sub" / "ok.py").write_text("# ok")
    (tmp_path / "sub" / "__pycache__" / "ok.cpython-312.pyc").write_text("bytes")
    (tmp_path / "README.md").write_text("no py")

    seen = sorted(p.name for p in hot_reload.iter_watch_files(tmp_path))
    assert seen == ["mod.py", "ok.py"]


def test_iter_watch_files_missing_root_is_empty(hot_reload, tmp_path):
    missing = tmp_path / "does-not-exist"
    assert list(hot_reload.iter_watch_files(missing)) == []


def test_snapshot_mtimes_returns_floats(hot_reload, tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x")
    snap = hot_reload.snapshot_mtimes([f])
    assert str(f) in snap
    assert isinstance(snap[str(f)], float)


def test_snapshot_mtimes_ignores_missing_paths(hot_reload, tmp_path):
    good = tmp_path / "a.py"
    good.write_text("x")
    missing = tmp_path / "never-existed.py"
    snap = hot_reload.snapshot_mtimes([good, missing])
    assert str(missing) not in snap
    assert str(good) in snap


def test_resolve_interval_defaults_when_invalid(hot_reload, monkeypatch):
    monkeypatch.setenv("IABV_MCP_HOT_RELOAD_INTERVAL", "not-a-number")
    assert hot_reload._resolve_interval() == 2.0


def test_resolve_interval_clamps_low(hot_reload, monkeypatch):
    monkeypatch.setenv("IABV_MCP_HOT_RELOAD_INTERVAL", "0.01")
    assert hot_reload._resolve_interval() == pytest.approx(0.2)


def test_resolve_interval_honors_override(hot_reload, monkeypatch):
    monkeypatch.setenv("IABV_MCP_HOT_RELOAD_INTERVAL", "5")
    assert hot_reload._resolve_interval() == pytest.approx(5.0)
