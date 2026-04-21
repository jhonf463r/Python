from __future__ import annotations

import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency for MCP adapter only
    httpx = None

from iabv_v15.domain.models import InferenceRequest, RunStatus, ToolActionType, ToolCard, ToolTask, ToolType
from iabv_v15.services.capture.browser_action_service import BrowserActionService
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController, sync_playwright
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.services.tools.ui_execution_runner import UIExecutionRunner


class ToolAdapter:
    tool_type: ToolType

    def __init__(self, runner_factory: Callable[[str], UIExecutionRunner] | None = None) -> None:
        self.runner_factory = runner_factory or (lambda workspace_root: UIExecutionRunner(workspace_root))
        # Inyectado por bootstrap cuando el adapter maneja asistentes externos
        # que pueden requerir login. Mantenerlo opcional evita romper
        # contratos para adapters que nunca tocan credenciales.
        self.credential_broker: Any = None

    def _resolve_credential_domain(self, card: ToolCard) -> str:
        """Dominio preferido para asociar credenciales de un asistente externo."""
        explicit = str(card.metadata.get('credential_domain') or '').strip().lower()
        if explicit:
            return explicit
        web_url = str(card.metadata.get('web_url') or '').strip()
        if web_url:
            try:
                host = (urlparse(web_url).hostname or '').strip().lower()
            except ValueError:
                host = ''
            if host:
                return host
        assistant_kind = str(card.metadata.get('assistant_kind') or '').strip().lower()
        return assistant_kind

    def _reingest_only_flag(self, *, card: ToolCard, task: ToolTask) -> bool:
        """Devuelve True si se debe reingerir la respuesta de una sesion ya abierta.

        Se activa cuando el orquestador, tras detectar una consulta expirada,
        programa un reintento marcando `reingest_existing_response=True`. En ese
        caso el runner debe saltar el re-pegado del prompt y solo leer la
        respuesta vigente en la sesion aislada.
        """
        task_metadata = dict(task.metadata or {})
        goal_parameters = dict(task_metadata.get('goal_parameters') or {})
        consultation_retry = dict(task_metadata.get('consultation_retry') or {})
        candidates = (
            task_metadata.get('reingest_existing_response'),
            goal_parameters.get('reingest_existing_response'),
            consultation_retry.get('reingest_only'),
            card.metadata.get('reingest_existing_response'),
        )
        return any(bool(value) for value in candidates)

    def _request_login_credentials(self, card: ToolCard) -> None:
        """Emite el prompt de credenciales si el broker esta disponible y aun faltan.

        Idempotente: si la credencial ya existe en el broker para el dominio,
        no vuelve a abrir el dialogo. Silencioso ante brokers no inyectados o
        fallas locales, para no romper la ruta externa.
        """
        broker = self.credential_broker
        if broker is None:
            return
        domain = self._resolve_credential_domain(card)
        if not domain:
            return
        try:
            if not broker.needs(domain):
                return
            reason = (
                f'Iniciar sesion en {card.title} una vez para que IABV pueda '
                'consultar en segundo plano desde su sesion aislada.'
            )
            username_hint = str(card.metadata.get('credential_username_hint') or '').strip() or None
            broker.request(domain, reason=reason, username_hint=username_hint)
        except Exception:
            # El broker nunca debe tumbar la ruta externa; si falla el prompt
            # simplemente seguimos con el mensaje de espera ya existente.
            return

    def is_available(self, card: ToolCard) -> bool:
        launch_mode = str(card.metadata.get('launch_mode') or '').strip().lower()
        response_capture_mode = str(card.metadata.get('response_capture_mode') or '').strip().lower()
        direct_response_text = str(card.metadata.get('direct_response_text') or '').strip()
        if response_capture_mode in {'direct_text', 'tool_result'} and direct_response_text:
            return True
        if launch_mode == 'web_assisted':
            return bool(str(card.metadata.get('web_url') or '').strip())
        return bool(self._resolve_launch_target(card))

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        launch_mode = str(card.metadata.get('launch_mode') or '').strip().lower()
        assistant_kind = str(card.metadata.get('assistant_kind') or card.tool_id)
        response_capture_mode = str(card.metadata.get('response_capture_mode') or task.metadata.get('response_capture_mode') or 'manual_pasteback').strip().lower()
        direct_response_text = str(card.metadata.get('direct_response_text') or task.metadata.get('direct_response_text') or '').strip()
        direct_capture = response_capture_mode in {'direct_text', 'tool_result'} and bool(direct_response_text)
        requires_manual_pasteback = False if direct_capture else bool(card.metadata.get('requires_manual_pasteback', task.metadata.get('requires_manual_pasteback', True)))
        prompt_text = next((action.value for action in task.actions if action.action_type == ToolActionType.LLM_QUERY and action.value), task.objective)
        prompt_preview = prompt_text[:400]
        launch_target = str(card.metadata.get('web_url') or '') if launch_mode == 'web_assisted' else self._resolve_launch_target(card)
        clipboard_capture = response_capture_mode == 'clipboard_capture' and launch_mode == 'desktop_app'
        browser_dom_capture = response_capture_mode in {'dom_capture', 'browser_dom'} and launch_mode == 'web_assisted'
        background_capture_mode = str(card.metadata.get('background_capture_mode') or task.metadata.get('background_capture_mode') or '').strip().lower()
        workspace_root = str(task.metadata.get('workspace_root') or card.metadata.get('workspace_root') or Path.cwd())
        session_scope = self._session_scope(card=card, task=task)
        session_label = self._session_label(card=card, task=task)
        isolated_session = bool(task.metadata.get('isolated_session_required', card.metadata.get('isolated_session_required', False)))
        capture_attempt_utc = datetime.now(timezone.utc).isoformat() if (clipboard_capture or browser_dom_capture or background_capture_mode == 'codex_rollout') else str(task.metadata.get('last_capture_attempt_utc') or '')
        consultation_metadata = self._consultation_runtime_metadata(card=card, task=task, capture_attempt_utc=capture_attempt_utc)
        if sandbox:
            available = bool(launch_target) or direct_capture
            return {
                'success': available,
                'output_text': 'Asistente externo listo para consulta guiada.' if available else 'No pude validar la via externa solicitada.',
                'extracted_data': {'assistant_kind': assistant_kind, 'launch_target': launch_target},
                'artifacts': [],
                'error_message': '' if available else 'assistant_unavailable',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': launch_mode,
                    'launch_target': launch_target,
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': requires_manual_pasteback,
                    'prepared_prompt': prompt_text,
                    'response_captured': direct_capture,
                    'session_scope': session_scope,
                    'session_label': session_label,
                    'isolated_session': isolated_session,
                    **consultation_metadata,
                },
            }
        if direct_capture:
            return {
                'success': True,
                'output_text': direct_response_text,
                'extracted_data': {'assistant_kind': assistant_kind, 'launch_target': launch_target, 'prompt_preview': prompt_preview},
                'artifacts': [],
                'error_message': '',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': launch_mode,
                    'launch_target': launch_target,
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': False,
                    'prepared_prompt': prompt_text,
                    'prompt_preview': prompt_preview,
                    'response_captured': True,
                    'direct_response': True,
                    'launched': False,
                    'session_scope': session_scope,
                    'session_label': session_label,
                    'isolated_session': isolated_session,
                    **consultation_metadata,
                },
            }
        if not launch_target:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {'assistant_kind': assistant_kind},
                'artifacts': [],
                'error_message': 'assistant_unavailable',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': launch_mode,
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': requires_manual_pasteback,
                    'prepared_prompt': prompt_text,
                    'session_scope': session_scope,
                    'session_label': session_label,
                    'isolated_session': isolated_session,
                    **consultation_metadata,
                },
            }
        dry_run = bool(task.metadata.get('dry_run_launch') or card.metadata.get('dry_run_launch'))
        reingest_only = self._reingest_only_flag(card=card, task=task)
        try:
            if (clipboard_capture or browser_dom_capture) and not dry_run:
                captured = self._capture_desktop_response(
                    card=card,
                    task=task,
                    launch_target=launch_target,
                    launch_mode=launch_mode,
                    prompt_text=prompt_text,
                    reingest_only=reingest_only,
                )
                # Fallback a clipboard si browser_dom falla por verificación de seguridad o falta de input
                if not captured.get('response_captured') and browser_dom_capture:
                    fallback_error = str(captured.get('error_message') or '').strip().lower()
                    if fallback_error in {'browser_security_verification', 'browser_input_missing', 'browser_dom_capture_pending'}:
                        clipboard_fallback = self.runner_factory(workspace_root).capture_response_from_app(
                            launch_target=launch_target,
                            title_hints=self._title_hints(card=card, task=task),
                            prompt_text=prompt_text,
                            launch_mode=launch_mode,
                            submit_after_paste=bool(task.metadata.get('submit_prompt_after_paste', card.metadata.get('submit_prompt_after_paste', True))) and not reingest_only,
                            launch_wait_seconds=float(task.metadata.get('launch_wait_seconds') or card.metadata.get('launch_wait_seconds') or 1.2),
                            window_wait_seconds=float(task.metadata.get('window_wait_seconds') or card.metadata.get('window_wait_seconds') or 8.0),
                            response_wait_seconds=float(task.metadata.get('response_wait_seconds') or card.metadata.get('response_wait_seconds') or 4.0),
                            background_capture_mode='',  # Forzar modo clipboard
                            reingest_only=reingest_only,
                        )
                        if clipboard_fallback.get('response_captured'):
                            captured = clipboard_fallback
                            captured['capture_source'] = 'clipboard_fallback'
                if captured.get('response_captured'):
                    capture_source = str(captured.get('capture_source') or response_capture_mode).strip().lower() or response_capture_mode
                    if background_capture_mode == 'codex_rollout' and capture_source != 'session_rollout':
                        return {
                            'success': False,
                            'output_text': '',
                            'extracted_data': {
                                'assistant_kind': assistant_kind,
                                'launch_target': launch_target,
                                'prompt_preview': prompt_preview,
                                'focused_title': str(captured.get('focused_title') or ''),
                            },
                            'artifacts': [],
                            'error_message': 'capture_unverified',
                            'execution_ms': int((time.perf_counter() - start) * 1000),
                            'metadata': {
                                'sandbox': sandbox,
                                'assistant_kind': assistant_kind,
                                'launch_mode': launch_mode,
                                'launch_target': launch_target,
                                'response_capture_mode': capture_source,
                                'manual_pasteback_required': False,
                                'prepared_prompt': prompt_text,
                                'prompt_preview': prompt_preview,
                                'response_captured': False,
                                'launched': bool(captured.get('launched')),
                                'auto_capture_attempted': True,
                                'auto_capture_reason': 'capture_unverified',
                                'focused_title': str(captured.get('focused_title') or ''),
                                'session_scope': session_scope,
                                'session_label': session_label,
                                'isolated_session': isolated_session,
                                **consultation_metadata,
                                'capture_source': capture_source,
                                'thread_verification': '',
                                'capture_unverified': True,
                                'used_fallback_capture': bool(captured.get('used_fallback_capture')),
                                'rollout_path': str(captured.get('rollout_path') or ''),
                                'browser_profile_dir': str(captured.get('browser_profile_dir') or ''),
                            },
                        }
                    if capture_source == 'session_rollout' and not bool(captured.get('thread_verified')):
                        return {
                            'success': False,
                            'output_text': '',
                            'extracted_data': {
                                'assistant_kind': assistant_kind,
                                'launch_target': launch_target,
                                'prompt_preview': prompt_preview,
                                'focused_title': str(captured.get('focused_title') or ''),
                            },
                            'artifacts': [],
                            'error_message': 'wrong_thread',
                            'execution_ms': int((time.perf_counter() - start) * 1000),
                            'metadata': {
                                'sandbox': sandbox,
                                'assistant_kind': assistant_kind,
                                'launch_mode': launch_mode,
                                'launch_target': launch_target,
                                'response_capture_mode': capture_source,
                                'manual_pasteback_required': False,
                                'prepared_prompt': prompt_text,
                                'prompt_preview': prompt_preview,
                                'response_captured': False,
                                'launched': bool(captured.get('launched')),
                                'auto_capture_attempted': True,
                                'auto_capture_reason': 'wrong_thread',
                                'focused_title': str(captured.get('focused_title') or ''),
                                'session_scope': session_scope,
                                'session_label': session_label,
                                'isolated_session': isolated_session,
                    **consultation_metadata,
                                'capture_source': capture_source,
                                'thread_verification': 'wrong_thread',
                                'thread_mismatch': True,
                                'capture_unverified': True,
                                'used_fallback_capture': bool(captured.get('used_fallback_capture')),
                                'rollout_path': str(captured.get('rollout_path') or ''),
                                'browser_profile_dir': str(captured.get('browser_profile_dir') or ''),
                            },
                        }
                    return {
                        'success': True,
                        'output_text': str(captured.get('captured_text') or ''),
                        'extracted_data': {
                            'assistant_kind': assistant_kind,
                            'launch_target': launch_target,
                            'prompt_preview': prompt_preview,
                            'focused_title': str(captured.get('focused_title') or ''),
                        },
                        'artifacts': [],
                        'error_message': '',
                        'execution_ms': int((time.perf_counter() - start) * 1000),
                        'metadata': {
                            'sandbox': sandbox,
                            'assistant_kind': assistant_kind,
                            'launch_mode': launch_mode,
                            'launch_target': launch_target,
                            'response_capture_mode': capture_source,
                            'manual_pasteback_required': False,
                            'prepared_prompt': prompt_text,
                            'prompt_preview': prompt_preview,
                            'response_captured': True,
                            'launched': bool(captured.get('launched')),
                            'auto_capture_attempted': True,
                            'auto_capture_reason': '',
                            'focused_title': str(captured.get('focused_title') or ''),
                            'session_scope': session_scope,
                            'session_label': session_label,
                            'isolated_session': isolated_session,
                    **consultation_metadata,
                            'capture_source': capture_source,
                            'thread_verification': 'verified' if bool(captured.get('thread_verified')) else '',
                            'used_fallback_capture': bool(captured.get('used_fallback_capture')),
                            'rollout_path': str(captured.get('rollout_path') or ''),
                            'browser_profile_dir': str(captured.get('browser_profile_dir') or ''),
                        },
                    }
                if captured.get('launched'):
                    fallback_reason = str(captured.get('error_message') or 'capture_pending')
                    if browser_dom_capture:
                        login_required = fallback_reason == 'assistant_login_required'
                        if login_required:
                            # Emitir popup de credenciales una sola vez por dominio.
                            # Si la UI ya acepto usuario/pass antes, broker.needs()
                            # devuelve False y esto es un noop.
                            self._request_login_credentials(card)
                        keep_waiting = login_required or fallback_reason == 'browser_dom_capture_pending'
                        if not keep_waiting:
                            return {
                                'success': False,
                                'output_text': '',
                                'extracted_data': {
                                    'assistant_kind': assistant_kind,
                                    'launch_target': launch_target,
                                    'prompt_preview': prompt_preview,
                                    'focused_title': str(captured.get('focused_title') or ''),
                                },
                                'artifacts': [],
                                'error_message': fallback_reason,
                                'execution_ms': int((time.perf_counter() - start) * 1000),
                                'metadata': {
                                    'sandbox': sandbox,
                                    'assistant_kind': assistant_kind,
                                    'launch_mode': launch_mode,
                                    'launch_target': launch_target,
                                    'response_capture_mode': response_capture_mode,
                                    'manual_pasteback_required': False,
                                    'prepared_prompt': prompt_text,
                                    'prompt_preview': prompt_preview,
                                    'response_captured': False,
                                    'launched': True,
                                    'auto_capture_attempted': True,
                                    'auto_capture_reason': fallback_reason,
                                    'response_capture_pending': False,
                                    'assistant_login_required': False,
                                    'focused_title': str(captured.get('focused_title') or ''),
                                    'session_scope': session_scope,
                                    'session_label': session_label,
                                    'isolated_session': isolated_session,
                    **consultation_metadata,
                                    'capture_source': str(captured.get('capture_source') or 'browser_dom').strip().lower() or 'browser_dom',
                                    'browser_profile_dir': str(captured.get('browser_profile_dir') or ''),
                                },
                            }
                        waiting_message = (
                            f'La sesion aislada de {card.title} necesita que inicies sesion una vez para que IABV pueda seguir consultando en segundo plano.'
                            if login_required
                            else f'Asistente externo {card.title} consultando en sesion aislada del programa. Todavia no hubo texto util para integrar.'
                        )
                        return {
                            'success': True,
                            'output_text': waiting_message,
                            'extracted_data': {
                                'assistant_kind': assistant_kind,
                                'launch_target': launch_target,
                                'prompt_preview': prompt_preview,
                                'focused_title': str(captured.get('focused_title') or ''),
                            },
                            'artifacts': [],
                            'error_message': '',
                            'execution_ms': int((time.perf_counter() - start) * 1000),
                            'metadata': {
                                'sandbox': sandbox,
                                'assistant_kind': assistant_kind,
                                'launch_mode': launch_mode,
                                'launch_target': launch_target,
                                'response_capture_mode': response_capture_mode,
                                'manual_pasteback_required': False,
                                'prepared_prompt': prompt_text,
                                'prompt_preview': prompt_preview,
                                'response_captured': False,
                                'launched': True,
                                'auto_capture_attempted': True,
                                'auto_capture_reason': fallback_reason,
                                'response_capture_pending': not login_required,
                                'assistant_login_required': login_required,
                                'focused_title': str(captured.get('focused_title') or ''),
                                'session_scope': session_scope,
                                'session_label': session_label,
                                'isolated_session': isolated_session,
                    **consultation_metadata,
                                'capture_source': str(captured.get('capture_source') or 'browser_dom').strip().lower() or 'browser_dom',
                                'browser_profile_dir': str(captured.get('browser_profile_dir') or ''),
                            },
                        }
                    if background_capture_mode == 'codex_rollout':
                        if fallback_reason == 'codex_state_missing':
                            return {
                                'success': False,
                                'output_text': '',
                                'extracted_data': {
                                    'assistant_kind': assistant_kind,
                                    'launch_target': launch_target,
                                    'prompt_preview': prompt_preview,
                                    'focused_title': str(captured.get('focused_title') or ''),
                                },
                                'artifacts': [],
                                'error_message': 'codex_state_missing',
                                'execution_ms': int((time.perf_counter() - start) * 1000),
                                'metadata': {
                                    'sandbox': sandbox,
                                    'assistant_kind': assistant_kind,
                                    'launch_mode': launch_mode,
                                    'launch_target': launch_target,
                                    'response_capture_mode': response_capture_mode,
                                    'manual_pasteback_required': False,
                                    'prepared_prompt': prompt_text,
                                    'prompt_preview': prompt_preview,
                                    'response_captured': False,
                                    'launched': True,
                                    'auto_capture_attempted': True,
                                    'auto_capture_reason': fallback_reason,
                                    'response_capture_pending': False,
                                    'focused_title': str(captured.get('focused_title') or ''),
                                    'session_scope': session_scope,
                                    'session_label': session_label,
                                    'isolated_session': isolated_session,
                                    **consultation_metadata,
                                    'capture_source': 'codex_rollout',
                                    'last_capture_attempt_utc': capture_attempt_utc,
                                    'missing_thread_tracking': True,
                                    'capture_unverified': True,
                                },
                            }
                        return {
                            'success': True,
                            'output_text': (
                                f'Asistente externo {card.title} consultando. '
                                'IABV sigue intentando capturar la respuesta desde la sesion de Codex en segundo plano.'
                            ),
                            'extracted_data': {
                                'assistant_kind': assistant_kind,
                                'launch_target': launch_target,
                                'prompt_preview': prompt_preview,
                                'focused_title': str(captured.get('focused_title') or ''),
                            },
                            'artifacts': [],
                            'error_message': '',
                            'execution_ms': int((time.perf_counter() - start) * 1000),
                            'metadata': {
                                'sandbox': sandbox,
                                'assistant_kind': assistant_kind,
                                'launch_mode': launch_mode,
                                'launch_target': launch_target,
                                'response_capture_mode': response_capture_mode,
                                'manual_pasteback_required': False,
                                'prepared_prompt': prompt_text,
                                'prompt_preview': prompt_preview,
                                'response_captured': False,
                                'launched': True,
                                'auto_capture_attempted': True,
                                'auto_capture_reason': fallback_reason,
                                'response_capture_pending': True,
                                'focused_title': str(captured.get('focused_title') or ''),
                                'session_scope': session_scope,
                                'session_label': session_label,
                                'isolated_session': isolated_session,
                    **consultation_metadata,
                                'capture_source': 'codex_rollout',
                                'last_capture_attempt_utc': capture_attempt_utc,
                            },
                        }
                    return {
                        'success': True,
                        'output_text': f'Asistente externo {card.title} preparado. Intente capturar la respuesta automaticamente, pero todavia no hubo texto util. Copia la respuesta y devuelvela a IABV.',
                        'extracted_data': {
                            'assistant_kind': assistant_kind,
                            'launch_target': launch_target,
                            'prompt_preview': prompt_preview,
                            'focused_title': str(captured.get('focused_title') or ''),
                        },
                        'artifacts': [],
                        'error_message': '',
                        'execution_ms': int((time.perf_counter() - start) * 1000),
                        'metadata': {
                            'sandbox': sandbox,
                            'assistant_kind': assistant_kind,
                            'launch_mode': launch_mode,
                            'launch_target': launch_target,
                            'response_capture_mode': 'manual_pasteback',
                            'manual_pasteback_required': True,
                            'prepared_prompt': prompt_text,
                            'prompt_preview': prompt_preview,
                            'response_captured': False,
                            'launched': True,
                            'auto_capture_attempted': True,
                            'auto_capture_reason': fallback_reason,
                            'focused_title': str(captured.get('focused_title') or ''),
                            'session_scope': session_scope,
                            'session_label': session_label,
                            'isolated_session': isolated_session,
                            **consultation_metadata,
                            'capture_lane': 'manual',
                            'awaiting_reason': 'Pendiente de pegar manualmente la respuesta en IABV.',
                            'last_capture_attempt_utc': capture_attempt_utc,
                        },
                    }
                if browser_dom_capture:
                    return {
                        'success': False,
                        'output_text': '',
                        'extracted_data': {'assistant_kind': assistant_kind, 'launch_target': launch_target},
                        'artifacts': [],
                        'error_message': str(captured.get('error_message') or 'browser_dom_launch_failed'),
                        'execution_ms': int((time.perf_counter() - start) * 1000),
                        'metadata': {
                            'sandbox': sandbox,
                            'assistant_kind': assistant_kind,
                            'launch_mode': launch_mode,
                            'launch_target': launch_target,
                            'response_capture_mode': response_capture_mode,
                            'manual_pasteback_required': False,
                            'prepared_prompt': prompt_text,
                            'session_scope': session_scope,
                            'session_label': session_label,
                            'isolated_session': isolated_session,
                    **consultation_metadata,
                            'auto_capture_attempted': True,
                            'auto_capture_reason': str(captured.get('error_message') or 'browser_dom_launch_failed'),
                        },
                    }
            launched = False
            if dry_run:
                launched = True
            elif launch_mode == 'web_assisted':
                launched = bool(webbrowser.open(str(launch_target)))
            else:
                resolved = Path(launch_target)
                if os.name == 'nt' and resolved.exists():
                    os.startfile(str(resolved))  # type: ignore[attr-defined]
                    launched = True
                else:
                    subprocess.Popen([str(launch_target)], cwd=str(Path(card.metadata.get('workspace_root') or Path.cwd())))
                    launched = True
            if dry_run and browser_dom_capture:
                return {
                    'success': True,
                    'output_text': f'Sesion aislada de {card.title} lista en modo dry-run. Llevare la consulta a un chat especial del programa cuando permitas el lanzamiento real.',
                    'extracted_data': {'assistant_kind': assistant_kind, 'launch_target': launch_target, 'prompt_preview': prompt_preview},
                    'artifacts': [],
                    'error_message': '',
                    'execution_ms': int((time.perf_counter() - start) * 1000),
                    'metadata': {
                        'sandbox': sandbox,
                        'assistant_kind': assistant_kind,
                        'launch_mode': launch_mode,
                        'launch_target': launch_target,
                        'response_capture_mode': response_capture_mode,
                        'manual_pasteback_required': False,
                        'prepared_prompt': prompt_text,
                        'prompt_preview': prompt_preview,
                        'response_captured': False,
                        'launched': True,
                        'auto_capture_attempted': False,
                        'auto_capture_reason': 'dry_run_launch',
                        'response_capture_pending': True,
                        'session_scope': session_scope,
                        'session_label': session_label,
                        'isolated_session': isolated_session,
                    **consultation_metadata,
                    },
                }
            response_capture_pending = bool(launched and not direct_capture)
            if requires_manual_pasteback:
                output_text = f'Asistente externo {card.title} preparado. Copia el prompt redactado y devuelve la respuesta a IABV.'
            elif response_capture_mode in {'clipboard_capture', 'dom_capture', 'browser_dom'}:
                output_text = f'Asistente externo {card.title} preparado. IABV queda esperando capturar la respuesta automaticamente.'
            else:
                output_text = f'Asistente externo {card.title} preparado para continuar la consulta guiada.'
            return {
                'success': launched,
                'output_text': output_text,
                'extracted_data': {'assistant_kind': assistant_kind, 'launch_target': launch_target, 'prompt_preview': prompt_preview},
                'artifacts': [],
                'error_message': '' if launched else 'assistant_launch_failed',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': launch_mode,
                    'launch_target': launch_target,
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': requires_manual_pasteback,
                    'prepared_prompt': prompt_text,
                    'prompt_preview': prompt_preview,
                    'launched': launched,
                    'response_capture_pending': response_capture_pending,
                    'session_scope': session_scope,
                    'session_label': session_label,
                    'isolated_session': isolated_session,
                    **consultation_metadata,
                },
            }
        except Exception as exc:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {'assistant_kind': assistant_kind, 'launch_target': launch_target},
                'artifacts': [],
                'error_message': str(exc),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': launch_mode,
                    'launch_target': launch_target,
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': requires_manual_pasteback,
                    'prepared_prompt': prompt_text,
                    'session_scope': session_scope,
                    'session_label': session_label,
                    'isolated_session': isolated_session,
                    **consultation_metadata,
                },
            }

    def _capture_desktop_response(
        self,
        *,
        card: ToolCard,
        task: ToolTask,
        launch_target: str,
        launch_mode: str,
        prompt_text: str,
        reingest_only: bool = False,
    ) -> dict[str, Any]:
        workspace_root = str(task.metadata.get('workspace_root') or card.metadata.get('workspace_root') or Path.cwd())
        runner = self.runner_factory(workspace_root)
        session_state_path, session_rollouts_root = self._session_capture_paths(card=card, task=task, workspace_root=workspace_root)
        fallback_session_state_path, fallback_session_rollouts_root = self._fallback_session_capture_paths(card=card, task=task)
        return runner.capture_response_from_app(
            launch_target=launch_target,
            title_hints=self._title_hints(card=card, task=task),
            prompt_text=prompt_text,
            launch_mode=launch_mode,
            submit_after_paste=bool(task.metadata.get('submit_prompt_after_paste', card.metadata.get('submit_prompt_after_paste', True))) and not reingest_only,
            launch_wait_seconds=float(task.metadata.get('launch_wait_seconds') or card.metadata.get('launch_wait_seconds') or 1.2),
            window_wait_seconds=float(task.metadata.get('window_wait_seconds') or card.metadata.get('window_wait_seconds') or 8.0),
            response_wait_seconds=float(task.metadata.get('response_wait_seconds') or card.metadata.get('response_wait_seconds') or 4.0),
            clipboard_settle_seconds=float(task.metadata.get('clipboard_settle_seconds') or card.metadata.get('clipboard_settle_seconds') or 0.2),
            background_capture_mode=str(task.metadata.get('background_capture_mode') or card.metadata.get('background_capture_mode') or ''),
            session_state_path=session_state_path,
            session_rollouts_root=session_rollouts_root,
            fallback_session_state_path=fallback_session_state_path,
            fallback_session_rollouts_root=fallback_session_rollouts_root,
            response_match_markers=self._response_match_markers(task=task, prompt_text=prompt_text),
            thread_key=str(task.metadata.get('thread_key') or ''),
            thread_title=str(task.metadata.get('thread_title') or ''),
            launch_env=self._launch_env(card=card, task=task, workspace_root=workspace_root),
            browser_profile_dir=self._browser_profile_dir(card=card, task=task, workspace_root=workspace_root),
            browser_headless=bool(task.metadata.get('background_headless', card.metadata.get('background_headless', True))) and not bool(task.metadata.get('debug_visible_browser', card.metadata.get('debug_visible_browser', False))),
            input_selectors=self._selectors(card=card, task=task, key='input_selectors'),
            response_selectors=self._selectors(card=card, task=task, key='response_selectors'),
            submit_selectors=self._selectors(card=card, task=task, key='submit_selectors'),
            reingest_only=reingest_only,
        )


    def _response_match_markers(self, *, task: ToolTask, prompt_text: str) -> list[str]:
        strong_markers: list[str] = []
        prompt = str(prompt_text or '').strip()
        for candidate in (prompt, str(task.metadata.get('context_pack') or '').strip()):
            if not candidate:
                continue
            for label, pattern in (
                ('Pending issue', r'Pending issue:\s*([^\n]+)'),
                ('IABV_QUERY_ID', r'IABV_QUERY_ID:\s*([^\n]+)'),
                ('IABV_THREAD_KEY', r'IABV_THREAD_KEY:\s*([^\n]+)'),
                ('IABV_THREAD_TITLE', r'IABV_THREAD_TITLE:\s*([^\n]+)'),
                ('Sitio', r'Sitio:\s*([^\n]+)'),
            ):
                for match in re.finditer(pattern, candidate, re.IGNORECASE):
                    value = str(match.group(1) or '').strip()
                    if not value:
                        continue
                    for marker in (value, f'{label}: {value}'):
                        if marker not in strong_markers:
                            strong_markers.append(marker)
        if strong_markers:
            return strong_markers[:6]
        markers: list[str] = []
        objective_marker = str(task.objective or '').strip()
        if objective_marker:
            markers.append(objective_marker[:180])
        compact_prompt = ' '.join(prompt.split())[:220]
        if compact_prompt and compact_prompt not in markers:
            markers.append(compact_prompt)
        return markers[:6]



    def _consultation_runtime_metadata(self, *, card: ToolCard, task: ToolTask, capture_attempt_utc: str) -> dict[str, Any]:
        task_metadata = dict(task.metadata or {})
        return {
            'thread_key': str(task_metadata.get('thread_key') or ''),
            'thread_title': str(task_metadata.get('thread_title') or ''),
            'capture_lane': str(task_metadata.get('capture_lane') or ''),
            'lane_priority': list(task_metadata.get('lane_priority') or []),
            'awaiting_reason': str(task_metadata.get('awaiting_reason') or ''),
            'last_capture_attempt_utc': str(capture_attempt_utc or task_metadata.get('last_capture_attempt_utc') or ''),
            'reused_thread': bool(task_metadata.get('reused_thread', False)),
            'session_profile_dir': str(task_metadata.get('session_profile_dir') or ''),
            'session_scope': self._session_scope(card=card, task=task),
            'session_label': self._session_label(card=card, task=task),
        }

    def _session_capture_paths(self, *, card: ToolCard, task: ToolTask, workspace_root: str) -> tuple[str, str]:
        assistant_kind = str(task.metadata.get('assistant_kind') or card.metadata.get('assistant_kind') or '').strip().lower()
        background_capture_mode = str(task.metadata.get('background_capture_mode') or card.metadata.get('background_capture_mode') or '').strip().lower()
        if assistant_kind == 'codex' and background_capture_mode == 'codex_rollout':
            codex_home = self._isolated_codex_home(workspace_root)
            return str(codex_home / 'state_5.sqlite'), str(codex_home / 'sessions')
        return (
            str(task.metadata.get('session_state_path') or card.metadata.get('session_state_path') or ''),
            str(task.metadata.get('session_rollouts_root') or card.metadata.get('session_rollouts_root') or ''),
        )


    def _fallback_session_capture_paths(self, *, card: ToolCard, task: ToolTask) -> tuple[str, str]:
        return (
            str(task.metadata.get('session_state_path') or card.metadata.get('session_state_path') or ''),
            str(task.metadata.get('session_rollouts_root') or card.metadata.get('session_rollouts_root') or ''),
        )

    def _launch_env(self, *, card: ToolCard, task: ToolTask, workspace_root: str) -> dict[str, str]:
        assistant_kind = str(task.metadata.get('assistant_kind') or card.metadata.get('assistant_kind') or '').strip().lower()
        background_capture_mode = str(task.metadata.get('background_capture_mode') or card.metadata.get('background_capture_mode') or '').strip().lower()
        if assistant_kind == 'codex' and background_capture_mode == 'codex_rollout':
            codex_home = self._isolated_codex_home(workspace_root)
            return {'CODEX_HOME': str(codex_home)}
        return {}

    def _isolated_codex_home(self, workspace_root: str) -> Path:
        codex_home = Path(workspace_root) / 'data' / 'tool_teaching' / 'external_assistants' / 'codex_home'
        (codex_home / 'sessions').mkdir(parents=True, exist_ok=True)
        return codex_home

    def _browser_profile_dir(self, *, card: ToolCard, task: ToolTask, workspace_root: str) -> str:
        background_capture_mode = str(task.metadata.get('background_capture_mode') or card.metadata.get('background_capture_mode') or '').strip().lower()
        if background_capture_mode != 'browser_dom':
            return str(task.metadata.get('browser_profile_dir') or card.metadata.get('browser_profile_dir') or '')
        assistant_kind = str(task.metadata.get('assistant_kind') or card.metadata.get('assistant_kind') or card.tool_id).strip().lower() or card.tool_id
        profile_root = Path(workspace_root) / 'data' / 'tool_teaching' / 'external_assistants' / f'{assistant_kind}_program_session' / 'browser_profile'
        profile_root.mkdir(parents=True, exist_ok=True)
        return str(profile_root)

    def _session_scope(self, *, card: ToolCard, task: ToolTask) -> str:
        return str(task.metadata.get('session_scope') or card.metadata.get('session_scope') or 'external_assistant').strip() or 'external_assistant'

    def _session_label(self, *, card: ToolCard, task: ToolTask) -> str:
        return str(task.metadata.get('session_label') or card.metadata.get('session_label') or card.title).strip() or card.title

    def _selectors(self, *, card: ToolCard, task: ToolTask, key: str) -> list[str]:
        values: list[str] = []
        for source in (task.metadata.get(key) or [], card.metadata.get(key) or []):
            items = source if isinstance(source, (list, tuple)) else [source]
            for item in items:
                value = str(item or '').strip()
                if value and value not in values:
                    values.append(value)
        return values

    def _title_hints(self, *, card: ToolCard, task: ToolTask) -> list[str]:
        hints: list[str] = []
        for item in task.metadata.get('window_title_hints') or []:
            value = str(item or '').strip()
            if value and value not in hints:
                hints.append(value)
        for item in card.metadata.get('window_title_hints') or []:
            value = str(item or '').strip()
            if value and value not in hints:
                hints.append(value)
        for item in (
            str(task.metadata.get('window_title') or '').strip(),
            str(card.metadata.get('window_title') or '').strip(),
            str(card.title or '').strip(),
            str(card.metadata.get('assistant_kind') or '').strip().title(),
        ):
            if item and item not in hints:
                hints.append(item)
        return hints

    def _resolve_launch_target(self, card: ToolCard) -> str:
        explicit_path = str(card.metadata.get('executable_path') or '').strip()
        if explicit_path and self._path_exists(explicit_path):
            return explicit_path
        command_candidates: list[str] = []
        command_name = str(card.metadata.get('command_name') or '').strip()
        if command_name:
            command_candidates.append(command_name)
        for alias in card.metadata.get('command_aliases') or []:
            probe = str(alias or '').strip()
            if probe:
                command_candidates.append(probe)
        for candidate_name in command_candidates:
            resolved = shutil.which(candidate_name)
            if resolved:
                return candidate_name if self._is_protected_windowsapps_path(resolved) else resolved
        for candidate in card.metadata.get('windows_default_paths') or []:
            for resolved_candidate in self._expand_candidate_paths(str(candidate)):
                if resolved_candidate and self._path_exists(resolved_candidate):
                    return resolved_candidate
        return ''

    def _expand_candidate_paths(self, candidate: str) -> list[str]:
        replacements = {
            '{localappdata}': os.environ.get('LOCALAPPDATA', ''),
            '{programfiles}': os.environ.get('ProgramFiles', ''),
            '{programfilesx86}': os.environ.get('ProgramFiles(x86)', ''),
            '{userprofile}': os.environ.get('USERPROFILE', ''),
        }
        expanded = candidate
        for token, value in replacements.items():
            expanded = expanded.replace(token, value)
        if os.sep != '\\':
            expanded = expanded.replace('\\', os.sep)
        if any(token in expanded for token in ('*', '?', '[')):
            return [str(Path(item)) for item in glob.glob(expanded, recursive=True)]
        return [expanded]

    def _path_exists(self, candidate: str) -> bool:
        try:
            return Path(candidate).exists()
        except OSError:
            lowered = str(candidate).lower().replace('/', '\\')
            if '\\windowsapps\\' in lowered and lowered.endswith('.exe'):
                return True
            return False

    def _is_protected_windowsapps_path(self, candidate: str) -> bool:
        lowered = str(candidate or '').lower().replace('/', '\\')
        return '\\program files\\windowsapps\\' in lowered

