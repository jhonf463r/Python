"""Tools de observación pasiva para el MCP server (F1.3).

Módulo sibling a `audit_tools.py`. Convención: cada frente agrega sus
tools en un módulo propio (`audit_tools_<tema>.py`) en vez de tocar
`audit_tools.py` directo. Esto evita conflicts entre frentes paralelos
(F1.3 / F3.1 / F3.2 / F3.3) y mantiene `audit_tools.py` como el core
estable (paths, pytest, git, read/list).

Cuatro tools expuestas:
    * `list_open_windows` — ventanas top-level visibles (título, pid,
      rect, foreground) en Windows; degrada en otras plataformas.
    * `list_running_processes` — procesos del sistema (pid, name, exe,
      cmdline, create_time) vía psutil, con cmdline sanitizado.
    * `read_clipboard` — contenido de texto del portapapeles vía
      pyperclip, con tkinter como fallback.
    * `dump_qml_tree` — árbol QObject/QQuickItem de la UI IABV si hay
      QApplication viva en el mismo proceso.

Contrato:
    * Nunca levantan: cualquier error se traduce a un dict
      `{"error": "...", "detail": "..."}`.
    * Si la dependencia nativa falta (pywin32, psutil, pyperclip,
      PySide6), devuelven `{"error": "not_supported_platform"}` o
      `{"error": "dependency_missing", "dependency": "..."}`.
    * El gate de governance queda en el `server.py` (`assistant_kind=
      "audit"`, `requires_network=False`), no en el helper.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes

MAX_PROCESSES_DEFAULT = 500
MAX_PROCESSES_HARD = 5000
MAX_CLIPBOARD_BYTES = 64 * 1024
MAX_CMDLINE_CHARS = 512
MAX_QML_NODES = 2000

_SENSITIVE_TOKEN_PATTERNS = (
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "api-key",
    "apikey",
    "private_key",
    "private-key",
    "auth",
)


def _sanitize_cmdline(parts: list[str] | None) -> list[str]:
    """Acorta args y redacta tokens sospechosos en cmdlines de procesos.

    Soporta las dos formas usuales:
        * ``--token=sk-abc`` → ``--token=<redacted>`` (valor inline).
        * ``--token sk-abc`` → ``<redacted>`` + ``<redacted>`` (el siguiente
          arg se redacta incondicionalmente porque es el valor posicional
          del flag sensible).
    """

    if not parts:
        return []
    out: list[str] = []
    redact_next = False
    for raw in parts[:50]:  # max 50 args por proceso
        if not isinstance(raw, str):
            # Un elemento no-string no puede coincidir con patrones
            # sensibles, pero sí consume el "slot" del valor posicional
            # si venimos de un flag sensible. Redactamos y reseteamos el
            # flag para no propagar la redacción al siguiente string.
            if redact_next:
                out.append("<redacted>")
                redact_next = False
            continue
        if redact_next:
            out.append("<redacted>")
            redact_next = False
            continue
        lowered = raw.lower()
        if any(token in lowered for token in _SENSITIVE_TOKEN_PATTERNS):
            if "=" in raw:
                key = raw.split("=", 1)[0]
                out.append(f"{key}=<redacted>")
            else:
                # `--token sk-abc`: redactar el flag y también el valor
                # posicional que viene en la próxima iteración.
                out.append("<redacted>")
                redact_next = True
            continue
        if len(raw) > MAX_CMDLINE_CHARS:
            out.append(raw[:MAX_CMDLINE_CHARS] + "...<truncated>")
        else:
            out.append(raw)
    return out


# ---------------------------------------------------------------------------
# list_open_windows


def list_open_windows() -> dict[str, Any]:
    """Lista ventanas top-level visibles (Windows, vía pywin32).

    Payload éxito::

        {
          "platform": "windows",
          "windows": [
            {"hwnd": 1234, "title": "IABV v1.5 — Control Center",
             "pid": 16952, "rect": [x, y, w, h],
             "is_visible": true, "is_foreground": false},
            ...
          ],
          "count": N,
          "foreground_hwnd": 1234 | null
        }

    Fuera de Windows o sin pywin32: ``{error: "not_supported_platform"}``.
    """

    if platform.system().lower() != "windows":
        return {
            "error": "not_supported_platform",
            "detail": (
                f"list_open_windows sólo corre en Windows (current={platform.system()})."
            ),
        }
    try:
        import win32con  # type: ignore
        import win32gui  # type: ignore
        import win32process  # type: ignore
    except Exception as exc:
        return {
            "error": "dependency_missing",
            "dependency": "pywin32",
            "detail": f"pywin32 no importable: {exc!r}",
        }

    try:
        foreground_hwnd = int(win32gui.GetForegroundWindow() or 0) or None
    except Exception:
        foreground_hwnd = None

    windows: list[dict[str, Any]] = []

    def _enum(hwnd: int, _lparam: object) -> bool:
        try:
            if not win32gui.IsWindow(hwnd):
                return True
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            if not title:
                return True
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(0, int(right) - int(left))
            height = max(0, int(bottom) - int(top))
            try:
                _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
                pid = int(pid)
            except Exception:
                pid = 0
            windows.append(
                {
                    "hwnd": int(hwnd),
                    "title": title[:256],
                    "pid": pid,
                    "rect": [int(left), int(top), width, height],
                    "is_visible": True,
                    "is_foreground": foreground_hwnd is not None and int(hwnd) == foreground_hwnd,
                }
            )
        except Exception as exc:  # pragma: no cover - defensivo por ventana rara
            logger.debug("enum window hwnd=%s error=%r", hwnd, exc)
        return True

    try:
        win32gui.EnumWindows(_enum, None)
    except Exception as exc:
        return {"error": "enum_windows_failed", "detail": repr(exc)}

    return {
        "platform": "windows",
        "windows": windows,
        "count": len(windows),
        "foreground_hwnd": foreground_hwnd,
    }


# ---------------------------------------------------------------------------
# list_running_processes


def list_running_processes(limit: int = MAX_PROCESSES_DEFAULT) -> dict[str, Any]:
    """Lista procesos del sistema vía psutil.

    Args:
        limit: corte duro aplicado después de la enumeración (default 500,
            max 5000). Útil para no devolver gigabytes en una sola tool call.

    Payload éxito::

        {
          "platform": "windows|linux|darwin",
          "processes": [
            {"pid": 1234, "ppid": 1, "name": "python.exe",
             "exe": "C:/.../python.exe",
             "cmdline": ["python", "-m", "iabv_v15.infra.mcp.server"],
             "status": "running", "create_time": 1745.0,
             "username": "faber"},
             ...
          ],
          "count": N,
          "truncated": bool,
          "total_seen": M
        }
    """

    try:
        limit_int = max(1, min(int(limit), MAX_PROCESSES_HARD))
    except Exception:
        limit_int = MAX_PROCESSES_DEFAULT

    try:
        import psutil  # type: ignore
    except Exception as exc:
        return {
            "error": "dependency_missing",
            "dependency": "psutil",
            "detail": f"psutil no importable: {exc!r}",
        }

    processes: list[dict[str, Any]] = []
    total_seen = 0
    truncated = False
    iterator = psutil.process_iter(["pid", "ppid", "name", "exe", "cmdline", "status", "create_time", "username"])
    for proc in iterator:
        total_seen += 1
        try:
            info = proc.info
            processes.append(
                {
                    "pid": int(info.get("pid") or 0),
                    "ppid": int(info.get("ppid") or 0),
                    "name": (info.get("name") or "")[:128],
                    "exe": (info.get("exe") or "")[:512],
                    "cmdline": _sanitize_cmdline(info.get("cmdline")),
                    "status": (info.get("status") or ""),
                    "create_time": float(info.get("create_time") or 0.0),
                    "username": (info.get("username") or "")[:128],
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as exc:  # pragma: no cover
            logger.debug("process_iter row error=%r", exc)
            continue
        if len(processes) >= limit_int:
            # Contamos cuántos quedaron sin procesar para reportar total_seen
            # real y marcar truncated=True.
            try:
                remaining = 0
                for _ in iterator:
                    remaining += 1
                total_seen += remaining
                if remaining > 0:
                    truncated = True
            except Exception:  # pragma: no cover
                truncated = True
            break

    return {
        "platform": platform.system().lower(),
        "processes": processes,
        "count": len(processes),
        "truncated": truncated,
        "total_seen": total_seen,
    }


# ---------------------------------------------------------------------------
# read_clipboard


def read_clipboard() -> dict[str, Any]:
    """Lee el contenido de texto del portapapeles.

    Orden de intentos:
        1. ``pyperclip`` (cross-platform, preferido).
        2. ``tkinter.Tk().clipboard_get()`` como fallback.

    Payload éxito::

        {"platform": "windows|linux|darwin",
         "content": "texto...",
         "length": N,
         "truncated": bool}

    Sin soporte: ``{error: "clipboard_unavailable", detail: "..."}``.
    """

    content: str | None = None
    source: str | None = None
    err_detail: list[str] = []

    try:
        import pyperclip  # type: ignore

        content = pyperclip.paste()
        source = "pyperclip"
    except Exception as exc:
        err_detail.append(f"pyperclip: {exc!r}")

    if content is None:
        try:
            import tkinter  # type: ignore

            root = tkinter.Tk()
            try:
                root.withdraw()
                content = root.clipboard_get()
                source = "tkinter"
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass
        except Exception as exc:
            err_detail.append(f"tkinter: {exc!r}")

    if content is None:
        return {
            "error": "clipboard_unavailable",
            "detail": "; ".join(err_detail) or "no clipboard backend available",
        }

    encoded = content.encode("utf-8", errors="replace")
    truncated = False
    if len(encoded) > MAX_CLIPBOARD_BYTES:
        encoded = encoded[:MAX_CLIPBOARD_BYTES]
        content = encoded.decode("utf-8", errors="replace")
        truncated = True

    return {
        "platform": platform.system().lower(),
        "source": source,
        "content": content,
        "length": len(content),
        "truncated": truncated,
    }


# ---------------------------------------------------------------------------
# dump_qml_tree


def dump_qml_tree(max_nodes: int = MAX_QML_NODES, app_factory: Any | None = None) -> dict[str, Any]:
    """Dumpa el árbol de QObjects de la UI IABV si hay QApplication viva.

    Args:
        max_nodes: corte duro para no serializar árboles enormes.
        app_factory: callable opcional que devuelve la `QApplication`;
            usado en tests para inyectar un fake sin PySide6.

    Payload éxito::

        {
          "nodes": [
            {"id": 1, "parent_id": null, "class": "MainWindow",
             "object_name": "main", "window_title": "IABV — ..."},
            {"id": 2, "parent_id": 1, "class": "QStackedWidget", ...},
            ...
          ],
          "count": N,
          "truncated": bool,
          "top_level_count": K
        }

    Sin QApplication o sin PySide6: ``{error: "ui_not_running"}`` /
    ``{error: "dependency_missing", dependency: "PySide6"}``.
    """

    try:
        max_nodes_int = max(1, min(int(max_nodes), MAX_QML_NODES))
    except Exception:
        max_nodes_int = MAX_QML_NODES

    app = None
    if app_factory is not None:
        try:
            app = app_factory()
        except Exception as exc:
            return {"error": "app_factory_failed", "detail": repr(exc)}
    else:
        try:
            from PySide6.QtWidgets import QApplication  # type: ignore

            app = QApplication.instance()
        except Exception as exc:
            return {
                "error": "dependency_missing",
                "dependency": "PySide6",
                "detail": repr(exc),
            }

    if app is None:
        return {"error": "ui_not_running", "detail": "no QApplication.instance() viva"}

    try:
        top_level = list(app.topLevelWidgets() or [])
    except Exception as exc:
        return {"error": "top_level_failed", "detail": repr(exc)}

    nodes: list[dict[str, Any]] = []
    queue: list[tuple[Any, int | None]] = [(w, None) for w in top_level]
    next_id = 1
    id_map: dict[int, int] = {}
    truncated = False

    while queue:
        if len(nodes) >= max_nodes_int:
            truncated = True
            break
        obj, parent_id = queue.pop(0)
        try:
            obj_key = id(obj)
        except Exception:
            continue
        if obj_key in id_map:
            continue
        this_id = next_id
        next_id += 1
        id_map[obj_key] = this_id

        cls = _safe_class_name(obj)
        object_name = _safe_attr(obj, "objectName") or ""
        window_title = _safe_attr(obj, "windowTitle") or ""
        nodes.append(
            {
                "id": this_id,
                "parent_id": parent_id,
                "class": cls,
                "object_name": str(object_name)[:128],
                "window_title": str(window_title)[:256],
            }
        )

        try:
            children = list(obj.children() or [])
        except Exception:
            children = []
        for child in children:
            queue.append((child, this_id))

    return {
        "nodes": nodes,
        "count": len(nodes),
        "truncated": truncated,
        "top_level_count": len(top_level),
    }


def _safe_class_name(obj: Any) -> str:
    try:
        meta = obj.metaObject()
        return str(meta.className())
    except Exception:
        pass
    try:
        return type(obj).__name__
    except Exception:  # pragma: no cover
        return "<unknown>"


def _safe_attr(obj: Any, name: str) -> Any:
    try:
        method = getattr(obj, name, None)
    except Exception:
        return None
    if method is None:
        return None
    if callable(method):
        try:
            return method()
        except Exception:
            return None
    return method
