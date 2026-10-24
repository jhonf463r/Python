"""Regression guards for disabled legacy MCP and tunnel auto-start.

Tests inspect the startup call graph and invoke only inert refusal hooks. They
never start AppBootstrap, subprocesses, MCP, or Cloudflare.
"""

from __future__ import annotations

import ast
import subprocess
import threading
from pathlib import Path

import pytest

from iabv_v15.bootstrap import AppBootstrap


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = PROJECT_ROOT / "src" / "iabv_v15" / "bootstrap.py"


def _bootstrap_method(name: str) -> ast.FunctionDef:
    tree = ast.parse(BOOTSTRAP_PATH.read_text(encoding="utf-8"))
    bootstrap_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AppBootstrap"
    )
    return next(
        node for node in bootstrap_class.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


def test_normal_bootstrap_run_has_no_legacy_mcp_or_tunnel_launch_edge() -> None:
    run_method = _bootstrap_method("run")
    calls = _called_attributes(run_method)
    assert not calls.intersection({
        "_start_mcp_subprocess",
        "_start_tunnel_subprocess",
        "_start_mcp_supervisor",
        "_is_mcp_port_in_use",
    })
    run_source = ast.get_source_segment(BOOTSTRAP_PATH.read_text(encoding="utf-8"), run_method)
    assert run_source is not None
    assert "IABV_SKIP_MCP_AUTOSTART" not in run_source
    assert "disabled unconditionally" in run_source


@pytest.mark.parametrize("skip_value", [None, "1", "0"])
def test_legacy_launch_hooks_never_call_popen(monkeypatch, skip_value: str | None) -> None:
    if skip_value is None:
        monkeypatch.delenv("IABV_SKIP_MCP_AUTOSTART", raising=False)
    else:
        monkeypatch.setenv("IABV_SKIP_MCP_AUTOSTART", skip_value)

    calls: list[object] = []

    def forbidden_popen(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append((args, kwargs))
        raise AssertionError("legacy MCP/tunnel hooks must not invoke Popen")

    monkeypatch.setattr(subprocess, "Popen", forbidden_popen)
    bootstrap = object.__new__(AppBootstrap)

    assert bootstrap._start_mcp_subprocess() is None
    assert bootstrap._start_tunnel_subprocess() is None
    assert calls == []


def test_supervisor_cannot_restart_processes_or_start_a_thread(monkeypatch) -> None:
    bootstrap = object.__new__(AppBootstrap)
    bootstrap._mcp_supervisor_running = True
    bootstrap._mcp_supervision_status = {}
    restart_calls: list[str] = []

    monkeypatch.setattr(
        bootstrap,
        "_start_mcp_subprocess",
        lambda: restart_calls.append("mcp"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_start_tunnel_subprocess",
        lambda: restart_calls.append("tunnel"),
    )

    def forbidden_thread(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("disabled supervisor must not create a thread")

    monkeypatch.setattr(threading, "Thread", forbidden_thread)
    bootstrap._mcp_supervision_loop()
    bootstrap._start_mcp_supervisor()

    assert restart_calls == []
    assert bootstrap._mcp_supervisor_running is False
    assert bootstrap.mcp_supervision_status() == {
        "mcp_alive": False,
        "tunnel_alive": False,
        "mcp_restarts": 0,
        "tunnel_restarts": 0,
        "mcp_max_restarts_reached": False,
        "tunnel_max_restarts_reached": False,
    }


def test_startup_scripts_do_not_restore_public_launch_path() -> None:
    launcher = (PROJECT_ROOT / "scripts" / "run_mcp_bridge.ps1").read_text(encoding="utf-8")
    start = (PROJECT_ROOT / "scripts" / "start_iabv.ps1").read_text(encoding="utf-8")

    assert "cloudflared tunnel" not in launcher.lower()
    assert "Start-Process" not in launcher
    assert "run_mcp_bridge.ps1" not in start
    assert "Stop-McpZombies -Port" not in start
    assert "MCP/tunnel auto-start deshabilitado" in start
