"""Static checks for ``scripts/_mcp_port_utils.ps1``.

Capa 2.1.1: utilidad compartida que mata procesos zombi escuchando el
puerto del MCP antes de spawnear uno nuevo. Es dot-sourced desde
``iabv_bootstrap.ps1`` y ``start_iabv.ps1``.

No corremos PowerShell en CI Linux; validamos forma del script por
fragmentos (el mismo patron que ``test_iabv_bootstrap_script.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "_mcp_port_utils.ps1"


@pytest.fixture(scope="module")
def utils_src() -> str:
    assert _SCRIPT_PATH.exists(), f"Falta {_SCRIPT_PATH}"
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_script_exists(utils_src: str) -> None:
    assert len(utils_src) > 0


@pytest.mark.parametrize(
    "fragment",
    [
        "function Stop-McpZombies",
        "[Parameter(Mandatory)][int]$Port",
        "Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue",
        "Stop-Process -Id $zombiePid -Force -ErrorAction Stop",
        # Idempotencia y mensajes.
        "Puerto :$Port libre",
        # Deduplicacion por PID.
        "Select-Object -ExpandProperty OwningProcess -Unique",
        # Gracia TIME_WAIT.
        "Start-Sleep -Seconds 2",
    ],
)
def test_port_utils_contains_expected_fragment(utils_src: str, fragment: str) -> None:
    assert fragment in utils_src, f"Falta fragmento esperado: {fragment!r}"


def test_port_utils_does_not_use_reserved_pids_var(utils_src: str) -> None:
    """$pids es variable automatica en PowerShell; reasignarla puede romper
    comportamiento. El script debe usar un nombre propio."""
    assert "$pids = " not in utils_src, "No uses $pids (variable automatica); usa $zombiePids"
    assert "$zombiePids" in utils_src


def test_port_utils_is_self_contained(utils_src: str) -> None:
    """La utilidad no debe depender de helpers definidos por el caller
    (ej. Write-Info/Write-Warn2 de iabv_bootstrap.ps1). Debe usar Write-Host
    directo para ser dot-sourceable desde cualquier entry point."""
    # Usamos Write-Host, no los wrappers con sufijo del bootstrap.
    assert "Write-Host" in utils_src
    assert "Write-Info" not in utils_src
    assert "Write-Warn2" not in utils_src
    assert "Write-Ok" not in utils_src


def test_port_utils_tolerates_missing_cmdlet(utils_src: str) -> None:
    """Get-NetTCPConnection puede no existir en algunas ediciones de Windows
    (ej. Nano). El script debe capturar y seguir, no matar al caller."""
    assert "try {" in utils_src
    assert "} catch {" in utils_src
    assert "Get-NetTCPConnection no disponible" in utils_src
