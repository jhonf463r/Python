"""Resumen humano en espanol de los commits entre dos SHAs.

Se invoca desde ``scripts/start_iabv.ps1`` cuando el auto-pull trajo
commits nuevos, para que el usuario entienda en 3-5 bullets que cambio
sin tener que leer el ``git log`` ni los diffs.

Estrategia:
1. Intentamos pedirle el resumen a Ollama local (modelo chico, para no
   romper el arranque si el server no esta prendido).
2. Si Ollama no responde o falla, caemos a una plantilla deterministica
   basada en ``git log --oneline <old>..<new>``. Siempre devolvemos
   bullets en espanol, estilo humano, nunca el diff crudo.

Uso:

    python -m iabv_v15.scripts.summarize_updates <old_sha> <new_sha>

No toca el repo ni persiste nada: solo imprime a stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Iterable, Sequence

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen3:8b"
MAX_BULLETS = 5
MIN_BULLETS = 3


def _run_git_log(old_sha: str, new_sha: str) -> list[str]:
    """Devuelve las lineas de ``git log --oneline <old>..<new>``.

    Se ejecuta en el cwd actual; ``start_iabv.ps1`` ya nos invoca desde
    el repo. Si git falla (sha desconocido, repo invalido), devolvemos
    lista vacia para que el caller maneje la condicion.
    """

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{old_sha}..{new_sha}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines


def _ask_ollama(commits: Sequence[str], *, url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL, timeout: float = 15.0) -> str:
    """Intenta generar un resumen con Ollama local.

    Devuelve el texto crudo del modelo (que luego normalizamos). Lanza
    ``RuntimeError`` si Ollama no responde o no devuelve contenido util;
    el caller decide si caer al fallback.
    """

    prompt = (
        "Resume estos commits en espanol neutro, en 3 a 5 bullets cortos, "
        "estilo humano (nada de codigo, nada de diffs, nada de SHAs). "
        "Habla como si le explicaras a un usuario no tecnico que cambio "
        "en su herramienta. Usa viñetas que empiecen con '- '.\n\n"
        "Commits:\n" + "\n".join(f"- {line}" for line in commits)
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"ollama no disponible: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ollama respuesta invalida: {exc}") from exc
    response = (parsed.get("response") or "").strip()
    if not response:
        raise RuntimeError("ollama devolvio texto vacio")
    return response


def _normalize_bullets(text: str) -> list[str]:
    """Convierte la salida cruda del LLM en bullets limpios.

    Aceptamos lineas que empiezan con ``-``, ``*`` o ``•``. Recortamos
    a ``MAX_BULLETS`` y descartamos lineas vacias. Si el modelo devolvio
    un parrafo sin bullets, lo partimos por oraciones como fallback
    suave dentro del fallback (para no quedarnos con un bloque gigante).
    """

    bullets: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        for prefix in ("- ", "* ", "• ", "– "):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break
        else:
            enum_match = re.match(r"^\d+[.)]\s*", line)
            if enum_match:
                line = line[enum_match.end():].strip()
        if line:
            bullets.append(line)
    if not bullets:
        pieces = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
        bullets = pieces[:MAX_BULLETS]
    return bullets[:MAX_BULLETS]


def _fallback_bullets(commits: Sequence[str]) -> list[str]:
    """Genera bullets en espanol a partir del ``git log --oneline``.

    No intenta ser inteligente: devuelve los primeros ``MAX_BULLETS``
    commits limpiados de su SHA corto inicial. Esto garantiza que el
    usuario siempre vea algo util, aunque Ollama este apagado.
    """

    cleaned: list[str] = []
    for line in commits:
        parts = line.split(None, 1)
        message = parts[1].strip() if len(parts) == 2 else line
        if message:
            cleaned.append(message)
    if not cleaned:
        return ["Se aplicaron cambios sin mensaje descriptivo visible."]
    return cleaned[:MAX_BULLETS]


def build_summary(
    old_sha: str,
    new_sha: str,
    *,
    git_log_fn=_run_git_log,
    ollama_fn=_ask_ollama,
) -> list[str]:
    """Arma el resumen final como lista de bullets en espanol.

    Parametros ``git_log_fn`` y ``ollama_fn`` existen para que los tests
    puedan inyectar stubs y no dependan de git ni de Ollama reales.
    """

    commits = git_log_fn(old_sha, new_sha)
    if not commits:
        return [
            f"No se detectaron commits nuevos entre {old_sha[:8]} y {new_sha[:8]}.",
        ]
    try:
        raw = ollama_fn(commits)
        bullets = _normalize_bullets(raw)
        if len(bullets) >= MIN_BULLETS:
            return bullets
    except Exception:
        pass
    return _fallback_bullets(commits)


def format_bullets(bullets: Iterable[str]) -> str:
    return "\n".join(f"- {b}" for b in bullets)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="iabv_v15.scripts.summarize_updates",
        description="Resume commits entre dos SHAs en 3-5 bullets en espanol.",
    )
    parser.add_argument("old_sha", help="SHA previo al pull (HEAD antes de sincronizar).")
    parser.add_argument("new_sha", help="SHA actual (HEAD despues del pull).")
    args = parser.parse_args(argv)

    bullets = build_summary(args.old_sha, args.new_sha)
    header = f"Resumen de cambios ({args.old_sha[:8]} -> {args.new_sha[:8]}):"
    print(header)
    print(format_bullets(bullets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
