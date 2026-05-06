from __future__ import annotations

from iabv_v15.ui.qt import QObject, Property, Signal, Slot


class MainWindowBridge(QObject):
    """Puente entre la ventana principal y servicios Python.

    Tambien sirve como punto de aterrizaje honesto para hitos de
    readiness: el shell QML llama ``signal_shell_loader_ready()`` cuando
    el ``mainShellLoader`` (asincrono) termina de instanciar el
    contenido real (no solo la ``ApplicationWindow`` vacia).

    Para diagnosticar por que en Windows pythonw.exe el ``shellLoaderReady``
    a veces no llega (la app cae al ``shell_loader_ready_fallback``), este
    bridge expone ahora slots adicionales que QML invoca en cada cambio
    de ``Loader.status`` y ``Loader.active``, en ``Component.onCompleted``
    de ``Main.qml`` y al cerrar el splash.  Bootstrap los marca como
    hitos en el timeline JSONL.  Asi, sin agregar memoria paralela ni
    servicio nuevo, la auditoria ve exactamente que pasa con la
    incubacion del shell en Windows.
    """

    statusChanged = Signal()
    deferredSetupActiveChanged = Signal()
    # Hito honesto: ``mainShellLoader`` (Loader async) termino de cargar.
    shellLoaderReady = Signal()
    # Hito mas honesto aun: ``pageLoader`` (la pagina interna del shell)
    # termino — el usuario realmente ve la pagina (Dashboard).
    pageLoaderReady = Signal()
    # Cada cambio de estado de un Loader QML (status/active).
    qmlLoaderEvent = Signal(str, int, bool)
    # ``Component.onCompleted`` de ``Main.qml`` ApplicationWindow.
    mainQmlCompleted = Signal()
    # QML llama a esto justo antes de ``splashWindow.close()``.
    splashClosing = Signal()

    def __init__(self, app_title: str, workspace_root: str) -> None:
        super().__init__()
        self._app_title = app_title
        self._workspace_root = workspace_root
        self._status_message = 'Stack local por roles activo.'
        self._shell_loader_ready_signaled = False
        self._page_loader_ready_signaled = False
        self._deferred_setup_active = False

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

    @Slot()
    def signal_page_loader_ready(self) -> None:
        """Llamado desde QML cuando ``pageLoader`` (interno) termina.

        Es el hito MAS honesto: cuando esto llega el usuario realmente
        esta viendo la pagina (Dashboard u otra ruta).  Idempotente.
        """
        if self._page_loader_ready_signaled:
            return
        self._page_loader_ready_signaled = True
        self.pageLoaderReady.emit()

    @Slot(str, int, bool)
    def signal_qml_loader_event(self, loader_name: str, status: int, active_now: bool) -> None:
        """Cada cambio de ``status``/``active`` de un Loader QML.

        ``status`` mapea a ``QQuickItem`` Loader status enum:
        ``0=Null, 1=Ready, 2=Loading, 3=Error``.  ``active_now`` es el
        valor actual de ``Loader.active``.

        El bridge reemite la senal sin filtrar; bootstrap la traduce a
        un hito JSONL granular.
        """
        self.qmlLoaderEvent.emit(loader_name, int(status), bool(active_now))

    @Slot()
    def signal_main_qml_completed(self) -> None:
        """Llamado desde ``Component.onCompleted`` de ``Main.qml``.

        Marca el momento exacto en que el QML root (ApplicationWindow)
        termino de evaluar su tree estatico.  Despues de esto QML
        agenda el ``mainShellKickoff`` Timer para activar el Loader.
        """
        self.mainQmlCompleted.emit()

    @Slot()
    def signal_splash_closing(self) -> None:
        """Llamado desde QML del splash justo antes de ``Window.close()``.

        Permite cerrar el ciclo de vida del splash en el timeline para
        diagnosticar si la ventana realmente se destruye (z-order) o si
        sigue arriba pese a ``set_ready()`` + fadeOut.
        """
        self.splashClosing.emit()

    def get_deferred_setup_active(self) -> bool:
        return self._deferred_setup_active

    def set_deferred_setup_active(self, value: bool) -> None:
        if self._deferred_setup_active != value:
            self._deferred_setup_active = value
            self.deferredSetupActiveChanged.emit()

    appTitle = Property(str, get_app_title, constant=True)
    workspaceRoot = Property(str, get_workspace_root, constant=True)
    statusMessage = Property(str, get_status_message, notify=statusChanged)
    deferredSetupActive = Property(bool, get_deferred_setup_active, notify=deferredSetupActiveChanged)