class PlaywrightToolAdapter:
    tool_type = ToolType.BROWSER

    def __init__(self, controller: BrowserSessionController | None = None) -> None:
        self.controller = controller or BrowserSessionController(headless=True)

    def is_available(self, card: ToolCard) -> bool:
        return sync_playwright is not None

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        artifacts: list[str] = []
        extracted: dict[str, Any] = {}
        output_chunks: list[str] = []
        page_created = False
        try:
            if self.controller.page is None:
                self.controller.start()
                page_created = True
            page = self.controller.page or self.controller.new_page()
            actions = BrowserActionService(page)
            if sandbox and not task.actions:
                output_chunks.append('Sandbox Playwright listo.')
            for action in task.actions:
                if action.action_type == ToolActionType.OPEN_URL:
                    actions.goto(action.target or str(action.parameters.get('url') or ''))
                    output_chunks.append(f'open_url:{action.target or action.parameters.get("url") or ""}')
                elif action.action_type == ToolActionType.CLICK:
                    actions.click(action.target or str(action.parameters.get('selector') or ''))
                    output_chunks.append(f'click:{action.target or action.parameters.get("selector") or ""}')
                elif action.action_type == ToolActionType.TYPE_TEXT:
                    selector = action.target or str(action.parameters.get('selector') or '')
                    value = action.value or str(action.parameters.get('text') or '')
                    actions.type_text(selector, value)
                    output_chunks.append(f'type_text:{selector}')
                elif action.action_type == ToolActionType.EXTRACT_TEXT:
                    selector = action.target or str(action.parameters.get('selector') or '')
                    text = page.locator(selector).inner_text()
                    extracted[action.label or selector or action.action_id] = text
                    output_chunks.append(f'extract_text:{selector}')
                elif action.action_type == ToolActionType.SCREENSHOT:
                    path = str(action.parameters.get('path') or action.target or '')
                    if path:
                        artifacts.append(actions.screenshot(path))
                        output_chunks.append(f'screenshot:{path}')
            return {
                'success': True,
                'output_text': '\n'.join(output_chunks) or 'Playwright ejecuto la tarea.',
                'extracted_data': extracted,
                'artifacts': artifacts,
                'error_message': '',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'page_created': page_created},
            }
        except Exception as exc:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': extracted,
                'artifacts': artifacts,
                'error_message': str(exc),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox},
            }
        finally:
            if sandbox:
                try:
                    self.controller.close()
                except Exception:
                    pass


