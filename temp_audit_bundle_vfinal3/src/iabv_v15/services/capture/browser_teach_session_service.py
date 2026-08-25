from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any
from urllib.parse import unquote, urlsplit

from iabv_v15.domain.models import (
    BrowserObservationBundle,
    BrowserProfileConfig,
    CaptureChannel,
    CapturedStep,
    DomSnapshot,
    EpisodeManifest,
    NetworkExchange,
    RedactionSummary,
    SessionArtifact,
    SitePolicy,
    SiteSessionResult,
)
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.screenshot_store import ScreenshotStore
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
from iabv_v15.services.capture.redaction_engine import RedactionEngine
from iabv_v15.services.capture.site_session_manager import SiteSessionManager


BRIDGE_INSTALL_EXPR = r"""
() => {
  if (window.__iabvTeachInstalled) {
    return true;
  }
  window.__iabvTeachInstalled = true;
  window.__iabvTeachPaused = false;
  window.__iabvTeachEvents = [];
  window.__iabvTeachHeartbeatTimer = window.__iabvTeachHeartbeatTimer || null;
  function eventId() {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  function cssPath(element) {
    if (!element || !element.tagName) {
      return "";
    }
    if (element.id) {
      return "#" + element.id;
    }
    const parts = [];
    let current = element;
    while (current && current.nodeType === 1 && parts.length < 5) {
      let part = current.tagName.toLowerCase();
      if (current.className && typeof current.className === "string") {
        const cls = current.className.trim().split(/\s+/).slice(0, 2).join(".");
        if (cls) {
          part += "." + cls;
        }
      }
      parts.unshift(part);
      current = current.parentElement;
    }
    return parts.join(" > ");
  }
  function inferElementRole(element, autocompleteValue) {
    if (!element || !element.tagName) {
      return "unknown";
    }
    const tag = element.tagName.toLowerCase();
    const type = (element.type || "").toLowerCase();
    const role = (element.getAttribute && (element.getAttribute("role") || "").toLowerCase()) || "";
    if (type === "password") return "password_input";
    if (type === "email" || (autocompleteValue || "").toLowerCase().includes("email")) return "email_input";
    if ((autocompleteValue || "").toLowerCase().includes("username")) return "username_input";
    if (["text", "email", "search", "tel", "url", "number"].includes(type)) return "text_input";
    if (["checkbox", "radio"].includes(type)) return "toggle";
    if (["submit", "button"].includes(type) || tag === "button" || role === "button") return "button";
    if (tag === "textarea") return "text_area";
    if (tag === "select") return "select";
    if (tag === "a") return "link";
    if (tag === "label") return "label";
    return tag;
  }
  function safeText(element) {
    if (!element) {
      return "";
    }
    const raw = element.innerText || element.textContent || "";
    return raw.trim().slice(0, 120);
  }
  function descriptor(target) {
    const element = target || document.activeElement || document.body;
    const autocomplete = element && element.autocomplete ? element.autocomplete : "";
    return {
      selector: cssPath(element),
      name: element && element.name ? element.name : "",
      inputType: element && element.type ? element.type : "",
      autocomplete: autocomplete,
      tagName: element && element.tagName ? element.tagName.toLowerCase() : "",
      elementRole: inferElementRole(element, autocomplete),
      textPreview: safeText(element),
      value: element && typeof element.value === "string" ? element.value : "",
      valueLength: element && typeof element.value === "string" ? element.value.length : 0,
      ariaLabel: element && element.getAttribute ? (element.getAttribute("aria-label") || "") : "",
      placeholder: element && element.placeholder ? element.placeholder : "",
      buttonText: element ? safeText(element) : "",
      disabled: !!(element && element.disabled),
      checked: !!(element && element.checked),
      elementRect: element && element.getBoundingClientRect ? (() => {
        const rect = element.getBoundingClientRect();
        return {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        };
      })() : null,
      viewportWidth: window.innerWidth || 0,
      viewportHeight: window.innerHeight || 0,
    };
  }
  function emitPayload(payload) {
    window.__iabvTeachEvents.push(payload);
    if (window.__iabvTeachEvents.length > 800) {
      window.__iabvTeachEvents.shift();
    }
  }
  function frameInfo() {
    return {
      frameUrl: window.location.href,
      frameName: window.name || "",
      frameSelector: "",
      isTopFrame: window.top === window,
    };
  }
  function pushEvent(type, nativeEvent, captureSource) {
    if (window.__iabvTeachPaused) {
      return;
    }
    const payload = descriptor(nativeEvent && nativeEvent.target ? nativeEvent.target : document.activeElement);
    const frame = frameInfo();
    const keyValue = nativeEvent && typeof nativeEvent.key === "string" ? nativeEvent.key : "";
    const keyPrintable = !!keyValue && keyValue.length === 1;
    emitPayload({
      eventId: eventId(),
      type: type,
      selector: payload.selector,
      name: payload.name,
      inputType: payload.inputType,
      autocomplete: payload.autocomplete,
      tagName: payload.tagName,
      elementRole: payload.elementRole,
      textPreview: payload.textPreview,
      value: payload.value,
      valueLength: payload.valueLength,
      ariaLabel: payload.ariaLabel,
      placeholder: payload.placeholder,
      buttonText: payload.buttonText,
      disabled: payload.disabled,
      checked: payload.checked,
      elementRect: payload.elementRect,
      viewportWidth: payload.viewportWidth,
      viewportHeight: payload.viewportHeight,
      key: keyPrintable ? "[character]" : keyValue,
      keyCode: nativeEvent && nativeEvent.code ? nativeEvent.code : "",
      keyPrintable: keyPrintable,
      url: window.location.href,
      frameUrl: frame.frameUrl,
      frameName: frame.frameName,
      frameSelector: frame.frameSelector,
      isTopFrame: frame.isTopFrame,
      captureSource: captureSource || "bridge",
      timestamp: new Date().toISOString(),
      scrollY: window.scrollY,
    });
  }
  ["click", "change", "submit", "focus"].forEach((eventName) => {
    document.addEventListener(eventName, (event) => pushEvent(eventName, event, "bridge"), true);
  });
  document.addEventListener("input", (event) => pushEvent("input", event, "bridge_buffered"), true);
  document.addEventListener("keydown", (event) => pushEvent("keydown", event, "bridge_buffered"), true);
  let scrollTimer = null;
  window.addEventListener("scroll", () => {
    if (scrollTimer) {
      return;
    }
    scrollTimer = window.setTimeout(() => {
      scrollTimer = null;
      pushEvent("scroll", { target: document.scrollingElement || document.body }, "bridge_buffered");
    }, 350);
  }, true);
  if (!window.__iabvTeachHeartbeatTimer) {
    window.__iabvTeachHeartbeatTimer = window.setInterval(() => {
      if (window.__iabvTeachPaused) {
        return;
      }
      const frame = frameInfo();
      emitPayload({
        eventId: eventId(),
        type: "heartbeat",
        selector: "body",
        name: "",
        inputType: "",
        autocomplete: "",
        tagName: "body",
        elementRole: "document",
        textPreview: safeText(document.body),
        value: "",
        valueLength: 0,
        ariaLabel: "",
        placeholder: "",
        buttonText: "",
        disabled: false,
        checked: false,
        url: window.location.href,
        frameUrl: frame.frameUrl,
        frameName: frame.frameName,
        frameSelector: frame.frameSelector,
        isTopFrame: frame.isTopFrame,
        captureSource: "interval",
        timestamp: new Date().toISOString(),
        scrollY: window.scrollY,
      });
    }, 3000);
  }
  return true;
}
"""

