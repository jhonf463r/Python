from __future__ import annotations

from pathlib import Path
import time

from iabv_v15.domain.models import CapturedStep, EpisodeManifest
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.screenshot_store import ScreenshotStore
from iabv_v15.services.capture.browser_action_service import BrowserActionService
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController


class DemoCaptureService:
    """Coordinates browser navigation, episode storage and screenshots."""

    def __init__(
        self,
        controller: BrowserSessionController,
        episode_repository: EpisodeRepository,
        screenshot_store: ScreenshotStore,
    ) -> None:
        self.controller = controller
        self.episode_repository = episode_repository
        self.screenshot_store = screenshot_store
        self.page = None
        self.actions = None
        self.current_episode: EpisodeManifest | None = None

    def start_episode(self, title: str, url: str, tags: list[str] | None = None) -> EpisodeManifest:
        self.controller.start()
        self.page = self.controller.new_page()
        self.actions = BrowserActionService(self.page)
        self.actions.goto(url)
        self.current_episode = self.episode_repository.create_episode(title=title, tags=tags)
        return self.current_episode

    def record_step(self, action_type: str, target: str | None = None, text_value: str | None = None) -> CapturedStep:
        if self.current_episode is None or self.page is None:
            raise RuntimeError("No active episode.")
        file_name = f"step_{int(time.time() * 1000)}.png"
        screenshot_path = self.screenshot_store.save_bytes(
            self.current_episode.episode_id,
            file_name,
            self.page.screenshot(),
        )
        step = CapturedStep(
            episode_id=self.current_episode.episode_id,
            action_type=action_type,
            target=target,
            text_value=text_value,
            screenshot_path=screenshot_path,
        )
        return self.episode_repository.save_step(self.current_episode.episode_id, step)

    def stop(self) -> None:
        self.controller.close()
        self.page = None
        self.actions = None