class AiderToolAdapter:
    tool_type = ToolType.CODE_EDITOR

    def is_available(self, card: ToolCard) -> bool:
        return shutil.which('aider') is not None

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            if sandbox:
                completed = subprocess.run(['aider', '--version'], capture_output=True, text=True, check=False)
            else:
                prompt = next((action.value for action in task.actions if action.value), task.objective)
                completed = subprocess.run(
                    ['aider', '--no-auto-commits', '--message', prompt],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=str(Path(card.metadata.get('workspace_root') or Path.cwd())),
                )
            success = completed.returncode == 0
            return {
                'success': success,
                'output_text': (completed.stdout or completed.stderr).strip(),
                'extracted_data': {},
                'artifacts': [],
                'error_message': '' if success else (completed.stderr or completed.stdout).strip(),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'returncode': completed.returncode},
            }
        except Exception as exc:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': str(exc),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox},
            }


class MCPToolAdapter:
    tool_type = ToolType.MCP_CLIENT

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def is_available(self, card: ToolCard) -> bool:
        return bool(card.metadata.get('server_url'))

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        server_url = str(card.metadata.get('server_url') or '')
        if not server_url:
            return {'success': False, 'output_text': '', 'extracted_data': {}, 'artifacts': [], 'error_message': 'MCP server_url no configurado.', 'execution_ms': 0, 'metadata': {'sandbox': sandbox}}
        if httpx is None:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': 'httpx_unavailable',
                'execution_ms': 0,
                'metadata': {'sandbox': sandbox, 'dependency_status': 'httpx_missing'},
            }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                if sandbox:
                    response = client.get(server_url.rstrip('/') + '/health')
                else:
                    payload = {'goal': task.objective, 'actions': [action.model_dump(mode='json') for action in task.actions]}
                    response = client.post(server_url.rstrip('/') + '/tool', json=payload)
            success = response.is_success
            body = response.text
            return {
                'success': success,
                'output_text': body,
                'extracted_data': {'status_code': response.status_code},
                'artifacts': [],
                'error_message': '' if success else body,
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'status_code': response.status_code},
            }
        except Exception as exc:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': str(exc),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox},
            }


