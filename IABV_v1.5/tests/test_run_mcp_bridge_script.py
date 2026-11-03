"""Static checks that the script bridge denies before setup or launch."""

from pathlib import Path
import re


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_mcp_bridge.ps1"


def test_run_mcp_bridge_denies_before_environment_or_process_setup() -> None:
    assert _SCRIPT_PATH.exists(), f"Missing {_SCRIPT_PATH}"
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    code = re.sub(r"(?m)^#.*$", "", source)
    denial = code.index("MCP bridge startup denied: G1/G2/G3 are not established")
    exit_code = code.index("exit 78", denial)

    for fragment in (
        "$ErrorActionPreference = 'Stop'",
        "$env:PYTHONPATH =",
        "Start-Process -PassThru -NoNewWindow -FilePath $pythonBin",
        "& $cloudflaredBin @tunnelArgs",
    ):
        assert code.index(fragment) > exit_code, fragment


def test_bridge_script_has_no_environmental_startup_bypass() -> None:
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    assert "IABV_SKIP_MCP_AUTOSTART" not in source
