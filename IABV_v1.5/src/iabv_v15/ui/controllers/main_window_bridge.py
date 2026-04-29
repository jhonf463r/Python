from __future__ import annotations

from iabv_v15.ui.qt import QObject, Property, Signal, Slot


class MainWindowBridge(QObject):
    """Puente entre la ventana principal y servicios Python.

    Tambien sirve como punto de aterrizaje honesto para hitos de
    readiness: el shell QML llama ``signal_shell_loader_ready()`` cuando
    el ``mainShellLoader`` (asincrono) termina de instanciar el
    contenido real (no solo la ``ApplicationWindow`` vacia).
    """

    statusChanged = Signal()
    # Emitida cuando QML reporta que el ``mainShellLoader`` esta listo.
    # Bootstrap conecta esto a ``_handle_shell_loader_ready`` para
    # marcar el hito ``shell_loader_ready`` y disparar
    # ``splashController.set_ready()`` con honestidad real.
    shellLoaderReady = Signal()

    def __init__(self, app_title: str, workspace_root: str) -> None:
        super().__init__()
        self._app_title = app_title
        self._workspace_root = workspace_root
        self._status_message = 'Stack local por roles activo.'
        self._shell_loader_ready_signaled = False

    def get_app_title(self) -> str:
        return self._app_title

    def get_workspace_root(self) -> str:
        return self._workspace_root

    def get_status_message(self) -> str:
        return self._status_message

    @Slot(str)
    def set_status_message(self, message: str) -> None:
        self._status_message = message
        self.statusChanged.emit()

    @Slot()
    def signal_shell_loader_ready(self) -> None:
        """Llamado desde QML cuando ``mainShellLoader`` termina su carga.

        Idempotente: una segunda llamada es no-op.  Esto sucede porque
        ``Loader.onLoaded`` puede dispararse mas de una vez si el
        ``sourceComponent`` se re-evalua tras un cambio de contexto.
        """
        if self._shell_loader_ready_signaled:
            return
        self._shell_loader_ready_signaled = True
        self.shellLoaderReady.emit()

    appTitle = Property(str, get_app_title, constant=True)
    workspaceRoot = Property(str, get_workspace_root, constant=True)
    statusMessage = Property(str, get_status_message, notify=statusChanged)