class OllamaToolAdapter:
    tool_type = ToolType.LLM_LOCAL

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def is_available(self, card: ToolCard) -> bool:
        health = self.provider.health_check()
        return bool(health.available)

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        prompt_text = next(
            (
                str(action.value).strip()
                for action in task.actions
                if action.action_type == ToolActionType.LLM_QUERY and str(action.value or '').strip()
            ),
            str(task.metadata.get('context_pack') or task.objective),
        )
        consultation_scope = str(task.metadata.get('consultation_scope') or '').strip().lower()
        assistant_kind = str(task.metadata.get('assistant_kind') or card.metadata.get('assistant_kind') or 'ollama').strip().lower() or 'ollama'
        response_capture_mode = str(
            task.metadata.get('response_capture_mode') or card.metadata.get('response_capture_mode') or 'tool_result'
        ).strip().lower() or 'tool_result'
        try:
            request = InferenceRequest(
                user_goal=task.objective,
                prompt=prompt_text,
                task_role=task.requested_by_role,
                offline_only=True,
                metadata={
                    'tool_id': card.tool_id,
                    'sandbox': sandbox,
                    'consultation_scope': consultation_scope,
                    'assistant_kind': assistant_kind,
                },
            )
            result = self.provider.answer_user(request)
            return {
                'success': True,
                'output_text': result.summary,
                'extracted_data': {'provider': result.provider_name, 'report_kind': result.report_kind.value},
                'artifacts': [],
                'error_message': '',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': str(card.metadata.get('launch_mode') or 'local_provider'),
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': False,
                    'prepared_prompt': prompt_text,
                    'response_captured': bool(str(result.summary or '').strip()),
                    'launched': False,
                    'consultation_scope': consultation_scope,
                },
            }
        except Exception as exc:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': str(exc),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {
                    'sandbox': sandbox,
                    'assistant_kind': assistant_kind,
                    'launch_mode': str(card.metadata.get('launch_mode') or 'local_provider'),
                    'response_capture_mode': response_capture_mode,
                    'manual_pasteback_required': False,
                    'prepared_prompt': prompt_text,
                    'consultation_scope': consultation_scope,
                },
            }


