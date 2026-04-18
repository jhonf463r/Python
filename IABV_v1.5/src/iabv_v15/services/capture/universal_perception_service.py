from __future__ import annotations

import csv
import io
import os
import subprocess
import threading
import time
from typing import Any

try:
    import ctypes
    from ctypes import wintypes
except Exception:  # pragma: no cover - non-Windows fallback
    ctypes = None
    wintypes = None

from iabv_v15.domain.models import ToolCard, VisualSignalSnapshot, canonical_external_state_flags
from iabv_v15.services.tools.tool_registry import ToolRegistry


class UniversalPerceptionService:
    """Builds a normalized multimodal perception signal for browser pages and desktop apps."""

    def __init__(self, *, tool_registry: ToolRegistry | None = None) -> None:
        self.tool_registry = tool_registry
        self._user32 = self._load_user32()
        self._desktop_probe_lock = threading.RLock()
        self._desktop_probe_cache = {
            "captured_at": 0.0,
            "process_rows": [],
            "windows": [],
        }

    def build_signal(
        self,
        *,
        replay_summary: dict[str, Any] | None = None,
        session_health: dict[str, Any] | None = None,
        lane_summary: dict[str, Any] | None = None,
        runtime_signals: list[dict[str, Any]] | None = None,
        tool_id: str = "",
        assistant_kind: str = "",
        site_id: str = "",
        external_state_flags: list[str] | None = None,
    ) -> VisualSignalSnapshot:
        base_signal = self.build_capture_signal(
            replay_summary=replay_summary,
            session_health=session_health,
            lane_summary=lane_summary,
            runtime_signals=runtime_signals,
            site_id=site_id,
            external_state_flags=external_state_flags,
        )
        if tool_id or assistant_kind:
            return self.scan_tool_context(
                tool_id=tool_id,
                assistant_kind=assistant_kind,
                fallback_signal=base_signal,
                external_state_flags=external_state_flags,
            )
        return base_signal

    def build_capture_signal(
        self,
        *,
        replay_summary: dict[str, Any] | None = None,
        session_health: dict[str, Any] | None = None,
        lane_summary: dict[str, Any] | None = None,
        runtime_signals: list[dict[str, Any]] | None = None,
        site_id: str = "",
        external_state_flags: list[str] | None = None,
    ) -> VisualSignalSnapshot:
        summary = dict(replay_summary or {})
        metadata = dict(summary.get("metadata") or {})
        session = dict(session_health or {})
        lane = dict(lane_summary or {})
        runtime = [dict(item) for item in (runtime_signals or []) if isinstance(item, dict)]
        visual_summary = dict(summary.get("visual_summary") or {})
        learning_readiness = dict(summary.get("learning_readiness") or {})
        cross_check = dict(summary.get("cross_check_summary") or {})
        login_learning = dict(summary.get("login_learning") or {})

        visible_targets = self._unique_strings(
            summary.get("visible_targets"),
            metadata.get("visible_targets"),
            summary.get("focus_targets"),
            metadata.get("focus_targets"),
        )[:8]
        visual_evidence_refs = self._unique_strings(
            summary.get("visual_evidence_refs"),
            metadata.get("visual_evidence_refs"),
            summary.get("evidence_refs"),
            metadata.get("evidence_refs"),
            summary.get("audit_findings"),
            metadata.get("audit_findings"),
        )[:8]
        latest_url = self._first_text(
            metadata.get("latest_url"),
            summary.get("latest_url"),
            metadata.get("url"),
            summary.get("url"),
            metadata.get("last_active_url"),
            session.get("current_url"),
        )
        latest_title = self._first_text(
            metadata.get("latest_title"),
            summary.get("latest_title"),
            metadata.get("page_title"),
            session.get("window_title"),
        )
        dom_available = bool(
            metadata.get("dom_available")
            or summary.get("dom_available")
            or metadata.get("dom_node_count")
            or summary.get("dom_node_count")
            or session.get("dom_available")
        )
        capture_available = bool(
            summary
            or lane.get("total")
            or session.get("status")
            or visual_evidence_refs
            or latest_url
            or latest_title
        )
        login_required = str(session.get("status") or "").strip().lower() == "login_required" or bool(session.get("login_required"))
        login_detected = bool(
            summary.get("login_detected")
            or metadata.get("login_detected")
            or login_learning.get("status") in {"partial", "ready"}
            or login_required
        )
        learning_ready = bool(
            summary.get("learning_ready")
            or metadata.get("learning_ready")
            or learning_readiness.get("status") == "ready"
        )
        cross_check_status = self._first_text(
            summary.get("cross_check_status"),
            metadata.get("cross_check_status"),
            cross_check.get("status"),
            learning_readiness.get("status"),
        )
        detected_blocks = self._detected_blocks(
            external_state_flags=external_state_flags,
            session_status=str(session.get("status") or ""),
            login_required=login_required,
        )
        unresolved_fields = [
            str(item).strip()
            for item in (summary.get("unresolved_fields") or metadata.get("unresolved_fields") or [])
            if str(item).strip()
        ]
        if not capture_available and "UNRESOLVED:visual_signal_source" not in unresolved_fields:
            unresolved_fields.append("UNRESOLVED:visual_signal_source")
        dom_summary = {
            "status": "available" if dom_available else "no_disponible",
            "reason": "" if dom_available else "dom_not_exposed_in_current_capture",
            "dom_available": dom_available,
            "node_count": int(metadata.get("dom_node_count") or summary.get("dom_node_count") or 0),
            "observed_page_count": int(metadata.get("observed_page_count") or metadata.get("page_count") or 0),
            "accessible_tree": "available" if dom_available else "no_disponible",
        }
        visual_snapshot = {
            "status": "available" if capture_available else "no_disponible",
            "capture_mode": "browser_or_page",
            "screen_capture": "available" if capture_available else "no_disponible",
            "green_count": int(visual_summary.get("green_count") or summary.get("green_count") or 0),
            "orange_count": int(visual_summary.get("orange_count") or summary.get("orange_count") or 0),
            "red_count": int(visual_summary.get("red_count") or summary.get("red_count") or 0),
            "useful_frame_count": int(summary.get("useful_frame_count") or metadata.get("useful_frame_count") or 0),
            "session_health_status": str(session.get("status") or ""),
            "window_title": latest_title,
        }
        available_actions = self._capture_available_actions(
            latest_url=latest_url,
            latest_title=latest_title,
            visible_targets=visible_targets,
            dom_available=dom_available,
            capture_available=capture_available,
            lane_summary=lane,
        )
        confidence = self._capture_confidence(
            capture_available=capture_available,
            dom_available=dom_available,
            latest_url=latest_url,
            latest_title=latest_title,
            visible_targets=visible_targets,
            evidence_refs=visual_evidence_refs,
            unresolved_fields=unresolved_fields,
        )
        return VisualSignalSnapshot(
            source=str(summary.get("source") or metadata.get("source") or "capture_studio_universal"),
            source_app=str(site_id or metadata.get("site_id") or summary.get("site_id") or "browser_page"),
            capture_available=capture_available,
            dom_available=dom_available,
            latest_url=latest_url,
            latest_title=latest_title,
            visible_targets=visible_targets,
            login_detected=login_detected,
            learning_ready=learning_ready,
            cross_check_status=cross_check_status,
            visual_evidence_refs=visual_evidence_refs,
            visual_snapshot=visual_snapshot,
            dom_summary=dom_summary,
            available_actions=available_actions,
            detected_blocks=detected_blocks,
            confidence=confidence,
            unresolved_fields=unresolved_fields,
            metadata={
                "source_context": "capture_studio",
                "lane_summary": lane,
                "runtime_signal_count": len(runtime),
                "session_health_status": str(session.get("status") or ""),
                "learning_status": str(learning_readiness.get("status") or ""),
                "login_status": str(login_learning.get("status") or ""),
            },
        )

    def scan_codex_local(self) -> VisualSignalSnapshot:
        return self.scan_tool_context(tool_id="codex_installed", assistant_kind="codex")

    def scan_tool_context(
        self,
        *,
        tool_id: str = "",
        assistant_kind: str = "",
        fallback_signal: VisualSignalSnapshot | dict[str, Any] | None = None,
        external_state_flags: list[str] | None = None,
    ) -> VisualSignalSnapshot:
        card = self._resolve_tool_card(tool_id=tool_id, assistant_kind=assistant_kind)
        hints = self._title_hints(card=card, assistant_kind=assistant_kind)
        desktop_snapshot = self._desktop_snapshot()
        process_rows = desktop_snapshot["process_rows"]
        windows = desktop_snapshot["windows"]
        matched_windows = [item for item in windows if self._window_matches(item, hints=hints)]
        matched_processes = [
            item
            for item in process_rows
            if self._process_matches(item, card=card, assistant_kind=assistant_kind, hints=hints, matched_windows=matched_windows)
        ]
        matched_pid = int((matched_windows[0] if matched_windows else matched_processes[0] if matched_processes else {}).get("pid") or 0)
        process_running = bool(matched_processes or matched_pid)
        window_title = self._first_text(*(item.get("title") for item in matched_windows))
        process_name = self._first_text(*(item.get("image_name") for item in matched_processes))
        resolved_source_app = self._first_text(
            str((card.metadata if card is not None else {}).get("assistant_kind") or ""),
            assistant_kind,
            card.title if card is not None else "",
            "desktop_app",
        )
        flags = canonical_external_state_flags(list(external_state_flags or []))
        detected_blocks = self._detected_blocks(
            external_state_flags=flags,
            session_status="",
            login_required=False,
        )
        unresolved_fields: list[str] = []
        if not matched_windows:
            unresolved_fields.append("UNRESOLVED:visual_snapshot")
        if process_running and not process_name:
            unresolved_fields.append("UNRESOLVED:process_name")
        dom_summary = {
            "status": "no_disponible",
            "reason": "desktop_app_without_accessible_dom",
            "dom_available": False,
            "accessible_tree": "no_disponible",
        }
        if not matched_windows and not matched_processes:
            dom_summary["reason"] = "desktop_app_not_observed"
        available_actions = self._tool_available_actions(card=card, window_visible=bool(matched_windows))
        fallback_metadata = {}
        if isinstance(fallback_signal, VisualSignalSnapshot):
            fallback_metadata = fallback_signal.model_dump(mode="json")
        elif isinstance(fallback_signal, dict):
            fallback_metadata = dict(fallback_signal)
        confidence = self._tool_confidence(
            has_card=card is not None,
            card_available=bool(card.available) if card is not None else False,
            process_running=process_running,
            window_visible=bool(matched_windows),
            unresolved_fields=unresolved_fields,
        )
        latest_title = window_title or (card.title if card is not None else "")
        visual_snapshot = {
            "status": "available" if matched_windows or matched_processes else "no_disponible",
            "capture_mode": "desktop_window_probe",
            "screen_capture": "no_disponible",
            "window_visible": bool(matched_windows),
            "window_title": window_title,
            "process_running": process_running,
            "process_name": process_name,
            "matched_pid": matched_pid,
        }
        latest_url = ""
        visible_targets = self._unique_strings(
            [(action.get("label") or "") for action in available_actions],
            list((fallback_metadata.get("visible_targets") or []))[:3],
        )[:8]
        evidence_refs = self._unique_strings(
            [f"window:{item.get('title')}" for item in matched_windows if str(item.get("title") or "").strip()],
            [f"process:{item.get('image_name')}:{item.get('pid')}" for item in matched_processes if str(item.get("image_name") or "").strip()],
            fallback_metadata.get("visual_evidence_refs"),
        )[:8]
        metadata = {
            "source_context": "desktop_tool_probe",
            "tool_id": card.tool_id if card is not None else tool_id,
            "assistant_kind": str((card.metadata if card is not None else {}).get("assistant_kind") or assistant_kind or ""),
            "launch_mode": str((card.metadata if card is not None else {}).get("launch_mode") or ""),
            "window_title_hints": hints,
            "process_name": process_name,
            "observed_pid": matched_pid,
            "window_count": len(matched_windows),
            "process_count": len(matched_processes),
            "fallback_visual_signal": fallback_metadata if fallback_metadata else {},
        }
        return VisualSignalSnapshot(
            source="universal_desktop_probe",
            source_app=resolved_source_app,
            capture_available=bool(matched_windows or process_running or (card.available if card is not None else False)),
            dom_available=False,
            latest_url=latest_url,
            latest_title=latest_title,
            visible_targets=visible_targets,
            login_detected=False,
            learning_ready=bool(fallback_metadata.get("learning_ready")),
            cross_check_status=str(fallback_metadata.get("cross_check_status") or ""),
            visual_evidence_refs=evidence_refs,
            visual_snapshot=visual_snapshot,
            dom_summary=dom_summary,
            available_actions=available_actions,
            detected_blocks=detected_blocks,
            confidence=confidence,
            unresolved_fields=unresolved_fields,
            metadata=metadata,
        )

    def _desktop_snapshot(self, *, max_age_seconds: float = 2.0) -> dict[str, list[dict[str, Any]]]:
        with self._desktop_probe_lock:
            cached_at = float(self._desktop_probe_cache.get("captured_at") or 0.0)
            if cached_at and (time.monotonic() - cached_at) <= max(float(max_age_seconds), 0.0):
                return {
                    "process_rows": [dict(item) for item in self._desktop_probe_cache.get("process_rows", [])],
                    "windows": [dict(item) for item in self._desktop_probe_cache.get("windows", [])],
                }
        process_rows = [dict(item) for item in self._list_process_rows()]
        windows = [dict(item) for item in self._list_windows()]
        snapshot = {
            "captured_at": time.monotonic(),
            "process_rows": process_rows,
            "windows": windows,
        }
        with self._desktop_probe_lock:
            self._desktop_probe_cache = snapshot
        return {
            "process_rows": [dict(item) for item in process_rows],
            "windows": [dict(item) for item in windows],
        }

    def _capture_available_actions(
        self,
        *,
        latest_url: str,
        latest_title: str,
        visible_targets: list[str],
        dom_available: bool,
        capture_available: bool,
        lane_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if latest_url:
            actions.append({"action": "open_visible_page", "label": latest_title or latest_url, "target": latest_url, "available": True})
        if dom_available:
            actions.append({"action": "inspect_dom", "label": "Inspeccionar DOM visible", "target": latest_title or latest_url, "available": True})
        for target in visible_targets[:4]:
            actions.append({"action": "interact_visible_target", "label": target, "target": target, "available": capture_available})
        if lane_summary.get("selected_task_id"):
            actions.append(
                {
                    "action": "review_assistant_lane",
                    "label": "Revisar lane asistente",
                    "target": str(lane_summary.get("selected_task_id") or ""),
                    "available": True,
                }
            )
        return actions[:8]

    def _tool_available_actions(self, *, card: ToolCard | None, window_visible: bool) -> list[dict[str, Any]]:
        if card is None:
            return []
        labels = {
            "launch_app": "Abrir aplicacion",
            "llm_query": "Enviar consulta",
            "consult_external": "Consultar desde IABV",
            "code_assistance": "Pedir ayuda tecnica",
            "explain_issue": "Pedir explicacion",
            "web_assisted": "Abrir via web",
        }
        actions: list[dict[str, Any]] = []
        for capability in list(card.capabilities or [])[:8]:
            actions.append(
                {
                    "action": str(capability),
                    "label": labels.get(str(capability), str(capability).replace("_", " ").capitalize()),
                    "target": card.tool_id,
                    "available": bool(card.available and (window_visible or capability == "launch_app")),
                }
            )
        return actions

    def _capture_confidence(
        self,
        *,
        capture_available: bool,
        dom_available: bool,
        latest_url: str,
        latest_title: str,
        visible_targets: list[str],
        evidence_refs: list[str],
        unresolved_fields: list[str],
    ) -> float:
        score = 0.1
        if capture_available:
            score += 0.25
        if dom_available:
            score += 0.2
        if latest_url:
            score += 0.15
        if latest_title:
            score += 0.1
        if visible_targets:
            score += 0.1
        if evidence_refs:
            score += 0.1
        score -= min(0.2, 0.05 * len(unresolved_fields))
        return round(max(0.0, min(0.95, score)), 3)

    def _tool_confidence(
        self,
        *,
        has_card: bool,
        card_available: bool,
        process_running: bool,
        window_visible: bool,
        unresolved_fields: list[str],
    ) -> float:
        score = 0.08
        if has_card:
            score += 0.22
        if card_available:
            score += 0.15
        if process_running:
            score += 0.25
        if window_visible:
            score += 0.25
        score -= min(0.18, 0.06 * len(unresolved_fields))
        return round(max(0.0, min(0.92, score)), 3)

    def _detected_blocks(
        self,
        *,
        external_state_flags: list[str] | None,
        session_status: str,
        login_required: bool,
    ) -> list[str]:
        blocks = canonical_external_state_flags(list(external_state_flags or []))
        normalized_status = str(session_status or "").strip().lower()
        if login_required or normalized_status == "login_required":
            blocks.append("login_required")
        if normalized_status in {"expired", "session_expired"}:
            blocks.append("session_expired")
        return self._unique_strings(blocks)

    def _resolve_tool_card(self, *, tool_id: str, assistant_kind: str) -> ToolCard | None:
        registry = self.tool_registry
        if registry is None:
            return None
        if tool_id:
            card = registry.get_card(tool_id)
            if card is not None:
                return registry.refresh_card(card)
        normalized_assistant = str(assistant_kind or "").strip().lower()
        if not normalized_assistant:
            return None
        preferred = [
            card
            for card in registry.list_cards()
            if str(card.metadata.get("assistant_kind") or "").strip().lower() == normalized_assistant
        ]
        preferred.sort(
            key=lambda card: (
                0 if str(card.metadata.get("launch_mode") or "").strip().lower() == "desktop_app" else 1,
                0 if card.available else 1,
                card.tool_id,
            )
        )
        if not preferred:
            return None
        return registry.refresh_card(preferred[0])

    def _title_hints(self, *, card: ToolCard | None, assistant_kind: str) -> list[str]:
        hints = self._unique_strings(
            list((card.metadata if card is not None else {}).get("window_title_hints") or []),
            [assistant_kind],
            [card.title] if card is not None else [],
        )
        return [item for item in hints if item]

    def _list_process_rows(self) -> list[dict[str, Any]]:
        if os.name != "nt":
            return []
        if os.getenv("PYTEST_CURRENT_TEST"):
            return []
        try:
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/v", "/nh"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=6,
                check=False,
            )
        except Exception:
            return []
        rows: list[dict[str, Any]] = []
        reader = csv.reader(io.StringIO(result.stdout))
        for row in reader:
            if len(row) < 9:
                continue
            rows.append(
                {
                    "image_name": str(row[0] or "").strip(),
                    "pid": int(str(row[1] or "0").strip() or 0),
                    "session_name": str(row[2] or "").strip(),
                    "session_number": str(row[3] or "").strip(),
                    "mem_usage": str(row[4] or "").strip(),
                    "status": str(row[5] or "").strip(),
                    "user_name": str(row[6] or "").strip(),
                    "cpu_time": str(row[7] or "").strip(),
                    "window_title": str(row[8] or "").strip(),
                }
            )
        return rows

    def _list_windows(self) -> list[dict[str, Any]]:
        if os.name != "nt" or self._user32 is None or ctypes is None or wintypes is None:
            return []
        if os.getenv("PYTEST_CURRENT_TEST"):
            return []
        windows: list[dict[str, Any]] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_proc(hwnd, lparam):  # pragma: no cover - exercised on Windows only
            if not self._user32.IsWindowVisible(hwnd):
                return True
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, len(buffer))
            title = str(buffer.value or "").strip()
            if not title:
                return True
            pid = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            windows.append({"title": title, "pid": int(pid.value or 0)})
            return True

        try:
            self._user32.EnumWindows(enum_proc, 0)
        except Exception:
            return []
        return windows

    def _process_matches(
        self,
        item: dict[str, Any],
        *,
        card: ToolCard | None,
        assistant_kind: str,
        hints: list[str],
        matched_windows: list[dict[str, Any]],
    ) -> bool:
        image_name = str(item.get("image_name") or "").strip().lower()
        window_title = str(item.get("window_title") or "").strip().lower()
        if not image_name and not window_title:
            return False
        aliases = self._unique_strings(
            [str((card.metadata if card is not None else {}).get("command_name") or "")],
            list((card.metadata if card is not None else {}).get("command_aliases") or []),
            [assistant_kind],
            [str((card.title if card is not None else "") or "").replace(" instalado", "")],
        )
        aliases = [alias.lower().replace(".exe", "").strip() for alias in aliases if alias]
        if any(alias and (alias in image_name or alias in window_title) for alias in aliases):
            return True
        if any(self._contains_hint(window_title, hint) for hint in hints):
            return True
        matched_pids = {int(item.get("pid") or 0) for item in matched_windows if int(item.get("pid") or 0)}
        return int(item.get("pid") or 0) in matched_pids

    def _window_matches(self, item: dict[str, Any], *, hints: list[str]) -> bool:
        title = str(item.get("title") or "").strip()
        return bool(title and any(self._contains_hint(title, hint) for hint in hints))

    def _contains_hint(self, value: str, hint: str) -> bool:
        normalized_value = str(value or "").strip().lower()
        normalized_hint = str(hint or "").strip().lower()
        if not normalized_value or not normalized_hint:
            return False
        return normalized_hint in normalized_value

    def _load_user32(self):  # pragma: no cover - platform-specific helper
        if os.name != "nt" or ctypes is None:
            return None
        try:
            return ctypes.windll.user32
        except Exception:
            return None

    def _first_text(self, *values: Any) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def _unique_strings(self, *collections: Any) -> list[str]:
        items: list[str] = []
        for collection in collections:
            if isinstance(collection, (list, tuple, set)):
                for item in collection:
                    normalized = str(item or "").strip()
                    if normalized and normalized not in items:
                        items.append(normalized)
            else:
                normalized = str(collection or "").strip()
                if normalized and normalized not in items:
                    items.append(normalized)
        return items
