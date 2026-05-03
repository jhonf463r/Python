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
# QML dialog audit bridge — records dialog open/close from Python VM signals
# ---------------------------------------------------------------------------

# Map VM signal names to human-readable dialog info
_DIALOG_SIGNAL_MAP: dict[str, dict[str, str]] = {
    'credentialPromptRequested': {
        'dialog': 'CredentialPromptDialog',
        'detail_key': 'domain',
        'category': CAT_INTENTIONAL,
    },
    'clarificationRequested': {
        'dialog': 'ClarificationDialog',
        'detail_key': 'question',
        'category': CAT_INTENTIONAL,
    },
    'missingDependencyRequested': {
        'dialog': 'MissingDependencyDialog',
        'detail_key': 'package_name',
        'category': CAT_INTENTIONAL,
    },
}


class QmlDialogAuditBridge:
    """Records audit events when QML dialogs are opened via ViewModel signals.

    Usage in bootstrap::

        bridge = QmlDialogAuditBridge(get_audit_log())
        bridge.install(control_center_vm)
        bridge.install(evolution_center_vm)

    Each dialog open emits a ``dialog_shown`` event with the dialog name,
    source ViewModel, and relevant payload detail (domain, question, etc.).
    """

    def __init__(self, audit: VisibilityAuditLog) -> None:
        self._audit = audit

    def install(self, viewmodel: Any) -> None:
        """Connect to dialog signals on a ViewModel (non-destructive)."""
        vm_name = type(viewmodel).__name__
        for signal_name, info in _DIALOG_SIGNAL_MAP.items():
            signal = getattr(viewmodel, signal_name, None)
            if signal is None:
                continue
            dialog = info['dialog']
            detail_key = info['detail_key']
            category = info['category']
            try:
                signal.connect(
                    lambda payload, _d=dialog, _k=detail_key, _c=category,
                    _vm=vm_name: self._on_dialog_requested(
                        payload, dialog=_d, detail_key=_k,
                        category=_c, vm_name=_vm,
                    )
                )
            except Exception:
                logger.debug('QmlDialogAuditBridge: cannot connect %s.%s',
                             vm_name, signal_name)

    def _on_dialog_requested(
        self,
        payload: dict[str, Any],
        *,
        dialog: str,
        detail_key: str,
        category: str,
        vm_name: str,
    ) -> None:
        detail_value = payload.get(detail_key, '') if isinstance(payload, dict) else ''
        self._audit.record(
            KIND_DIALOG_SHOWN,
            source=SRC_QML,
            title=dialog,
            detail=f'{dialog} opened: {detail_key}={detail_value}',
            event_category=category,
            extra={
                'viewmodel': vm_name,
                'signal_payload': _safe_serialize(payload),
            },
        )

    def record_dialog_closed(
        self,
        dialog: str,
        *,
        vm_name: str = '',
        response_type: str = '',
    ) -> None:
        """Manually record a dialog close (called from VM response slots)."""
        self._audit.record(
            KIND_DIALOG_CLOSED,
            source=SRC_QML,
            title=dialog,
            detail=f'{dialog} closed: response={response_type}',
            event_category=CAT_INTENTIONAL,
            extra={'viewmodel': vm_name, 'response_type': response_type},
        )


def _safe_serialize(obj: Any) -> dict[str, Any] | str:
    """Produce a JSON-safe representation of a payload dict."""
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for k, v in obj.items():
            if k in ('password', 'secret', 'token', 'api_key'):
                result[k] = '***REDACTED***'
            elif isinstance(v, str):
                result[k] = v[:200]
            else:
                result[k] = str(v)[:200]
        return result
    return str(obj)[:500]


# ---------------------------------------------------------------------------
# Toast audit adapter — auto-registers toast notifications
# ---------------------------------------------------------------------------

class ToastAuditAdapter:
    """Wraps ``WinToastBridge`` so every notification is automatically audited.

    Usage::

        adapter = ToastAuditAdapter(get_audit_log(), win_toast_bridge)
        adapter.install()  # monkey-patches the bridge methods

    After ``install()``, every call to ``notify()`` on the bridge will
    automatically record a ``toast_shown`` event in the audit log.
    """

    def __init__(self, audit: VisibilityAuditLog, bridge: Any) -> None:
        self._audit = audit
        self._bridge = bridge
        self._installed = False

    def install(self) -> None:
        """Monkey-patch the bridge's internal methods to record events."""
        if self._installed:
            return
        bridge = self._bridge

        original_winotify = getattr(bridge, '_notify_winotify', None)
        original_balloon = getattr(bridge, '_notify_balloon', None)

        if original_winotify is not None:
            def _audited_winotify(title: str, body: str, *, icon: str = 'info',
                                  _orig: Any = original_winotify) -> bool:
                result = _orig(title, body, icon=icon)
                self._record_toast(title, body, backend='winotify',
                                   icon=icon, success=result)
                return result
            bridge._notify_winotify = _audited_winotify  # noqa: SLF001

        if original_balloon is not None:
            def _audited_balloon(title: str, body: str, *, icon: str = 'info',
                                 duration_ms: int = 5000,
                                 _orig: Any = original_balloon) -> bool:
                result = _orig(title, body, icon=icon, duration_ms=duration_ms)
                self._record_toast(title, body, backend='balloon',
                                   icon=icon, success=result)
                return result
            bridge._notify_balloon = _audited_balloon  # noqa: SLF001

        self._installed = True

    def _record_toast(
        self,
        title: str,
        body: str,
        *,
        backend: str,
        icon: str,
        success: bool,
    ) -> None:
        self._audit.record(
            KIND_TOAST_SHOWN,
            source=f'WinToastBridge.{backend}',
            title=title,
            detail=body[:500],
            event_category=CAT_INTENTIONAL,
            extra={
                'backend': backend,
                'icon': icon,
                'success': success,
            },
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
