from __future__ import annotations

from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.ui.qt import QObject, Property, QTimer, Signal, Slot


class KnowledgeBaseViewModel(QObject):
    dataChanged = Signal()

    def __init__(self, repository: KnowledgeRepository, *, defer_initial_refresh: bool = False) -> None:
        super().__init__()
        self.repository = repository
        self._search_term = ""
        self._items: list[dict] = []
        if defer_initial_refresh:
            QTimer.singleShot(0, self.refresh)
        else:
            self.refresh()

    def get_items(self) -> list[dict]:
        return self._items

    def get_search_term(self) -> str:
        return self._search_term

    @Slot(str)
    def setSearchTerm(self, value: str) -> None:
        self._search_term = value
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        self._items = [item.model_dump(mode="json") for item in self.repository.search(self._search_term)]
        self.dataChanged.emit()

    items = Property(list, get_items, notify=dataChanged)
    searchTerm = Property(str, get_search_term, notify=dataChanged)
