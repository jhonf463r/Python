"""Static checks for ``scripts/start_iabv.ps1``.

Cubre tres contratos que viven en el mismo script:

- Flag ``-StartUI`` (issue #136 / PR #140): spawnea la ventana
  ControlCenter via ``python -m iabv_v15 app`` en un proceso aparte no
  bloqueante, sin matar el MCP si la UI falla.
- Capa 2.1.1 (PR #132 + PR #133): el entry point tambien debe limpiar
  zombis en el puerto antes de delegar en ``run_mcp_bridge.ps1``, via la
  utilidad compartida ``_mcp_port_utils.ps1``.
- Flags ``-AutoPull`` / ``-NoAutoPull`` (issue #139 / PR #141): auto
  ``git pull --rebase=false`` con resumen humano, sin forzar merges.

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


# ---------------------------------------------------------------------------
# -AutoPull / -NoAutoPull (issue #139 / PR #141)
# ---------------------------------------------------------------------------


import re  # noqa: E402


@pytest.fixture(scope="module")
def script_text() -> str:
    assert _SCRIPT_PATH.exists(), f"no existe {_SCRIPT_PATH}"
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_declares_autopull_switch_default_on(script_text: str) -> None:
    # El default debe ser ON: '[switch]$AutoPull = $true'
    assert re.search(r"\[switch\]\s*\$AutoPull\s*=\s*\$true", script_text), (
        "se espera que -AutoPull este declarado y por defecto en $true"
    )


def test_declares_noautopull_switch(script_text: str) -> None:
    assert re.search(r"\[switch\]\s*\$NoAutoPull", script_text), (
        "se espera que exista el switch -NoAutoPull para desactivar el auto-pull"
    )


def test_noautopull_disables_autopull(script_text: str) -> None:
    # Debe existir una rama explicita que apague AutoPull cuando
    # NoAutoPull esta presente.
    pattern = re.compile(
        r"if\s*\(\s*\$NoAutoPull\s*\)\s*\{[^}]*\$AutoPull\s*=\s*\$false",
        re.DOTALL,
    )
    assert pattern.search(script_text), (
        "-NoAutoPull debe forzar \\$AutoPull = \\$false para que el pull no corra"
    )


def test_pull_lives_inside_autopull_branch(script_text: str) -> None:
    """El ``git pull --rebase=false`` solo debe ocurrir si ``$AutoPull`` es true.

    Verificamos por orden de aparicion (mas robusto que intentar parsear
    llaves balanceadas de PowerShell con regex):

    1. Debe aparecer ``if ($AutoPull)`` antes de ``git pull --rebase=false``.
    2. Debe aparecer el branch ``else`` (del mismo if) despues del pull
       (el else reporta 'Auto-pull : OFF').
    3. No debe haber NINGUN ``git pull --rebase=false`` fuera de ese rango.
    """

    if_pos = script_text.find("if ($AutoPull)")
    assert if_pos != -1, "se espera un bloque 'if ($AutoPull)'"

    # Buscamos la INVOCACION real del pull (lineas que empiezan con '& git'
    # o '& git -C ... pull --rebase=false'), no las menciones en comentarios.
    invocation_pattern = re.compile(
        r"^[ \t]*&\s*git\b[^\n]*\bpull\s+--rebase=false", re.MULTILINE
    )
    invocations = [m.start() for m in invocation_pattern.finditer(script_text)]
    assert len(invocations) == 1, (
        f"se espera exactamente una invocacion real de git pull --rebase=false, "
        f"se encontraron {len(invocations)}"
    )
    pull_pos = invocations[0]
    assert pull_pos > if_pos, "la invocacion del pull debe estar despues del if"

    # El ``else`` con el mensaje OFF indica el cierre del if principal.
    off_pos = script_text.find("Auto-pull : OFF", pull_pos)
    assert off_pos != -1, "se espera un else que reporte 'Auto-pull : OFF'"
    assert off_pos > pull_pos


def test_aborts_on_pull_failure_without_forcing(script_text: str) -> None:
    # Si el pull falla, abortamos. No hay rastro de --force ni reset --hard.
    assert re.search(r"git pull --rebase=false", script_text), "debe usar --rebase=false"
    assert "exit 1" in script_text, "debe abortar con exit 1 cuando el pull falla"
    assert "--force" not in script_text, "NO debe forzar merges"
    assert "reset --hard" not in script_text, "NO debe resetear a la fuerza"


def test_invokes_summarize_updates_module(script_text: str) -> None:
    assert "iabv_v15.scripts.summarize_updates" in script_text, (
        "cuando hay commits nuevos, debe invocar python -m iabv_v15.scripts.summarize_updates"
    )
    # Y debe pasarle old y new SHA (variables $oldSha y $newSha).
    assert "$oldSha" in script_text and "$newSha" in script_text
