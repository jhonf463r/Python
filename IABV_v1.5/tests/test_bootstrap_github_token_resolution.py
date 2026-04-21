"""Regresion: el github_api adapter debe tomar su token de varios env vars.

Antes, `GitHubApiToolAdapter` solo miraba ``GITHUB_TOKEN_IABV``. Cuando
el usuario arrancaba el MCP en su laptop con un PAT cargado como
``GITHUB_TOKEN`` (convencion de ``gh`` CLI y de muchas CIs), el adapter
quedaba sin token y `run_self_audit` reportaba ``github_api [missing]``
aunque el token existiera realmente en el entorno.

Ahora `_resolve_github_token` acepta, en orden:

    ``GITHUB_TOKEN_IABV``  (preferido; scope dedicado a IABV)
    ``IABV_GITHUB_TOKEN``
    ``GITHUB_TOKEN``
    ``GH_TOKEN``

El orden preserva la intencion original (scope dedicado gana si existe)
pero evita que el usuario tenga que duplicar el PAT solo para IABV.
"""

from __future__ import annotations

from iabv_v15.bootstrap import _resolve_github_token


def test_prefers_iabv_specific_env_var() -> None:
    env = {
        "GITHUB_TOKEN_IABV": "iabv_pat",
        "GITHUB_TOKEN": "global_pat",
    }

    assert _resolve_github_token(env) == "iabv_pat"


def test_falls_back_to_iabv_prefix_alternative() -> None:
    env = {"IABV_GITHUB_TOKEN": "alt_pat"}

    assert _resolve_github_token(env) == "alt_pat"


def test_falls_back_to_github_token() -> None:
    env = {"GITHUB_TOKEN": "global_pat"}

    assert _resolve_github_token(env) == "global_pat"


def test_falls_back_to_gh_token_last() -> None:
    env = {"GH_TOKEN": "gh_cli_pat"}

    assert _resolve_github_token(env) == "gh_cli_pat"


def test_returns_empty_when_no_token_set() -> None:
    assert _resolve_github_token({}) == ""


def test_treats_whitespace_only_as_empty_and_keeps_looking() -> None:
    env = {
        "GITHUB_TOKEN_IABV": "   ",
        "GITHUB_TOKEN": "real_pat",
    }

    assert _resolve_github_token(env) == "real_pat"


def test_strips_surrounding_whitespace() -> None:
    env = {"GITHUB_TOKEN_IABV": "  padded_pat  "}

    assert _resolve_github_token(env) == "padded_pat"
