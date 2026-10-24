"""Static guards for the PowerShell MCP bridge launch chain.

These tests inspect source only; they never run PowerShell, the application,
the MCP server, cloudflared, or another process.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_bridge_launcher_is_stdio_only_and_has_no_tunnel_process_path() -> None:
    script = (PROJECT_ROOT / "scripts" / "run_mcp_bridge.ps1").read_text(encoding="utf-8")

    assert "if (-not $transport) { $transport = 'stdio' }" in script
    assert "$transport -ne 'stdio'" in script
    assert "IABV_MCP_TRANSPORT = 'stdio'" in script
    assert "IABV_MCP_PROFILE = 'local_restricted'" in script
    assert "cloudflared tunnel" not in script.lower()
    assert "Start-Process" not in script
    assert "FASTMCP_HOST" not in script
    assert "FASTMCP_PORT" not in script
    assert "start_iabv.ps1" not in script.lower()
    assert "pythonw" not in script.lower()


def test_start_iabv_does_not_delegate_to_bridge_or_kill_bridge_processes() -> None:
    script = (PROJECT_ROOT / "scripts" / "start_iabv.ps1").read_text(encoding="utf-8")

    assert "run_mcp_bridge.ps1" not in script
    assert "Stop-McpZombies -Port $McpPort" not in script
    assert "MCP/tunnel auto-start deshabilitado" in script
    assert "IABV_SKIP_MCP_AUTOSTART" not in script
