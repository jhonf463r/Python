from __future__ import annotations

from iabv_v15.domain.models import ThemeConfig
from iabv_v15.ui.qt import QObject, Property


class ThemeController(QObject):
    def __init__(self, theme: ThemeConfig) -> None:
        super().__init__()
        self._theme = theme

    def get_palette(self) -> dict:
        return self._theme.model_dump()

    palette = Property(dict, get_palette, constant=True)
