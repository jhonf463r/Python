"""
Observatory ViewModel - Minimal Read-Only UI (P0.184)

Minimal read-only ViewModel that consumes the observatory surface contract
from organism_state_snapshot.py. This is purely for display without any
decision logic or authority.

This ViewModel does NOT:
- Write to files
- Modify state
- Execute tools
- Make decisions
- Replace existing services

It ONLY:
- Reads the surface contract
- Exposes data for QML display
- Shows UNRESOLVED when evidence is missing
"""

from pathlib import Path
from typing import Any
from PySide6.QtCore import QObject, Signal, Slot, Property


class ObservatoryViewModel(QObject):
    """Minimal read-only ViewModel for observatory surface contract."""

    # Signals for QML binding
    dataChanged = Signal()
    loadingChanged = Signal()
    errorChanged = Signal()

    def __init__(self, workspace_root: str | Path, parent: QObject = None):
        super().__init__(parent)
        self._workspace_root = Path(workspace_root)
        self._surface_contract: dict[str, Any] = {}
        self._loading = False
        self._error = ""

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        """Whether data is currently loading."""
        return self._loading

    @Property(str, notify=errorChanged)
    def error(self) -> str:
        """Error message if loading failed."""
        return self._error

    @Property("QVariantMap", notify=dataChanged)
    def surfaceContract(self) -> dict[str, Any]:
        """The current surface contract data."""
        return self._surface_contract

    @Property(str, notify=dataChanged)
    def timestamp(self) -> str:
        """Timestamp of the surface contract."""
        return self._surface_contract.get("timestamp", "")

    @Property(str, notify=dataChanged)
    def workspaceRoot(self) -> str:
        """Workspace root path."""
        return self._surface_contract.get("workspace_root", "")

    @Property("QVariantMap", notify=dataChanged)
    def humanVision(self) -> dict[str, Any]:
        """Human vision section."""
        return self._surface_contract.get("human_vision", {})

    @Property("QVariantMap", notify=dataChanged)
    def organHealth(self) -> dict[str, Any]:
        """Organ health section."""
        return self._surface_contract.get("organ_health", {})

    @Property("QVariantMap", notify=dataChanged)
    def stability(self) -> dict[str, Any]:
        """Stability section."""
        return self._surface_contract.get("stability", {})

    @Property("QVariantMap", notify=dataChanged)
    def learning(self) -> dict[str, Any]:
        """Learning section."""
        return self._surface_contract.get("learning", {})

    @Property("QVariantMap", notify=dataChanged)
    def confidence(self) -> dict[str, Any]:
        """Confidence section."""
        return self._surface_contract.get("confidence", {})

    @Property("QVariantList", notify=dataChanged)
    def evidenceSources(self) -> list[str]:
        """Evidence sources list."""
        return self._surface_contract.get("evidence_sources", [])

    @Property("QVariantList", notify=dataChanged)
    def unresolvedFields(self) -> list[str]:
        """Unresolved fields list."""
        return self._surface_contract.get("unresolved_fields", [])

    @Slot()
    def refresh(self):
        """Refresh the surface contract data."""
        self._loading = True
        self._error = ""
        self.loadingChanged.emit()

        try:
            from iabv_v15.services.evolution.organism_state_snapshot import (
                export_observatory_surface_contract,
            )

            self._surface_contract = export_observatory_surface_contract(
                self._workspace_root
            )
            self._error = ""
        except Exception as e:
            self._error = str(e)
            self._surface_contract = {}
        finally:
            self._loading = False
            self.loadingChanged.emit()
            self.dataChanged.emit()
            self.errorChanged.emit()
