"""Regresion: el devin_api adapter debe tomar su API key de varios env vars.

Antes, ``DevinApiToolAdapter`` se construia con ``os.environ.get('DEVIN_API_KEY', '')``
directo, sin fallback. Si el usuario tenia la key cargada bajo un alias
comun (por ejemplo ``IABV_DEVIN_API_KEY``), el adapter quedaba sin token y
``run_self_audit`` reportaba ``devin_api [missing]`` aunque la key existiera.

Ahora ``_resolve_devin_api_key`` acepta, en orden:

    ``DEVIN_API_KEY_IABV``  (preferido; scope dedicado a IABV)
    ``IABV_DEVIN_API_KEY``
    ``DEVIN_API_KEY``

El orden preserva el scope dedicado primero y cae al nombre generico solo
si ningun alias IABV esta disponible.
"""

from __future__ import annotations

from iabv_v15.bootstrap import _resolve_devin_api_key


def test_prefers_iabv_specific_env_var() -> None:
    env = {
        "DEVIN_API_KEY_IABV": "iabv_key",
        "DEVIN_API_KEY": "global_key",
    }

    assert _resolve_devin_api_key(env) == "iabv_key"


def test_falls_back_to_iabv_prefix_alternative() -> None:
    env = {"IABV_DEVIN_API_KEY": "alt_key"}

    assert _resolve_devin_api_key(env) == "alt_key"


def test_falls_back_to_devin_api_key() -> None:
    env = {"DEVIN_API_KEY": "global_key"}

    assert _resolve_devin_api_key(env) == "global_key"


def test_returns_empty_when_no_key_set() -> None:
    assert _resolve_devin_api_key({}) == ""


def test_treats_whitespace_only_as_empty_and_keeps_looking() -> None:
    env = {
        "DEVIN_API_KEY_IABV": "   ",
        "DEVIN_API_KEY": "real_key",
    }

    assert _resolve_devin_api_key(env) == "real_key"


def test_strips_surrounding_whitespace() -> None:
    env = {"DEVIN_API_KEY_IABV": "  padded_key  "}

    assert _resolve_devin_api_key(env) == "padded_key"
