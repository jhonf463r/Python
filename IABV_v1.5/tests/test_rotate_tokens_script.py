"""Static checks for ``scripts/rotate_tokens.ps1``.

No podemos ejecutar PowerShell en CI Linux; validamos que el fix del
``gh auth status`` (stderr tratado como error fatal bajo
``$ErrorActionPreference='Stop'``) sigue presente y que el script no
regresa al patron inseguro de antes.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "rotate_tokens.ps1"


@pytest.fixture(scope="module")
def rotate_src() -> str:
    assert _SCRIPT_PATH.exists(), f"Falta {_SCRIPT_PATH}"
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_gh_auth_status_downgrades_error_action_preference(rotate_src: str) -> None:
    """`gh auth status` escribe a stderr cuando no hay login y bajo
    `$ErrorActionPreference='Stop'` eso mata el script antes de poder
    leer `$LASTEXITCODE`. El script debe bajar el preference localmente
    alrededor de esa llamada."""
    # El bloque concreto del fix.
    assert "$ErrorActionPreference = 'Continue'" in rotate_src
    assert "gh auth status --hostname github.com" in rotate_src
    assert "$ghStatusExit" in rotate_src
    # Se restaura el preference previo.
    assert "$ErrorActionPreference = $prevEAP" in rotate_src


def test_device_flow_is_used_for_github(rotate_src: str) -> None:
    assert "gh auth login --hostname github.com --git-protocol https --scopes repo --web" in rotate_src


def test_devin_key_uses_secure_input(rotate_src: str) -> None:
    assert "Read-Host -AsSecureString" in rotate_src
    # Validacion HTTP 200 ANTES de escribir.
    assert "La key no es valida. No la escribo al archivo." in rotate_src


def test_flags_exposed(rotate_src: str) -> None:
    for flag in ("$ForceGitHub", "$ForceDevin", "$SkipGitHub", "$SkipDevin"):
        assert flag in rotate_src, f"Falta flag {flag}"
