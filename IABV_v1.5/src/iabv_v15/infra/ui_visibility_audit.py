"""UI visibility audit — registro de eventos visibles para el usuario.

Captura y registra todo lo que el usuario realmente ve: ventanas emergentes,
dialogs modales, mensajes de error, notificaciones, banners y popups
inesperados de Windows.

Separacion obligatoria:
  1. Auditoria tecnica interna: logs, quota, world model, tests, rutas.
  2. Auditoria visible: screenshots, popups, dialogs, banners, mensajes.

Principios:
  - Provider probing y checks tecnicos van en background (nunca abren ventana).
  - Todo popup visible queda registrado como evento auditable.
  - FileNotFoundError se captura con evidencia exacta (archivo, ruta, modulo,
    stack trace).
  - Se distingue entre UI intencional, popup inesperado y check en background.

Arquitectura:
  - Append-only JSONL en ``data/logs/visible_events.jsonl``
  - NO es un servicio — es un registro pasivo que observa sin intervenir
  - Singleton via ``get_audit_log()``
"""
from __future__ import annotations

import contextlib
import json
import logging
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event kind constants
# ---------------------------------------------------------------------------

KIND_DIALOG_SHOWN = 'dialog_shown'
KIND_DIALOG_CLOSED = 'dialog_closed'
KIND_TOAST_SHOWN = 'toast_shown'
KIND_WIN32_POPUP = 'win32_popup_detected'
KIND_FILE_NOT_FOUND = 'file_not_found_error'
KIND_BG_CHECK = 'background_check'
KIND_INIT_CHECK = 'init_check'

# ---------------------------------------------------------------------------
# Event category constants
# ---------------------------------------------------------------------------

CAT_INTENTIONAL = 'intentional'
CAT_UNEXPECTED = 'unexpected'
CAT_BACKGROUND = 'background'

# ---------------------------------------------------------------------------
# Source constants
# ---------------------------------------------------------------------------

SRC_BOOTSTRAP = 'bootstrap'
SRC_PROVIDER = 'provider_probing'
SRC_QML = 'qml'
SRC_WIN32 = 'Win32PopupWatcher'


