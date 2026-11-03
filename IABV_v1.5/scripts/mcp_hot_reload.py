"""Disabled hot-reload wrapper for the MCP server of IABV v1.5.

The current entry point returns a denial without starting a watcher or
subprocess. The historical behavior below documents why this wrapper exists.

Uso:

    $env:IABV_MCP_HOT_RELOAD='1'
    python -m scripts.mcp_hot_reload

o desde ``start_iabv.ps1 -HotReload``.

Semantica:
- Polling simple por ``stat().st_mtime`` (sin dependencias nuevas como
  watchdog).
- Intervalo configurable via ``IABV_MCP_HOT_RELOAD_INTERVAL`` (default 2s).
- Solo reinicia si hay cambios reales desde la ultima revision. Si el
  subprocess se muere solo (crash), tambien lo respawnea.

Contratos respetados (ver ``AGENTS.md``):
- No crea otro cerebro ni orquestador: solo envuelve el mismo ``run()``.
- No toca el estado vivo; el WorldModel se reconstruye naturalmente en
  cada arranque del MCP.
- Si el reload es abusivo se desactiva con ``IABV_MCP_HOT_RELOAD`` != 1.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Iterator


logger = logging.getLogger("iabv.mcp.hot_reload")


def iter_watch_files(root: Path) -> Iterator[Path]:
    """Recorre ``root`` y emite cada ``.py`` legible.

    Ignora ``__pycache__`` y cualquier cosa no-.py. Pensado para correr
    sobre ``src/iabv_v15`` en el repo IABV. Si ``root`` no existe, no
    emite nada (no explota).
    """

    if not root.exists():
        return
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def snapshot_mtimes(paths: Iterable[Path]) -> dict[str, float]:
    """Captura mtimes como dict ``{path_str: mtime}``.

    Si un archivo desaparece (race condition entre ``rglob`` y ``stat``)
    lo omite en vez de explotar.
    """

    snapshot: dict[str, float] = {}
    for path in paths:
        try:
            snapshot[str(path)] = path.stat().st_mtime
        except FileNotFoundError:
            continue
    return snapshot


def changed_paths(
    previous: dict[str, float],
    current: dict[str, float],
) -> list[str]:
    """Devuelve las rutas con mtime distinto o nuevas/borradas.

    Pure function para que sea testeable sin disco.
    """

    changes: list[str] = []
    keys = set(previous) | set(current)
    for key in keys:
        if previous.get(key) != current.get(key):
            changes.append(key)
    return sorted(changes)


def _resolve_watch_root() -> Path:
    """Ruta raiz a vigilar. Por defecto ``src/iabv_v15`` junto a este script."""

    override = os.environ.get("IABV_MCP_HOT_RELOAD_ROOT")
    if override:
        return Path(override).resolve()
    script_dir = Path(__file__).resolve().parent
    return (script_dir.parent / "src" / "iabv_v15").resolve()


def _resolve_interval() -> float:
    raw = os.environ.get("IABV_MCP_HOT_RELOAD_INTERVAL", "2")
    try:
        value = float(raw)
    except ValueError:
        return 2.0
    return max(0.2, value)


START_DENIED_EXIT_CODE = 78


def _spawn_server() -> subprocess.Popen[bytes]:
    """Reject subprocess creation until an authorized startup path exists."""

    raise RuntimeError("MCP_START_AUTHORIZATION_NOT_ESTABLISHED")


def _terminate_server(proc: subprocess.Popen[bytes], timeout: float = 5.0) -> None:
    if proc.poll() is not None:
        return
    logger.info("terminating MCP server pid=%s", proc.pid)
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
    except Exception as exc:
        logger.warning("terminate failed: %s", exc)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning("SIGTERM no respondio en %.1fs; kill -9", timeout)
        proc.kill()
        proc.wait()


def run_forever() -> int:
    """Fail closed without entering a watcher or respawn loop."""

    return START_DENIED_EXIT_CODE


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(run_forever())