BRIDGE_DRAIN_EXPR = """
() => {
  const events = window.__iabvTeachEvents || [];
  window.__iabvTeachEvents = [];
  return events;
}
"""

BRIDGE_SET_PAUSED_EXPR = """
(value) => {
  window.__iabvTeachPaused = !!value;
  return window.__iabvTeachPaused;
}
"""

MAX_EVENTS_PER_FLUSH = 120
MAX_SCREENSHOTS_PER_FLUSH = 2
MAX_SAVED_NETWORK_EXCHANGES = 120
MAX_RECENT_CONSOLE_MESSAGES = 120
SLOW_API_THRESHOLD_MS = 1800.0
BASELINE_SAMPLES_PER_ENDPOINT = 2
PERIODIC_SCREENSHOT_SECONDS = 3.0


DOM_SNAPSHOT_EXPR = """
() => {
  const fieldData = Array.from(document.querySelectorAll("input, textarea, select")).slice(0, 120).map((element) => ({
    selector: element.id ? ("#" + element.id) : element.tagName.toLowerCase(),
    name: element.name || "",
    type: element.type || "",
    autocomplete: element.autocomplete || "",
    placeholder: element.placeholder || "",
    disabled: !!element.disabled,
    value_length: typeof element.value === "string" ? element.value.length : 0,
  }));
  return {
    url: window.location.href,
    title: document.title || "",
    html_excerpt: document.documentElement.outerHTML.slice(0, 12000),
    visible_text_excerpt: (document.body && document.body.innerText ? document.body.innerText : "").slice(0, 6000),
    form_fields: fieldData,
    storage_keys: {
      localStorage: Object.keys(window.localStorage || {}),
      sessionStorage: Object.keys(window.sessionStorage || {}),
    },
  };
}
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_frame_event_context(frame_reference: str) -> dict[str, Any]:
    if not frame_reference:
        return {}
    parsed = urlsplit(frame_reference)
    fragment = parsed.fragment or ''
    if not fragment:
        return {}
    try:
        payload = json.loads(unquote(fragment))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


class BrowserTeachSessionService:
    def __init__(
        self,
        controller: BrowserSessionController,
        episode_repository: EpisodeRepository,
        screenshot_store: ScreenshotStore,
        artifact_repository: SessionArtifactRepository,
        redaction_engine: RedactionEngine,
        site_session_manager: SiteSessionManager,
    ) -> None:
        self.controller = controller
        self.episode_repository = episode_repository
        self.screenshot_store = screenshot_store
        self.artifact_repository = artifact_repository
        self.redaction_engine = redaction_engine
        self.site_session_manager = site_session_manager
        self.page = None
        self.current_episode: EpisodeManifest | None = None
        self.profile_config: BrowserProfileConfig | None = None
        self.site_policy: SitePolicy | None = None
        self.session_state: SiteSessionResult | None = None
        self.redaction_summary = RedactionSummary()
        self._pending_network: dict[str, tuple[NetworkExchange, float]] = {}
        self._completed_network: list[NetworkExchange] = []
        self._saved_network_exchange_ids: set[str] = set()
        self._last_network_by_endpoint: dict[str, NetworkExchange] = {}
        self._network_seen_by_endpoint: dict[str, int] = {}
        self._console_messages: list[dict[str, Any]] = []
        self._paused = False
        self._bridge_active = False
        self._processed_event_ids: set[str] = set()
        self._processed_event_order: list[str] = []
        self._visible_step_count = 0
        self._screenshot_count = 0
        self._api_seen_count = 0
        self._api_saved_count = 0
        self._api_dropped_count = 0
        self._frames_detected = 0
        self._last_periodic_capture_at = 0.0
        self._reported_frame_fallbacks: set[str] = set()
        self._observed_page_ids: set[int] = set()
        self._session_status = 'idle'
        self._finalize_error = ''
        self._session_started_at = 0.0
        self._last_visible_progress_at = 0.0
        self._last_screenshot_at = 0.0
        self._heartbeat_count = 0
        self._last_queue_depth = 0
        self._poll_without_progress_count = 0
        self._page_records: dict[int, dict[str, Any]] = {}
        self._recent_urls: list[str] = []
        self._storage_state_available = False
        self._manual_login_required_repeated = False
        self._last_finalize_duration_ms = 0.0
        self._reported_structured_fallbacks: set[str] = set()

    @property
    def capture_stats(self) -> dict[str, Any]:
        return {
            'status': self._session_status,
            'bridge_active': self._bridge_active,
            'capture_visible_ok': self._visible_step_count > 0 or self._screenshot_count > 0,
            'frames_detected': self._frames_detected,
            'api_capture_mode': 'smart',
            'periodic_screenshot_seconds': PERIODIC_SCREENSHOT_SECONDS,
            'visible_step_count': self._visible_step_count,
            'screenshot_count': self._screenshot_count,
            'api_seen_count': self._api_seen_count,
            'api_saved_count': self._api_saved_count,
            'api_dropped_count': self._api_dropped_count,
            'finalize_error': self._finalize_error,
            'queue_depth': self._last_queue_depth,
            'heartbeat_count': self._heartbeat_count,
            'finalize_duration_ms': self._last_finalize_duration_ms,
        }

    def _current_page(self):
        page = self.controller.page or self.page
        if page is not None:
            self.page = page
        return page

    def _attach_context_page_observer(self) -> None:
        context = self.controller.context
        if context is None:
            return
        try:
            context.on('page', self._on_new_page)
        except Exception:
            return

    def _observe_page(self, page) -> None:
        if page is None:
            return
        self.page = page
        if hasattr(self.controller, 'adopt_page'):
            self.controller.adopt_page(page)
        page_id = id(page)
        record = self._page_records.setdefault(page_id, {'created_at': time.monotonic(), 'last_progress_at': time.monotonic(), 'bridge_active': False, 'url': getattr(page, 'url', '') or ''})
        record['url'] = getattr(page, 'url', '') or record.get('url', '')
        self._remember_url(record['url'])
        if page_id in self._observed_page_ids:
            return
        self._observed_page_ids.add(page_id)
        self._install_bridge(page)
        self._attach_network_capture(page)
        self._attach_frame_observers(page)
        try:
            page.on('domcontentloaded', lambda: self._mark_page_progress(getattr(page, 'url', '') or ''))
            page.on('load', lambda: self._mark_page_progress(getattr(page, 'url', '') or ''))
        except Exception:
            pass

    def _on_new_page(self, page) -> None:
        page_id = id(page)
        self._page_records.setdefault(page_id, {'created_at': time.monotonic(), 'last_progress_at': time.monotonic(), 'bridge_active': False, 'url': getattr(page, 'url', '') or ''})
        self._observe_page(page)

    def start_session(
        self,
        *,
        title: str,
        url: str,
        profile_config: BrowserProfileConfig,
        site_policy: SitePolicy,
        tags: list[str] | None = None,
    ) -> tuple[EpisodeManifest, SiteSessionResult]:
        self.profile_config = profile_config
        self.site_policy = site_policy
        self.redaction_summary = RedactionSummary()
        self._pending_network = {}
        self._completed_network = []
        self._saved_network_exchange_ids = set()
        self._last_network_by_endpoint = {}
        self._network_seen_by_endpoint = {}
        self._console_messages = []
        self._paused = False
        self._bridge_active = False
        self._processed_event_ids = set()
        self._processed_event_order = []
        self._visible_step_count = 0
        self._screenshot_count = 0
        self._api_seen_count = 0
        self._api_saved_count = 0
        self._api_dropped_count = 0
        self._frames_detected = 0
        self._last_periodic_capture_at = 0.0
        self._reported_frame_fallbacks = set()
        self._observed_page_ids = set()
        self._session_status = 'capturing'
        self._finalize_error = ''
        self._session_started_at = time.monotonic()
        self._last_visible_progress_at = self._session_started_at
        self._last_screenshot_at = self._session_started_at
        self._heartbeat_count = 0
        self._last_queue_depth = 0
        self._poll_without_progress_count = 0
        self._page_records = {}
        self._recent_urls = []
        self._storage_state_available = bool(profile_config.storage_state_path and Path(profile_config.storage_state_path).exists())
        self._manual_login_required_repeated = False
        self._last_finalize_duration_ms = 0.0
        self._reported_structured_fallbacks = set()
        self._last_periodic_capture_at = self._session_started_at

        self.controller.start(profile_config)
        self.page = self.controller.page or self.controller.new_page()
        self.current_episode = self.episode_repository.create_episode(
            title=title,
            tags=(tags or []) + ['browser_teach', f'site:{site_policy.site_id}'],
            notes=f'teach_url={url}',
        )
        self._attach_context_page_observer()
        self._observe_page(self.page)
        self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        self.session_state = self.site_session_manager.load_or_prompt_login(self.page, profile_config, site_policy)
        self._manual_login_required_repeated = bool(self._storage_state_available and self.session_state.requires_manual_login)
        self._remember_url(getattr(self.page, 'url', '') or url)
        if self.session_state.authenticated and self.profile_config is not None:
            self.site_session_manager.save_site_state(self.controller, self.profile_config)
        return self.current_episode, self.session_state

    def runtime_snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        active_page = self._current_page()
        active_page_id = id(active_page) if active_page is not None else None
        active_record = self._page_records.get(active_page_id, {}) if active_page_id is not None else {}
        page_count = 0
        try:
            context = self.controller.context
            page_count = len(context.pages) if context is not None else 0
        except Exception:
            page_count = max(len(self._page_records), 1 if active_page is not None else 0)
        observed_count = len(self._page_records)
        max_unobserved_tab_age = 0.0
        if page_count > observed_count and self._session_started_at:
            max_unobserved_tab_age = max(0.0, now - self._session_started_at)
        active_url = getattr(active_page, 'url', '') if active_page is not None else ''
        self._remember_url(active_url)
        return {
            **self.capture_stats,
            'episode_id': self.current_episode.episode_id if self.current_episode is not None else '',
            'site_id': self.site_policy.site_id if self.site_policy is not None else '',
            'status': self._session_status,
            'page_count': page_count,
            'observed_page_count': observed_count,
            'last_active_url': active_url,
            'recent_urls': list(self._recent_urls),
            'seconds_since_session_start': max(0.0, now - self._session_started_at) if self._session_started_at else 0.0,
            'seconds_since_last_visible_progress': max(0.0, now - self._last_visible_progress_at) if self._last_visible_progress_at else 0.0,
            'seconds_since_last_screenshot': max(0.0, now - self._last_screenshot_at) if self._last_screenshot_at else 0.0,
            'active_navigation_stall_seconds': max(0.0, now - float(active_record.get('last_progress_at', self._last_visible_progress_at or now))),
            'max_unobserved_tab_age': max_unobserved_tab_age,
            'poll_without_progress_count': self._poll_without_progress_count,
            'storage_state_available': self._storage_state_available,
            'manual_login_required_repeated': self._manual_login_required_repeated,
            'recent_evidence_ids': list(self._processed_event_order[-5:]),
        }

    def record_step(
        self,
        *,
        action_type: str,
        target: str | None = None,
        text_value: str | None = None,
        metadata: dict[str, Any] | None = None,
        capture_screenshot: bool = True,
    ) -> CapturedStep:
        if self.current_episode is None:
            raise RuntimeError('No active browser teach session.')
        step_metadata = dict(metadata or {})
        active_page = self._current_page()
        screenshot_path = None
        if capture_screenshot and active_page is not None:
            try:
                screenshot_name = f"visible_{int(_utc_now().timestamp() * 1000)}.png"
                screenshot_bytes = active_page.screenshot(full_page=False)
                screenshot_path = self.screenshot_store.save_bytes(self.current_episode.episode_id, screenshot_name, screenshot_bytes)
                step_metadata.setdefault('capture_channel', CaptureChannel.VISIBLE.value)
                self._screenshot_count += 1
                self._last_screenshot_at = time.monotonic()
            except Exception:
                screenshot_path = None
        step = CapturedStep(
            episode_id=self.current_episode.episode_id,
            action_type=action_type,
            target=target,
            text_value=text_value,
            screenshot_path=screenshot_path,
            metadata=step_metadata,
        )
        redacted_step, summary = self.redaction_engine.redact_step(step, self.site_policy)
        self._merge_summary(summary)
        saved = self.episode_repository.save_step(self.current_episode.episode_id, redacted_step)
        if step_metadata.get('capture_channel') == CaptureChannel.VISIBLE.value and action_type != 'teaching_brief':
            self._visible_step_count += 1
            self._last_visible_progress_at = time.monotonic()
        frame_url = step_metadata.get('frame_url') or step_metadata.get('url') or getattr(self._current_page(), 'url', '')
        if frame_url:
            self._remember_url(frame_url)
            self._mark_page_progress(frame_url)
        return saved

    def poll_live_capture(self) -> dict[str, Any]:
        if self.current_episode is None or self._paused or self._session_status == 'finalizing':
            return self.runtime_snapshot()
        active_page = self._current_page()
        if active_page is None:
            return self.runtime_snapshot()
        before_progress = self._visible_step_count + self._screenshot_count
        events = self._drain_bridge_events()
        self._last_queue_depth = len(events)
        for event in events[-MAX_EVENTS_PER_FLUSH:]:
            self._consume_visible_event(event)
        after_progress = self._visible_step_count + self._screenshot_count
        if after_progress <= before_progress:
            self._poll_without_progress_count += 1
        else:
            self._poll_without_progress_count = 0
        if time.monotonic() - self._last_periodic_capture_at >= PERIODIC_SCREENSHOT_SECONDS and not events:
            self._capture_periodic_checkpoint(self._current_checkpoint_payload())
        self._remember_url(getattr(active_page, 'url', '') or '')
        return self.runtime_snapshot()

    def flush_observations(self) -> BrowserObservationBundle:
        if self.current_episode is None:
            raise RuntimeError('No active browser teach session.')
        dom_snapshots: list[DomSnapshot] = []
        network_exchanges: list[NetworkExchange] = []
        storage_summary: dict[str, Any] = {}
        capture_channels: list[CaptureChannel] = [CaptureChannel.VISIBLE]
        active_page = self._current_page()
        current_url = getattr(active_page, 'url', '') if active_page is not None else ''

        if active_page is not None:
            for event in self._drain_bridge_events()[-MAX_EVENTS_PER_FLUSH:]:
                self._consume_visible_event(event)
            if self.site_policy is not None and self.site_policy.capture_dom:
                dom_snapshot = self._capture_dom_snapshot()
                if dom_snapshot is not None:
                    dom_snapshots.append(dom_snapshot)
                    storage_summary = dom_snapshot.storage_keys
                    capture_channels.append(CaptureChannel.BACKGROUND)
                    self._save_artifact(
                        kind='dom_snapshot',
                        relative_path=f'{self.current_episode.episode_id}/background/{dom_snapshot.snapshot_id}.json',
                        payload=dom_snapshot.model_dump(mode='json'),
                        metadata={
                            'artifact_kind': 'dom_snapshot',
                            'capture_channel': CaptureChannel.BACKGROUND.value,
                            'domain': self.site_session_manager.domain_for_url(dom_snapshot.url),
                            'site_id': self.site_policy.site_id,
                            'content_type': 'application/json',
                            'redacted': True,
                        },
                    )

        for exchange in self._prepare_network_exchanges_for_persist():
            network_exchanges.append(exchange)
            capture_channels.append(CaptureChannel.API)
            self._save_artifact(
                kind='network_exchange',
                relative_path=f'{self.current_episode.episode_id}/api/{exchange.exchange_id}.json',
                payload=exchange.model_dump(mode='json'),
                metadata={
                    'artifact_kind': 'network_exchange',
                    'capture_channel': CaptureChannel.API.value,
                    'domain': self.site_session_manager.domain_for_url(exchange.url),
                    'site_id': self.site_policy.site_id if self.site_policy is not None else '',
                    'content_type': exchange.content_type or 'application/json',
                    'redacted': exchange.redacted,
                    'redacted_fields': self.redaction_summary.redacted_network_fields,
                },
            )

        if self._console_messages:
            capture_channels.append(CaptureChannel.BACKGROUND)
            self._save_artifact(
                kind='console_log',
                relative_path=f'{self.current_episode.episode_id}/background/console.json',
                payload=self._console_messages,
                metadata={
                    'artifact_kind': 'console_log',
                    'capture_channel': CaptureChannel.BACKGROUND.value,
                    'domain': self.site_session_manager.domain_for_url(current_url),
                    'site_id': self.site_policy.site_id if self.site_policy is not None else '',
                    'content_type': 'application/json',
                    'redacted': True,
                },
            )

        bundle = BrowserObservationBundle(
            episode_id=self.current_episode.episode_id,
            url=current_url,
            capture_channels=sorted(set(capture_channels), key=lambda item: item.value),
            dom_snapshots=dom_snapshots,
            network_exchanges=network_exchanges,
            console_messages=list(self._console_messages),
            storage_summary=storage_summary,
            capture_stats=self.capture_stats,
        )
        self._completed_network = []
        self._saved_network_exchange_ids = set()
        self._last_network_by_endpoint = {}
        self._console_messages = []
        return bundle

    def stop_session(self) -> tuple[BrowserObservationBundle, SiteSessionResult | None]:
        if self.current_episode is None:
            raise RuntimeError('No active browser teach session.')
        self._session_status = 'finalizing'
        bundle: BrowserObservationBundle | None = None
        finalize_error: Exception | None = None
        finalize_started = time.monotonic()
        active_page = self._current_page()
        current_url = getattr(active_page, 'url', '') if active_page is not None else ''
        try:
            self._maybe_record_visibility_fallback('stop_recovery')
            bundle = self.flush_observations()
            self._session_status = 'completed'
        except Exception as exc:
            finalize_error = exc
            self._finalize_error = str(exc)
            self._session_status = 'partial_recovery'
            bundle = BrowserObservationBundle(
                episode_id=self.current_episode.episode_id,
                url=current_url,
                capture_channels=[CaptureChannel.VISIBLE],
                capture_stats=self.capture_stats,
            )
        finally:
            self._last_finalize_duration_ms = max(0.0, (time.monotonic() - finalize_started) * 1000.0)
            if self.profile_config is not None:
                try:
                    self.site_session_manager.save_site_state(self.controller, self.profile_config)
                except Exception:
                    pass
            try:
                self.controller.close()
            finally:
                self.page = None
                self._paused = False
        if bundle is not None:
            stats = dict(bundle.capture_stats)
            stats.update(self.capture_stats)
            bundle = bundle.model_copy(update={'capture_stats': stats})
        if finalize_error is not None:
            self._finalize_error = str(finalize_error)
        return bundle, self.session_state

    def pause_session(self) -> None:
        self._paused = True
        self._session_status = 'paused'
        self._set_bridge_paused(True)

    def resume_session(self) -> None:
        self._paused = False
        self._session_status = 'capturing'
        self._set_bridge_paused(False)

    def _install_bridge(self, page=None) -> None:
        page = page or self._current_page()
        if page is None:
            return
        page.add_init_script(script=BRIDGE_INSTALL_EXPR)
        try:
            page.evaluate(BRIDGE_INSTALL_EXPR)
            self._bridge_active = True
            record = self._page_records.setdefault(id(page), {'created_at': time.monotonic(), 'last_progress_at': time.monotonic(), 'bridge_active': False, 'url': getattr(page, 'url', '') or ''})
            record['bridge_active'] = True
            record['url'] = getattr(page, 'url', '') or record.get('url', '')
        except Exception:
            return

    def _attach_network_capture(self, page=None) -> None:
        page = page or self._current_page()
        if page is None:
            return
        page.on('request', self._on_request)
        page.on('response', self._on_response)
        page.on('console', self._on_console)

    def _attach_frame_observers(self, page=None) -> None:
        page = page or self._current_page()
        if page is None:
            return
        page.on('frameattached', self._on_frame_observed)
        page.on('framenavigated', self._on_frame_observed)

    def _on_frame_observed(self, frame) -> None:
        active_page = self._current_page()
        if active_page is None:
            return
        try:
            self._frames_detected = max(self._frames_detected, len(active_page.frames))
        except Exception:
            self._frames_detected = max(self._frames_detected, 1)
        if frame is None or frame == active_page.main_frame:
            return
        try:
            frame.evaluate(BRIDGE_INSTALL_EXPR)
        except Exception:
            self._record_frame_fallback(frame, 'frame_embedded_unhooked')

    def _on_visible_event(self, payload: dict[str, Any]) -> bool:
        self._bridge_active = True
        self._consume_visible_event(payload)
        return True

    def _consume_visible_event(self, event: dict[str, Any]) -> None:
        if self.current_episode is None or not event:
            return
        event_id = str(event.get('eventId') or '')
        if event_id:
            if event_id in self._processed_event_ids:
                return
            self._processed_event_ids.add(event_id)
            self._processed_event_order.append(event_id)
            if len(self._processed_event_order) > 2000:
                stale = self._processed_event_order.pop(0)
                self._processed_event_ids.discard(stale)
        action_type = event.get('type', 'event')
        if action_type == 'heartbeat':
            self._heartbeat_count += 1
            if not event.get('isTopFrame', True):
                return
            now = time.monotonic()
            self._remember_url(event.get('url') or event.get('frameUrl') or '')
            if now - self._last_periodic_capture_at >= PERIODIC_SCREENSHOT_SECONDS:
                self._capture_periodic_checkpoint(event)
            return
        capture_screenshot = self._should_capture_screenshot(action_type, event)
        text_value = None if action_type == 'keydown' else (event.get('value') or None)
        self.record_step(
            action_type=action_type,
            target=event.get('selector'),
            text_value=text_value,
            metadata={
                'selector': event.get('selector'),
                'name': event.get('name'),
                'input_type': event.get('inputType'),
                'autocomplete': event.get('autocomplete'),
                'tag_name': event.get('tagName'),
                'element_role': event.get('elementRole'),
                'textPreview': event.get('textPreview'),
                'value_length': event.get('valueLength'),
                'aria_label': event.get('ariaLabel'),
                'placeholder': event.get('placeholder'),
                'button_text': event.get('buttonText'),
                'disabled': event.get('disabled'),
                'checked': event.get('checked'),
                'url': event.get('url'),
                'frame_url': event.get('frameUrl') or event.get('url'),
                'frame_name': event.get('frameName') or '',
                'frame_selector': event.get('frameSelector') or '',
                'capture_source': event.get('captureSource') or 'bridge',
                'captured_at': event.get('timestamp'),
                'scroll_y': event.get('scrollY'),
                'element_rect': event.get('elementRect'),
                'viewport_width': event.get('viewportWidth'),
                'viewport_height': event.get('viewportHeight'),
                'key_display': event.get('key') or '',
                'key_code': event.get('keyCode') or '',
                'key_printable': bool(event.get('keyPrintable')),
                'capture_channel': CaptureChannel.VISIBLE.value,
                'screenshot_reason': 'interaction' if capture_screenshot else '',
            },
            capture_screenshot=capture_screenshot,
        )

    def _current_checkpoint_payload(self) -> dict[str, Any]:
        active_page = self._current_page()
        if active_page is None:
            return {}
        return {
            'selector': 'body',
            'captureSource': 'interval',
            'frameUrl': getattr(active_page, 'url', '') or '',
            'frameName': '',
            'frameSelector': '',
            'textPreview': '',
            'url': getattr(active_page, 'url', '') or '',
        }

    def _sanitize_display_text(self, value: str | None) -> str:
        return self.redaction_engine.redact_free_text(value, site_policy=self.site_policy) or ''

    def _build_frame_fallback_preview(self, payload: dict[str, Any], reason: str) -> str:
        request_type = str(payload.get('requestType') or '').strip()
        if request_type == 'LoginAndGetTempToken':
            return 'Login detectado en frame embebido; se reconstruyen correo, contrasena y envio protegido.'
        if request_type == 'Logout':
            return 'Logout detectado en frame embebido; se conserva la accion protegida.'
        if request_type:
            return f'Accion detectada en frame embebido: {request_type}.'
        return 'Se detecto un frame embebido sin bridge directo; se conserva captura visible de respaldo.'

    def _should_capture_frame_fallback(self, payload: dict[str, Any], reason: str) -> bool:
        request_type = str(payload.get('requestType') or '').strip()
        if request_type in {'LoginAndGetTempToken', 'Logout'}:
            return True
        return self._screenshot_count == 0 and reason != 'frame_embedded_unhooked'

    def _record_structured_frame_actions(self, payload: dict[str, Any], *, sanitized_frame_url: str) -> None:
        request_type = str(payload.get('requestType') or '').strip()
        request_id = str(payload.get('requestId') or request_type or sanitized_frame_url)
        dedupe_key = f'{request_type}:{request_id}'
        if not request_type or dedupe_key in self._reported_structured_fallbacks:
            return
        self._reported_structured_fallbacks.add(dedupe_key)
        post_params = payload.get('postParams') if isinstance(payload.get('postParams'), dict) else {}
        common = {
            'capture_channel': CaptureChannel.VISIBLE.value,
            'capture_source': 'frame_fallback_structured',
            'frame_url': sanitized_frame_url,
            'frame_name': '',
            'frame_selector': '',
            'frame_request_type': request_type,
        }
        if request_type == 'LoginAndGetTempToken':
            username = post_params.get('username')
            password = post_params.get('password')
            if username:
                self.record_step(
                    action_type='input',
                    target='#login-username',
                    text_value=str(username),
                    metadata={
                        **common,
                        'selector': '#login-username',
                        'name': 'username',
                        'input_type': 'email' if '@' in str(username) else 'text',
                        'element_role': 'email_input' if '@' in str(username) else 'username_input',
                        'placeholder': 'Correo o usuario',
                        'screenshot_reason': '',
                    },
                    capture_screenshot=False,
                )
            if password:
                self.record_step(
                    action_type='input',
                    target='#login-password',
                    text_value=str(password),
                    metadata={
                        **common,
                        'selector': '#login-password',
                        'name': 'password',
                        'input_type': 'password',
                        'element_role': 'password_input',
                        'placeholder': 'Contrasena',
                        'screenshot_reason': '',
                    },
                    capture_screenshot=False,
                )
            self.record_step(
                action_type='keydown',
                target='#login-password',
                text_value=None,
                metadata={
                    **common,
                    'selector': '#login-password',
                    'name': 'password',
                    'input_type': 'password',
                    'element_role': 'password_input',
                    'key_display': 'Enter',
                    'key_code': 'Enter',
                    'key_printable': False,
                    'screenshot_reason': '',
                },
                capture_screenshot=False,
            )
            self.record_step(
                action_type='submit',
                target='#login-form',
                text_value=None,
                metadata={
                    **common,
                    'selector': '#login-form',
                    'element_role': 'form',
                    'button_text': 'Iniciar sesion',
                    'screenshot_reason': 'structured_submit',
                },
                capture_screenshot=True,
            )
        elif request_type == 'Logout':
            self.record_step(
                action_type='click',
                target='#logout',
                text_value=None,
                metadata={
                    **common,
                    'selector': '#logout',
                    'element_role': 'button',
                    'button_text': 'Cerrar sesion',
                    'screenshot_reason': 'structured_logout',
                },
                capture_screenshot=True,
            )

    def _capture_periodic_checkpoint(self, event: dict[str, Any] | None = None) -> None:
        if self.current_episode is None:
            return
        self._last_periodic_capture_at = time.monotonic()
        payload = event or {}
        self.record_step(
            action_type='visual_checkpoint',
            target=payload.get('selector') or 'body',
            text_value=None,
            metadata={
                'selector': payload.get('selector') or 'body',
                'element_role': 'document',
                'capture_channel': CaptureChannel.VISIBLE.value,
                'capture_source': payload.get('captureSource') or 'interval',
                'frame_url': payload.get('frameUrl') or payload.get('url') or getattr(self._current_page(), 'url', ''),
                'frame_name': payload.get('frameName') or '',
                'frame_selector': payload.get('frameSelector') or '',
                'screenshot_reason': 'interval',
                'textPreview': payload.get('textPreview') or '',
            },
            capture_screenshot=True,
        )

    def _maybe_record_visibility_fallback(self, reason: str) -> None:
        active_page = self._current_page()
        if self.current_episode is None or active_page is None or self._screenshot_count > 0:
            return
        self.record_step(
            action_type='visible_recovery',
            target=getattr(active_page, 'url', '') or 'current_page',
            text_value=None,
            metadata={
                'selector': 'body',
                'element_role': 'document',
                'capture_channel': CaptureChannel.VISIBLE.value,
                'capture_source': 'fallback',
                'screenshot_reason': reason,
                'frame_url': getattr(active_page, 'url', ''),
                'frame_name': '',
                'frame_selector': '',
            },
            capture_screenshot=True,
        )

    def _record_frame_fallback(self, frame, reason: str) -> None:
        if self.current_episode is None:
            return
        frame_url = getattr(frame, 'url', '') or ''
        frame_name = getattr(frame, 'name', '') or ''
        fallback_key = f'{frame_name}|{frame_url}|{reason}'
        if fallback_key in self._reported_frame_fallbacks:
            return
        self._reported_frame_fallbacks.add(fallback_key)
        payload = parse_frame_event_context(frame_url)
        request_type = str(payload.get('requestType') or '').strip()
        sanitized_frame_url = self._sanitize_display_text(frame_url)
        target = f'frame:{request_type.lower()}' if request_type else (frame_name or sanitized_frame_url or 'embedded_frame')
        self.record_step(
            action_type='frame_fallback',
            target=target,
            text_value=None,
            metadata={
                'selector': target,
                'element_role': 'frame',
                'capture_channel': CaptureChannel.VISIBLE.value,
                'capture_source': 'frame_fallback',
                'screenshot_reason': reason,
                'frame_url': sanitized_frame_url,
                'frame_name': frame_name,
                'frame_selector': '',
                'frame_request_type': request_type,
                'textPreview': self._build_frame_fallback_preview(payload, reason),
            },
            capture_screenshot=self._should_capture_frame_fallback(payload, reason),
        )
        if payload:
            self._record_structured_frame_actions(payload, sanitized_frame_url=sanitized_frame_url)

    def _on_request(self, request) -> None:
        if self.current_episode is None:
            return
        key = self._request_key(request)
        body = self._read_request_body(request)
        graphql_operation = self._extract_graphql_operation(body)
        exchange = NetworkExchange(
            episode_id=self.current_episode.episode_id,
            url=request.url,
            method=request.method,
            resource_type=getattr(request, 'resource_type', None),
            request_headers=dict(request.headers),
            request_body=body,
            graphql_operation=graphql_operation,
        )
        self._pending_network[key] = (exchange, time.monotonic())

    def _on_response(self, response) -> None:
        if self.current_episode is None:
            return
        request = response.request
        key = self._request_key(request)
        pending = self._pending_network.pop(key, None)
        if pending is None:
            exchange = NetworkExchange(
                episode_id=self.current_episode.episode_id,
                url=request.url,
                method=request.method,
            )
            started = time.monotonic()
        else:
            exchange, started = pending
        headers = dict(response.headers)
        content_type = headers.get('content-type')
        response_body = None
        if content_type and any(token in content_type for token in ('json', 'text', 'graphql')):
            try:
                response_body = response.text()
            except Exception:
                response_body = None
        exchange = exchange.model_copy(
            update={
                'status_code': response.status,
                'response_headers': headers,
                'response_body': response_body,
                'finished_at_utc': _utc_now(),
                'content_type': content_type,
            }
        )
        redacted_exchange, summary = self.redaction_engine.redact_network_exchange(exchange, self.site_policy)
        self._merge_summary(summary)
        self._consider_network_exchange(redacted_exchange, latency_ms=(time.monotonic() - started) * 1000.0)

    def _consider_network_exchange(self, exchange: NetworkExchange, *, latency_ms: float) -> None:
        self._api_seen_count += 1
        endpoint = self._endpoint_key(exchange)
        seen = self._network_seen_by_endpoint.get(endpoint, 0) + 1
        self._network_seen_by_endpoint[endpoint] = seen
        important = (
            (exchange.status_code or 0) >= 400
            or latency_ms >= SLOW_API_THRESHOLD_MS
            or bool(exchange.graphql_operation)
            or 'graphql' in (exchange.content_type or '').lower()
        )
        should_keep = important or seen <= BASELINE_SAMPLES_PER_ENDPOINT
        if should_keep and self._api_saved_count < MAX_SAVED_NETWORK_EXCHANGES:
            self._completed_network.append(exchange)
            self._saved_network_exchange_ids.add(exchange.exchange_id)
            self._api_saved_count += 1
            return
        self._api_dropped_count += 1
        self._last_network_by_endpoint[endpoint] = exchange

    def _prepare_network_exchanges_for_persist(self) -> list[NetworkExchange]:
        exchanges = list(self._completed_network)
        for exchange in self._last_network_by_endpoint.values():
            if exchange.exchange_id in self._saved_network_exchange_ids:
                continue
            if len(exchanges) >= MAX_SAVED_NETWORK_EXCHANGES:
                break
            exchanges.append(exchange)
            self._saved_network_exchange_ids.add(exchange.exchange_id)
            self._api_saved_count += 1
        return exchanges

    def _on_console(self, message) -> None:
        if len(self._console_messages) >= MAX_RECENT_CONSOLE_MESSAGES:
            self._console_messages.pop(0)
        self._console_messages.append(
            {
                'type': message.type,
                'text': message.text,
                'location': getattr(message, 'location', None),
                'captured_at': _utc_now().isoformat(),
            }
        )

    def _remember_url(self, url: str) -> None:
        value = (url or '').strip()
        if not value:
            return
        if self._recent_urls and self._recent_urls[-1] == value:
            return
        self._recent_urls.append(value)
        if len(self._recent_urls) > 3:
            self._recent_urls = self._recent_urls[-3:]

    def _mark_page_progress(self, url: str) -> None:
        current = time.monotonic()
        self._last_visible_progress_at = current
        for record in self._page_records.values():
            if url and record.get('url') == url:
                record['last_progress_at'] = current
                return
        if self.page is not None:
            self._page_records.setdefault(id(self.page), {'created_at': current, 'last_progress_at': current, 'bridge_active': self._bridge_active, 'url': url})

    def _drain_bridge_events(self) -> list[dict[str, Any]]:
        active_page = self._current_page()
        if active_page is None:
            return []
        try:
            events = active_page.evaluate(BRIDGE_DRAIN_EXPR)
        except Exception:
            return []
        return events or []

    def _select_screenshot_event_indexes(self, events: list[dict[str, Any]]) -> set[int]:
        relevant_types = {'click', 'change', 'submit', 'focus'}
        indexes = [index for index, event in enumerate(events) if event.get('type') in relevant_types]
        if len(indexes) <= MAX_SCREENSHOTS_PER_FLUSH:
            return set(indexes)
        return set(indexes[-MAX_SCREENSHOTS_PER_FLUSH:])

    def _should_capture_screenshot(self, action_type: str, event: dict[str, Any] | None = None) -> bool:
        if action_type in {'click', 'change', 'submit', 'focus'}:
            return True
        if action_type == 'keydown':
            key_display = str((event or {}).get('key') or '').lower()
            return key_display in {'enter', 'tab'}
        return False

    def _capture_dom_snapshot(self) -> DomSnapshot | None:
        active_page = self._current_page()
        if active_page is None or self.current_episode is None:
            return None
        try:
            payload = active_page.evaluate(DOM_SNAPSHOT_EXPR)
        except Exception:
            return None
        cookies_summary = []
        try:
            context = self.controller.context
            if context is not None and payload.get('url'):
                for cookie in context.cookies([payload.get('url')]):
                    cookies_summary.append(
                        {
                            'name': cookie.get('name'),
                            'domain': cookie.get('domain'),
                            'path': cookie.get('path'),
                            'secure': cookie.get('secure'),
                            'httpOnly': cookie.get('httpOnly'),
                            'expires': cookie.get('expires'),
                        }
                    )
        except Exception:
            cookies_summary = []
        frame_sources = []
        try:
            for frame in active_page.frames:
                frame_sources.append(
                    {
                        'url': getattr(frame, 'url', '') or '',
                        'name': getattr(frame, 'name', '') or '',
                        'is_main_frame': frame == active_page.main_frame,
                    }
                )
            self._frames_detected = max(self._frames_detected, len(frame_sources))
        except Exception:
            frame_sources = []
        return DomSnapshot(
            episode_id=self.current_episode.episode_id,
            url=payload.get('url') or getattr(active_page, 'url', ''),
            title=payload.get('title', ''),
            html_excerpt=payload.get('html_excerpt', ''),
            visible_text_excerpt=payload.get('visible_text_excerpt', ''),
            form_fields=payload.get('form_fields', []),
            storage_keys=payload.get('storage_keys', {}),
            cookies_summary=cookies_summary,
            frame_count=len(frame_sources),
            frame_sources=frame_sources,
        )

    def _save_artifact(self, *, kind: str, relative_path: str, payload: Any, metadata: dict[str, Any]) -> SessionArtifact:
        artifact = SessionArtifact(
            episode_id=self.current_episode.episode_id,
            kind=kind,
            path=relative_path,
            metadata=metadata,
        )
        return self.artifact_repository.save(artifact, payload=payload)

    def _read_request_body(self, request) -> str | None:
        try:
            post_data_buffer = getattr(request, 'post_data_buffer', None)
        except Exception:
            post_data_buffer = None
        if callable(post_data_buffer):
            try:
                raw = post_data_buffer()
                if raw is None:
                    return None
                if isinstance(raw, bytes):
                    return raw.decode('utf-8', errors='replace')
                return str(raw)
            except Exception:
                pass
        try:
            post_data = getattr(request, 'post_data', None)
        except Exception:
            post_data = None
        if callable(post_data):
            try:
                return post_data()
            except Exception:
                return None
        return post_data

    def _extract_graphql_operation(self, body: str | None) -> str | None:
        if not body:
            return None
        try:
            payload = json.loads(body)
        except Exception:
            return None
        if isinstance(payload, dict):
            return payload.get('operationName')
        return None

    def _set_bridge_paused(self, paused: bool) -> None:
        active_page = self._current_page()
        if active_page is None:
            return
        try:
            active_page.evaluate(BRIDGE_SET_PAUSED_EXPR, paused)
        except Exception:
            return

    def _request_key(self, request) -> str:
        return f'{request.method}:{request.url}:{id(request)}'

    def _endpoint_key(self, exchange: NetworkExchange) -> str:
        parsed = urlsplit(exchange.url)
        return f'{exchange.method}:{parsed.netloc}{parsed.path}'

    def _merge_summary(self, summary: RedactionSummary) -> None:
        self.redaction_summary.redacted_steps += summary.redacted_steps
        self.redaction_summary.redacted_network_fields += summary.redacted_network_fields
        self.redaction_summary.stored_secrets += summary.stored_secrets
        self.redaction_summary.warnings.extend(summary.warnings)


