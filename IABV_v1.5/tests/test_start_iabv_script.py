"""Static checks for ``scripts/start_iabv.ps1``.

Cubre dos contratos que viven en el mismo script:

- Flag ``-StartUI`` (issue #136 / PR #140): spawnea la ventana
  ControlCenter via ``python -m iabv_v15 app`` en un proceso aparte no
  bloqueante, sin matar el MCP si la UI falla.
- Capa 2.1.1 (PR #132 + PR #133): el entry point tambien debe limpiar
  zombis en el puerto antes de delegar en ``run_mcp_bridge.ps1``, via la
  utilidad compartida ``_mcp_port_utils.ps1``.

No lanzamos PowerShell (no esta garantizado en CI Linux). Validamos que el
script existe y que contiene los fragmentos necesarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "start_iabv.ps1"


@pytest.fixture(scope="module")
def start_iabv_src() -> str:
    assert _SCRIPT_PATH.exists(), f"Falta {_SCRIPT_PATH}"
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_script_exists(start_iabv_src: str) -> None:
    assert len(start_iabv_src) > 0


# ---------------------------------------------------------------------------
# -StartUI flag (issue #136 / PR #140)
# ---------------------------------------------------------------------------


def test_declares_start_ui_switch(start_iabv_src: str) -> None:
    """El parametro ``-StartUI`` debe estar declarado como [switch]."""
    assert "[switch]$StartUI" in start_iabv_src


@pytest.mark.parametrize(
    "fragment",
    [
        # Pre-existentes (regresion): otros flags siguen vivos.
        "[switch]$SkipHealthChecks",
        "[switch]$HotReload",
        "[switch]$Quiet",
        # Comment-based help para StartUI (paso 4 del issue).
        ".PARAMETER StartUI",
        # Guardia del flag.
        "if ($StartUI)",
        # Spawn no bloqueante via Start-Process (paso 3 del issue).
        "Start-Process",
        # Comando hacia el modulo iabv_v15 (paso 2 del issue).
        "'-m','iabv_v15','app'",
        # Seguridad: si la UI falla, NO matar el MCP.
        "try {",
        "} catch {",
        # El bridge (MCP + tunel) sigue siendo el punto de arranque principal.
        "run_mcp_bridge.ps1",
    ],
)
def test_start_iabv_contains_expected_fragment(
    start_iabv_src: str, fragment: str
) -> None:
    assert fragment in start_iabv_src, f"Falta fragmento esperado: {fragment!r}"


def test_start_ui_uses_start_process_with_iabv_module(start_iabv_src: str) -> None:
    """Con ``-StartUI``, el script debe invocar ``python -m iabv_v15 app``
    via ``Start-Process`` (no bloqueante). Validamos que ambos fragmentos
    caen dentro del bloque ``if ($StartUI) { ... }``."""
    start = start_iabv_src.index("if ($StartUI)")
    # Tomamos un pedazo generoso despues del if para cubrir el bloque completo.
    block = start_iabv_src[start : start + 1500]
    assert "Start-Process" in block, "Debe usarse Start-Process (no bloqueante)"
    assert "'-m','iabv_v15','app'" in block, (
        "Debe generarse el comando 'python -m iabv_v15 app' como argumentos "
        "de Start-Process"
    )


def test_start_ui_failure_does_not_kill_mcp(start_iabv_src: str) -> None:
    """Contrato del issue: si la UI falla, se loguea el error pero el MCP
    sigue vivo. Validamos que el spawn esta envuelto en try/catch y que el
    `& ... $bridge` (blocking MCP launch) se ejecuta DESPUES del bloque
    de lanzamiento de UI, no antes ni dentro del catch."""
    ui_if_idx = start_iabv_src.index("if ($StartUI)")
    # El bloque debe contener try/catch propio.
    catch_idx = start_iabv_src.index("} catch {", ui_if_idx)
    # El bridge debe lanzarse despues (fuera) del bloque del if.
    bridge_idx = start_iabv_src.rindex("& powershell -ExecutionPolicy Bypass -File $bridge")
    assert ui_if_idx < catch_idx < bridge_idx, (
        "El spawn de UI debe estar en try/catch y el bridge debe lanzarse "
        "despues, para que un fallo de UI no tumbe el MCP."
    )


def test_start_ui_documented_in_header(start_iabv_src: str) -> None:
    """La ayuda rapida (`# Opciones:`) tambien debe mencionar ``-StartUI``."""
    assert "-StartUI" in start_iabv_src
    # Y especificamente dentro del bloque de opciones de cabecera.
    header_end = start_iabv_src.index("<#")
    header = start_iabv_src[:header_end]
    assert "-StartUI" in header, (
        "El flag -StartUI debe aparecer tambien en el header de ayuda rapida"
    )


# ---------------------------------------------------------------------------
# Capa 2.1.1: kill MCP zombi antes del bridge (PR #132 + PR #133)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fragment",
    [
        # Capa 2.1.1 aca tambien.
        "[int]$McpPort",
        "Stop-McpZombies -Port $McpPort",
        ". (Join-Path $PSScriptRoot '_mcp_port_utils.ps1')",
    ],
)
def test_start_contains_mcp_port_fragment(
    start_iabv_src: str, fragment: str
) -> None:
    assert fragment in start_iabv_src, f"Falta fragmento esperado: {fragment!r}"


def test_start_kills_mcp_zombie_before_bridge(start_iabv_src: str) -> None:
    """El kill debe correr ANTES de spawnear el bridge; si no, el nuevo MCP
    falla por puerto ocupado y el kill ya no sirve."""
    kill_idx = start_iabv_src.index("Stop-McpZombies -Port $McpPort")
    # La invocacion real al bridge es la linea que empieza con "& powershell".
    bridge_idx = start_iabv_src.rindex("& powershell -ExecutionPolicy Bypass -File $bridge")
    assert kill_idx < bridge_idx, (
        "Stop-McpZombies debe ejecutarse antes del bridge"
    )


def test_start_does_not_redefine_stop_mcp_zombies(start_iabv_src: str) -> None:
    """No duplicar la implementacion: debe venir del dot-source de
    _mcp_port_utils.ps1 (misma utilidad que usa iabv_bootstrap.ps1)."""
    assert "function Stop-McpZombies" not in start_iabv_src


def test_start_does_not_require_admin(start_iabv_src: str) -> None:
    """El script no deberia invocar elevacion."""
    for token in ("Start-Process.*-Verb RunAs", "RequireAdministrator", "elevate"):
        assert token.lower() not in start_iabv_src.lower(), token
