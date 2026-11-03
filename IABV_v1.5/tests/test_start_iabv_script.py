"""Static checks that the external launcher is disabled before side effects."""

from pathlib import Path
import re

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "start_iabv.ps1"


@pytest.fixture(scope="module")
def source() -> str:
    assert _SCRIPT_PATH.exists(), f"Missing {_SCRIPT_PATH}"
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_launcher_denies_before_checkout_or_process_side_effects(source: str) -> None:
    code = re.sub(r"<#.*?#>", "", source, flags=re.DOTALL)
    code = "\n".join(line.split("#", 1)[0] for line in code.splitlines())
    denial = code.index("MCP bridge startup denied: G1/G2/G3 are not established")
    exit_code = code.index("exit 78", denial)
    param_end = code.index("\n)", code.index("param("))
    assert param_end < denial < exit_code

    for blocked_operation in (
        "New-Item -ItemType Directory",
        "Set-Content -Path $lockFile",
        "& git -C",
        "Stop-McpZombies -Port",
        "Start-Process",
        "& powershell -ExecutionPolicy Bypass -File $bridge",
    ):
        assert code.index(blocked_operation) > exit_code


def test_ordinary_environment_switch_cannot_skip_denial(source: str) -> None:
    code = re.sub(r"<#.*?#>", "", source, flags=re.DOTALL)
    code = "\n".join(line.split("#", 1)[0] for line in code.splitlines())
    denial = code.index("exit 78")
    assert code.index("IABV_SKIP_MCP_AUTOSTART") > denial
    assert code.index("run_mcp_bridge.ps1") > denial
