from __future__ import annotations

from iabv_v15.domain.models import BrowserProfileConfig, SitePolicy, SiteSessionResult
from iabv_v15.infra.persistence.session_state_store import SessionStateStore
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController


class SiteSessionManager:
    def __init__(self, state_store: SessionStateStore):
        self.state_store = state_store

    def load_or_prompt_login(self, page, profile: BrowserProfileConfig, policy: SitePolicy) -> SiteSessionResult:
        current_url = getattr(page, "url", None)
        authenticated = False
        requires_manual_login = False
        reason = "No login heuristic matched yet."

        if self._selector_present(page, policy.logout_selector):
            authenticated = True
            reason = "Logout selector found; session appears authenticated."
        elif self._selector_present(page, profile.logout_check_selector):
            authenticated = True
            reason = "Profile logout selector found; session appears authenticated."
        elif self._selector_present(page, policy.login_selector) or self._selector_present(page, profile.login_check_selector):
            requires_manual_login = True
            reason = "Login selector still visible; manual login is required."
        elif profile.storage_state_path:
            requires_manual_login = not self._storage_state_exists(profile.storage_state_path)
            authenticated = not requires_manual_login
            if authenticated:
                reason = "Storage state exists and no login selector is visible."

        return SiteSessionResult(
            site_id=policy.site_id,
            authenticated=authenticated,
            requires_manual_login=requires_manual_login,
            storage_state_path=profile.storage_state_path,
            reason=reason,
            current_url=current_url,
        )

    def save_site_state(self, controller: BrowserSessionController, profile: BrowserProfileConfig) -> str | None:
        if not profile.storage_state_path:
            return None
        return controller.save_storage_state(profile.storage_state_path)

    def domain_for_url(self, url: str | None) -> str:
        if not url:
            return ""
        value = url.split("//", 1)[-1]
        return value.split("/", 1)[0]

    def _selector_present(self, page, selector: str | None) -> bool:
        if page is None or not selector:
            return False
        try:
            if hasattr(page, "locator"):
                return page.locator(selector).count() > 0
            if hasattr(page, "query_selector"):
                return page.query_selector(selector) is not None
        except Exception:
            return False
        return False

    def _storage_state_exists(self, path: str) -> bool:
        try:
            self.state_store.load_json(path)
            return True
        except Exception:
            return False
