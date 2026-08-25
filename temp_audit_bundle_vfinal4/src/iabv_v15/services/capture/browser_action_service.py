from __future__ import annotations

from typing import Any


class BrowserActionService:
    """Thin action layer to keep browser control separate from capture orchestration."""

    def __init__(self, page: Any):
        self.page = page

    def goto(self, url: str) -> None:
        self.page.goto(url)

    def click(self, selector: str) -> None:
        self.page.click(selector)

    def type_text(self, selector: str, text: str) -> None:
        self.page.fill(selector, text)

    def wait_for(self, selector: str, timeout_ms: int = 5000) -> None:
        self.page.wait_for_selector(selector, timeout=timeout_ms)

    def screenshot(self, path: str) -> str:
        self.page.screenshot(path=path)
        return path