class ShellToolAdapter:
    tool_type = ToolType.SHELL
    BLOCKED_TOKENS = ('rm ', ' del ', 'remove-item', 'format ', 'shutdown', 'reboot', 'mkfs', 'git reset --hard')

    def is_available(self, card: ToolCard) -> bool:
        return True

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        command = next((action.value or action.target for action in task.actions if action.action_type == ToolActionType.RUN_COMMAND), '')
        if not command:
            command = str(task.metadata.get('command') or '')
        lowered = f' {command.lower()} '
        if any(token in lowered for token in self.BLOCKED_TOKENS):
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': 'Comando bloqueado por politica de seguridad.',
                'execution_ms': 0,
                'metadata': {'sandbox': sandbox, 'blocked': True},
            }
        try:
            completed = subprocess.run(command, capture_output=True, text=True, shell=True, check=False)
            success = completed.returncode == 0
            return {
                'success': success,
                'output_text': (completed.stdout or '').strip(),
                'extracted_data': {'stderr': (completed.stderr or '').strip(), 'returncode': completed.returncode},
                'artifacts': [],
                'error_message': '' if success else (completed.stderr or completed.stdout).strip(),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'command': command},
            }
        except Exception as exc:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': str(exc),
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'command': command},
            }


class DesktopHumanToolAdapter:
    tool_type = ToolType.CUSTOM

    def __init__(self, workspace_root: str) -> None:
        self.runner = UIExecutionRunner(workspace_root)

    def is_available(self, card: ToolCard) -> bool:
        return self.runner.is_available()

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        return self.runner.run(card, task, sandbox=sandbox)


class ExternalAssistantToolAdapter(ToolAdapter):
    tool_type = ToolType.CUSTOM