class VisibilityAuditLog:
    """Append-only registry of UI-visible events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._file: Path | None = None
        self._fh: Any = None

    # -- lifecycle -----------------------------------------------------------

    def open(self, path: Path | None = None) -> None:
        if path is None:
            path = Path('data/logs/visible_events.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path
        self._fh = open(path, 'a', encoding='utf-8')  # noqa: SIM115
        self.record(KIND_INIT_CHECK, source=SRC_BOOTSTRAP,
                    detail='visibility audit log opened',
                    event_category=CAT_BACKGROUND)

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    # -- record events -------------------------------------------------------

    def record(
        self,
        kind: str,
        *,
        source: str = '',
        detail: str = '',
        title: str = '',
        event_category: str = CAT_BACKGROUND,
        unresolved: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        event = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'kind': kind,
            'source': source,
            'detail': detail,
            'title': title,
            'event_category': event_category,
            'unresolved': unresolved,
            'extra': extra or {},
        }
        with self._lock:
            self._events.append(event)
            if self._fh:
                self._fh.write(json.dumps(event, ensure_ascii=False) + '\n')
                self._fh.flush()
        logger.debug(
            'ui_visible [%s|%s] source=%s detail=%r title=%r',
            kind, event_category, source, detail, title,
        )

    def record_background(self, detail: str, *, source: str = '') -> None:
        self.record(KIND_BG_CHECK, source=source, detail=detail,
                    event_category=CAT_BACKGROUND)

    def record_file_not_found(
        self,
        exc: FileNotFoundError,
        *,
        source: str = '',
        cmd: list[str] | None = None,
    ) -> None:
        frame = sys._getframe(1)  # noqa: SLF001
        tb = traceback.format_exc()[:2000]
        filename = getattr(exc, 'filename', '') or ''
        strerror = getattr(exc, 'strerror', str(exc))
        self.record(
            KIND_FILE_NOT_FOUND,
            source=source,
            detail=f'FileNotFoundError: {strerror} \u2014 {filename}',
            event_category=CAT_BACKGROUND,
            unresolved=True,
            extra={
                'filename': filename,
                'strerror': strerror,
                'originating_file': frame.f_code.co_filename,
                'originating_module': frame.f_code.co_name,
                'originating_line': frame.f_lineno,
                'traceback': tb,
                'cmd': ' '.join(cmd) if cmd else '',
            },
        )

    # -- summary -------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)
        by_cat: dict[str, int] = {}
        fnf: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for ev in events:
            cat = ev.get('event_category', CAT_BACKGROUND)
            by_cat[cat] = by_cat.get(cat, 0) + 1
            if ev['kind'] == KIND_FILE_NOT_FOUND:
                fnf.append(ev)
            if ev.get('unresolved'):
                unresolved.append(ev)
        return {
            'total_events': len(events),
            'by_category': by_cat,
            'file_not_found_count': len(fnf),
            'file_not_found': fnf,
            'unresolved_count': len(unresolved),
            'unresolved': unresolved,
            'events': events,
        }


# ---------------------------------------------------------------------------
# Subprocess wrapper — captures FileNotFoundError from Popen
# ---------------------------------------------------------------------------

class SubprocessAuditWrapper:
    """Context manager that captures FileNotFoundError from subprocess calls."""

    def __init__(
        self,
        audit: VisibilityAuditLog,
        *,
        cmd: list[str],
        source: str = SRC_BOOTSTRAP,
    ) -> None:
        self._audit = audit
        self._cmd = cmd
        self._source = source

    def __enter__(self) -> SubprocessAuditWrapper:
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None,
                 exc_tb: Any) -> bool:
        if exc_type is FileNotFoundError and exc_val is not None:
            self._audit.record_file_not_found(
                exc_val, source=self._source, cmd=self._cmd,  # type: ignore[arg-type]
            )
        return False


# ---------------------------------------------------------------------------
# Splash observer — records when splash appears / disappears
# ---------------------------------------------------------------------------

class SplashAuditAdapter:
    """Attaches to a SplashController and records visibility events."""

    def __init__(self, audit: VisibilityAuditLog) -> None:
        self._audit = audit

    def on_shown(self) -> None:
        self._audit.record(
            KIND_DIALOG_SHOWN, source=SRC_BOOTSTRAP,
            detail='SplashScreen shown',
            event_category=CAT_INTENTIONAL,
        )

    def on_closed(self) -> None:
        self._audit.record(
            KIND_DIALOG_CLOSED, source=SRC_BOOTSTRAP,
            detail='SplashScreen closed',
            event_category=CAT_INTENTIONAL,
        )


# ---------------------------------------------------------------------------
# Win32 popup watcher — daemon thread that polls for unexpected message boxes
# ---------------------------------------------------------------------------

class Win32PopupWatcher:
    """Background daemon that detects unexpected Win32 message box popups.

    Only active on Windows. Uses ctypes to enumerate top-level windows and
    detect MessageBox-class windows that were not initiated by IABV.
    """

    _KNOWN_BENIGN_CLASSES: frozenset[str] = frozenset({
        'Shell_TrayWnd', 'Progman', 'WorkerW',
        'DummyDWMListenerWindow', 'ForegroundStaging',
        'Windows.UI.Core.CoreWindow', 'ApplicationFrameWindow',
        'Shell_SecondaryTrayWnd', 'NotifyIconOverflowWindow',
        'tooltips_class32', 'TaskListThumbnailWnd',
        'MSTaskSwWClass', 'TrayNotifyWnd',
    })

    _SUSPICIOUS_TITLE_PATTERNS: tuple[str, ...] = (
        'error', 'no se puede', 'cannot find', 'not found',
        'archivo', 'file', 'acceso denegado', 'access denied',
        'falta', 'missing', 'falló', 'failed',
    )

    def __init__(self, audit: VisibilityAuditLog,
                 poll_interval: float = 2.0) -> None:
        self._audit = audit
        self._interval = poll_interval
        self._stop = threading.Event()
        self._known_hwnds: set[int] = set()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if sys.platform != 'win32':
            return
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True,
            name='win32-popup-watcher',
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _poll_loop(self) -> None:
        while not self._stop.wait(self._interval):
            with contextlib.suppress(Exception):
                self._process_snapshot()

    @staticmethod
    def _is_suspicious(title: str) -> bool:
        lower = title.lower()
        return any(p in lower for p in Win32PopupWatcher._SUSPICIOUS_TITLE_PATTERNS)

    def _process_snapshot(self) -> None:
        try:
            import ctypes
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        except Exception:
            return

        WNDENUMPROC = ctypes.WINFUNCTYPE(  # noqa: N806
            ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        )

        found: list[tuple[int, str, str]] = []

        def callback(hwnd: Any, _: Any) -> bool:
            buf = ctypes.create_unicode_buffer(256)
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            title = buf.value
            cls_name = cls_buf.value
            if user32.IsWindowVisible(hwnd) and hwnd not in self._known_hwnds:
                if cls_name == '#32770' or cls_name not in self._KNOWN_BENIGN_CLASSES:
                    found.append((hwnd, title, cls_name))
                    self._known_hwnds.add(hwnd)
            return True

        try:
            user32.EnumWindows(WNDENUMPROC(callback), 0)
        except Exception:
            return

        for hwnd, title, cls_name in found:
            if cls_name in self._KNOWN_BENIGN_CLASSES:
                category = CAT_BACKGROUND
                unresolved = False
            elif self._is_suspicious(title):
                category = CAT_UNEXPECTED
                unresolved = True
            else:
                category = CAT_UNEXPECTED
                unresolved = False

            self._audit.record(
                KIND_WIN32_POPUP,
                source=SRC_WIN32,
                title=title,
                detail=f'Win32 dialog class={cls_name} hwnd={hwnd}',
                event_category=category,
                unresolved=unresolved,
                extra={'hwnd': hwnd, 'class_name': cls_name},
            )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_audit_log: VisibilityAuditLog | None = None


def get_audit_log() -> VisibilityAuditLog:
    global _audit_log  # noqa: PLW0603
    if _audit_log is None:
        _audit_log = VisibilityAuditLog()
    return _audit_log
