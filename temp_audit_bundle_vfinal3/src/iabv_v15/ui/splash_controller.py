"""Splash screen controller for IABV v1.5 startup.

Shows a loading screen with the BURVE logo, status messages, and a
detailed step-by-step diagnostic log while the application bootstraps.

The diagnostic log is designed so the user can copy it and share it
with development AIs (Devin, ChatGPT, Claude, etc.) for troubleshooting.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from iabv_v15.ui.qt import PYSIDE_AVAILABLE, QObject, Signal, Slot, Property

logger = logging.getLogger(__name__)


class SplashController(QObject):
    """Drives the QML splash screen with live status updates and diagnostics."""

    statusChanged = Signal()
    progressChanged = Signal()
    hasErrorChanged = Signal()
    readyChanged = Signal()
    logChanged = Signal()
    # Emitida desde QML justo antes de ``splashWindow.close()`` para que
    # bootstrap pueda marcar el hito ``splash_window_closing`` en el
    # startup_timeline.  Permite distinguir si el splash realmente se
    # cierra o si Windows lo deja arriba por Z-order pese al fadeOut.
    closingNow = Signal()

    def __init__(self, workspace_dir: str | Path | None = None, parent=None):
        super().__init__(parent)
        self._status: str = 'Iniciando BURVE...'
        self._progress: float = 0.0
        self._has_error: bool = False
        self._error_detail: str = ''
        self._ready: bool = False
        self._steps_done: int = 0
        self._steps_total: int = 10
        self._start_time: float = time.time()
        self._step_start: float = self._start_time

        # Diagnostic log: each entry is one line for the user to share
        self._log_lines: list[str] = []
        self._log_lines.append(f'=== BURVE - IABV v1.5 — Reporte de arranque ===')
        self._log_lines.append(f'Inicio: {time.strftime("%Y-%m-%d %H:%M:%S")}')
        self._log_lines.append('')

        # Resolve icon path for QML
        self._icon_path: str = ''
        if workspace_dir:
            ico = Path(workspace_dir) / 'assets' / 'burve.png'
            if ico.exists():
                self._icon_path = str(ico).replace('\\', '/')
            self._log_lines.append(f'Workspace: {workspace_dir}')
            self._log_lines.append('')

    # -- Properties exposed to QML --

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    @Property(bool, notify=hasErrorChanged)
    def hasError(self) -> bool:
        return self._has_error

    @Property(str, notify=hasErrorChanged)
    def errorDetail(self) -> str:
        return self._error_detail

    @Property(bool, notify=readyChanged)
    def ready(self) -> bool:
        return self._ready

    @Property(str, constant=True)
    def iconPath(self) -> str:
        return self._icon_path

    @Property(str, notify=logChanged)
    def diagnosticLog(self) -> str:
        return '\n'.join(self._log_lines)

    # -- Methods called from bootstrap --

    def set_status(self, message: str) -> None:
        """Update the splash status message and advance progress."""
        now = time.time()
        elapsed = now - self._step_start
        self._step_start = now

        self._steps_done += 1
        self._progress = min(self._steps_done / self._steps_total, 0.95)
        self._status = message

        self._log_lines.append(f'  [{self._steps_done:2d}/{self._steps_total}] OK  ({elapsed:.1f}s) {message}')

        try:
            self.statusChanged.emit()
            self.progressChanged.emit()
            self.logChanged.emit()
        except Exception:
            pass
        logger.info('splash: %s (%.0f%%)', message, self._progress * 100)

    def set_error(self, message: str, detail: str = '') -> None:
        """Show an error on the splash screen (bootstrap continues anyway)."""
        now = time.time()
        elapsed = now - self._step_start
        self._step_start = now

        self._status = message
        self._has_error = True
        self._error_detail = detail

        self._log_lines.append(f'  [ERR]  ({elapsed:.1f}s) {message}')
        if detail:
            for line in detail.splitlines()[:5]:
                self._log_lines.append(f'         {line}')

        try:
            self.statusChanged.emit()
            self.hasErrorChanged.emit()
            self.logChanged.emit()
        except Exception:
            pass
        logger.error('splash error: %s — %s', message, detail)

    def set_progress(self, percent: int) -> None:
        """Set splash progress to an explicit percentage (0-100).

        Used by bootstrap to report honest progress milestones during
        the splash→shell transition instead of relying solely on the
        auto-incrementing step counter.
        """
        self._progress = max(0.0, min(float(percent) / 100.0, 0.99))
        try:
            self.progressChanged.emit()
        except Exception:
            pass

    def set_ready(self) -> None:
        """Signal that bootstrap is complete — splash will fade out."""
        total_elapsed = time.time() - self._start_time
        self._status = 'Listo'
        self._progress = 1.0
        self._ready = True

        self._log_lines.append('')
        if self._has_error:
            self._log_lines.append(f'=== ARRANQUE CON ADVERTENCIAS ({total_elapsed:.1f}s total) ===')
            self._log_lines.append('Algunos servicios fallaron. El programa sigue funcionando')
            self._log_lines.append('pero puede haber funcionalidad limitada.')
        else:
            self._log_lines.append(f'=== ARRANQUE EXITOSO ({total_elapsed:.1f}s total) ===')
            self._log_lines.append('Todos los servicios cargaron correctamente.')

        self._log_lines.append('')
        self._log_lines.append('Si necesitas ayuda, copia este reporte y compartelo')
        self._log_lines.append('con tu asistente IA de desarrollo.')

        try:
            self.statusChanged.emit()
            self.progressChanged.emit()
            self.readyChanged.emit()
            self.logChanged.emit()
        except Exception:
            pass

    @Slot(result=str)
    def copyDiagnostic(self) -> str:
        """Return diagnostic text for clipboard copy from QML."""
        return self.diagnosticLog

    @Slot()
    def dismiss(self) -> None:
        """Called from QML when splash fade-out animation finishes."""
        pass

    @Slot()
    def signal_closing(self) -> None:
        """Llamado desde QML justo antes de ``splashWindow.close()``.

        Permite al bootstrap marcar el hito ``splash_window_closing`` en
        el startup_timeline.  Idempotente: re-emisiones se ignoran sin
        ruido.
        """
        try:
            self.closingNow.emit()
        except Exception:
            pass
