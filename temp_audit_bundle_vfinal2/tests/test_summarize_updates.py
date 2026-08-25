"""Tests para ``iabv_v15.scripts.summarize_updates``.

No dependemos ni de ``git`` real ni de un servidor Ollama: inyectamos
stubs via los parametros ``git_log_fn`` y ``ollama_fn`` de
``build_summary``, mas un test de integracion liviano sobre ``main``
que mockea ``subprocess.run`` y ``urllib.request.urlopen``.
"""

from __future__ import annotations

import io
import json
import subprocess
from typing import Sequence

import pytest

from iabv_v15.scripts import summarize_updates


def test_build_summary_uses_ollama_when_it_returns_bullets():
    commits = ["abc1234 feat: algo", "def5678 fix: otra cosa"]

    def fake_git_log(old: str, new: str) -> list[str]:
        assert old == "OLD"
        assert new == "NEW"
        return commits

    def fake_ollama(lines: Sequence[str]) -> str:
        assert list(lines) == commits
        return (
            "- Ahora el arranque sincroniza el workspace automaticamente.\n"
            "- Se agrego un resumen humano de los cambios recientes.\n"
            "- Se mejoro el mensaje cuando el pull falla por divergencia.\n"
        )

    bullets = summarize_updates.build_summary(
        "OLD",
        "NEW",
        git_log_fn=fake_git_log,
        ollama_fn=fake_ollama,
    )

    assert len(bullets) >= summarize_updates.MIN_BULLETS
    assert all(isinstance(b, str) and b.strip() for b in bullets)
    assert not any(b.startswith("- ") for b in bullets), "bullets no deben repetir el prefijo"


def test_build_summary_falls_back_when_ollama_raises():
    commits = [
        "abc1234 feat(chat): ingest user-declared capabilities",
        "def5678 fix(chat): expose devin_api + github_api",
        "aaa0001 chore: bump version",
    ]

    def fake_git_log(old: str, new: str) -> list[str]:
        return commits

    def broken_ollama(lines: Sequence[str]) -> str:
        raise RuntimeError("ollama apagado")

    bullets = summarize_updates.build_summary(
        "OLD",
        "NEW",
        git_log_fn=fake_git_log,
        ollama_fn=broken_ollama,
    )

    assert bullets, "el fallback debe devolver algo no vacio"
    assert any("feat(chat)" in b for b in bullets)
    # el fallback no debe incluir el SHA corto
    assert all("abc1234" not in b for b in bullets)


def test_build_summary_handles_empty_commits():
    bullets = summarize_updates.build_summary(
        "a" * 40,
        "b" * 40,
        git_log_fn=lambda _o, _n: [],
        ollama_fn=lambda _c: "nunca se llama",
    )
    assert len(bullets) == 1
    assert "No se detectaron commits" in bullets[0]


def test_build_summary_uses_fallback_when_ollama_returns_too_few_bullets():
    commits = ["abc feat: uno", "def fix: dos", "ghi chore: tres"]

    def only_one_bullet(_lines: Sequence[str]) -> str:
        return "- Solo un bullet."

    bullets = summarize_updates.build_summary(
        "OLD",
        "NEW",
        git_log_fn=lambda _o, _n: commits,
        ollama_fn=only_one_bullet,
    )

    # Debe caer al fallback (que preserva los mensajes de commit).
    assert any("feat: uno" in b for b in bullets)
    assert any("fix: dos" in b for b in bullets)


def test_normalize_bullets_strips_common_prefixes():
    raw = "- Uno\n* Dos\n• Tres\n1. Cuatro\n2) Cinco"
    bullets = summarize_updates._normalize_bullets(raw)
    assert bullets[:5] == ["Uno", "Dos", "Tres", "Cuatro", "Cinco"]


def test_fallback_bullets_without_commits_returns_default():
    assert summarize_updates._fallback_bullets([]) == [
        "Se aplicaron cambios sin mensaje descriptivo visible."
    ]


def test_main_prints_bullets_with_mocked_subprocess(monkeypatch, capsys):
    """Integracion liviana: mockea git y ollama a nivel subprocess/urllib."""

    fake_log = "abc1234 feat: auto-pull en start_iabv\ndef5678 fix: mensaje claro en divergencia\n"

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        assert cmd[:2] == ["git", "log"]
        return subprocess.CompletedProcess(cmd, 0, stdout=fake_log, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    class FakeResp:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    def fake_urlopen(req, timeout):  # noqa: ANN001
        body = json.dumps(
            {
                "response": (
                    "- Auto-pull antes de arrancar.\n"
                    "- Mensaje claro cuando hay divergencia.\n"
                    "- Resumen humano de los commits nuevos.\n"
                )
            }
        ).encode("utf-8")
        return FakeResp(body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    rc = summarize_updates.main(["OLDSHA00", "NEWSHA11"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Resumen de cambios" in out
    # Debe haber al menos 3 bullets en la salida.
    assert out.count("\n- ") >= summarize_updates.MIN_BULLETS


def test_ask_ollama_raises_on_empty_response(monkeypatch):
    class FakeResp:
        def read(self) -> bytes:
            return json.dumps({"response": ""}).encode("utf-8")

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: FakeResp())
    with pytest.raises(RuntimeError):
        summarize_updates._ask_ollama(["abc feat: x"])
