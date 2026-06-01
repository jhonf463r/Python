from __future__ import annotations

import csv
import io
import os
import re
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

    def build_web_page_signal(
        self,
        *,
        dom_observation: dict[str, Any] | None = None,
        assistant_kind: str = "",
        requested_target: str = "",
        external_state_flags: list[str] | None = None,
    ) -> VisualSignalSnapshot:
        """Convert a live web page observation into universal visual concepts.

        This is the shared perception contract for pages observed through CDP,
        DOM, accessibility or OCR.  It does not automate the page and it does
        not decide a route; it only names what is actually observable so other
        layers can reason from grounded evidence instead of a screenshot alone.
        """
        observation = dict(dom_observation or {})
        metadata = dict(observation.get("metadata") or {})
        elements = self._normalize_web_elements(
            observation.get("interactive_elements"),
            observation.get("inputs"),
            observation.get("elements"),
            metadata.get("interactive_elements"),
            metadata.get("inputs"),
        )
        body_text = self._first_text(
            observation.get("body_text"),
            observation.get("bodyText"),
            observation.get("bodyTextSample"),
            observation.get("body_text_sample"),
            metadata.get("body_text"),
            metadata.get("bodyTextSample"),
        )
        title = self._first_text(
            observation.get("title"),
            observation.get("latest_title"),
            metadata.get("title"),
            metadata.get("latest_title"),
        )
        url = self._first_text(
            observation.get("url"),
            observation.get("latest_url"),
            metadata.get("url"),
            metadata.get("latest_url"),
        )
        source_flags = canonical_external_state_flags(list(external_state_flags or []))
        concepts, concept_weights = self._derive_web_concepts(
            body_text=body_text,
            title=title,
            url=url,
            elements=elements,
            assistant_kind=assistant_kind,
            requested_target=requested_target,
            metadata=metadata,
            external_state_flags=source_flags,
        )
        visible_targets = self._web_visible_targets(
            title=title,
            url=url,
            concepts=concepts,
            elements=elements,
        )
        unresolved_fields = self._web_unresolved_fields(
            concepts=concepts,
            elements=elements,
            metadata=metadata,
            body_text=body_text,
            assistant_kind=assistant_kind,
            requested_target=requested_target,
        )
        detected_blocks = self._unique_strings(
            source_flags,
            ["login_required"] if "login_screen_candidate" in concepts else [],
            ["security_verification"] if "security_verification_candidate" in concepts else [],
            ["target_missing"] if "target_missing" in concepts else [],
        )
        semantic_sources = self._unique_strings(
            ["dom"] if body_text or elements else [],
            ["cdp"] if observation.get("cdp_url") or metadata.get("cdp_url") or observation.get("source") == "cdp" else [],
            ["accessibility"] if observation.get("accessibility_tree") or metadata.get("accessibility_tree") else [],
            ["ocr"] if observation.get("ocr_text") or metadata.get("ocr_text") else [],
        )
        missing_sources = [
            source
            for source in ("dom", "cdp", "accessibility", "ocr")
            if source not in semantic_sources
        ]
        dom_available = bool(body_text or elements or observation.get("dom_available") or metadata.get("dom_available"))
        capture_available = bool(dom_available or observation.get("screenshot_path") or metadata.get("screenshot_path"))
        confidence = self._web_concept_confidence(
            concepts=concepts,
            concept_weights=concept_weights,
            unresolved_fields=unresolved_fields,
            dom_available=dom_available,
            element_count=len(elements),
        )
        return VisualSignalSnapshot(
            source=str(observation.get("source") or metadata.get("source") or "web_page_observation"),
            source_app=str(assistant_kind or requested_target or metadata.get("site_id") or "web_page"),
            capture_available=capture_available,
            dom_available=dom_available,
            latest_url=url,
            latest_title=title,
            visible_targets=visible_targets,
            login_detected="login_screen_candidate" in concepts,
            learning_ready=bool(concepts and "low_information_capture" not in concepts),
            cross_check_status="grounded" if dom_available and concepts else "unresolved",
            visual_evidence_refs=self._unique_strings(
                observation.get("visual_evidence_refs"),
                metadata.get("visual_evidence_refs"),
                [f"web:{title or url}"] if title or url else [],
            )[:8],
            visual_snapshot={
                "status": "available" if capture_available else "no_disponible",
                "capture_mode": str(observation.get("capture_mode") or metadata.get("capture_mode") or "web_dom_concept"),
                "screen_capture": "available" if observation.get("screenshot_path") or metadata.get("screenshot_path") else "not_required",
                "semantic_concepts": concepts,
                "concept_weights": concept_weights,
                "element_count": len(elements),
                "body_text_length": len(body_text),
                "window_title": title,
            },
            dom_summary={
                "status": "available" if dom_available else "no_disponible",
                "reason": "" if dom_available else "no_semantic_reader_available",
                "dom_available": dom_available,
                "node_count": int(observation.get("dom_node_count") or metadata.get("dom_node_count") or 0),
                "interactive_element_count": len(elements),
                "semantic_sources": semantic_sources,
                "missing_semantic_sources": missing_sources,
            },
            available_actions=self._web_available_actions(concepts=concepts, elements=elements),
            detected_blocks=detected_blocks,
            confidence=confidence,
            unresolved_fields=unresolved_fields,
            metadata={
                "source_context": "web_page_concept_resolver",
                "assistant_kind": assistant_kind,
                "requested_target": requested_target,
                "visual_concepts": concepts,
                "concept_weights": concept_weights,
                "semantic_sources": semantic_sources,
                "missing_semantic_sources": missing_sources,
                "element_sample": elements[:12],
                "body_text_sample": body_text[:500],
            },
        )

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
        web_observation = summary.get("web_dom_observation") or metadata.get("web_dom_observation")
        if isinstance(web_observation, dict):
            return self.build_web_page_signal(
                dom_observation=web_observation,
                assistant_kind=str(metadata.get("assistant_kind") or summary.get("assistant_kind") or ""),
                requested_target=str(metadata.get("requested_target") or summary.get("requested_target") or site_id or ""),
                external_state_flags=external_state_flags,
            )
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

    def _normalize_web_elements(self, *collections: Any) -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []
        for collection in collections:
            if not isinstance(collection, (list, tuple)):
                continue
            for raw in collection:
                if not isinstance(raw, dict):
                    continue
                label = self._first_text(
                    raw.get("text"),
                    raw.get("aria"),
                    raw.get("aria_label"),
                    raw.get("placeholder"),
                    raw.get("label"),
                    raw.get("name"),
                )
                tag = str(raw.get("tag") or raw.get("tagName") or "").strip().lower()
                role = str(raw.get("role") or "").strip().lower()
                element = {
                    "tag": tag,
                    "role": role,
                    "text": label[:200],
                    "aria": str(raw.get("aria") or raw.get("aria_label") or "").strip()[:200],
                    "placeholder": str(raw.get("placeholder") or "").strip()[:200],
                    "type": str(raw.get("type") or "").strip().lower(),
                    "disabled": bool(raw.get("disabled")),
                    "visible": bool(raw.get("visible", True)),
                    "rect": dict(raw.get("rect") or {}),
                }
                if element not in elements:
                    elements.append(element)
        return elements

    def _derive_web_concepts(
        self,
        *,
        body_text: str,
        title: str,
        url: str,
        elements: list[dict[str, Any]],
        assistant_kind: str,
        requested_target: str,
        metadata: dict[str, Any],
        external_state_flags: list[str],
    ) -> tuple[list[str], dict[str, float]]:
        combined = self._normalize_text(
            " ".join(
                [
                    body_text,
                    title,
                    url,
                    " ".join(str(item.get("text") or "") for item in elements),
                    " ".join(str(item.get("aria") or "") for item in elements),
                    " ".join(str(item.get("placeholder") or "") for item in elements),
                    " ".join(external_state_flags),
                ]
            )
        )
        concepts: list[str] = []
        weights: dict[str, float] = {}

        def add(name: str, weight: float) -> None:
            if name not in concepts:
                concepts.append(name)
            weights[name] = max(float(weights.get(name, 0.0)), round(weight, 3))

        target = self._normalize_text(requested_target or assistant_kind)
        page_identity = self._normalize_text(f"{title} {url} {metadata.get('site_id', '')}")
        if target and not any(token in page_identity for token in self._target_aliases(target)):
            add("target_missing", 0.9)
        elif page_identity:
            add("target_bound", 0.82)

        if self._contains_any(combined, ("captcha", "cloudflare", "security verification", "verificacion de seguridad", "verificación de seguridad", "verify you are not a bot", "checking your browser", "just a moment")):
            add("security_verification_candidate", 0.95)
        if self._contains_any(combined, ("iniciar sesion", "inicia sesion", "log in", "login", "sign in", "registrarse", "continue with google", "continuar con google", "obtén respuestas adaptadas")):
            add("login_screen_candidate", 0.9)
            add("unauthenticated_session", 0.86)

        textboxes = [
            item for item in elements
            if item.get("visible")
            and not item.get("disabled")
            and (
                item.get("tag") in {"textarea", "input"}
                or item.get("role") == "textbox"
                or self._contains_any(
                    self._normalize_text(f"{item.get('text', '')} {item.get('aria', '')} {item.get('placeholder', '')}"),
                    ("pregunta", "message", "mensaje", "chatear", "chat"),
                )
            )
        ]
        if textboxes:
            add("chat_input_ready", 0.86)

        send_controls = [
            item for item in elements
            if item.get("visible")
            and not item.get("disabled")
            and self._contains_any(
                self._normalize_text(f"{item.get('text', '')} {item.get('aria', '')} {item.get('placeholder', '')}"),
                ("enviar", "send", "submit"),
            )
        ]
        if send_controls:
            add("send_control_ready", 0.82)
        elif textboxes:
            add("submit_control_missing", 0.72)

        assistant_messages = metadata.get("assistant_messages") or metadata.get("response_text") or metadata.get("captured_text")
        if isinstance(assistant_messages, (list, tuple)):
            has_response = any(str(item or "").strip() for item in assistant_messages)
        else:
            has_response = bool(str(assistant_messages or "").strip())
        if has_response or bool(metadata.get("response_captured")):
            add("response_captured", 0.92)
        elif metadata.get("prompt_sent") or metadata.get("prompt_pasted"):
            add("response_capture_pending", 0.74)

        if not body_text.strip() and not elements:
            add("low_information_capture", 0.9)
        if metadata.get("self_capture"):
            add("self_capture", 0.95)
        if metadata.get("wrong_profile"):
            add("wrong_profile", 0.88)
        return concepts, weights

    def _web_visible_targets(self, *, title: str, url: str, concepts: list[str], elements: list[dict[str, Any]]) -> list[str]:
        targets = self._unique_strings(
            [title] if title else [],
            [url] if url else [],
            concepts,
            [str(item.get("text") or "") for item in elements[:8]],
        )
        return targets[:10]

    def _web_unresolved_fields(
        self,
        *,
        concepts: list[str],
        elements: list[dict[str, Any]],
        metadata: dict[str, Any],
        body_text: str,
        assistant_kind: str,
        requested_target: str,
    ) -> list[str]:
        unresolved: list[str] = []
        if "target_missing" in concepts:
            unresolved.append("UNRESOLVED:visual_target_missing")
        if "low_information_capture" in concepts:
            unresolved.append("UNRESOLVED:low_information_capture")
        if "chat_input_ready" in concepts and "send_control_ready" not in concepts:
            unresolved.append("UNRESOLVED:submit_control_not_observed")
        if "login_screen_candidate" in concepts:
            unresolved.append("UNRESOLVED:login_or_session_required")
        if "security_verification_candidate" in concepts:
            unresolved.append("UNRESOLVED:security_verification_required")
        if not metadata.get("ocr_text"):
            unresolved.append("OCR_UNAVAILABLE")
        if not body_text.strip() and not elements:
            unresolved.append("UNRESOLVED:semantic_page_read_missing")
        if (assistant_kind or requested_target) and not (metadata.get("response_captured") or metadata.get("captured_text")):
            unresolved.append("UNRESOLVED:response_not_captured")
        return self._unique_strings(unresolved)

    def _web_available_actions(self, *, concepts: list[str], elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if "login_screen_candidate" in concepts:
            actions.append({"action": "request_human_login", "label": "Completar inicio de sesion/verificacion", "available": True})
        if "security_verification_candidate" in concepts:
            actions.append({"action": "request_human_security_verification", "label": "Completar verificacion humana", "available": True})
        if "chat_input_ready" in concepts:
            actions.append({"action": "type_prompt", "label": "Escribir prompt en el campo de chat", "available": True})
        if "send_control_ready" in concepts:
            actions.append({"action": "submit_prompt", "label": "Enviar prompt", "available": True})
        elif "chat_input_ready" in concepts:
            actions.append({"action": "discover_submit_control", "label": "Detectar boton/tecla de envio", "available": False})
        if "response_captured" in concepts:
            actions.append({"action": "ingest_response", "label": "Ingerir respuesta capturada", "available": True})
        if not actions:
            actions.append({"action": "request_human_visual_help", "label": "Pedir ayuda visual concreta", "available": True})
        return actions[:8]

    def _web_concept_confidence(
        self,
        *,
        concepts: list[str],
        concept_weights: dict[str, float],
        unresolved_fields: list[str],
        dom_available: bool,
        element_count: int,
    ) -> float:
        score = 0.18
        if dom_available:
            score += 0.25
        if element_count:
            score += 0.18
        if concepts:
            score += min(0.24, 0.04 * len(concepts))
        if concept_weights:
            score += min(0.1, sum(concept_weights.values()) / max(len(concept_weights), 1) * 0.1)
        score -= min(0.22, 0.035 * len(unresolved_fields))
        return round(max(0.0, min(0.96, score)), 3)

    def _target_aliases(self, target: str) -> list[str]:
        aliases = [target]
        if "chatgpt" in target or "chat gpt" in target or "gpt" in target:
            aliases.extend(["chatgpt", "chat gpt", "openai"])
        if "claude" in target:
            aliases.extend(["claude", "anthropic"])
        if "codex" in target:
            aliases.append("codex")
        return self._unique_strings(aliases)

    def _contains_any(self, value: str, needles: tuple[str, ...]) -> bool:
        return any(needle in value for needle in needles)

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
            "ñ": "n",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return re.sub(r"\s+", " ", text)

    def _desktop_snapshot(self, *, max_age_seconds: float = 2.0) -> dict[str, list[dict[str, Any]]]:
        with self._desktop_probe_lock:
            cached_at = float(self._desktop_probe_cache.get("captured_at") or 0.0)
            cached_windows = self._desktop_probe_cache.get("windows", [])
            cached_processes = self._desktop_probe_cache.get("process_rows", [])
            if (cached_windows or cached_processes) and cached_at and (time.monotonic() - cached_at) <= max(float(max_age_seconds), 0.0):
                return {
                    "process_rows": [dict(item) for item in cached_processes],
                    "windows": [dict(item) for item in cached_windows],
                }
        process_rows = [dict(item) for item in self._list_process_rows()]
        windows = [dict(item) for item in self._list_windows()]
        snapshot = {
            "captured_at": time.monotonic() if (process_rows or windows) else 0.0,
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
