from __future__ import annotations

from iabv_v15.ui.qt import QObject, Property, Signal, Slot


class MainWindowBridge(QObject):
    statusChanged = Signal()

    def __init__(self, app_title: str, workspace_root: str) -> None:
        super().__init__()
        self._app_title = app_title
        self._workspace_root = workspace_root
        self._status_message = 'Stack local por roles activo.'

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

    appTitle = Property(str, get_app_title, constant=True)
    workspaceRoot = Property(str, get_workspace_root, constant=True)
    statusMessage = Property(str, get_status_message, notify=statusChanged)
