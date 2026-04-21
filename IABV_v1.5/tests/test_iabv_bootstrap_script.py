"""Static checks for ``scripts/iabv_bootstrap.ps1``.

No lanzamos PowerShell (no esta garantizado en CI Linux). Validamos que el
script existe, incluye los pasos documentados y los delega a los otros
scripts del bundle. Esto previene regresiones silenciosas (alguien borra
el paso de ``rotate_tokens.ps1``, etc.).
"""

from __future__ import annotations

from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "iabv_bootstrap.ps1"


@pytest.fixture(scope="module")
def bootstrap_src() -> str:
    assert _SCRIPT_PATH.exists(), f"Falta {_SCRIPT_PATH}"
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_script_exists(bootstrap_src: str) -> None:
    assert len(bootstrap_src) > 0


@pytest.mark.parametrize(
    "fragment",
    [
        "Install-GhPortable",
        "Install-CloudflaredPortable",
        "setup_iabv_profile.ps1",
        "rotate_tokens.ps1",
        "start_iabv.ps1",
        # Version pin para reproducibilidad.
        "$ghVersion = '2.90.0'",
        "cloudflared-windows-amd64.exe",
        # Verificacion de integridad del ZIP de gh.
        "$ghZipSha256",
        "SHA256 mismatch",
        # Flags documentados.
        "[switch]$Force",
        "[switch]$NoStart",
        "[switch]$SkipInstalls",
        # Persistencia del PATH.
        "Add-ToProfilePath",
        # No asume admin.
        "$HOME\\.iabv\\tools",
    ],
)
def test_bootstrap_contains_expected_fragment(bootstrap_src: str, fragment: str) -> None:
    assert fragment in bootstrap_src, f"Falta fragmento esperado: {fragment!r}"


def test_bootstrap_references_only_official_hosts(bootstrap_src: str) -> None:
    """Paranoia: no bajamos binarios desde CDNs random."""
    bad_hosts = ("cdn.", "mirror.", "dropbox.", "we-transfer", "bit.ly")
    for host in bad_hosts:
        assert host not in bootstrap_src, f"URL sospechosa en script: {host}"
    # Y los oficiales si tienen que estar:
    assert "github.com/cli/cli/releases" in bootstrap_src
    assert "github.com/cloudflare/cloudflared" in bootstrap_src


def test_bootstrap_does_not_require_admin(bootstrap_src: str) -> None:
    """El script no deberia invocar elevacion."""
    for token in ("Start-Process.*-Verb RunAs", "RequireAdministrator", "elevate"):
        # Chequeos simples por fragmento, no regex estricto.
        assert token.lower() not in bootstrap_src.lower(), token


def test_bootstrap_references_rotate_tokens_fix(bootstrap_src: str) -> None:
    """El bootstrap debe delegar la rotacion al script que ya tiene el fix
    de stderr para ``gh auth status``; no debe duplicar esa logica."""
    # rotate_tokens.ps1 es el unico lugar donde vive el fix. El bootstrap
    # debe invocarlo, no reimplementarlo.
    assert "rotate_tokens.ps1" in bootstrap_src
    assert "gh auth login" not in bootstrap_src, (
        "No duplicar device-flow; delegar a rotate_tokens.ps1"
    )