class DevinApiToolAdapter:
    """Adapter REST para Devin (Cognition AI) via API v1.

    Crea una sesion remota con el prompt del task, hace polling hasta que
    la sesion termine o se agote el timeout, y retorna el resultado en el
    formato estandar de adapters.  No es otro cerebro: el
    ``ToolTeachService`` decide cuando usarlo.

    Endpoints reales de la API (v1):
      POST https://api.devin.ai/v1/sessions        -> crear sesion
      GET  https://api.devin.ai/v1/session/{id}    -> poll estado

    El Bearer token identifica la organizacion; ``org_id`` se conserva
    solo por compatibilidad con el constructor previo pero no se usa en
    las llamadas reales.
    """

    tool_type = ToolType.MCP_CLIENT
    BASE_URL = 'https://api.devin.ai/v1'

    def __init__(
        self,
        api_key: str = '',
        org_id: str = '',
        timeout_seconds: float = 120.0,
        poll_interval_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.org_id = org_id  # kept for backwards compat; unused in v1 API.
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    @property
    def _sessions_url(self) -> str:
        return f'{self.BASE_URL}/sessions'

    def _session_detail_url(self, session_id: str) -> str:
        return f'{self.BASE_URL}/session/{session_id}'

    def _headers(self) -> dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def is_available(self, card: ToolCard) -> bool:
        if not self.api_key:
            return False
        if httpx is None:
            return False
        try:
            resp = httpx.get(
                self._sessions_url,
                headers=self._headers(),
                params={'limit': '1'},
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        if httpx is None:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': 'httpx no esta instalado.',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'tool_id': card.tool_id},
            }
        if not self.api_key:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': 'DEVIN_API_KEY no configurado.',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox, 'tool_id': card.tool_id},
            }

        context_pack = str(task.metadata.get('context_pack') or '') if task.metadata else ''
        prompt = str(task.objective or '')
        if context_pack:
            prompt = f'{prompt}\n\n--- context ---\n{context_pack}'

        session_id = ''
        session_url = ''
        session_status = ''
        structured_output = ''
        error_message = ''
        try:
            create_resp = httpx.post(
                self._sessions_url,
                headers=self._headers(),
                json={'prompt': prompt},
                timeout=30.0,
            )
            if create_resp.status_code not in (200, 201):
                error_message = f'Devin API create session HTTP {create_resp.status_code}: {create_resp.text[:500]}'
                return {
                    'success': False,
                    'output_text': '',
                    'extracted_data': {},
                    'artifacts': [],
                    'error_message': error_message,
                    'execution_ms': int((time.perf_counter() - start) * 1000),
                    'metadata': {'sandbox': sandbox, 'tool_id': card.tool_id},
                }
            body = create_resp.json()
            session_id = str(body.get('session_id') or body.get('id') or '')
            session_url = str(body.get('url') or body.get('session_url') or '')
            if not session_url and session_id:
                session_url = f'https://app.devin.ai/sessions/{session_id}'

            deadline = time.perf_counter() + self.timeout_seconds
            session_status = str(body.get('status') or 'running')
            while session_status == 'running' and time.perf_counter() < deadline:
                time.sleep(self.poll_interval_seconds)
                poll_resp = httpx.get(
                    self._session_detail_url(session_id),
                    headers=self._headers(),
                    timeout=15.0,
                )
                if poll_resp.status_code == 200:
                    poll_body = poll_resp.json()
                    session_status = str(poll_body.get('status') or 'running')
                    structured_output = str(
                        poll_body.get('structured_output')
                        or poll_body.get('result')
                        or poll_body.get('output')
                        or ''
                    )
                else:
                    error_message = f'Devin API poll HTTP {poll_resp.status_code}'
                    break
        except Exception as exc:
            error_message = f'{type(exc).__name__}: {exc}'

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            'success': session_status == 'finished',
            'output_text': structured_output or '',
            'extracted_data': {'session_id': session_id, 'session_url': session_url},
            'artifacts': [],
            'error_message': error_message or '',
            'execution_ms': elapsed_ms,
            'metadata': {
                'sandbox': sandbox,
                'tool_id': card.tool_id,
                'devin_session_status': session_status,
            },
        }


