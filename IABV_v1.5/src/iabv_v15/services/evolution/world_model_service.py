from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
from typing import Any

from iabv_v15.domain.models import (
    BackgroundProcessSnapshot,
    EnvironmentSelfModel,
    ExternalStateFlag,
    IssueSeverity,
    NetworkStatusSnapshot,
    ObservationPermissionGate,
    OperationalBlockRecord,
    ToolCard,
    ToolLiveStatus,
    WindowObservation,
    WorldModelSnapshot,
    canonical_external_state_flags,
    utc_now,
)


class WorldModelService:
    """Keeps a lightweight operational picture of windows, tools, network and blockers."""

    _DEFAULT_SCAN_INTERVAL = 18.0
    _DEFAULT_FULL_SCAN_INTERVAL = 120.0
    _NETWORK_TIMEOUT_SECONDS = 1.4
    _HIGH_MEMORY_MB = 900.0

    def __init__(
        self,
        *,
        workspace_root: str,
        evolution_dir: str,
        tool_registry: Any | None = None,
        tool_record_repository: Any | None = None,
        environment_self_awareness_service: Any | None = None,
        universal_perception_service: Any | None = None,
        role_router: Any | None = None,
        auto_start: bool | None = None,
        bootstrap_scan: bool = True,
        scan_interval_seconds: float = _DEFAULT_SCAN_INTERVAL,
        full_scan_interval_seconds: float = _DEFAULT_FULL_SCAN_INTERVAL,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.state_dir = Path(evolution_dir).resolve() / 'world_model'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.tool_registry = tool_registry
        self.tool_record_repository = tool_record_repository
        self.environment_self_awareness_service = environment_self_awareness_service
        self.universal_perception_service = universal_perception_service
        self.role_router = role_router
        self.scan_interval_seconds = max(float(scan_interval_seconds), 8.0)
        self.full_scan_interval_seconds = max(float(full_scan_interval_seconds), self.scan_interval_seconds)
        self._auto_start = (not self._in_test_mode()) if auto_start is None else bool(auto_start)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._refresh_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending_refresh_reason = 'scheduled_light'
        self._pending_full_refresh = False
        self._last_scan_monotonic = 0.0
        self._last_full_scan_monotonic = 0.0
        self._current_snapshot = self._load_latest_snapshot() or WorldModelSnapshot()
        self._observation_permissions: dict[str, dict[str, Any]] = {}
        self._user32 = self._load_user32()
        if bootstrap_scan:
            self.scan_now(reason='startup', full=not self._in_test_mode())
        if self._auto_start:
            self.start()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name='iabv-world-model', daemon=True)
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 1.0) -> None:
        self._stop_event.set()
        self._refresh_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(timeout_seconds, 0.1))

    def current_model(self) -> WorldModelSnapshot:
        with self._lock:
            return self._decorate_snapshot(self._current_snapshot)

    def request_refresh(self, *, reason: str = 'manual', full: bool = False) -> WorldModelSnapshot:
        with self._lock:
            if full:
                self._pending_full_refresh = True
            self._pending_refresh_reason = str(reason or 'manual')
            too_soon = (time.monotonic() - self._last_scan_monotonic) < 5.0
            if too_soon and not full and self._thread is not None and self._thread.is_alive():
                return self._decorate_snapshot(self._current_snapshot)
        if self._thread is not None and self._thread.is_alive():
            self._refresh_event.set()
            return self.current_model()
        return self.scan_now(reason=reason, full=full)

    def scan_now(self, *, reason: str = 'manual', full: bool = False) -> WorldModelSnapshot:
        previous = self.current_model()
        snapshot = self._build_snapshot(previous=previous, reason=reason, full=full)
        with self._lock:
            self._current_snapshot = snapshot
            now_monotonic = time.monotonic()
            self._last_scan_monotonic = now_monotonic
            if full:
                self._last_full_scan_monotonic = now_monotonic
        self._persist_snapshot(snapshot)
        return self._decorate_snapshot(snapshot)

    def grant_observation_permission(
        self,
        *,
        scope: str,
        assistant_kind: str = '',
        title: str = '',
        detail: str = '',
        granted_by: str = 'user',
    ) -> WorldModelSnapshot:
        normalized = self._normalize_permission_scope(scope, assistant_kind=assistant_kind)
        with self._lock:
            self._observation_permissions[normalized] = {
                'scope': normalized,
                'assistant_kind': str(assistant_kind or '').strip().lower(),
                'title': str(title or normalized.replace(':', ' ')).strip(),
                'detail': str(detail or '').strip(),
                'granted': True,
                'granted_by': str(granted_by or 'user').strip(),
                'updated_at': utc_now().isoformat(),
            }
        return self.request_refresh(reason=f'permission_granted:{normalized}', full=True)

    def revoke_observation_permission(self, *, scope: str, assistant_kind: str = '') -> WorldModelSnapshot:
        normalized = self._normalize_permission_scope(scope, assistant_kind=assistant_kind)
        with self._lock:
            self._observation_permissions.pop(normalized, None)
        return self.request_refresh(reason=f'permission_revoked:{normalized}', full=False)

    def permission_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._observation_permissions.values()]

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            triggered = self._refresh_event.wait(self.scan_interval_seconds)
            if self._stop_event.is_set():
                break
            if triggered:
                self._refresh_event.clear()
            with self._lock:
                full = self._pending_full_refresh or (
                    (time.monotonic() - self._last_full_scan_monotonic) >= self.full_scan_interval_seconds
                )
                reason = self._pending_refresh_reason if triggered else ('scheduled_full' if full else 'scheduled_light')
                self._pending_full_refresh = False
                self._pending_refresh_reason = 'scheduled_light'
            try:
                self.scan_now(reason=reason, full=full)
            except Exception:
                with self._lock:
                    existing = self._current_snapshot.model_copy(deep=True)
                    existing.metadata = {
                        **dict(existing.metadata or {}),
                        'background_refresh_failed': True,
                    }
                    existing.detected_blocks = list(dict.fromkeys(list(existing.detected_blocks) + ['world_model_refresh_failed']))
                    self._current_snapshot = existing

    def _build_snapshot(self, *, previous: WorldModelSnapshot, reason: str, full: bool) -> WorldModelSnapshot:
        started = time.perf_counter()
        environment = self._environment_self_model()
        raw_windows = self._list_windows()
        focused = self._focused_window()
        network_status, network_unresolved = self._network_status(full=full)
        tool_live_status, tool_unresolved = self._tool_live_status(
            raw_windows=raw_windows,
            focused=focused,
            network_status=network_status,
            environment=environment,
            full=full,
        )
        active_windows = self._annotated_windows(raw_windows=raw_windows, focused=focused, tool_live_status=tool_live_status)
        background_processes = self._background_processes(full=full)
        permission_gates = self._permission_gates(tool_live_status=tool_live_status)
        detected_blocks = self._detected_blocks(
            environment=environment,
            network_status=network_status,
            tool_live_status=tool_live_status,
            background_processes=background_processes,
            permission_gates=permission_gates,
        )
        block_records = self._block_records(
            environment=environment,
            network_status=network_status,
            tool_live_status=tool_live_status,
            background_processes=background_processes,
            focused=focused,
            permission_gates=permission_gates,
        )
        inferred_state = self._inferred_state(
            environment=environment,
            network_status=network_status,
            tool_live_status=tool_live_status,
            focused=focused,
            active_windows=active_windows,
            detected_blocks=detected_blocks,
            block_records=block_records,
            permission_gates=permission_gates,
        )
        unresolved_fields = list(dict.fromkeys([*network_unresolved, *tool_unresolved]))
        if focused is None:
            unresolved_fields.append('UNRESOLVED:focused_window')
        if background_processes and not self._gpu_process_probe_available():
            unresolved_fields.append('UNRESOLVED:gpu_process_usage')
        observation_sources = self._observation_sources(
            network_status=network_status,
            tool_live_status=tool_live_status,
            background_processes=background_processes,
            permission_gates=permission_gates,
        )
        confidence = self._confidence(
            active_windows=active_windows,
            tool_live_status=tool_live_status,
            network_status=network_status,
            unresolved_fields=unresolved_fields,
        )
        metadata = {
            'scan_reason': str(reason or 'manual'),
            'scan_mode': 'full' if full else 'light',
            'workspace_root': str(self.workspace_root),
            'observation_sources': list(observation_sources),
            'permission_gates': [item.model_dump(mode='json') for item in permission_gates],
            'changed_since_last_scan': self._changes_from_previous(
                previous=previous,
                current_blocks=detected_blocks,
                tool_live_status=tool_live_status,
                focused=focused,
            ),
        }
        return WorldModelSnapshot(
            active_windows=active_windows,
            focused_window=focused,
            tool_live_status=tool_live_status,
            network_status=network_status,
            background_processes=background_processes,
            detected_blocks=detected_blocks,
            block_records=block_records,
            permission_gates=permission_gates,
            observation_sources=observation_sources,
            inferred_state=inferred_state,
            confidence=confidence,
            freshness_ms=max(0, int((time.perf_counter() - started) * 1000.0)),
            last_updated=utc_now(),
            unresolved_fields=unresolved_fields,
            metadata=metadata,
        )

    def _tool_live_status(
        self,
        *,
        raw_windows: list[dict[str, Any]],
        focused: WindowObservation | None,
        network_status: NetworkStatusSnapshot,
        environment: EnvironmentSelfModel,
        full: bool,
    ) -> tuple[list[ToolLiveStatus], list[str]]:
        unresolved: list[str] = []
        statuses: list[ToolLiveStatus] = []
        cards = self._cards_to_probe()
        provider_health = {
            str(item.get('provider_name') or '').strip().lower(): dict(item)
            for item in (environment.metadata or {}).get('provider_health', [])
            if isinstance(item, dict)
        }
        focused_pid = int(focused.pid or 0) if focused is not None else 0
        for card in cards:
            assistant_kind = str(card.metadata.get('assistant_kind') or '').strip().lower()
            signal = self._tool_signal(card)
            history = self._recent_tool_history(card.tool_id)
            observed_via = self._tool_observation_sources(card=card, signal=signal, history=history)
            external_flags = list(history.get('external_state_flags') or [])
            detected_blocks = list(external_flags)
            status = 'no_disponible'
            detail = ''
            thread_status = 'no_aplica'
            messages_status = 'no_disponible'
            session_status = 'no_aplica'
            capture_status = 'no_disponible'
            probe_status = 'pasivo'
            permission_state = 'no_requerido'
            last_verified_at = None
            observed_pid = int((signal.metadata or {}).get('observed_pid') or 0)
            window_open = bool((signal.visual_snapshot or {}).get('window_visible') or (signal.visual_snapshot or {}).get('process_running'))
            is_focused = bool(observed_pid and focused_pid and observed_pid == focused_pid)
            browser_security = bool(history.get('browser_security_verification'))
            if browser_security and 'browser_security_verification' not in detected_blocks:
                detected_blocks.append('browser_security_verification')
            if assistant_kind == 'ollama':
                health = provider_health.get('ollama') or provider_health.get('ollama vision') or {}
                health_status = str(health.get('status') or '').strip().lower()
                if bool(health.get('available')) or bool(dict(environment.ai_capacity or {}).get('local_runtime', {}).get('available')):
                    status = 'disponible' if health_status != 'degraded' else 'lento'
                    detail = str(health.get('detail') or 'Proveedor local listo.')
                    session_status = 'activa'
                    messages_status = 'disponibles'
                    capture_status = 'tool_result'
                    probe_status = 'verificado_pasivo'
                    last_verified_at = utc_now()
                else:
                    status = 'no_disponible'
                    detail = str(health.get('detail') or 'No tengo confirmacion de respuesta local ahora mismo.')
                    detected_blocks.append('assistant_unavailable')
                    probe_status = 'sin_confirmacion'
            else:
                status, detail, session_status, messages_status = self._external_tool_status(
                    card=card,
                    assistant_kind=assistant_kind,
                    external_flags=external_flags,
                    browser_security=browser_security,
                    window_open=window_open,
                    network_status=network_status,
                )
                if ExternalStateFlag.CAPTURE_UNVERIFIED.value in external_flags:
                    capture_status = 'capture_unverified'
                elif bool(history.get('awaiting_response')):
                    capture_status = 'awaiting_response'
                elif bool(history.get('latest_success')):
                    capture_status = 'respuesta_verificada'
                elif browser_security:
                    capture_status = 'capture_unverified'
                if assistant_kind == 'codex':
                    thread_status, thread_detail, thread_unresolved = self._codex_thread_status(card)
                    detail = thread_detail or detail
                    if thread_unresolved:
                        unresolved.extend(thread_unresolved)
                    if thread_status == 'correcto_probable':
                        detected_blocks = [item for item in detected_blocks if item != 'wrong_thread']
                        if status == 'hilo_incorrecto':
                            status = 'abierto' if window_open else 'listo'
                    if thread_status == 'otro_hilo_activo' and 'wrong_thread' not in detected_blocks:
                        detected_blocks.append('wrong_thread')
                elif messages_status == 'no_disponible':
                    messages_status = 'desconocidos'
                (
                    probe_status,
                    permission_state,
                    probe_detail,
                    probe_unresolved,
                    probe_verified,
                ) = self._probe_state_for_tool(
                    card=card,
                    assistant_kind=assistant_kind,
                    window_open=window_open,
                    status=status,
                    session_status=session_status,
                    messages_status=messages_status,
                    history=history,
                    full=full,
                )
                if probe_detail:
                    detail = probe_detail if not detail else detail
                if probe_unresolved:
                    unresolved.extend(probe_unresolved)
                if permission_state == 'requerido' and 'permission_required' not in detected_blocks:
                    detected_blocks.append('permission_required')
                if probe_verified:
                    last_verified_at = utc_now()
            if not detail:
                detail = str(history.get('detail') or '').strip()
            normalized_blocks = canonical_external_state_flags(detected_blocks)
            for block in detected_blocks:
                if block in {'browser_security_verification', 'assistant_unavailable', 'network_blocked'} and block not in normalized_blocks:
                    normalized_blocks.append(block)
            statuses.append(
                ToolLiveStatus(
                    tool_id=card.tool_id,
                    title=card.title,
                    assistant_kind=assistant_kind,
                    available=bool(card.available),
                    status=status,
                    detail=detail,
                    launch_mode=str(card.metadata.get('launch_mode') or ''),
                    window_open=window_open,
                    focused=is_focused,
                    thread_status=thread_status,
                    messages_status=messages_status,
                    session_status=session_status,
                    capture_status=capture_status,
                    probe_status=probe_status,
                    permission_state=permission_state,
                    observed_via=observed_via,
                    last_verified_at=last_verified_at,
                    external_state_flags=canonical_external_state_flags(detected_blocks),
                    detected_blocks=normalized_blocks,
                    confidence=self._tool_confidence(card=card, signal=signal, history=history),
                    metadata={
                        'observed_pid': observed_pid,
                        'observed_title': str(signal.latest_title or ''),
                        'window_count': int((signal.metadata or {}).get('window_count') or 0),
                        'process_count': int((signal.metadata or {}).get('process_count') or 0),
                        'response_capture_mode': str(card.metadata.get('response_capture_mode') or ''),
                        'browser_security_verification': browser_security,
                        'latest_error_message': str(history.get('error_message') or ''),
                        'history_state': str(history.get('state') or ''),
                        'permission_scope': self._content_permission_scope(assistant_kind),
                    },
                )
            )
        return statuses, list(dict.fromkeys(unresolved))

    def _tool_observation_sources(self, *, card: ToolCard, signal: Any, history: dict[str, Any]) -> list[str]:
        sources = ['tool_registry', 'universal_perception_signal']
        if bool((signal.visual_snapshot or {}).get('window_visible')):
            sources.append('windows_api')
        if bool((signal.visual_snapshot or {}).get('process_running')):
            sources.append('process_scan')
        if history.get('external_state_flags') or history.get('error_message'):
            sources.append('tool_history')
        if str(card.metadata.get('assistant_kind') or '').strip().lower() == 'codex':
            sources.append('codex_state_sqlite')
        return list(dict.fromkeys(item for item in sources if str(item).strip()))

    def _probe_state_for_tool(
        self,
        *,
        card: ToolCard,
        assistant_kind: str,
        window_open: bool,
        status: str,
        session_status: str,
        messages_status: str,
        history: dict[str, Any],
        full: bool,
    ) -> tuple[str, str, str, list[str], bool]:
        if assistant_kind == 'ollama':
            return 'verificado_pasivo', 'no_requerido', '', [], True
        scope = self._content_permission_scope(assistant_kind)
        needs_content_probe = self._needs_content_probe(
            assistant_kind=assistant_kind,
            window_open=window_open,
            status=status,
            session_status=session_status,
            messages_status=messages_status,
            history=history,
        )
        if not needs_content_probe:
            return ('verificado_pasivo' if history.get('latest_success') or history.get('error_message') else 'pasivo'), 'no_requerido', '', [], bool(history.get('latest_success') or history.get('error_message'))
        if not self._has_observation_permission(scope, assistant_kind=assistant_kind):
            return (
                'permiso_requerido',
                'requerido',
                self._permission_prompt(assistant_kind=assistant_kind),
                [f'UNRESOLVED:{assistant_kind}_content_probe'],
                False,
            )
        if not full:
            return 'permiso_concedido_esperando_probe', 'concedido', '', [], False
        probe_note = self._tool_live_probe_detail(assistant_kind=assistant_kind, history=history)
        unresolved: list[str] = []
        if assistant_kind in {'chatgpt', 'claude'} and not probe_note:
            unresolved.append(f'UNRESOLVED:{assistant_kind}_content_probe')
        return (
            'verificado_parcial' if probe_note else 'concedido_sin_probe',
            'concedido',
            probe_note,
            unresolved,
            bool(probe_note),
        )

    def _needs_content_probe(
        self,
        *,
        assistant_kind: str,
        window_open: bool,
        status: str,
        session_status: str,
        messages_status: str,
        history: dict[str, Any],
    ) -> bool:
        if assistant_kind not in {'codex', 'chatgpt', 'claude'}:
            return False
        if not window_open:
            return False
        if str(status or '').strip() in {'limitado', 'bloqueado', 'sesion_expirada', 'hilo_incorrecto', 'no_disponible'}:
            return False
        if history.get('browser_security_verification') or ExternalStateFlag.ACCOUNT_LIMITED.value in list(history.get('external_state_flags') or []):
            return False
        return str(messages_status or '').strip() in {'no_disponible', 'desconocidos'} or str(session_status or '').strip() in {'desconocida', 'abierta'}

    def _content_permission_scope(self, assistant_kind: str) -> str:
        normalized = str(assistant_kind or '').strip().lower()
        return f'observe_window_content:{normalized}' if normalized else 'observe_window_content:external'

    def _normalize_permission_scope(self, scope: str, *, assistant_kind: str = '') -> str:
        normalized = str(scope or '').strip().lower()
        if normalized:
            return normalized
        return self._content_permission_scope(assistant_kind)

    def _has_observation_permission(self, scope: str, *, assistant_kind: str = '') -> bool:
        normalized = self._normalize_permission_scope(scope, assistant_kind=assistant_kind)
        with self._lock:
            payload = dict(self._observation_permissions.get(normalized) or {})
        return bool(payload.get('granted'))

    def _permission_prompt(self, *, assistant_kind: str) -> str:
        title = 'esa ventana'
        normalized = str(assistant_kind or '').strip().lower()
        if normalized:
            title = normalized.capitalize()
        return f'Para verificar si {title} esta listo de verdad necesito observar el contenido visible de esa ventana.'

    def _tool_live_probe_detail(self, *, assistant_kind: str, history: dict[str, Any]) -> str:
        detail = str(history.get('detail') or '').strip()
        if assistant_kind == 'codex' and detail:
            return detail
        if assistant_kind in {'chatgpt', 'claude'} and detail and any(token in detail.lower() for token in ('session', 'sesion', 'quota', 'limit', 'security', 'login', 'credit', 'mensaje')):
            return detail
        return ''

    def _external_tool_status(
        self,
        *,
        card: ToolCard,
        assistant_kind: str,
        external_flags: list[str],
        browser_security: bool,
        window_open: bool,
        network_status: NetworkStatusSnapshot,
    ) -> tuple[str, str, str, str]:
        status = 'no_disponible'
        detail = ''
        session_status = 'no_disponible'
        messages_status = 'no_disponible'
        if ExternalStateFlag.ACCOUNT_LIMITED.value in external_flags:
            return 'limitado', 'La cuenta o cuota de esta via externa quedo limitada.', 'limitada', 'agotados_o_limitados'
        if ExternalStateFlag.SESSION_EXPIRED.value in external_flags or ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value in external_flags:
            return 'sesion_expirada', 'La sesion de esta herramienta necesita recuperarse antes de usarla.', 'expirada', 'desconocidos'
        if browser_security:
            return 'bloqueado', 'El sitio quedo bloqueado por verificacion de seguridad.', 'verificacion_seguridad', 'desconocidos'
        if ExternalStateFlag.WRONG_THREAD.value in external_flags:
            return 'hilo_incorrecto', 'La evidencia reciente apunta a un hilo distinto del esperado.', 'abierta' if window_open else 'desconocida', 'desconocidos'
        if assistant_kind in {'chatgpt', 'claude'} and network_status.status in {'desconectado', 'bloqueado'}:
            return 'bloqueado', 'La red no esta en condiciones de sostener esta via externa.', 'bloqueada_red', 'desconocidos'
        if card.available and window_open:
            status = 'abierto'
            detail = 'La herramienta esta abierta y observable.'
            session_status = 'abierta'
        elif card.available:
            status = 'listo'
            detail = 'La herramienta esta registrada y se puede intentar abrir.'
            session_status = 'desconocida'
        else:
            status = 'no_disponible'
            detail = 'La herramienta no quedo confirmada como disponible en esta laptop.'
            session_status = 'no_disponible'
        return status, detail, session_status, messages_status

    def _cards_to_probe(self) -> list[ToolCard]:
        registry = self.tool_registry
        if registry is None:
            return []
        try:
            cards = [registry.refresh_card(card) for card in registry.list_cards()]
        except Exception:
            return []
        selected: list[ToolCard] = []
        non_assistant_allowlist = {
            'playwright_browser',
            'desktop_human_runner',
            'shell_command',
            'site_explorer_v1',
            'cloudflared_cli',
            'gh_cli',
            'git_cli',
            'github_api',
            'mcp_client',
            'winget_cli',
            'aider_coder',
        }
        for card in cards:
            assistant_kind = str(card.metadata.get('assistant_kind') or '').strip()
            if assistant_kind or card.tool_id in non_assistant_allowlist:
                selected.append(card)
        return selected

    def _tool_signal(self, card: ToolCard):
        service = self.universal_perception_service
        if service is None:
            return self._fallback_signal(card)
        try:
            return service.scan_tool_context(
                tool_id=card.tool_id,
                assistant_kind=str(card.metadata.get('assistant_kind') or ''),
            )
        except Exception:
            return self._fallback_signal(card)

    def _fallback_signal(self, card: ToolCard):
        from iabv_v15.domain.models import VisualSignalSnapshot

        return VisualSignalSnapshot(
            source='world_model_fallback',
            source_app=str(card.metadata.get('assistant_kind') or card.tool_id),
            capture_available=bool(card.available),
            latest_title=card.title,
            confidence=0.18,
            unresolved_fields=['UNRESOLVED:visual_snapshot'],
            metadata={'tool_id': card.tool_id},
        )

    def _recent_tool_history(self, tool_id: str) -> dict[str, Any]:
        repository = self.tool_record_repository
        if repository is None:
            return {}
        results = repository.list_results(tool_id=tool_id, limit=4)
        logs = repository.list_log(tool_id=tool_id, limit=6)
        external_flags: list[str] = []
        error_messages: list[str] = []
        state = ''
        detail = ''
        latest_success = False
        awaiting_response = False
        for result in results:
            latest_success = latest_success or bool(result.success)
            state = state or str(result.execution_state.state or '')
            detail = detail or str(result.execution_state.detail or result.output_text or '')
            if result.error_message:
                error_messages.append(str(result.error_message))
            external_flags.extend(
                canonical_external_state_flags(
                    list(result.metadata.get('external_state_flags') or [])
                    + list((result.execution_state.metadata or {}).get('external_state_flags') or [])
                    + [result.error_message]
                )
            )
            awaiting_response = awaiting_response or (
                str(result.execution_state.state or '').strip().lower() == 'awaiting_response'
                or ExternalStateFlag.AWAITING_RESPONSE.value in external_flags
            )
        for entry in logs:
            payload = dict(entry.get('payload') or {})
            state = state or str(entry.get('state') or '')
            detail = detail or str(payload.get('detail') or payload.get('summary') or '')
            external_flags.extend(
                canonical_external_state_flags(
                    list(payload.get('external_state_flags') or [])
                    + list(dict(payload.get('ia_trace_entry') or {}).get('external_state_flags') or [])
                    + [payload.get('error_message') or '', payload.get('detail') or '']
                )
            )
            error_text = str(payload.get('error_message') or payload.get('detail') or '').strip()
            if error_text:
                error_messages.append(error_text)
        joined_errors = ' '.join(error_messages).lower()
        return {
            'external_state_flags': canonical_external_state_flags(external_flags),
            'error_message': error_messages[0] if error_messages else '',
            'browser_security_verification': 'browser_security_verification' in joined_errors or 'just a moment' in joined_errors,
            'state': state,
            'detail': detail,
            'latest_success': latest_success,
            'awaiting_response': awaiting_response,
        }

    def _codex_thread_status(self, card: ToolCard) -> tuple[str, str, list[str]]:
        metadata = dict(card.metadata or {})
        explicit_state_path = str(metadata.get('session_state_path') or '').strip()
        state_path = Path(self._expand_external_path(explicit_state_path or r'{userprofile}\.codex\state_5.sqlite'))
        if self._in_test_mode():
            workspace_root = self.workspace_root.resolve()
            state_path_resolved = state_path.resolve(strict=False)
            if workspace_root not in (state_path_resolved, *state_path_resolved.parents):
                return 'no_disponible', 'No pude verificar el hilo activo de Codex dentro del entorno de pruebas.', ['UNRESOLVED:codex_thread_tracking']
        if not state_path.exists():
            return 'no_disponible', 'No pude verificar el hilo activo de Codex porque no encontre su estado local.', ['UNRESOLVED:codex_thread_tracking']
        try:
            conn = sqlite3.connect(str(state_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT rollout_path, updated_at, cwd, title FROM threads WHERE archived = 0 ORDER BY updated_at DESC LIMIT 12"
                ).fetchall()
            finally:
                conn.close()
        except Exception:
            return 'no_disponible', 'No pude leer el estado local de Codex para verificar el hilo activo.', ['UNRESOLVED:codex_thread_tracking']
        if not rows:
            return 'no_disponible', 'Codex no expuso hilos recientes para esta verificacion.', ['UNRESOLVED:codex_thread_tracking']
        workspace = str(self.workspace_root).lower()
        normalized_rows = [
            {
                'cwd': str(row['cwd'] or '').strip().lower(),
                'title': str(row['title'] or '').strip(),
            }
            for row in rows
        ]
        latest = normalized_rows[0]
        workspace_matches = [item for item in normalized_rows if item['cwd'] and workspace and workspace in item['cwd']]
        if latest['cwd'] and workspace and workspace in latest['cwd']:
            title = latest['title'] or 'el hilo mas reciente'
            return 'correcto_probable', f'Codex parece estar enfocado en el hilo correcto del workspace actual ({title}).', []
        if workspace_matches:
            title = latest['title'] or latest['cwd'] or 'otro hilo'
            return 'otro_hilo_activo', f'Codex esta abierto, pero el hilo activo mas reciente parece distinto al del workspace actual ({title}).', []
        return 'sin_hilo_iabv', 'No encontre un hilo reciente de Codex asociado a este workspace.', []

    def _annotated_windows(
        self,
        *,
        raw_windows: list[dict[str, Any]],
        focused: WindowObservation | None,
        tool_live_status: list[ToolLiveStatus],
    ) -> list[WindowObservation]:
        tool_by_pid = {
            int(item.metadata.get('observed_pid') or 0): item
            for item in tool_live_status
            if int(item.metadata.get('observed_pid') or 0)
        }
        items: list[WindowObservation] = []
        for raw in raw_windows[:24]:
            pid = int(raw.get('pid') or 0)
            title = str(raw.get('title') or '').strip()
            live = tool_by_pid.get(pid)
            items.append(
                WindowObservation(
                    title=title,
                    app_name=str((live.title if live is not None else title.split(' - ')[0] if title else '') or ''),
                    pid=pid,
                    focused=bool(focused is not None and pid and pid == focused.pid and title == focused.title),
                    visible=True,
                    tool_id=live.tool_id if live is not None else '',
                    assistant_kind=live.assistant_kind if live is not None else '',
                    state=live.status if live is not None else 'visible',
                    detail=live.detail if live is not None else '',
                )
            )
        return items

    def _focused_window(self) -> WindowObservation | None:
        if os.name != 'nt' or self._user32 is None:
            return None
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None
        length = self._user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return None
        buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, len(buffer))
        title = str(buffer.value or '').strip()
        if not title:
            return None
        pid = wintypes.DWORD()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return WindowObservation(
            title=title,
            app_name=title.split(' - ')[0] if title else '',
            pid=int(pid.value or 0),
            focused=True,
            visible=True,
            state='focused',
        )

    def _list_windows(self) -> list[dict[str, Any]]:
        if os.name != 'nt' or self._user32 is None:
            return []
        windows: list[dict[str, Any]] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_proc(hwnd, lparam):  # pragma: no cover - Windows only
            if not self._user32.IsWindowVisible(hwnd):
                return True
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, len(buffer))
            title = str(buffer.value or '').strip()
            if not title:
                return True
            pid = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            windows.append({'title': title, 'pid': int(pid.value or 0)})
            return True

        try:
            self._user32.EnumWindows(enum_proc, 0)
        except Exception:
            return []
        return windows

    def _network_status(self, *, full: bool) -> tuple[NetworkStatusSnapshot, list[str]]:
        latency_ms, error = self._network_connectivity_probe()
        if latency_ms is None:
            detail = 'No pude confirmar conectividad a internet ahora mismo.'
            if error:
                detail = f'No pude confirmar conectividad a internet: {error}.'
            return (
                NetworkStatusSnapshot(
                    connected=False,
                    status='desconectado',
                    quality='sin_red',
                    detail=detail,
                    evidence=[error] if error else [],
                ),
                ['UNRESOLVED:network_latency'] if error and 'timeout' not in error.lower() else [],
            )
        if latency_ms >= 900.0:
            status = 'lento'
            quality = 'lenta'
            detail = 'La red responde, pero esta bastante lenta para rutas web delicadas.'
        elif latency_ms >= 300.0:
            status = 'conectado'
            quality = 'media'
            detail = 'La red esta disponible con una latencia media.'
        else:
            status = 'conectado'
            quality = 'buena'
            detail = 'La red responde bien para consultas externas normales.'
        return (
            NetworkStatusSnapshot(
                connected=True,
                status=status,
                quality=quality,
                latency_ms=round(latency_ms, 2),
                detail=detail,
                evidence=[f'latency_ms:{round(latency_ms, 2)}'],
            ),
            [],
        )

    def _network_connectivity_probe(self) -> tuple[float | None, str]:
        started = time.perf_counter()
        try:
            with socket.create_connection(('1.1.1.1', 53), timeout=self._NETWORK_TIMEOUT_SECONDS):
                latency_ms = (time.perf_counter() - started) * 1000.0
                return latency_ms, ''
        except Exception as exc:
            return None, str(exc)

    def _background_processes(self, *, full: bool) -> list[BackgroundProcessSnapshot]:
        if self._in_test_mode() and not full:
            return []
        payload = self._powershell_json(
            "Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | "
            "Where-Object { $_.Name -and $_.IDProcess -gt 0 -and $_.Name -notin @('_Total','Idle') } | "
            "Sort-Object PercentProcessorTime -Descending | "
            "Select-Object -First 12 Name,IDProcess,PercentProcessorTime,WorkingSetPrivate | ConvertTo-Json -Compress"
        )
        rows = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
        items: list[BackgroundProcessSnapshot] = []
        for row in rows:
            try:
                process_name = str(row.get('Name') or row.get('ProcessName') or '').strip()
                pid = int(row.get('IDProcess') or row.get('Id') or 0)
                cpu_value = row.get('PercentProcessorTime')
                memory_bytes = row.get('WorkingSetPrivate') or row.get('WorkingSet64') or 0.0
                memory_mb = round(float(memory_bytes) / (1024 * 1024), 2)
            except Exception:
                continue
            if not process_name:
                continue
            state = 'ok'
            detail = ''
            cpu_load = float(cpu_value) if isinstance(cpu_value, (int, float)) else None
            if cpu_load is not None and cpu_load >= 80.0:
                state = 'cpu_heavy'
                detail = 'Este proceso esta consumiendo bastante CPU justo ahora.'
            if memory_mb >= self._HIGH_MEMORY_MB:
                state = 'memory_heavy'
                detail = 'Este proceso esta usando bastante memoria y puede interferir con tareas pesadas.'
            items.append(
                BackgroundProcessSnapshot(
                    process_name=process_name,
                    pid=pid,
                    cpu_percent=cpu_load,
                    cpu_load_percent=cpu_load,
                    memory_mb=memory_mb,
                    responding=None,
                    state=state,
                    detail=detail,
                    interferes_with_capture=process_name.lower() in {'snippingtool', 'sharex', 'powertoys', 'onedrive'},
                    gpu_percent=None,
                )
            )
        return items

    def _detected_blocks(
        self,
        *,
        environment: EnvironmentSelfModel,
        network_status: NetworkStatusSnapshot,
        tool_live_status: list[ToolLiveStatus],
        background_processes: list[BackgroundProcessSnapshot],
        permission_gates: list[ObservationPermissionGate],
    ) -> list[str]:
        blocks: list[str] = []
        if not network_status.connected:
            blocks.append('network_blocked')
        elif network_status.status == 'lento':
            blocks.append('network_slow')
        for status in tool_live_status:
            for block in status.detected_blocks:
                if block not in blocks:
                    blocks.append(block)
        for risk in environment.risk_signals:
            if risk.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL} and str(risk.kind or '') not in blocks:
                blocks.append(str(risk.kind or ''))
        for process in background_processes:
            if process.interferes_with_capture and process.state != 'ok':
                blocks.append(f'process_interference:{process.process_name.lower()}')
            if process.state == 'cpu_heavy':
                blocks.append(f'process_cpu_heavy:{process.process_name.lower()}')
        for gate in permission_gates:
            if gate.status == 'requerido':
                blocks.append(f'permission_required:{gate.scope}')
        return blocks[:18]

    def _permission_gates(self, *, tool_live_status: list[ToolLiveStatus]) -> list[ObservationPermissionGate]:
        gates: list[ObservationPermissionGate] = []
        permission_state = {item.get('scope'): item for item in self.permission_snapshot()}
        for tool in tool_live_status:
            if tool.permission_state == 'no_requerido':
                continue
            scope = str(tool.metadata.get('permission_scope') or self._content_permission_scope(tool.assistant_kind))
            permission = dict(permission_state.get(scope) or {})
            gates.append(
                ObservationPermissionGate(
                    scope=scope,
                    assistant_kind=tool.assistant_kind,
                    title=f'Observar {tool.title or tool.assistant_kind or "ventana externa"}',
                    detail=(
                        str(permission.get('detail') or '').strip()
                        or self._permission_prompt(assistant_kind=tool.assistant_kind)
                    ),
                    status='concedido' if tool.permission_state == 'concedido' else 'requerido',
                    required_for=[f'consult_{tool.assistant_kind}'] if tool.assistant_kind else [],
                    granted=bool(permission.get('granted')) or tool.permission_state == 'concedido',
                    confidence=max(0.45, float(tool.confidence or 0.0)),
                    metadata={
                        'tool_id': tool.tool_id,
                        'probe_status': tool.probe_status,
                        'window_open': tool.window_open,
                        'last_verified_at': tool.last_verified_at.isoformat() if tool.last_verified_at is not None else '',
                    },
                )
            )
        return gates

    def _block_records(
        self,
        *,
        environment: EnvironmentSelfModel,
        network_status: NetworkStatusSnapshot,
        tool_live_status: list[ToolLiveStatus],
        background_processes: list[BackgroundProcessSnapshot],
        focused: WindowObservation | None,
        permission_gates: list[ObservationPermissionGate],
    ) -> list[OperationalBlockRecord]:
        records: list[OperationalBlockRecord] = []
        if not network_status.connected:
            records.append(
                OperationalBlockRecord(
                    block_type='network_blocked',
                    target_scope='consult_external',
                    title='Red no disponible',
                    detail=str(network_status.detail or 'La red no quedo confirmada para consultas externas.'),
                    reason='Sin red confiable, las rutas web externas no son viables.',
                    evidence=list(network_status.evidence or []),
                    confidence=0.9,
                )
            )
        elif network_status.status == 'lento':
            records.append(
                OperationalBlockRecord(
                    block_type='network_slow',
                    target_scope='consult_external',
                    title='Red lenta',
                    detail=str(network_status.detail or 'La red responde, pero con latencia alta.'),
                    reason='La red lenta puede degradar rutas web y producir fallas aparentes del sitio.',
                    evidence=list(network_status.evidence or []),
                    confidence=0.76,
                )
            )
        for gate in permission_gates:
            if gate.status != 'requerido':
                continue
            target_scope = str((gate.required_for or ['consult_external'])[0] or 'consult_external')
            records.append(
                OperationalBlockRecord(
                    block_type='permission_required',
                    target_scope=target_scope,
                    assistant_kind=gate.assistant_kind,
                    title=gate.title,
                    detail=gate.detail,
                    reason='Falta permiso explicito para observar contenido visible antes de usar esta ruta.',
                    evidence=[gate.scope],
                    confidence=max(0.72, float(gate.confidence or 0.0)),
                    metadata={'scope': gate.scope},
                )
            )
        for tool in tool_live_status:
            route_scope = f'consult_{tool.assistant_kind}' if tool.assistant_kind else 'consult_external'
            for block in tool.detected_blocks:
                if block == 'wrong_thread':
                    records.append(
                        OperationalBlockRecord(
                            block_type='wrong_thread',
                            target_scope=route_scope,
                            assistant_kind=tool.assistant_kind,
                            title=tool.title,
                            detail=str(tool.detail or 'La evidencia reciente apunta a otro hilo.'),
                            reason='No conviene pegar o consultar en un hilo distinto del workspace esperado.',
                            evidence=[tool.tool_id],
                            confidence=max(0.82, float(tool.confidence or 0.0)),
                        )
                    )
                elif block == 'browser_security_verification':
                    records.append(
                        OperationalBlockRecord(
                            block_type='browser_security_verification',
                            target_scope=route_scope,
                            assistant_kind=tool.assistant_kind,
                            title=tool.title,
                            detail=str(tool.detail or 'El sitio activo una verificacion antes de abrir el chat.'),
                            reason='El bloqueo es del sitio y no debe tratarse como selector roto.',
                            evidence=[tool.tool_id],
                            confidence=max(0.78, float(tool.confidence or 0.0)),
                        )
                    )
                elif block in {'assistant_unavailable', 'network_blocked'}:
                    records.append(
                        OperationalBlockRecord(
                            block_type=block,
                            target_scope=route_scope,
                            assistant_kind=tool.assistant_kind,
                            title=tool.title,
                            detail=str(tool.detail or ''),
                            reason='La herramienta no quedo confirmada como lista en este estado operativo.',
                            evidence=[tool.tool_id],
                            confidence=max(0.72, float(tool.confidence or 0.0)),
                        )
                    )
            if tool.messages_status == 'agotados_o_limitados':
                records.append(
                    OperationalBlockRecord(
                        block_type='account_limited',
                        target_scope=route_scope,
                        assistant_kind=tool.assistant_kind,
                        title=tool.title,
                        detail=str(tool.detail or 'La cuenta o los mensajes estan limitados.'),
                        reason='La cuenta externa no parece disponible para una consulta nueva.',
                        evidence=[tool.tool_id],
                        confidence=max(0.84, float(tool.confidence or 0.0)),
                    )
                )
        for risk in environment.risk_signals:
            if str(risk.kind or '') in {'ram_pressure', 'ram_critical', 'cpu_pressure', 'throttling_detected'}:
                records.append(
                    OperationalBlockRecord(
                        block_type=str(risk.kind or ''),
                        target_scope='heavy_local_model',
                        title='Entorno bajo presion',
                        detail=risk.summary,
                        reason='Conviene evitar tareas pesadas hasta que baje la presion del equipo.',
                        evidence=[str(risk.kind or '')],
                        confidence=0.8,
                    )
                )
        if focused is not None and not str(focused.title or '').strip():
            records.append(
                OperationalBlockRecord(
                    block_type='focus_unresolved',
                    target_scope='ui_focus_interaction',
                    title='Foco no confirmado',
                    detail='No pude confirmar que ventana tiene el foco en este instante.',
                    reason='No deberia interactuar con UI sensible sin foco confirmado.',
                    confidence=0.63,
                )
            )
        for process in background_processes:
            if process.state in {'cpu_heavy', 'memory_heavy'}:
                records.append(
                    OperationalBlockRecord(
                        block_type=process.state,
                        target_scope='heavy_local_model',
                        title=process.process_name,
                        detail=str(process.detail or ''),
                        reason='Hay consumo alto en segundo plano que puede degradar la tarea.',
                        evidence=[f'pid:{process.pid}'],
                        confidence=0.68,
                    )
                )
        unique: list[OperationalBlockRecord] = []
        seen: set[tuple[str, str, str]] = set()
        for item in records:
            key = (item.block_type, item.target_scope, item.assistant_kind)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique[:16]

    def _inferred_state(
        self,
        *,
        environment: EnvironmentSelfModel,
        network_status: NetworkStatusSnapshot,
        tool_live_status: list[ToolLiveStatus],
        focused: WindowObservation | None,
        active_windows: list[WindowObservation],
        detected_blocks: list[str],
        block_records: list[OperationalBlockRecord],
        permission_gates: list[ObservationPermissionGate],
    ) -> dict[str, Any]:
        deductions: list[str] = []
        focused_title = str(focused.title or '') if focused is not None else ''
        if focused_title:
            deductions.append(f'La ventana en foco ahora mismo es {focused_title}.')
        codex = next((item for item in tool_live_status if item.assistant_kind == 'codex'), None)
        if codex is not None and codex.thread_status == 'otro_hilo_activo':
            deductions.append('Codex esta abierto, pero el hilo activo no parece ser el del workspace de IABV.')
        if codex is not None and codex.messages_status == 'agotados_o_limitados':
            deductions.append('Codex muestra senales recientes de limite de cuenta o mensajes agotados.')
        for tool in tool_live_status:
            if 'browser_security_verification' in tool.detected_blocks:
                deductions.append(f'{tool.title} quedo bloqueado por verificacion de seguridad del sitio.')
            if tool.permission_state == 'requerido':
                deductions.append(f'Antes de verificar de verdad a {tool.title} necesito permiso para observar su contenido visible.')
            if network_status.connected and tool.status in {'bloqueado', 'limitado', 'sesion_expirada'}:
                deductions.append(f'La red si responde; el bloqueo principal parece venir de {tool.title} y no de internet.')
        if not network_status.connected:
            deductions.append('La red no quedo confirmada; el bloqueo parece ser de conectividad y no del codigo.')
        elif network_status.status == 'lento':
            deductions.append('La red esta disponible, pero lenta; una falla web puede venir de latencia y no solo del selector.')
        if any(str(risk.kind or '') in {'ram_pressure', 'ram_critical', 'cpu_pressure', 'throttling_detected'} for risk in environment.risk_signals):
            deductions.append('El entorno esta bajo presion y conviene evitar tareas pesadas antes de seguir.')
        summary = 'Observacion operativa actualizada.'
        if detected_blocks:
            summary = 'Hay bloqueos operativos activos que conviene respetar antes de lanzar otra accion.'
        return {
            'summary': summary,
            'focused_window': focused_title,
            'active_window_count': len(active_windows),
            'blocked_routes': [
                {
                    'block_type': item.block_type,
                    'target_scope': item.target_scope,
                    'assistant_kind': item.assistant_kind,
                }
                for item in block_records[:8]
            ],
            'permission_gates': [
                {
                    'scope': item.scope,
                    'assistant_kind': item.assistant_kind,
                    'status': item.status,
                    'required_for': list(item.required_for),
                }
                for item in permission_gates[:6]
            ],
            'blocked_tools': [
                {
                    'assistant_kind': item.assistant_kind,
                    'tool_id': item.tool_id,
                    'status': item.status,
                    'detected_blocks': list(item.detected_blocks),
                }
                for item in tool_live_status
                if item.detected_blocks
            ][:8],
            'deductions': deductions[:8],
        }

    def _observation_sources(
        self,
        *,
        network_status: NetworkStatusSnapshot,
        tool_live_status: list[ToolLiveStatus],
        background_processes: list[BackgroundProcessSnapshot],
        permission_gates: list[ObservationPermissionGate],
    ) -> list[str]:
        sources = ['environment_self_model']
        if str(network_status.status or '').strip():
            sources.append('network_probe')
        if background_processes:
            sources.append('process_perf_probe')
        for tool in tool_live_status:
            sources.extend(list(tool.observed_via or []))
        if permission_gates:
            sources.append('permission_registry')
        return list(dict.fromkeys(item for item in sources if str(item).strip()))

    def _gpu_process_probe_available(self) -> bool:
        return False

    def _decorate_snapshot(self, snapshot: WorldModelSnapshot) -> WorldModelSnapshot:
        model = snapshot.model_copy(deep=True)
        freshness_ms = 0
        if model.last_updated is not None:
            freshness_ms = max(
                0,
                int((utc_now() - model.last_updated).total_seconds() * 1000.0),
            )
        model.freshness_ms = freshness_ms
        return model

    def _confidence(
        self,
        *,
        active_windows: list[WindowObservation],
        tool_live_status: list[ToolLiveStatus],
        network_status: NetworkStatusSnapshot,
        unresolved_fields: list[str],
    ) -> float:
        score = 0.18
        if active_windows:
            score += 0.22
        if any(item.available for item in tool_live_status):
            score += 0.18
        if network_status.status in {'conectado', 'lento'}:
            score += 0.16
        if any(item.window_open for item in tool_live_status):
            score += 0.12
        score -= min(0.3, 0.04 * len(unresolved_fields))
        return round(max(0.0, min(0.94, score)), 3)

    def _tool_confidence(self, *, card: ToolCard, signal: Any, history: dict[str, Any]) -> float:
        score = 0.16
        if bool(card.available):
            score += 0.16
        if bool((signal.visual_snapshot or {}).get('window_visible')):
            score += 0.24
        elif bool((signal.visual_snapshot or {}).get('process_running')):
            score += 0.16
        if history.get('external_state_flags'):
            score += 0.08
        if history.get('browser_security_verification'):
            score += 0.08
        history_state = str(history.get('history_state') or '')
        if history_state == 'executed':
            score += 0.12
        elif history_state in ('awaiting_response', 'failed'):
            score += 0.04
        if history.get('last_verified_at'):
            score += 0.06
        score -= min(0.2, 0.06 * len(signal.unresolved_fields or []))
        return round(max(0.0, min(0.9, score)), 3)

    def _changes_from_previous(
        self,
        *,
        previous: WorldModelSnapshot,
        current_blocks: list[str],
        tool_live_status: list[ToolLiveStatus],
        focused: WindowObservation | None,
    ) -> list[str]:
        if not previous.snapshot_id:
            return []
        changes: list[str] = []
        previous_blocks = set(previous.detected_blocks or [])
        for block in current_blocks:
            if block not in previous_blocks:
                changes.append(f'block:{block}')
        previous_focus = str((previous.focused_window.title if previous.focused_window is not None else '') or '')
        current_focus = str((focused.title if focused is not None else '') or '')
        if current_focus and current_focus != previous_focus:
            changes.append(f'focus:{current_focus}')
        previous_tool_status = {item.tool_id: item.status for item in previous.tool_live_status}
        for item in tool_live_status:
            if previous_tool_status.get(item.tool_id) != item.status:
                changes.append(f'tool:{item.tool_id}->{item.status}')
        return changes[:10]

    def _environment_self_model(self) -> EnvironmentSelfModel:
        service = self.environment_self_awareness_service
        if service is None:
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            return service.current_model()
        except Exception:
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _load_user32(self):  # pragma: no cover - Windows only
        if os.name != 'nt':
            return None
        try:
            return ctypes.windll.user32
        except Exception:
            return None

    def _expand_external_path(self, candidate: str) -> str:
        expanded = str(candidate or '')
        replacements = {
            '{localappdata}': os.environ.get('LOCALAPPDATA', ''),
            '{programfiles}': os.environ.get('ProgramFiles', ''),
            '{programfilesx86}': os.environ.get('ProgramFiles(x86)', ''),
            '{userprofile}': os.environ.get('USERPROFILE', str(Path.home())),
        }
        for token, value in replacements.items():
            expanded = expanded.replace(token, value)
        return expanded

    def _powershell_json(self, command: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        shell = shutil.which('powershell') or shutil.which('pwsh')
        if not shell:
            return None
        result = self._run_command([shell, '-Command', command], timeout_seconds=4.0)
        if not result or result.get('returncode') != 0:
            return None
        stdout = str(result.get('stdout') or '').strip()
        if not stdout:
            return None
        try:
            return json.loads(stdout)
        except Exception:
            return None

    def _run_command(self, command: list[str], *, timeout_seconds: float) -> dict[str, Any] | None:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=timeout_seconds,
                check=False,
            )
        except Exception:
            return None
        return {'returncode': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr}

    def _latest_snapshot_path(self) -> Path:
        return self.state_dir / 'latest.json'

    def _load_latest_snapshot(self) -> WorldModelSnapshot | None:
        path = self._latest_snapshot_path()
        if not path.exists():
            return None
        try:
            return WorldModelSnapshot.model_validate_json(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def _persist_snapshot(self, snapshot: WorldModelSnapshot) -> None:
        payload = json.dumps(snapshot.model_dump(mode='json'), ensure_ascii=True, indent=2)
        self._latest_snapshot_path().write_text(payload, encoding='utf-8')

    def _in_test_mode(self) -> bool:
        return bool(os.getenv('PYTEST_CURRENT_TEST'))
