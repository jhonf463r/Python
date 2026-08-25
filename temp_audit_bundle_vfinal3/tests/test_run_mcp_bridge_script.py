"""Static checks for ``scripts/run_mcp_bridge.ps1``.

This script launches the external MCP server path used by ``start_iabv.ps1``.
The startup timeline audit belongs to the visible UI boot, so the bridge-launched
MCP must explicitly disable ``IABV_STARTUP_TIMELINE`` to avoid contaminating
``data/logs/startup_timeline.jsonl`` with non-UI events.
"""

from __future__ import annotations

from pathlib import Path


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_mcp_bridge.ps1"


def test_run_mcp_bridge_script_exists() -> None:
    assert _SCRIPT_PATH.exists(), f"Falta {_SCRIPT_PATH}"


def test_run_mcp_bridge_disables_startup_timeline_for_external_mcp() -> None:
    src = _SCRIPT_PATH.read_text(encoding="utf-8")
    assert "$env:IABV_STARTUP_TIMELINE = '0'" in src
    env_idx = src.index("$env:IABV_STARTUP_TIMELINE = '0'")
    launch_idx = src.index("Start-Process -PassThru -NoNewWindow -FilePath $pythonBin")
    assert env_idx < launch_idx, (
        "IABV_STARTUP_TIMELINE debe apagarse antes de lanzar el MCP externo"
    )


def test_run_mcp_bridge_still_launches_mcp_server_module() -> None:
    src = _SCRIPT_PATH.read_text(encoding="utf-8")
    assert "'-m', 'iabv_v15.infra.mcp.server'" in src