class GitHubApiToolAdapter:
    """Adapter REST para la API de GitHub, scoped a un repo concreto.

    Permite que IABV opere sobre un repo sin que el humano tenga que salir
    del programa: crear PRs, habilitar auto-merge, mergear, leer PRs,
    comentar issues, listar issues.  El token va como ``Bearer`` (acepta
    tanto classic PAT como fine-grained PAT).

    No es otro cerebro: la ruta se decide antes (ToolTeachService,
    AutonomyGovernancePolicy).  Este adapter solo ejecuta la accion
    declarada por el ``ToolTask``.

    Accion solicitada via ``task.metadata['github_action']``.  Parametros
    en ``task.metadata['github_params']`` (dict).  Acciones soportadas:

      * ``read_pr``           params: {pull_number}
      * ``create_pr``         params: {title, body, head, base}
      * ``merge_pr``          params: {pull_number, merge_method?}
      * ``enable_auto_merge`` params: {pull_number, merge_method?}
      * ``comment_issue``     params: {issue_number, body}
      * ``list_issues``       params: {state?}
      * ``list_prs``          params: {state?}

    Con ``sandbox=True`` el adapter NO toca la red: devuelve el plan
    (endpoint, metodo, payload) sin ejecutarlo, para que sandbox /
    AutonomousValidationCycle puedan evaluarlo antes.
    """

    tool_type = ToolType.MCP_CLIENT
    BASE_URL = 'https://api.github.com'
    GRAPHQL_URL = 'https://api.github.com/graphql'

    SUPPORTED_ACTIONS = frozenset(
        {
            'read_pr',
            'create_pr',
            'merge_pr',
            'enable_auto_merge',
            'comment_issue',
            'list_issues',
            'list_prs',
        }
    )

    def __init__(
        self,
        token: str = '',
        repo: str = '',
        timeout_seconds: float = 30.0,
    ) -> None:
        self.token = token
        self.repo = repo  # formato "owner/name", p.ej. "jhonf463r/Python"
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }

    def is_available(self, card: ToolCard) -> bool:
        if not self.token or not self.repo:
            return False
        if httpx is None:
            return False
        try:
            # Ping liviano: metadata del repo autenticada.  Si el token no
            # tiene scope a este repo, GitHub devuelve 404 (no 401) aunque
            # el token sea valido; es la unica forma de detectar falta de
            # scope a nivel fino-grained.
            resp = httpx.get(
                f'{self.BASE_URL}/repos/{self.repo}',
                headers=self._headers(),
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _plan(self, action: str, method: str, url: str, payload: Any = None) -> dict[str, Any]:
        plan: dict[str, Any] = {'action': action, 'method': method, 'url': url}
        if payload is not None:
            plan['payload'] = payload
        return plan

    def _response(
        self,
        *,
        success: bool,
        output_text: str,
        extracted_data: dict[str, Any],
        sandbox: bool,
        tool_id: str,
        start: float,
        error_message: str = '',
        http_status: int | None = None,
        action: str = '',
    ) -> dict[str, Any]:
        return {
            'success': success,
            'output_text': output_text,
            'extracted_data': extracted_data,
            'artifacts': [],
            'error_message': error_message,
            'execution_ms': int((time.perf_counter() - start) * 1000),
            'metadata': {
                'sandbox': sandbox,
                'tool_id': tool_id,
                'github_action': action,
                'github_http_status': http_status,
            },
        }

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            return self._run_action(card, task, sandbox=sandbox, start=start)
        except Exception as exc:  # noqa: BLE001
            return self._response(
                success=False,
                output_text='',
                extracted_data={},
                sandbox=sandbox,
                tool_id=card.tool_id,
                start=start,
                error_message=f'{type(exc).__name__}: {exc}',
            )

    def _run_action(
        self,
        card: ToolCard,
        task: ToolTask,
        *,
        sandbox: bool,
        start: float,
    ) -> dict[str, Any]:
        if httpx is None:
            return self._response(
                success=False,
                output_text='',
                extracted_data={},
                sandbox=sandbox,
                tool_id=card.tool_id,
                start=start,
                error_message='httpx no esta instalado.',
            )
        if not self.token or not self.repo:
            return self._response(
                success=False,
                output_text='',
                extracted_data={},
                sandbox=sandbox,
                tool_id=card.tool_id,
                start=start,
                error_message=(
                    'GitHub token o GITHUB_REPO no configurados. '
                    'Exporta GITHUB_TOKEN_IABV (preferido) o, en su '
                    'defecto, IABV_GITHUB_TOKEN / GITHUB_TOKEN / GH_TOKEN.'
                ),
            )

        metadata = task.metadata or {}
        action = str(metadata.get('github_action') or '').strip()
        params = metadata.get('github_params') or {}
        if not isinstance(params, dict):
            params = {}

        if action not in self.SUPPORTED_ACTIONS:
            return self._response(
                success=False,
                output_text='',
                extracted_data={},
                sandbox=sandbox,
                tool_id=card.tool_id,
                start=start,
                error_message=(
                    f"github_action '{action}' no soportado. "
                    f'Soportados: {sorted(self.SUPPORTED_ACTIONS)}.'
                ),
                action=action,
            )

        repo_url = f'{self.BASE_URL}/repos/{self.repo}'

        # --- read_pr -----------------------------------------------------
        if action == 'read_pr':
            pn = params.get('pull_number')
            if not isinstance(pn, int):
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=sandbox, tool_id=card.tool_id, start=start,
                    error_message='read_pr requiere pull_number (int).',
                    action=action,
                )
            url = f'{repo_url}/pulls/{pn}'
            if sandbox:
                return self._response(
                    success=True, output_text='dry-run: read_pr',
                    extracted_data={'plan': self._plan(action, 'GET', url)},
                    sandbox=True, tool_id=card.tool_id, start=start,
                    action=action,
                )
            resp = httpx.get(url, headers=self._headers(), timeout=self.timeout_seconds)
            data = resp.json() if resp.status_code == 200 else {}
            return self._response(
                success=resp.status_code == 200,
                output_text=str(data.get('title', '')),
                extracted_data=data,
                sandbox=False, tool_id=card.tool_id, start=start,
                http_status=resp.status_code,
                error_message='' if resp.status_code == 200 else f'HTTP {resp.status_code}: {resp.text[:500]}',
                action=action,
            )

        # --- create_pr ---------------------------------------------------
        if action == 'create_pr':
            missing = [k for k in ('title', 'head', 'base') if not params.get(k)]
            if missing:
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=sandbox, tool_id=card.tool_id, start=start,
                    error_message=f'create_pr falta: {missing}',
                    action=action,
                )
            payload = {
                'title': str(params['title']),
                'head': str(params['head']),
                'base': str(params['base']),
                'body': str(params.get('body') or ''),
            }
            url = f'{repo_url}/pulls'
            if sandbox:
                return self._response(
                    success=True, output_text='dry-run: create_pr',
                    extracted_data={'plan': self._plan(action, 'POST', url, payload)},
                    sandbox=True, tool_id=card.tool_id, start=start,
                    action=action,
                )
            resp = httpx.post(url, headers=self._headers(), json=payload, timeout=self.timeout_seconds)
            data = resp.json() if resp.status_code in (200, 201) else {}
            return self._response(
                success=resp.status_code in (200, 201),
                output_text=str(data.get('html_url', '')),
                extracted_data=data,
                sandbox=False, tool_id=card.tool_id, start=start,
                http_status=resp.status_code,
                error_message='' if resp.status_code in (200, 201) else f'HTTP {resp.status_code}: {resp.text[:500]}',
                action=action,
            )

        # --- merge_pr ----------------------------------------------------
        if action == 'merge_pr':
            pn = params.get('pull_number')
            if not isinstance(pn, int):
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=sandbox, tool_id=card.tool_id, start=start,
                    error_message='merge_pr requiere pull_number (int).',
                    action=action,
                )
            merge_method = str(params.get('merge_method') or 'squash').lower()
            if merge_method not in ('merge', 'squash', 'rebase'):
                merge_method = 'squash'
            payload = {'merge_method': merge_method}
            url = f'{repo_url}/pulls/{pn}/merge'
            if sandbox:
                return self._response(
                    success=True, output_text='dry-run: merge_pr',
                    extracted_data={'plan': self._plan(action, 'PUT', url, payload)},
                    sandbox=True, tool_id=card.tool_id, start=start,
                    action=action,
                )
            resp = httpx.put(url, headers=self._headers(), json=payload, timeout=self.timeout_seconds)
            data = resp.json() if resp.status_code == 200 else {}
            merged = resp.status_code == 200 and bool(data.get('merged'))
            if resp.status_code != 200:
                err_msg = f'HTTP {resp.status_code}: {resp.text[:500]}'
            elif not data.get('merged'):
                err_msg = (
                    f"merge_pr devolvio HTTP 200 pero merged={data.get('merged')!r}"
                    f" (mensaje GitHub: {str(data.get('message') or '')[:200]})"
                )
            else:
                err_msg = ''
            return self._response(
                success=merged,
                output_text=str(data.get('sha', '')),
                extracted_data=data,
                sandbox=False, tool_id=card.tool_id, start=start,
                http_status=resp.status_code,
                error_message=err_msg,
                action=action,
            )

        # --- enable_auto_merge (GraphQL) --------------------------------
        if action == 'enable_auto_merge':
            pn = params.get('pull_number')
            if not isinstance(pn, int):
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=sandbox, tool_id=card.tool_id, start=start,
                    error_message='enable_auto_merge requiere pull_number (int).',
                    action=action,
                )
            merge_method = str(params.get('merge_method') or 'squash').upper()
            if merge_method not in ('MERGE', 'SQUASH', 'REBASE'):
                merge_method = 'SQUASH'
            # Paso 1: obtener node_id del PR (GraphQL necesita ids, no numeros).
            rest_url = f'{repo_url}/pulls/{pn}'
            if sandbox:
                return self._response(
                    success=True, output_text='dry-run: enable_auto_merge',
                    extracted_data={
                        'plan': self._plan(
                            action, 'POST', self.GRAPHQL_URL,
                            {'pull_number': pn, 'merge_method': merge_method},
                        ),
                    },
                    sandbox=True, tool_id=card.tool_id, start=start,
                    action=action,
                )
            pr_resp = httpx.get(rest_url, headers=self._headers(), timeout=self.timeout_seconds)
            if pr_resp.status_code != 200:
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=False, tool_id=card.tool_id, start=start,
                    http_status=pr_resp.status_code,
                    error_message=f'enable_auto_merge lookup HTTP {pr_resp.status_code}: {pr_resp.text[:500]}',
                    action=action,
                )
            node_id = str(pr_resp.json().get('node_id') or '')
            if not node_id:
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=False, tool_id=card.tool_id, start=start,
                    error_message='PR sin node_id (respuesta GitHub inesperada).',
                    action=action,
                )
            query = (
                'mutation($id:ID!,$m:PullRequestMergeMethod!){'
                'enablePullRequestAutoMerge(input:{pullRequestId:$id,mergeMethod:$m}){'
                'pullRequest{number autoMergeRequest{enabledAt mergeMethod}}}}'
            )
            gql_body = {
                'query': query,
                'variables': {'id': node_id, 'm': merge_method},
            }
            gql_resp = httpx.post(
                self.GRAPHQL_URL, headers=self._headers(), json=gql_body,
                timeout=self.timeout_seconds,
            )
            gql_data = gql_resp.json() if gql_resp.status_code == 200 else {}
            errors = gql_data.get('errors') or []
            ok = gql_resp.status_code == 200 and not errors
            return self._response(
                success=ok,
                output_text=f'auto-merge enabled on PR #{pn}' if ok else '',
                extracted_data=gql_data,
                sandbox=False, tool_id=card.tool_id, start=start,
                http_status=gql_resp.status_code,
                error_message='' if ok else f'GraphQL errors: {errors or gql_resp.text[:500]}',
                action=action,
            )

        # --- comment_issue ----------------------------------------------
        if action == 'comment_issue':
            ino = params.get('issue_number')
            body = params.get('body')
            if not isinstance(ino, int) or not body:
                return self._response(
                    success=False, output_text='', extracted_data={},
                    sandbox=sandbox, tool_id=card.tool_id, start=start,
                    error_message='comment_issue requiere issue_number (int) y body (str).',
                    action=action,
                )
            payload = {'body': str(body)}
            url = f'{repo_url}/issues/{ino}/comments'
            if sandbox:
                return self._response(
                    success=True, output_text='dry-run: comment_issue',
                    extracted_data={'plan': self._plan(action, 'POST', url, payload)},
                    sandbox=True, tool_id=card.tool_id, start=start,
                    action=action,
                )
            resp = httpx.post(url, headers=self._headers(), json=payload, timeout=self.timeout_seconds)
            data = resp.json() if resp.status_code == 201 else {}
            return self._response(
                success=resp.status_code == 201,
                output_text=str(data.get('html_url', '')),
                extracted_data=data,
                sandbox=False, tool_id=card.tool_id, start=start,
                http_status=resp.status_code,
                error_message='' if resp.status_code == 201 else f'HTTP {resp.status_code}: {resp.text[:500]}',
                action=action,
            )

        # --- list_issues / list_prs -------------------------------------
        if action in ('list_issues', 'list_prs'):
            state = str(params.get('state') or 'open')
            if state not in ('open', 'closed', 'all'):
                state = 'open'
            suffix = 'issues' if action == 'list_issues' else 'pulls'
            url = f'{repo_url}/{suffix}'
            if sandbox:
                return self._response(
                    success=True, output_text=f'dry-run: {action}',
                    extracted_data={'plan': self._plan(action, 'GET', url, {'state': state})},
                    sandbox=True, tool_id=card.tool_id, start=start,
                    action=action,
                )
            resp = httpx.get(
                url, headers=self._headers(),
                params={'state': state, 'per_page': 50},
                timeout=self.timeout_seconds,
            )
            items = resp.json() if resp.status_code == 200 else []
            if not isinstance(items, list):
                items = []
            return self._response(
                success=resp.status_code == 200,
                output_text=f'{len(items)} {suffix}',
                extracted_data={'items': items, 'count': len(items)},
                sandbox=False, tool_id=card.tool_id, start=start,
                http_status=resp.status_code,
                error_message='' if resp.status_code == 200 else f'HTTP {resp.status_code}: {resp.text[:500]}',
                action=action,
            )

        # Should be unreachable (SUPPORTED_ACTIONS gate above).
        return self._response(  # pragma: no cover
            success=False, output_text='', extracted_data={},
            sandbox=sandbox, tool_id=card.tool_id, start=start,
            error_message=f'accion no enrutada: {action}', action=action,
        )


class SiteExplorerToolAdapter:
    """Adapter delgado sobre `SiteExplorationService`.

    No toma decisiones de ruta: parsea la primera accion `open_url` del
    `ToolTask` como punto de partida, lee `max_pages` y `priority_keywords`
    de `parameters`, corre la exploracion y persiste el manual. El
    `ToolCallingBridge` puede invocarlo desde el chat local sin pasar por
    governance externa; igual respeta `requires_human_approval=True` a
    nivel ToolCard.
    """

    tool_type = ToolType.BROWSER

    def __init__(self, service: Any, repository: Any) -> None:
        self.service = service
        self.repository = repository

    def is_available(self, card: ToolCard) -> bool:
        checker = getattr(self.service, 'is_available', None)
        return bool(checker()) if callable(checker) else True

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        start_url = ''
        max_pages: int | None = None
        priority_keywords: list[str] = []
        for action in task.actions:
            if action.action_type == ToolActionType.OPEN_URL:
                start_url = action.target or str(action.parameters.get('url') or '')
                max_pages_raw = action.parameters.get('max_pages')
                if isinstance(max_pages_raw, int) and max_pages_raw > 0:
                    max_pages = max_pages_raw
                elif isinstance(max_pages_raw, str) and max_pages_raw.strip().isdigit():
                    max_pages = int(max_pages_raw.strip())
                raw_keywords = action.parameters.get('priority_keywords')
                if isinstance(raw_keywords, (list, tuple)):
                    priority_keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
                break
        if not start_url:
            # fallback solo si el objective parece una URL absoluta; evita
            # que descripciones humanas se interpreten como target.
            candidate = str(task.objective or '').strip()
            if candidate.startswith(('http://', 'https://')):
                start_url = candidate
        if not start_url:
            return {
                'success': False,
                'output_text': '',
                'extracted_data': {},
                'artifacts': [],
                'error_message': 'SiteExplorer requiere una accion OPEN_URL con url valida.',
                'execution_ms': int((time.perf_counter() - start) * 1000),
                'metadata': {'sandbox': sandbox},
            }
        result = self.service.explore(
            start_url=start_url,
            max_pages=max_pages,
            priority_keywords=priority_keywords,
        )
        artifacts: list[str] = []
        manual_payload = result.to_manual()
        if result.success and self.repository is not None:
            try:
                json_path, md_path = self.repository.save(manual_payload)
                artifacts.extend([str(json_path), str(md_path)])
            except Exception as exc:  # noqa: BLE001
                return {
                    'success': False,
                    'output_text': '',
                    'extracted_data': manual_payload,
                    'artifacts': artifacts,
                    'error_message': f'No se pudo persistir el manual: {type(exc).__name__}: {exc}',
                    'execution_ms': int((time.perf_counter() - start) * 1000),
                    'metadata': {'sandbox': sandbox, 'hostname': result.hostname},
                }
        summary_text = (
            f'Explore {result.hostname}: {len(result.pages)} paginas visitadas.'
            if result.success
            else f'Exploracion de {result.hostname or start_url} fallo: {result.error_message}'
        )
        return {
            'success': result.success,
            'output_text': summary_text,
            'extracted_data': manual_payload,
            'artifacts': artifacts,
            'error_message': result.error_message,
            'execution_ms': int((time.perf_counter() - start) * 1000),
            'metadata': {
                'sandbox': sandbox,
                'hostname': result.hostname,
                'pages_visited': len(result.pages),
            },
        }


class LocalCliToolAdapter:
    """Adapter read-only para CLIs locales (gh, cloudflared, git, winget).

    Complementa a ``ShellToolAdapter`` sin reemplazarlo: ese corre comandos
    libres con ``shell=True``; este conoce herramientas concretas, busca su
    ejecutable en PATH o rutas Windows tipicas, restringe los verbos permitidos
    y ejecuta con ``shell=False`` para no exponer inyeccion. Es la base que
    consume ``ToolRegistry`` para ``gh_cli``, ``cloudflared_cli``, ``git_cli``
    y ``winget_cli``.

    Contratos respetados:
    - No decide rutas: ``AutonomyGovernancePolicy`` sigue siendo el gate.
      ``requires_human_approval=True`` en la ``ToolCard`` mantiene cualquier
      operacion fuera del whitelist detras de ``ToolApprovalPolicy``.
    - No inventa observaciones: si el binario no existe, ``is_available``
      devuelve ``False`` y ``run`` corta antes del subprocess.
    - Read-only por diseno: ``card.metadata['allowed_verbs']`` declara los
      primeros tokens permitidos; ``BLOCKED_TOKENS`` bloquea tokens
      destructivos aunque aparezcan listados por error en ``allowed_verbs``.
    """

    tool_type = ToolType.SHELL

    # Failsafe sobre la allowlist declarada por cada tool: aunque un operador
    # agregue un verbo destructivo por error al ``allowed_verbs`` de una
    # ``ToolCard``, los patrones abajo lo bloquean antes del subprocess.
    # Alineado con ``ShellToolAdapter.BLOCKED_TOKENS`` para no dejar un bypass
    # en el adapter nuevo. Los patrones se chequean con padding de espacios.
    BLOCKED_TOKENS: tuple[str, ...] = (
        ' rm ',
        ' rm -rf',
        ' del ',
        ' remove-item ',
        ' format ',
        ' shutdown ',
        ' reboot ',
        ' mkfs ',
        ' reset --hard',
        ' push --force',
        ' push -f ',
        ' clean -fd',
    )

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def is_available(self, card: ToolCard) -> bool:
        return bool(self._resolve_executable(card))

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        executable = self._resolve_executable(card)
        if not executable:
            return self._fail(
                start,
                'executable_not_found',
                sandbox=sandbox,
                executable='',
                args='',
            )

        args_text = self._extract_args(task)
        if not args_text:
            # Version probe por default. Nunca inventa: si la ToolCard declara
            # otro ``version_command`` respeta esa intencion, sin caer a
            # verbos destructivos.
            args_text = str(card.metadata.get('version_command') or '--version').strip()

        allowed = [
            str(v).strip().lower()
            for v in (card.metadata.get('allowed_verbs') or [])
            if str(v or '').strip()
        ]
        first_token = args_text.strip().split()[0].lower() if args_text.strip() else ''
        if allowed and first_token not in allowed:
            return self._fail(
                start,
                f"verb '{first_token}' no esta en allowed_verbs {allowed}",
                sandbox=sandbox,
                executable=executable,
                args=args_text,
                blocked=True,
            )

        padded = f' {args_text.lower()} '
        if any(token in padded for token in self.BLOCKED_TOKENS):
            return self._fail(
                start,
                'argumento bloqueado por politica read-only de LocalCliToolAdapter',
                sandbox=sandbox,
                executable=executable,
                args=args_text,
                blocked=True,
            )

        # shlex preserva comillas: ``log --format="%H %s"`` queda como
        # ``['log', '--format=%H %s']`` en lugar de mis-tokenizar. En Windows
        # respetamos quoting estilo cmd.exe (``posix=False``) para que rutas
        # con espacios no se rompan al llegar al subprocess.
        try:
            tokens = shlex.split(args_text, posix=(sys.platform != 'win32'))
        except ValueError as exc:
            return self._fail(
                start,
                f'args malformados: {exc}',
                sandbox=sandbox,
                executable=executable,
                args=args_text,
                blocked=True,
            )
        cmd_list = [executable, *tokens]
        try:
            completed = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return self._fail(
                start,
                f'timeout {self.timeout_seconds}s',
                sandbox=sandbox,
                executable=executable,
                args=args_text,
            )
        except (FileNotFoundError, OSError) as exc:
            return self._fail(
                start,
                f'{type(exc).__name__}: {exc}',
                sandbox=sandbox,
                executable=executable,
                args=args_text,
            )

        success = completed.returncode == 0
        stderr = (completed.stderr or '').strip()
        stdout = (completed.stdout or '').strip()
        return {
            'success': success,
            'output_text': stdout,
            'extracted_data': {
                'stderr': stderr,
                'returncode': completed.returncode,
                'args': args_text,
                'tool_id': card.tool_id,
            },
            'artifacts': [],
            'error_message': '' if success else (stderr or stdout),
            'execution_ms': int((time.perf_counter() - start) * 1000),
            'metadata': {
                'sandbox': sandbox,
                'executable': executable,
                'args': args_text,
                'blocked': False,
            },
        }

    def _extract_args(self, task: ToolTask) -> str:
        for action in task.actions:
            if action.action_type == ToolActionType.RUN_COMMAND:
                for source in (action.value, action.target):
                    candidate = str(source or '').strip()
                    if candidate:
                        return candidate
        return str(task.metadata.get('command_args') or '').strip()

    def _resolve_executable(self, card: ToolCard) -> str:
        explicit = str(card.metadata.get('executable_path') or '').strip()
        if explicit and self._path_exists(explicit):
            return explicit
        candidates: list[str] = []
        command_name = str(card.metadata.get('command_name') or '').strip()
        if command_name:
            candidates.append(command_name)
        for alias in card.metadata.get('command_aliases') or []:
            text = str(alias or '').strip()
            if text:
                candidates.append(text)
        for name in candidates:
            resolved = shutil.which(name)
            if resolved:
                return resolved
        for pattern in card.metadata.get('windows_default_paths') or []:
            for cand in self._expand_candidate_paths(str(pattern)):
                if cand and self._path_exists(cand):
                    return cand
        return ''

    def _expand_candidate_paths(self, candidate: str) -> list[str]:
        replacements = {
            '{localappdata}': os.environ.get('LOCALAPPDATA', ''),
            '{programfiles}': os.environ.get('ProgramFiles', ''),
            '{programfilesx86}': os.environ.get('ProgramFiles(x86)', ''),
            '{userprofile}': os.environ.get('USERPROFILE', ''),
        }
        expanded = candidate
        for token, value in replacements.items():
            expanded = expanded.replace(token, value)
        if os.sep != '\\':
            expanded = expanded.replace('\\', os.sep)
        if any(token in expanded for token in ('*', '?', '[')):
            return [str(Path(item)) for item in glob.glob(expanded, recursive=True)]
        return [expanded]

    def _path_exists(self, candidate: str) -> bool:
        try:
            return Path(candidate).exists()
        except OSError:
            return False

    def _fail(
        self,
        start: float,
        reason: str,
        *,
        sandbox: bool,
        executable: str,
        args: str,
        blocked: bool = False,
    ) -> dict[str, Any]:
        return {
            'success': False,
            'output_text': '',
            'extracted_data': {
                'args': args,
            },
            'artifacts': [],
            'error_message': reason,
            'execution_ms': int((time.perf_counter() - start) * 1000),
            'metadata': {
                'sandbox': sandbox,
                'executable': executable,
                'args': args,
                'blocked': blocked,
            },
        }
