from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    AppConfig,
    CodexAcceptanceCriteria,
    CodexContextPack,
    CodexFileScope,
    CodexPendingIssue,
    CodexTaskSpec,
    CodexTestPlan,
    DecisionContext,
    DiagnosticCategory,
    ExternalStateFlag,
    EvaluationRoute,
    ExperimentDomain,
    IATraceEntry,
    IncidentQuery,
    canonical_external_state_flags,
)
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


_LIVE_AUDIT_SUMMARY_PATTERN = re.compile(
    r"Decision:\s*[\w\-]+\.\s*Confianza\s+\d+\.\d+\.\s*$",
    re.IGNORECASE,
)


def _looks_like_live_audit_summary(text: str) -> bool:
    """Return True if text matches LiveAuditSupervisor.summarize_snapshot output.

    LiveAuditSupervisor produces strings shaped as
    "{lead} Decision: {action}. Confianza 0.NN." which are useful for a live
    operational dashboard but useless as the `summary`/`probable_cause` of a
    CodexPendingIssue: they describe the live audit decision, not the technical
    problem the backlog item should drive to resolution. This guard lets the
    pending-issue builders reject those strings and fall back to explicit
    placeholders instead of propagating the audit summary into three identical
    Codex fields with no actionable content.
    """
    if not text:
        return False
    return bool(_LIVE_AUDIT_SUMMARY_PATTERN.search(text.strip()))


class AutonomousEvolutionService:
    FILE_SCOPE_PATTERN = re.compile(r"(?:src|tests)[\/][\w./-]+\.py", re.IGNORECASE)
    SECTION_LINE_PATTERN = re.compile(r"(?:^|\n)\s*(?:-\s*)?(?P<label>[A-Za-z0-9_ /.-]+?)\s*:\s*(?P<value>.+)", re.IGNORECASE)

    def __init__(
        self,
        *,
        config: AppConfig,
        tool_teach_service: ToolTeachService,
        incident_packet_service: IncidentPacketService,
        pending_issue_repository: PendingIssueRepository,
    ) -> None:
        self.config = config
        self.tool_teach_service = tool_teach_service
        self.incident_packet_service = incident_packet_service
        self.pending_issue_repository = pending_issue_repository
        # Servicios opcionales inyectados desde bootstrap como atributos. Se
        # declaran aqui con valor por defecto None para que los llamadores
        # puedan probar `self.xxx is not None` sin depender de setattr.
        self.clarification_request_service = None
        self.credential_broker = None
        self.environment_bootstrap_service = None
        self.provider_health_router = None

    def plan_or_execute(self, *, adaptive_payload: dict[str, Any], user_goal: str, source: str, decision_context: DecisionContext | dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(adaptive_payload or {})
        assessment = self._assessment_from_decision_context(decision_context) or self._assess(payload=payload, user_goal=user_goal)
        if assessment.get('action') == 'request_observation_permission' and not assessment.get('should_consult'):
            permission = self._request_observation_permission(
                assessment=assessment,
                payload=payload,
                user_goal=user_goal,
            )
            if permission.get('approved'):
                # El usuario dio permiso explicito de observar. Se levanta el
                # gate localmente para este intento y se anota en metadata
                # para que el adapter/runner lo registren.
                assessment = {
                    **assessment,
                    'should_consult': True,
                    'action': f"consult_{str(assessment.get('assistant_kind') or '').strip().lower()}" if assessment.get('assistant_kind') else 'consult_external',
                    'reason': permission.get('detail') or assessment.get('reason') or '',
                }
                metadata = dict(payload.get('metadata') or {})
                metadata['observation_permission_granted'] = True
                metadata['observation_permission_detail'] = permission.get('detail') or ''
                payload['metadata'] = metadata
            elif permission.get('attempted'):
                # Se pidio el permiso pero fue denegado o expiro. Se reporta
                # con mas detalle al llamador sin consultar.
                denial_reason = permission.get('detail') or 'El usuario no aprobo la observacion externa.'
                assessment = {**assessment, 'reason': denial_reason}
        if not assessment['should_consult']:
            return {
                'status': 'noop',
                'reason': assessment['reason'],
                'assistant_kind': '',
                'requested_assistant_kind': '',
                'actual_assistant_kind': '',
                'decision_source': source,
                'recommended_action': assessment['action'],
            }
        requested_assistant_kind = str(assessment['assistant_kind'])
        pending_issue = self._ensure_pending_issue(
            payload=payload,
            user_goal=user_goal,
            assistant_kind=requested_assistant_kind,
            source=source,
            reason=str(assessment['reason']),
        )
        query = self._build_incident_query(payload=payload, pending_issue_id=pending_issue.issue_id if pending_issue is not None else '')
        context_pack = self._build_context_pack(
            assistant_kind=requested_assistant_kind,
            payload=payload,
            user_goal=user_goal,
            pending_issue_id=pending_issue.issue_id if pending_issue is not None else '',
            query=query,
        )
        launch_dry_run = not self.config.autonomous_external_launch
        approved = True if launch_dry_run else bool(self.config.autonomous_external_launch)
        task, result, preview = self.tool_teach_service.execute_external_consultation(
            user_goal=user_goal,
            assistant_preference=requested_assistant_kind,
            context_pack=context_pack,
            site_id=self._site_id(payload) or None,
            diagnostic_category=str(assessment['diagnostic_category']),
            incident_kind=self._incident_kind(payload),
            approved=approved,
            launch_dry_run=launch_dry_run,
            allow_local_automatic_consultation=True,
            goal_parameters=self._goal_context(payload),
        )
        actual_assistant_kind = str(
            result.execution_state.metadata.get('assistant_kind')
            or result.metadata.get('assistant_kind')
            or task.metadata.get('assistant_kind')
            or requested_assistant_kind
        )
        manual_pending = bool(
            result.execution_state.metadata.get('manual_pasteback_required', True)
            and not result.execution_state.metadata.get('response_captured')
            and str(result.execution_state.metadata.get('response_capture_mode') or '').strip().lower() == 'manual_pasteback'
        )
        automatic_pending = bool(result.execution_state.metadata.get('response_capture_pending'))
        login_required = bool(result.execution_state.metadata.get('assistant_login_required'))
        coherence_flags = self._consultation_coherence_flags(task=task, result=result, requested_assistant_kind=requested_assistant_kind)
        external_state_flags = self._consultation_external_state_flags(task=task, result=result, requested_assistant_kind=requested_assistant_kind, coherence_flags=coherence_flags)
        blocking_external = any(
            flag in external_state_flags
            for flag in {
                ExternalStateFlag.ACCOUNT_LIMITED.value,
                ExternalStateFlag.SESSION_EXPIRED.value,
                ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value,
                ExternalStateFlag.WRONG_THREAD.value,
            }
        )
        status = (
            'blocked_external'
            if blocking_external
            else 'awaiting_response' if result.success and (manual_pending or automatic_pending or login_required)
            else 'reused' if result.success and bool(task.metadata.get('reuse_guard_active'))
            else 'prepared' if result.success
            else 'failed'
        )
        detail = str(result.output_text or result.execution_state.detail or result.error_message or '').strip()
        if status == 'awaiting_response' and not detail:
            detail = 'La consulta externa fue abierta, pero la respuesta todavia no ha sido ingerida por IABV.'
        elif status == 'blocked_external' and not detail:
            detail = 'La ruta externa quedo bloqueada por cuenta, sesion o verificacion. IABV debe notificarlo y seguir por la mejor via local disponible.'
        consultation_state = {
            'status': status,
            'assistant_kind': actual_assistant_kind,
            'requested_assistant_kind': requested_assistant_kind,
            'actual_assistant_kind': actual_assistant_kind,
            'assistant_configuration': dict(
                result.execution_state.metadata.get('assistant_configuration')
                or result.metadata.get('assistant_configuration')
                or task.metadata.get('assistant_configuration')
                or {}
            ),
            'config_signature': str(
                result.execution_state.metadata.get('config_signature')
                or result.metadata.get('config_signature')
                or task.metadata.get('config_signature')
                or ''
            ),
            'reason': str(assessment['reason']),
            'decision_source': source,
            'recommended_action': str(assessment['action']),
            'pending_issue_id': pending_issue.issue_id if pending_issue is not None else '',
            'query': query.model_dump(mode='json'),
            'dry_run': launch_dry_run,
            'selected_tool_id': result.tool_id or task.tool_id,
            'launch_mode': str(result.execution_state.metadata.get('launch_mode') or ''),
            'response_capture_mode': str(result.execution_state.metadata.get('response_capture_mode') or ''),
            'manual_pasteback_required': bool(result.execution_state.metadata.get('manual_pasteback_required', True)),
            'response_capture_pending': bool(result.execution_state.metadata.get('response_capture_pending')),
            'assistant_login_required': bool(result.execution_state.metadata.get('assistant_login_required')),
            'session_scope': str(result.execution_state.metadata.get('session_scope') or task.metadata.get('session_scope') or ''),
            'session_label': str(result.execution_state.metadata.get('session_label') or task.metadata.get('session_label') or ''),
            'thread_key': str(result.execution_state.metadata.get('thread_key') or task.metadata.get('thread_key') or ''),
            'thread_title': str(result.execution_state.metadata.get('thread_title') or task.metadata.get('thread_title') or ''),
            'capture_lane': str(result.execution_state.metadata.get('capture_lane') or task.metadata.get('capture_lane') or ''),
            'lane_priority': list(result.execution_state.metadata.get('lane_priority') or task.metadata.get('lane_priority') or []),
            'awaiting_reason': str(result.execution_state.metadata.get('awaiting_reason') or task.metadata.get('awaiting_reason') or ''),
            'last_capture_attempt_utc': str(result.execution_state.metadata.get('last_capture_attempt_utc') or task.metadata.get('last_capture_attempt_utc') or ''),
            'reused_thread': bool(result.execution_state.metadata.get('reused_thread', task.metadata.get('reused_thread', False))),
            'session_profile_dir': str(result.execution_state.metadata.get('session_profile_dir') or result.execution_state.metadata.get('browser_profile_dir') or task.metadata.get('session_profile_dir') or ''),
            'isolated_session': bool(result.execution_state.metadata.get('isolated_session')),
            'coherence_flags': coherence_flags,
            'external_state_flags': external_state_flags,
            'reuse_guard_active': bool(task.metadata.get('reuse_guard_active')),
            'comparison_scope_key': str(result.execution_state.metadata.get('comparison_scope_key') or result.metadata.get('comparison_scope_key') or task.metadata.get('comparison_scope_key') or ''),
            'source_trace_ids': list(result.execution_state.metadata.get('source_trace_ids') or result.metadata.get('source_trace_ids') or task.metadata.get('source_trace_ids') or []),
            'proposal_summary': str(result.execution_state.metadata.get('proposal_summary') or result.metadata.get('proposal_summary') or task.metadata.get('proposal_summary') or task.metadata.get('context_pack') or task.objective or '')[:240],
            'context_pack_excerpt': context_pack[:600],
            'preview_summary': str(preview.get('summary') or ''),
            'outcome_summary': str(result.metadata.get('outcome_summary') or result.output_text or detail or '')[:240],
            'detail': detail,
            'task_id': task.task_id,
            'result_id': result.result_id,
            'execution_ms': int(result.execution_ms or result.execution_state.metadata.get('execution_ms') or task.metadata.get('execution_ms') or 0),
        }
        consultation_state['ia_trace_entry'] = self._consultation_trace_entry(
            consultation=consultation_state,
            route=self._consultation_evaluation_route(assistant_kind=actual_assistant_kind, consultation=consultation_state),
        ).model_dump(mode='json')
        updated_task = task.model_copy(
            update={
                'metadata': {
                    **dict(task.metadata or {}),
                    'autonomous_consultation': consultation_state,
                    'external_state_flags': list(external_state_flags),
                    'ia_trace_entry': dict(consultation_state['ia_trace_entry']),
                }
            }
        )
        updated_result = result.model_copy(
            update={
                'metadata': {
                    **dict(result.metadata or {}),
                    'autonomous_consultation': consultation_state,
                    'external_state_flags': list(external_state_flags),
                    'ia_trace_entry': dict(consultation_state['ia_trace_entry']),
                }
            }
        )
        repository = self.tool_teach_service.memory.repository
        repository.save_task(updated_task)
        repository.save_result(updated_result)
        auto_ingested = self._maybe_auto_ingest_consultation_response(
            payload=payload,
            user_goal=user_goal,
            source=source,
            consultation_state=consultation_state,
            result=updated_result,
        )
        if auto_ingested is not None:
            return auto_ingested
        return dict(consultation_state)


    def reingest_existing_session(
        self,
        *,
        existing_consultation: dict[str, Any],
        adaptive_payload: dict[str, Any],
        user_goal: str,
        source: str,
    ) -> dict[str, Any]:
        """Fuerza una re-ingesta de la sesion abierta antes de relanzar.

        Cuando la consulta anterior quedo en ``session_expired`` pero la
        sesion aislada sigue abierta con una respuesta visible, este metodo
        ejecuta una captura liviana (``reingest_only=True``) sin pasar por
        el assessment completo de ``plan_or_execute``.  Si la captura obtiene
        texto util, lo ingiere directamente y devuelve el resultado con
        ``pre_capture_ingested=True``.  Si no hay texto util, devuelve
        ``pre_capture_ingested=False`` para que el llamador siga con el
        reintento normal.
        """
        tool_id = str(existing_consultation.get('selected_tool_id') or '').strip()
        assistant_kind = str(existing_consultation.get('assistant_kind') or '').strip().lower()
        if not tool_id or not assistant_kind:
            return {'pre_capture_ingested': False, 'reason': 'no_tool_or_assistant'}

        goal_parameters = {
            'reingest_existing_response': True,
            'tool_id': tool_id,
            'assistant_kind': assistant_kind,
            'response_capture_mode': str(existing_consultation.get('response_capture_mode') or ''),
            'session_scope': str(existing_consultation.get('session_scope') or ''),
            'session_label': str(existing_consultation.get('session_label') or ''),
            'session_profile_dir': str(existing_consultation.get('session_profile_dir') or ''),
            'thread_key': str(existing_consultation.get('thread_key') or ''),
            'thread_title': str(existing_consultation.get('thread_title') or ''),
            'isolated_session_required': bool(existing_consultation.get('isolated_session')),
        }
        try:
            task, result, _preview = self.tool_teach_service.execute_external_consultation(
                user_goal=user_goal,
                assistant_preference=assistant_kind,
                context_pack='',
                site_id=str(existing_consultation.get('site_id') or '') or None,
                diagnostic_category=str(existing_consultation.get('diagnostic_category') or ''),
                incident_kind=str(existing_consultation.get('incident_kind') or ''),
                approved=True,
                launch_dry_run=False,
                allow_local_automatic_consultation=False,
                goal_parameters=goal_parameters,
            )
        except Exception:
            return {'pre_capture_ingested': False, 'reason': 'capture_exception'}

        response_captured = bool(result.execution_state.metadata.get('response_captured'))
        captured_text = str(result.output_text or '').strip()
        if not response_captured or not captured_text:
            return {
                'pre_capture_ingested': False,
                'reason': str(result.error_message or 'no_response_text'),
                'task_id': task.task_id,
                'result_id': result.result_id,
            }

        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        metadata['autonomous_evolution'] = dict(existing_consultation)
        payload['metadata'] = metadata
        if existing_consultation.get('pending_issue_id'):
            payload['pending_issue_id'] = existing_consultation['pending_issue_id']
        ingested = self.ingest_consult_response(
            adaptive_payload=payload,
            user_goal=user_goal,
            response_text=captured_text,
            source=f'{source}_pre_capture',
        )
        ingested['pre_capture_ingested'] = True
        ingested['pre_capture_task_id'] = task.task_id
        ingested['pre_capture_result_id'] = result.result_id
        ingested['pre_capture_source'] = str(
            result.execution_state.metadata.get('capture_source') or 'reingest'
        )
        return ingested

    def preview_plan(self, *, adaptive_payload: dict[str, Any], user_goal: str, source: str, decision_context: DecisionContext | dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(adaptive_payload or {})
        assessment = self._assessment_from_decision_context(decision_context) or self._assess(payload=payload, user_goal=user_goal)
        requested_assistant_kind = str(assessment.get('assistant_kind') or '')
        live_audit = self._live_audit(payload)
        base = {
            'status': 'preview',
            'should_consult': bool(assessment.get('should_consult')),
            'assistant_kind': requested_assistant_kind,
            'requested_assistant_kind': requested_assistant_kind,
            'actual_assistant_kind': requested_assistant_kind,
            'decision_source': source,
            'recommended_action': str(assessment.get('action') or ''),
            'reason': str(assessment.get('reason') or ''),
            'site_id': self._site_id(payload),
            'incident_kind': self._incident_kind(payload),
            'live_audit_summary': str(live_audit.get('summary') or ''),
            'selected_tool_id': '',
            'launch_mode': '',
            'available': False,
            'fallback_used': False,
            'context_pack_excerpt': '',
            'preview_summary': '',
        }
        if not assessment['should_consult']:
            return base
        pending_issue_id = str(payload.get('pending_issue_id') or '').strip()
        query = self._build_incident_query(payload=payload, pending_issue_id=pending_issue_id)
        context_pack = self._build_context_pack(
            assistant_kind=requested_assistant_kind,
            payload=payload,
            user_goal=user_goal,
            pending_issue_id=pending_issue_id,
            query=query,
        )
        preview = self.tool_teach_service.preview_external_consultation(
            user_goal=user_goal,
            assistant_preference=requested_assistant_kind,
            context_pack=context_pack,
            site_id=self._site_id(payload) or None,
            diagnostic_category=str(assessment['diagnostic_category']),
            incident_kind=self._incident_kind(payload),
            launch_dry_run=not self.config.autonomous_external_launch,
            allow_local_automatic_consultation=True,
            goal_parameters=self._goal_context(payload),
        )
        tool_card = dict(preview.get('tool_card') or {})
        tool_metadata = dict(tool_card.get('metadata') or {})
        mode_selection = dict(preview.get('mode_selection') or {})
        actual_assistant_kind = str(tool_metadata.get('assistant_kind') or requested_assistant_kind)
        return {
            **base,
            'actual_assistant_kind': actual_assistant_kind,
            'assistant_kind': actual_assistant_kind,
            'assistant_configuration': dict((preview.get('tool_task') or {}).get('metadata', {}).get('assistant_configuration') or {}),
            'config_signature': str((preview.get('tool_task') or {}).get('metadata', {}).get('config_signature') or ''),
            'selected_tool_id': str(tool_card.get('tool_id') or (preview.get('tool_task') or {}).get('tool_id') or ''),
            'launch_mode': str(tool_metadata.get('launch_mode') or ''),
            'available': bool(preview.get('available')),
            'fallback_used': bool(mode_selection.get('fallback_used')),
            'context_pack_excerpt': context_pack[:600],
            'preview_summary': str(preview.get('summary') or ''),
        }

    def _maybe_auto_ingest_consultation_response(
        self,
        *,
        payload: dict[str, Any],
        user_goal: str,
        source: str,
        consultation_state: dict[str, Any],
        result,
    ) -> dict[str, Any] | None:
        capture_mode = str(result.execution_state.metadata.get('response_capture_mode') or consultation_state.get('response_capture_mode') or '').strip().lower()
        manual_required = bool(result.execution_state.metadata.get('manual_pasteback_required', consultation_state.get('manual_pasteback_required', True)))
        response_captured = bool(result.execution_state.metadata.get('response_captured'))
        response_text = str(result.output_text or '').strip()
        if not result.success or manual_required or not response_text:
            return None
        if not response_captured and capture_mode not in {'tool_result', 'direct_text', 'session_rollout'}:
            return None
        if capture_mode in {'', 'manual_pasteback'} and not response_captured:
            return None
        consult_payload = dict(payload or {})
        metadata = dict(consult_payload.get('metadata') or {})
        metadata['autonomous_evolution'] = dict(consultation_state)
        consult_payload['metadata'] = metadata
        if consultation_state.get('pending_issue_id'):
            consult_payload['pending_issue_id'] = consultation_state.get('pending_issue_id')
        bridge = self.ingest_consult_response(
            adaptive_payload=consult_payload,
            user_goal=user_goal,
            response_text=response_text,
            source=f'{source}_auto_capture',
        )
        bridge['auto_response_ingested'] = True
        bridge['auto_response_capture_mode'] = capture_mode or 'tool_result'
        bridge['manual_pasteback_required'] = False
        bridge['consultation_task_id'] = str(consultation_state.get('task_id') or '')
        bridge['consultation_result_id'] = str(consultation_state.get('result_id') or '')
        return bridge

    def _consultation_coherence_flags(self, *, task, result, requested_assistant_kind: str) -> list[str]:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        actual_assistant = str(execution_metadata.get('assistant_kind') or getattr(result, 'metadata', {}).get('assistant_kind') or task_metadata.get('assistant_kind') or '').strip().lower()
        requested = str(requested_assistant_kind or task_metadata.get('assistant_kind') or '').strip().lower()
        lane = str(execution_metadata.get('capture_lane') or task_metadata.get('capture_lane') or '').strip().lower()
        session_scope = str(execution_metadata.get('session_scope') or task_metadata.get('session_scope') or '').strip().lower()
        thread_key = str(execution_metadata.get('thread_key') or task_metadata.get('thread_key') or '').strip()
        session_profile_dir = str(execution_metadata.get('session_profile_dir') or execution_metadata.get('browser_profile_dir') or task_metadata.get('session_profile_dir') or '').strip()
        flags: list[str] = []
        if requested and actual_assistant and requested != actual_assistant and not (requested == 'codex' and actual_assistant in {'chatgpt', 'ollama'}) and not (requested == 'chatgpt' and actual_assistant == 'chatgpt') and not (requested == 'claude' and actual_assistant == 'claude'):
            flags.append(f'family_mismatch:{requested}->{actual_assistant}')
        if lane in {'background', 'app'} and session_scope in {'program_chat', 'external_app'} and not thread_key:
            flags.append('missing_thread_tracking')
        if session_scope == 'program_chat' and not session_profile_dir:
            flags.append('missing_program_session_profile')
        if execution_metadata.get('response_capture_mode') == 'manual_pasteback' and task_metadata.get('capture_lane') in {'background', 'app'} and not execution_metadata.get('response_captured'):
            flags.append('premature_manual_fallback')
        if getattr(result, 'metadata', {}).get('external_consult_response') and not execution_metadata.get('response_captured'):
            flags.append('learning_without_captured_response')
        return flags

    def _consultation_external_state_flags(
        self,
        *,
        task,
        result,
        requested_assistant_kind: str,
        coherence_flags: list[str] | None = None,
    ) -> list[str]:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        result_metadata = dict(getattr(result, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        flags = canonical_external_state_flags(
            [
                *(coherence_flags or []),
                *(task_metadata.get('external_state_flags') or []),
                *(result_metadata.get('external_state_flags') or []),
                *(execution_metadata.get('external_state_flags') or []),
            ]
        )
        if str(getattr(getattr(result, 'execution_state', None), 'state', '') or '').strip().lower() == ExternalStateFlag.AWAITING_RESPONSE.value:
            if ExternalStateFlag.AWAITING_RESPONSE.value not in flags:
                flags.append(ExternalStateFlag.AWAITING_RESPONSE.value)
        if bool(execution_metadata.get('response_capture_pending')):
            if ExternalStateFlag.AWAITING_RESPONSE.value not in flags:
                flags.append(ExternalStateFlag.AWAITING_RESPONSE.value)
        if bool(execution_metadata.get('assistant_login_required')):
            if ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value not in flags:
                flags.append(ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value)
        if bool(execution_metadata.get('session_expired')) or str(execution_metadata.get('session_status') or '').strip().lower() == 'expired':
            if ExternalStateFlag.SESSION_EXPIRED.value not in flags:
                flags.append(ExternalStateFlag.SESSION_EXPIRED.value)
        quota_status = str(execution_metadata.get('quota_status') or '').strip().lower()
        rate_limit_status = str(execution_metadata.get('rate_limit_status') or '').strip().lower()
        plan_status = str(execution_metadata.get('plan_status') or '').strip().lower()
        capture_error = str(
            execution_metadata.get('auto_capture_reason')
            or execution_metadata.get('error_message')
            or result_metadata.get('error_message')
            or ''
        ).strip().lower()
        if (
            bool(execution_metadata.get('account_limited'))
            or bool(execution_metadata.get('credits_exhausted'))
            or bool(execution_metadata.get('rate_limited'))
            or bool(execution_metadata.get('plan_upgrade_required'))
            or str(execution_metadata.get('account_status') or '').strip().lower() in {'limited', 'blocked'}
            or quota_status in {'exhausted', 'limited', 'blocked'}
            or rate_limit_status in {'limited', 'blocked', 'exhausted'}
            or plan_status in {'upgrade_required', 'limited', 'blocked'}
        ):
            if ExternalStateFlag.ACCOUNT_LIMITED.value not in flags:
                flags.append(ExternalStateFlag.ACCOUNT_LIMITED.value)
        thread_verification = str(execution_metadata.get('thread_verification') or '').strip().lower()
        if thread_verification in {ExternalStateFlag.WRONG_THREAD.value, 'thread_mismatch', 'mismatch'} or bool(execution_metadata.get('thread_mismatch')):
            if ExternalStateFlag.WRONG_THREAD.value not in flags:
                flags.append(ExternalStateFlag.WRONG_THREAD.value)
        response_capture_mode = str(execution_metadata.get('response_capture_mode') or task_metadata.get('response_capture_mode') or '').strip().lower()
        if (
            capture_error in {'browser_dom_unavailable', 'browser_dom_launch_failed', 'browser_dom_capture_pending'}
            or (
                response_capture_mode in {'clipboard_capture', 'dom_capture', 'browser_dom'}
                and bool(execution_metadata.get('launched'))
                and not bool(execution_metadata.get('response_captured'))
                and not bool(execution_metadata.get('assistant_login_required'))
            )
        ):
            if ExternalStateFlag.CAPTURE_UNVERIFIED.value not in flags:
                flags.append(ExternalStateFlag.CAPTURE_UNVERIFIED.value)
        if ExternalStateFlag.WRONG_THREAD.value in flags and ExternalStateFlag.CAPTURE_UNVERIFIED.value not in flags:
            flags.append(ExternalStateFlag.CAPTURE_UNVERIFIED.value)
        return flags

    def _consultation_trace_entry(
        self,
        *,
        consultation: dict[str, Any],
        route: EvaluationRoute,
        confidence: float | None = None,
        verdict: str = '',
        success: bool | None = None,
        evidence_refs: list[str] | None = None,
    ) -> IATraceEntry:
        configuration_payload = consultation.get('assistant_configuration') or {}
        if isinstance(configuration_payload, AssistantConfigurationSnapshot):
            configuration = configuration_payload
        else:
            configuration = AssistantConfigurationSnapshot.model_validate(configuration_payload or {})
        external_state_flags = canonical_external_state_flags(
            list(consultation.get('external_state_flags') or [])
            + list(consultation.get('coherence_flags') or [])
        )
        return IATraceEntry(
            assistant_kind=str(consultation.get('assistant_kind') or ''),
            requested_assistant_kind=str(consultation.get('requested_assistant_kind') or consultation.get('assistant_kind') or ''),
            actual_assistant_kind=str(consultation.get('actual_assistant_kind') or consultation.get('assistant_kind') or ''),
            assistant_configuration=configuration,
            config_signature=str(consultation.get('config_signature') or ''),
            comparison_scope_key=str(consultation.get('comparison_scope_key') or ''),
            source_trace_ids=[str(item) for item in (consultation.get('source_trace_ids') or []) if str(item).strip()],
            route=route.value,
            tool_id=str(consultation.get('selected_tool_id') or consultation.get('tool_id') or ''),
            task_id=str(consultation.get('task_id') or ''),
            result_id=str(consultation.get('result_id') or ''),
            session_scope=str(consultation.get('session_scope') or ''),
            thread_key=str(consultation.get('thread_key') or ''),
            thread_title=str(consultation.get('thread_title') or ''),
            capture_lane=str(consultation.get('capture_lane') or ''),
            state=str(consultation.get('status') or ''),
            detail=str(consultation.get('detail') or consultation.get('reason') or ''),
            proposal_summary=str(consultation.get('proposal_summary') or consultation.get('preview_summary') or consultation.get('reason') or '')[:240],
            outcome_summary=str(consultation.get('outcome_summary') or consultation.get('response_summary') or consultation.get('detail') or '')[:240],
            result_label=str(consultation.get('response_summary') or consultation.get('detail') or consultation.get('preview_summary') or '')[:240],
            success=bool(success if success is not None else consultation.get('status') in {'prepared', 'reused', 'ingested', 'captured', 'awaiting_response'}),
            execution_ms=int(consultation.get('execution_ms') or 0),
            confidence=float(confidence if confidence is not None else consultation.get('response_confidence') or consultation.get('confidence') or 0.0),
            evidence_refs=list(evidence_refs or []),
            reused_later=bool(consultation.get('reuse_guard_active', False)),
            verdict=str(verdict or consultation.get('validation_status') or consultation.get('adoption_status') or consultation.get('status') or ''),
            coherence_flags=list(consultation.get('coherence_flags') or []),
            external_state_flags=external_state_flags,
            metadata={
                'response_capture_mode': str(consultation.get('response_capture_mode') or ''),
                'background_capture_mode': str(consultation.get('background_capture_mode') or ''),
            },
        )

    # Palabras que el usuario puede responder al popup de permiso y que
    # consideramos como aprobacion explicita. Se comparan en minusculas.
    _OBSERVATION_PERMISSION_APPROVALS: frozenset[str] = frozenset({
        'si', 'sí', 'yes', 'ok', 'okay', 'dale', 'adelante',
        'aprobar', 'apruebo', 'aprobado', 'permiso',
        'autorizo', 'autorizar', 'autorizado',
        'conceder', 'concedo', 'concedido', 'allow', 'approve',
    })
    # Negaciones que invalidan la aprobacion aunque aparezca un token
    # positivo despues (ej. "no autorizo", "no apruebo").
    _OBSERVATION_PERMISSION_DENIALS: frozenset[str] = frozenset({
        'no', 'nop', 'nope', 'cancelar', 'cancelo', 'cancel',
        'deny', 'denegar', 'denegado', 'rechazo', 'rechazar', 'rechazado',
        'nunca', 'niego', 'negar',
    })

    def _request_observation_permission(
        self,
        *,
        assessment: dict[str, Any],
        payload: dict[str, Any],
        user_goal: str,
    ) -> dict[str, Any]:
        """Pide permiso explicito al usuario para observar la herramienta externa.

        Consume `ClarificationRequestService.ask`, que emite
        `clarificationRequested` hacia la UI (ControlCenter/EvolutionCenter)
        y bloquea hasta recibir respuesta. Se respeta el contrato de
        governance: si el usuario no aprueba, el gate sigue cerrado.

        Devuelve un dict con:
        - `attempted`: se llamo realmente al servicio (False si no existe).
        - `approved`: el usuario respondio afirmativamente.
        - `detail`: texto humano de la respuesta (para logs/UI).
        - `raw_response`: la respuesta cruda del usuario (si hubo).
        """
        service = self.clarification_request_service
        if service is None:
            return {'attempted': False, 'approved': False, 'detail': '', 'raw_response': ''}
        assistant_kind = str(assessment.get('assistant_kind') or '').strip().lower() or 'la herramienta externa'
        reason = str(assessment.get('reason') or 'Necesito permiso explicito para observar el contenido visible antes de seguir con esta ruta.').strip()
        question = f"¿Autorizas que IABV observe la ventana de {assistant_kind} para responder '{str(user_goal or '').strip()[:120]}'?"
        context_lines: list[str] = [reason]
        if payload.get('session_id'):
            context_lines.append(f"Sesion: {payload.get('session_id')}")
        timeout_s = None
        config_timeout = getattr(self.config, 'observation_permission_timeout_s', None)
        if isinstance(config_timeout, (int, float)) and float(config_timeout) > 0:
            timeout_s = float(config_timeout)
        try:
            raw = service.ask(
                question=question,
                options=['Autorizo', 'No autorizo'],
                context='\n'.join(context_lines),
                timeout_s=timeout_s,
            )
        except Exception as exc:  # noqa: BLE001 - cubre Timeout, Cancelled o errores del handler
            return {
                'attempted': True,
                'approved': False,
                'detail': f'El permiso no fue resuelto: {type(exc).__name__}',
                'raw_response': '',
            }
        normalized = str(raw or '').strip().lower()
        # strip punctuation comun para que "No, autorizo" no bypasee el
        # chequeo de negacion y "autorizo." matchee el set de aprobacion.
        tokens = [t.strip('.,;:!?¿¡()[]"\'') for t in normalized.split()]
        tokens = [t for t in tokens if t]
        has_denial_prefix = bool(tokens) and tokens[0] in self._OBSERVATION_PERMISSION_DENIALS
        has_approval_token = (
            normalized in self._OBSERVATION_PERMISSION_APPROVALS
            or any(token in self._OBSERVATION_PERMISSION_APPROVALS for token in tokens)
        )
        approved = has_approval_token and not has_denial_prefix
        detail = (
            f'El usuario aprobo observar {assistant_kind}.'
            if approved
            else f"El usuario no aprobo observar {assistant_kind} (respondio: '{raw}')."
        )
        return {
            'attempted': True,
            'approved': approved,
            'detail': detail,
            'raw_response': str(raw or ''),
        }

    def _assessment_from_decision_context(self, decision_context: DecisionContext | dict[str, Any] | None) -> dict[str, Any]:
        if decision_context is None:
            return {}
        context = decision_context.model_dump(mode='json') if isinstance(decision_context, DecisionContext) else dict(decision_context or {})
        governance = dict(context.get('governance') or {})
        if not governance:
            return {}
        metadata = dict(context.get('metadata') or {})
        preferred_assistant_kind = str(metadata.get('preferred_assistant_kind') or '').strip().lower()
        preferred_config_signature = str(metadata.get('preferred_config_signature') or '').strip()
        return {
            'should_consult': bool(governance.get('should_consult')),
            'assistant_kind': str(governance.get('assistant_kind') or preferred_assistant_kind or ''),
            'preferred_assistant_kind': preferred_assistant_kind,
            'preferred_config_signature': preferred_config_signature,
            'diagnostic_category': str(governance.get('diagnostic_category') or ''),
            'action': str(governance.get('recommended_action') or 'continue_local'),
            'reason': str(governance.get('reason') or 'DecisionContext sin razon explicita.'),
        }

    def ingest_consult_response(
        self,
        *,
        adaptive_payload: dict[str, Any],
        user_goal: str,
        response_text: str,
        source: str,
    ) -> dict[str, Any]:
        payload = dict(adaptive_payload or {})
        response = str(response_text or '').strip()
        if not response:
            return {
                'status': 'empty',
                'assistant_kind': '',
                'next_action': 'stop_and_wait_user',
                'detail': 'No recibi texto de respuesta para interpretar.',
            }
        consultation = self._consultation_metadata(payload)
        if not consultation:
            return {
                'status': 'missing_context',
                'assistant_kind': '',
                'next_action': 'stop_and_wait_user',
                'detail': 'No encontre una consulta externa activa para asociar esta respuesta.',
            }
        assistant_kind = self._assistant_kind_for_response(consultation=consultation, response=response)
        parsed = self._parse_external_response(
            response=response,
            assistant_kind=assistant_kind,
            payload=payload,
            user_goal=user_goal,
        )
        response_validation = self._validate_external_response(
            parsed=parsed,
            assistant_kind=assistant_kind,
            payload=payload,
        )
        adoption_plan = self._build_adoption_plan(
            parsed=parsed,
            response_validation=response_validation,
            consultation=consultation,
            payload=payload,
        )
        parsed['response_validation'] = response_validation
        parsed['adoption_plan'] = adoption_plan
        pending_issue = self._ensure_pending_issue(
            payload=payload,
            user_goal=user_goal,
            assistant_kind='codex' if parsed['response_kind'] in {'code_fix', 'runtime_tuning'} else assistant_kind,
            source=source,
            reason=str(parsed['summary'] or parsed['recommended_change'] or consultation.get('reason') or 'Respuesta externa interpretada.'),
        )
        if pending_issue is not None:
            pending_issue = self._merge_pending_issue(
                issue=pending_issue,
                parsed=parsed,
                assistant_kind=assistant_kind,
                source=source,
                payload=payload,
            )
        repository = self.tool_teach_service.memory.repository
        task, result = self._resolve_consultation_records(consultation)
        timestamp = datetime.now(timezone.utc).isoformat()
        ingestion_status = 'ingested' if str(response_validation.get('status') or '') != 'insufficient' and parsed['useful'] else 'captured'
        response_metadata = {
            **consultation,
            'status': ingestion_status,
            'assistant_kind': assistant_kind,
            'requested_assistant_kind': str(consultation.get('requested_assistant_kind') or assistant_kind),
            'actual_assistant_kind': assistant_kind,
            'response_source': source,
            'response_summary': parsed['summary'],
            'response_probable_cause': parsed['probable_cause'],
            'response_recommended_change': parsed['recommended_change'],
            'response_kind': parsed['response_kind'],
            'response_next_action': str(adoption_plan.get('next_action') or parsed['next_action']),
            'response_confidence': parsed['confidence'],
            'response_useful': parsed['useful'],
            'response_excerpt': response[:1500],
            'response_file_scope': list(parsed['file_scope']),
            'response_tests': list(parsed['suggested_tests']),
            'response_signals': list(parsed['signals']),
            'response_validation': dict(response_validation),
            'adoption_plan': dict(adoption_plan),
            'response_ingested': ingestion_status == 'ingested',
            'response_ingested_at_utc': timestamp,
            'pending_issue_id': pending_issue.issue_id if pending_issue is not None else str(consultation.get('pending_issue_id') or ''),
            'proposal_summary': str(consultation.get('proposal_summary') or consultation.get('preview_summary') or consultation.get('context_pack_excerpt') or '')[:240],
            'outcome_summary': str(parsed.get('summary') or parsed.get('recommended_change') or consultation.get('detail') or '')[:240],
            'codex_task_spec': dict(parsed['codex_task_spec'] or {}),
            # Flatten guarded adoption details so UI/runtime consumers can
            # read the safe lane directly without reconstructing nested state.
            'execution_lane': str(adoption_plan.get('execution_lane') or ''),
            'adoption_status': str(adoption_plan.get('status') or ''),
            'sandbox_required': bool(response_validation.get('sandbox_required')),
            'rollback_ready': bool(adoption_plan.get('rollback_ready') or response_validation.get('rollback_ready')),
            'requires_human_approval': bool(response_validation.get('requires_human_approval') or adoption_plan.get('requires_human_approval')),
            'validation_track': str(response_validation.get('validation_track') or ''),
            'human_help': str(adoption_plan.get('human_help') or ''),
        }
        response_metadata['external_state_flags'] = canonical_external_state_flags(
            [
                *(consultation.get('external_state_flags') or []),
                *(consultation.get('coherence_flags') or []),
            ]
        )
        response_metadata['external_state_flags'] = [
            item
            for item in response_metadata['external_state_flags']
            if item not in {ExternalStateFlag.AWAITING_RESPONSE.value, ExternalStateFlag.CAPTURE_UNVERIFIED.value}
        ]
        experiment_feedback = self._record_consultation_experiment(
            payload=payload,
            user_goal=user_goal,
            consultation=consultation,
            assistant_kind=assistant_kind,
            parsed=parsed,
            response_validation=response_validation,
            adoption_plan=adoption_plan,
            source=source,
        )
        if experiment_feedback is not None:
            response_metadata['experiment_feedback'] = experiment_feedback
        evidence_refs = self._merge_text_items(
            list(response_metadata.get('evidence_refs') or []),
            [
                str(response_metadata.get('pending_issue_id') or ''),
                str(response_metadata.get('task_id') or ''),
                str(response_metadata.get('result_id') or ''),
                str((experiment_feedback or {}).get('run_id') or ''),
                str((experiment_feedback or {}).get('recommendation_id') or ''),
            ],
        )
        response_metadata['ia_trace_entry'] = self._consultation_trace_entry(
            consultation=response_metadata,
            route=self._consultation_evaluation_route(assistant_kind=assistant_kind, consultation=response_metadata),
            confidence=float(parsed.get('confidence') or response_validation.get('confidence') or 0.0),
            verdict=str(response_validation.get('status') or adoption_plan.get('status') or ingestion_status),
            success=bool(parsed.get('useful')),
            evidence_refs=evidence_refs,
        ).model_dump(mode='json')
        if task is not None:
            updated_task = task.model_copy(
                update={
                    'metadata': {
                        **dict(task.metadata or {}),
                        'autonomous_consultation': response_metadata,
                        'external_state_flags': list(response_metadata.get('external_state_flags') or []),
                        'ia_trace_entry': dict(response_metadata.get('ia_trace_entry') or {}),
                        'manual_pasteback_completed': True,
                        'response_ingested_at_utc': timestamp,
                    }
                }
            )
            repository.save_task(updated_task)
            task = updated_task
        if result is not None:
            updated_result = result.model_copy(
                update={
                    'metadata': {
                        **dict(result.metadata or {}),
                        'autonomous_consultation': response_metadata,
                        'external_state_flags': list(response_metadata.get('external_state_flags') or []),
                        'ia_trace_entry': dict(response_metadata.get('ia_trace_entry') or {}),
                        'external_consult_response': {
                            'summary': parsed['summary'],
                            'recommended_change': parsed['recommended_change'],
                            'next_action': str(adoption_plan.get('next_action') or parsed['next_action']),
                            'confidence': parsed['confidence'],
                            'useful': parsed['useful'],
                            'validation': dict(response_validation),
                            'adoption_plan': dict(adoption_plan),
                        },
                    },
                    'output_text': str(result.output_text or parsed['detail'] or consultation.get('detail') or '').strip(),
                }
            )
            repository.save_result(updated_result)
            self._attach_response_to_interaction_episode(result=updated_result, response_metadata=response_metadata)
            result = updated_result
        self.tool_teach_service.memory.audit_event(
            tool_id=str((task.tool_id if task is not None else consultation.get('selected_tool_id') or consultation.get('tool_id') or 'external_assistant') or 'external_assistant'),
            task_id=task.task_id if task is not None else str(consultation.get('task_id') or '') or None,
            action_type='external_response_ingested',
            state=str(response_metadata['status']),
            payload={
                'assistant_kind': assistant_kind,
                'next_action': str(adoption_plan.get('next_action') or parsed['next_action']),
                'summary': parsed['summary'],
                'pending_issue_id': response_metadata['pending_issue_id'],
                'validation_status': str(response_validation.get('status') or ''),
                'adoption_lane': str(adoption_plan.get('execution_lane') or ''),
                'trace_id': str((response_metadata.get('ia_trace_entry') or {}).get('trace_id') or ''),
            },
        )
        return {
            **response_metadata,
            'next_action': str(adoption_plan.get('next_action') or parsed['next_action']),
            'execution_lane': str(adoption_plan.get('execution_lane') or ''),
            'adoption_status': str(adoption_plan.get('status') or ''),
            'sandbox_required': bool(response_validation.get('sandbox_required')),
            'rollback_ready': bool(adoption_plan.get('rollback_ready') or response_validation.get('rollback_ready')),
            'requires_human_approval': bool(response_validation.get('requires_human_approval') or adoption_plan.get('requires_human_approval')),
            'validation_track': str(response_validation.get('validation_track') or ''),
            'human_help': str(adoption_plan.get('human_help') or ''),
            'detail': parsed['detail'],
            'task_id': task.task_id if task is not None else str(consultation.get('task_id') or ''),
            'result_id': result.result_id if result is not None else str(consultation.get('result_id') or ''),
        }

    def _assess(self, *, payload: dict[str, Any], user_goal: str) -> dict[str, Any]:
        diagnosis = dict(payload.get('probe_diagnosis') or {})
        live_audit = self._live_audit(payload)
        assistant_guidance = dict(payload.get('assistant_guidance') or {})
        category = str(diagnosis.get('category') or '').strip().lower()
        guidance_mode = str(assistant_guidance.get('mode') or '').strip().lower()
        live_action = str(live_audit.get('decision_action') or (live_audit.get('decision') or {}).get('action') or '').strip().lower()
        incident_kind = self._incident_kind(payload)
        if category in {'need_codex_fix', 'need_adapter'} or guidance_mode in {'need_codex_fix', 'need_adapter'} or live_action == 'consult_codex' or incident_kind in {'bridge_lag', 'navigation_stall', 'session_restore_weak', 'visual_alignment_weak', 'critical_object_missing'}:
            return {
                'should_consult': True,
                'assistant_kind': 'codex',
                'diagnostic_category': category or 'need_codex_fix',
                'action': 'consult_codex',
                'reason': str(diagnosis.get('summary') or live_audit.get('summary') or 'El caso requiere una consulta tecnica autonoma para seguir evolucionando.'),
            }
        if category == 'need_teaching' and live_action == 'consult_chatgpt':
            return {
                'should_consult': True,
                'assistant_kind': 'chatgpt',
                'diagnostic_category': category,
                'action': 'consult_chatgpt',
                'reason': str(diagnosis.get('summary') or live_audit.get('summary') or 'Hace falta una explicacion externa antes de reensenar el flujo.'),
            }
        if guidance_mode == 'need_teaching' and 'explica' in user_goal.lower():
            return {
                'should_consult': True,
                'assistant_kind': 'chatgpt',
                'diagnostic_category': category or 'need_teaching',
                'action': 'consult_chatgpt',
                'reason': str(diagnosis.get('summary') or assistant_guidance.get('prompt') or 'Conviene pedir una explicacion mas clara del hueco de ensenanza.'),
            }
        return {
            'should_consult': False,
            'assistant_kind': '',
            'diagnostic_category': category,
            'action': str(live_action or 'continue_local'),
            'reason': str(diagnosis.get('summary') or live_audit.get('summary') or 'La evidencia actual no justifica una consulta externa automatica.'),
        }

    def _ensure_pending_issue(
        self,
        *,
        payload: dict[str, Any],
        user_goal: str,
        assistant_kind: str,
        source: str,
        reason: str,
    ) -> CodexPendingIssue | None:
        issue_id = str(payload.get('pending_issue_id') or '').strip()
        if issue_id:
            existing = self.pending_issue_repository.get(issue_id)
            if existing is not None:
                return existing
        diagnosis = dict(payload.get('probe_diagnosis') or {})
        category = self._pending_category(diagnosis.get('category'), assistant_kind)
        # The incoming `reason` may be a LiveAudit summary like
        # "Sin hallazgos. Decision: continue_local. Confianza 0.66." which is
        # meaningful as an operational audit line but worthless as the summary
        # or probable_cause of a CodexPendingIssue. Drop it from the text
        # fallback path so the backlog is not polluted with three identical
        # fields carrying the same non-actionable audit line. The live audit
        # context is still preserved through `audit_snapshot_id` in
        # `evidence_refs` and through the incident packet built later.
        reason_for_text = '' if _looks_like_live_audit_summary(reason) else reason
        summary = str(diagnosis.get('summary') or reason_for_text or 'Consulta evolutiva autonoma requerida.').strip()
        probable_cause = str(diagnosis.get('probable_cause') or reason_for_text or '').strip()
        runtime_adjustments = list(payload.get('runtime_adjustments') or [])
        evidence = [str(item) for item in (payload.get('evidence_refs') or []) if str(item).strip()]
        live_audit = self._live_audit(payload)
        if live_audit.get('audit_snapshot_id'):
            evidence.append(str(live_audit.get('audit_snapshot_id')))
        context = dict(payload.get('context') or {})
        session_readiness = dict(context.get('session_readiness') or {})
        if session_readiness.get('dominant_incident'):
            evidence.append(f"incident:{session_readiness.get('dominant_incident')}")
        issue = CodexPendingIssue(
            goal=user_goal,
            category=category,
            summary=summary,
            probable_cause=probable_cause,
            unresolved_reason=str(diagnosis.get('recommended_action') or reason_for_text or '').strip(),
            run_id=str(payload.get('run_id') or '') or None,
            episode_id=str(payload.get('episode_id') or self._episode_id(payload) or '') or None,
            session_id=str(payload.get('session_id') or '') or None,
            evidence_refs=evidence[:8],
            runtime_adjustments=[item if hasattr(item, 'model_dump') else item for item in runtime_adjustments],
            recommended_change=str(diagnosis.get('recommended_action') or reason_for_text or '').strip(),
            suggested_tests=self._suggested_tests(payload, user_goal),
            metadata={
                'autonomous_evolution': True,
                'assistant_kind': assistant_kind,
                'source': source,
                'site_id': self._site_id(payload),
                'intent_key': str((payload.get('intent') or {}).get('intent_key') or ''),
            },
        )
        return self.pending_issue_repository.save(issue)

    def _build_context_pack(
        self,
        *,
        assistant_kind: str,
        payload: dict[str, Any],
        user_goal: str,
        pending_issue_id: str,
        query: IncidentQuery,
    ) -> str:
        packet = self.incident_packet_service.build_codex_packet_for_issue(query)
        live_audit = self._live_audit(payload)
        lines = [
            'Consulta autonoma IABV v1.5',
            f'Workspace: {self.config.workspace_root}',
            f'Objetivo: {user_goal}',
            f'Asistente elegido: {assistant_kind}',
        ]
        if pending_issue_id:
            lines.append(f'Pending issue: {pending_issue_id}')
            lines.append(f'IABV_QUERY_ID: {pending_issue_id}')
        if self._site_id(payload):
            lines.append(f'Sitio: {self._site_id(payload)}')
        if live_audit.get('summary'):
            lines.append(f"Auditoria viva: {live_audit.get('summary')}")
        if assistant_kind in {'chatgpt', 'claude'}:
            lines.append('Objetivo de la consulta: explicar el bloqueo, contrastar el siguiente paso seguro y no mezclar esta consulta con un hilo de otro asistente.')
        elif assistant_kind == 'ollama':
            lines.append('Objetivo de la consulta: intentar una explicacion o diagnostico local antes de escalar a otra IA.')
        else:
            lines.append('Objetivo de la consulta: diagnosticar la causa raiz tecnica y proponer el siguiente cambio vertical verificable.')
        lines.extend(
            [
                'Formato de salida obligatorio:',
                'Causa raiz probable: <una frase concreta>',
                'Cambio vertical recomendado: <siguiente cambio o microajuste>',
                'Pruebas sugeridas: <1 a 3 pruebas cortas separadas por coma>',
                'file_scope: <rutas src/tests si aplica; si no aplica, escribe n/a>',
            ]
        )
        if assistant_kind == 'codex':
            lines.append('Paquete estructurado:')
            lines.append(packet.strip())
        else:
            lines.append('Resumen estructurado del caso:')
            lines.extend(
                [
                    f"Diagnostico actual: {str((payload.get('probe_diagnosis') or {}).get('summary') or live_audit.get('summary') or user_goal).strip()}",
                    f"Incidente dominante: {self._incident_kind(payload) or 'n/d'}",
                    f"Evidencia util: {', '.join(list((payload.get('evidence_refs') or []))[:4]) or 'sin evidencia adicional'}",
                    'Si identificas que este caso ya requiere parche tecnico o cambio de repo, dilo explicitamente en el cambio recomendado.',
                ]
            )
            if packet.strip():
                lines.append('Paquete tecnico complementario:')
                lines.append(packet.strip())
        return '\n'.join(item for item in lines if item).strip()

    def _build_incident_query(self, *, payload: dict[str, Any], pending_issue_id: str) -> IncidentQuery:
        if pending_issue_id:
            return IncidentQuery(pending_issue_id=pending_issue_id, limit=5)
        run_id = str(payload.get('run_id') or '').strip()
        episode_id = self._episode_id(payload)
        incident_kind = self._incident_kind(payload)
        issue_hint = str((payload.get('probe_diagnosis') or {}).get('summary') or '').strip()
        return IncidentQuery(
            run_id=run_id or None,
            episode_id=episode_id or None,
            incident_kind=incident_kind,
            issue_hint=issue_hint,
            limit=5,
        )

    def _consultation_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(payload.get('metadata') or {})
        consultation = dict(metadata.get('autonomous_evolution') or {})
        if consultation:
            return consultation
        return dict(metadata.get('external_consultation') or {})

    def _assistant_kind_for_response(self, *, consultation: dict[str, Any], response: str) -> str:
        assistant_kind = str(consultation.get('actual_assistant_kind') or consultation.get('assistant_kind') or consultation.get('requested_assistant_kind') or '').strip().lower()
        if assistant_kind:
            return assistant_kind
        lowered = response.lower()
        if 'chatgpt' in lowered:
            return 'chatgpt'
        if 'claude' in lowered:
            return 'claude'
        if 'codex' in lowered:
            return 'codex'
        return 'codex'

    def _resolve_consultation_records(self, consultation: dict[str, Any]):
        repository = self.tool_teach_service.memory.repository
        task = None
        result = None
        task_id = str(consultation.get('task_id') or '').strip()
        result_id = str(consultation.get('result_id') or '').strip()
        if task_id:
            task = repository.get_task(task_id)
        if task is not None:
            results = repository.list_results(task_id=task.task_id, limit=5)
            if result_id:
                result = next((item for item in results if item.result_id == result_id), None)
            if result is None and results:
                result = results[0]
        elif result_id:
            results = repository.list_results(limit=50)
            result = next((item for item in results if item.result_id == result_id), None)
        return task, result

    def _parse_external_response(
        self,
        *,
        response: str,
        assistant_kind: str,
        payload: dict[str, Any],
        user_goal: str,
    ) -> dict[str, Any]:
        probable_cause = self._extract_named_value(response, ['Causa raiz probable', 'Probable cause'])
        recommended_change = self._extract_named_value(response, ['Cambio vertical recomendado', 'Cambio recomendado', 'Siguiente paso recomendado', 'Recommended change'])
        summary = probable_cause or self._extract_named_value(response, ['Diagnostico breve', 'Resumen', 'Summary']) or self._first_meaningful_line(response)
        file_scope = self._extract_file_scope(response)
        suggested_tests = self._extract_suggested_tests(response)
        lowered = response.lower()
        teaching_markers = ('ensenanza', 'reensenar', 'capturas visibles', 'submit', 'flujo guiado', 'teaching', 'visual')
        runtime_markers = ('runtime', 'threshold', 'backoff', 'sondeo', 'cola', 'drenado', 'retry', 'rebuild', 'ajustar')
        technical_markers = ('bridge', 'adapter', 'replay', 'capture_studio_viewmodel', 'browser_teach_session_service', 'interaction_learning_service', 'pytest', 'patch', 'archivo', '.py', 'file_scope')
        has_teaching = any(marker in lowered for marker in teaching_markers)
        has_runtime = any(marker in lowered for marker in runtime_markers)
        has_technical = bool(file_scope) or any(marker in lowered for marker in technical_markers)
        if has_technical:
            response_kind = 'code_fix'
        elif has_runtime:
            response_kind = 'runtime_tuning'
        elif has_teaching or assistant_kind in {'chatgpt', 'claude'}:
            response_kind = 'teaching_gap'
        else:
            response_kind = 'explanation'
        if response_kind == 'teaching_gap':
            next_action = 'open_teaching_studio'
        elif response_kind == 'runtime_tuning' and not file_scope:
            next_action = 'run_self_test'
        elif response_kind == 'code_fix':
            next_action = 'prepare_codex_packet'
        else:
            next_action = 'open_evolution_center'
        useful = bool(summary or recommended_change or file_scope or suggested_tests)
        signals = []
        if has_technical:
            signals.append('technical')
        if has_runtime:
            signals.append('runtime')
        if has_teaching:
            signals.append('teaching')
        confidence = min(0.95, 0.3 + (0.2 if summary else 0.0) + (0.2 if recommended_change else 0.0) + (0.15 if file_scope else 0.0) + (0.1 if suggested_tests else 0.0))
        codex_task_spec = {}
        if response_kind in {'code_fix', 'runtime_tuning'}:
            codex_task_spec = self._build_codex_task_spec(
                user_goal=user_goal,
                payload=payload,
                assistant_kind=assistant_kind,
                summary=summary,
                recommended_change=recommended_change,
                file_scope=file_scope,
                suggested_tests=suggested_tests,
            )
        detail = summary or recommended_change or 'La respuesta externa ya fue interpretada.'
        if recommended_change and recommended_change not in detail:
            detail = f"{detail} Siguiente accion sugerida: {recommended_change}"
        return {
            'summary': summary,
            'probable_cause': probable_cause or summary,
            'recommended_change': recommended_change,
            'file_scope': file_scope,
            'suggested_tests': suggested_tests,
            'response_kind': response_kind,
            'next_action': next_action,
            'confidence': round(confidence, 2),
            'useful': useful,
            'signals': signals,
            'codex_task_spec': codex_task_spec,
            'detail': detail,
        }

    def _validate_external_response(
        self,
        *,
        parsed: dict[str, Any],
        assistant_kind: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response_kind = str(parsed.get('response_kind') or '')
        useful = bool(parsed.get('useful'))
        confidence = float(parsed.get('confidence') or 0.0)
        file_scope = list(parsed.get('file_scope') or [])
        suggested_tests = list(parsed.get('suggested_tests') or [])
        goal_context = self._goal_context(payload)
        goal_blocker = str(goal_context.get('goal_blocker') or '').strip()
        sandbox_required = response_kind in {'code_fix', 'runtime_tuning'} or bool(file_scope)
        requires_human_approval = response_kind == 'code_fix' or bool(file_scope)
        rollback_ready = False
        structured_response = bool(parsed.get('recommended_change') or file_scope or suggested_tests)
        summary = str(parsed.get('summary') or '').strip()
        summary_signal = summary.lower()
        vague_markers = (
            'no se',
            'revisa eso',
            'revisa esto',
            'no estoy seguro',
            'no tengo suficiente contexto',
            'no puedo determinar',
        )
        vague_response = bool(summary_signal) and any(marker in summary_signal for marker in vague_markers)
        if not useful or confidence < 0.45 or not structured_response or vague_response:
            status = 'insufficient'
            validation_track = 'manual_review'
            rationale = 'La respuesta externa no trae suficiente estructura o confianza para adoptarla de forma segura.'
        elif response_kind == 'teaching_gap':
            status = 'approved'
            validation_track = 'teaching_replay'
            rationale = 'La respuesta orienta un refuerzo de ensenanza y replay, sin cambios directos sobre el repo.'
        elif response_kind == 'runtime_tuning' and not file_scope:
            status = 'approved'
            validation_track = 'runtime_self_test'
            rationale = 'El ajuste sugerido puede contrastarse con autotest y auditoria antes de consolidarlo.'
        else:
            status = 'review_needed'
            validation_track = 'packet_review'
            rationale = 'La respuesta implica cambios tecnicos o alcance suficiente para requerir revision guiada antes de adoptarla.'
        blockers = []
        if goal_blocker:
            blockers.append(goal_blocker)
        if sandbox_required:
            blockers.append('La adopcion debe pasar por sandbox o validacion equivalente antes de consolidarse.')
        if requires_human_approval:
            blockers.append('La respuesta no debe aplicarse sola fuera de la ruta guiada o del packet tecnico.')
        if not suggested_tests:
            blockers.append('Faltan pruebas concretas para validar la respuesta externa en el siguiente ciclo.')
        return {
            'status': status,
            'confidence': round(confidence, 2),
            'validation_track': validation_track,
            'sandbox_required': sandbox_required,
            'rollback_ready': rollback_ready,
            'requires_human_approval': requires_human_approval,
            'rationale': rationale,
            'blockers': self._merge_text_items([], blockers)[:4],
            'assistant_kind': assistant_kind,
        }

    def _build_adoption_plan(
        self,
        *,
        parsed: dict[str, Any],
        response_validation: dict[str, Any],
        consultation: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response_kind = str(parsed.get('response_kind') or '')
        validation_status = str(response_validation.get('status') or '')
        sandbox_required = bool(response_validation.get('sandbox_required'))
        requires_human_approval = bool(response_validation.get('requires_human_approval'))
        rollback_ready = bool(response_validation.get('rollback_ready'))
        if validation_status == 'insufficient':
            execution_lane = 'audit_again'
            next_action = 'audit_autonomy'
            status = 'insufficient'
            human_help = 'Conviene volver a auditar la autonomia o pedir una respuesta externa mas especifica.'
        elif response_kind == 'teaching_gap':
            execution_lane = 'teaching_replay'
            next_action = 'open_teaching_studio'
            status = 'ready'
            human_help = 'Refuerza la ensenanza y valida el replay auditado antes de darlo por aprendido.'
        elif response_kind == 'runtime_tuning' and not parsed.get('file_scope'):
            execution_lane = 'runtime_self_test'
            next_action = 'run_self_test'
            status = 'ready'
            human_help = 'Corre un autotest y conserva solo el ajuste que mejore el caso sin aumentar el riesgo.'
        elif response_kind == 'code_fix':
            execution_lane = 'codex_packet'
            next_action = 'prepare_codex_packet'
            status = 'guarded'
            human_help = 'Actualiza el packet tecnico y revisa el cambio propuesto antes de tocar el repo.'
        else:
            execution_lane = 'evolution_review'
            next_action = 'open_evolution_center'
            status = 'guarded'
            human_help = 'Revisa la evidencia consolidada antes de convertir la respuesta en una accion permanente.'
        validation_steps = []
        if sandbox_required:
            validation_steps.append('Validar en sandbox o via controlada antes de consolidar el cambio.')
        if parsed.get('suggested_tests'):
            validation_steps.extend(list(parsed.get('suggested_tests') or [])[:3])
        elif execution_lane == 'teaching_replay':
            validation_steps.append('Comparar replay auditado antes y despues del refuerzo.')
        elif execution_lane == 'runtime_self_test':
            validation_steps.append('Repetir autotest con la misma meta y comparar el outcome.')
        elif execution_lane == 'codex_packet':
            validation_steps.append('Revisar packet tecnico y aceptar solo cambios verificables con evidencia.')
        validation_steps = self._merge_text_items([], validation_steps)
        return {
            'status': status,
            'execution_lane': execution_lane,
            'next_action': next_action,
            'sandbox_required': sandbox_required,
            'rollback_ready': rollback_ready,
            'requires_human_approval': requires_human_approval,
            'validation_steps': validation_steps[:4],
            'human_help': human_help,
            'site_id': self._site_id(payload),
            'pending_issue_id': str(consultation.get('pending_issue_id') or ''),
        }

    def _build_codex_task_spec(
        self,
        *,
        user_goal: str,
        payload: dict[str, Any],
        assistant_kind: str,
        summary: str,
        recommended_change: str,
        file_scope: list[str],
        suggested_tests: list[str],
    ) -> dict[str, Any]:
        file_scope_items = [
            CodexFileScope(path=item.replace('\\', '/'), writable=item.replace('\\', '/').startswith('src/'), reason='Sugerido por la respuesta externa.')
            for item in file_scope[:6]
        ]
        acceptance = [
            CodexAcceptanceCriteria(description=summary or recommended_change or 'La causa raiz debe quedar explicada con evidencia reutilizable.')
        ]
        test_plan = CodexTestPlan(
            title='Pruebas sugeridas por la consulta externa',
            commands=suggested_tests[:4],
            expected_outcomes=['La siguiente iteracion debe dejar el caso mejor explicado o verificablemente corregido.'],
            metadata={'assistant_kind': assistant_kind},
        )
        context_pack = CodexContextPack(
            summary=summary or recommended_change or user_goal,
            evidence_refs=[item for item in [str(payload.get('pending_issue_id') or ''), self._incident_kind(payload)] if item],
            interaction_episode_ids=[item for item in [self._episode_id(payload)] if item],
            metadata={'assistant_kind': assistant_kind, 'site_id': self._site_id(payload)},
        )
        spec = CodexTaskSpec(
            title='Aplicar respuesta autonoma',
            goal=recommended_change or summary or user_goal,
            file_scope=file_scope_items,
            acceptance_criteria=acceptance,
            test_plan=test_plan,
            context_pack=context_pack,
            metadata={'assistant_kind': assistant_kind, 'autonomous_response': True},
        )
        return spec.model_dump(mode='json')

    def _merge_pending_issue(
        self,
        *,
        issue: CodexPendingIssue,
        parsed: dict[str, Any],
        assistant_kind: str,
        source: str,
        payload: dict[str, Any],
    ) -> CodexPendingIssue:
        evidence_refs = self._merge_text_items(
            list(issue.evidence_refs),
            [
                f"assistant:{assistant_kind}",
                f"response_source:{source}",
                *(f"file:{item}" for item in parsed['file_scope'][:4]),
            ],
        )
        suggested_tests = self._merge_text_items(list(issue.suggested_tests), list(parsed['suggested_tests']))
        metadata = {
            **dict(issue.metadata or {}),
            'external_consult_response': {
                'assistant_kind': assistant_kind,
                'summary': parsed['summary'],
                'recommended_change': parsed['recommended_change'],
                'next_action': str(parsed.get('adoption_plan', {}).get('next_action') or parsed['next_action']),
                'confidence': parsed['confidence'],
                'response_kind': parsed['response_kind'],
                'file_scope': list(parsed['file_scope']),
                'suggested_tests': list(parsed['suggested_tests']),
                'response_validation': dict(parsed.get('response_validation') or {}),
                'adoption_plan': dict(parsed.get('adoption_plan') or {}),
                'ingested_at_utc': datetime.now(timezone.utc).isoformat(),
            },
            'autonomous_response_codex_task_spec': dict(parsed['codex_task_spec'] or {}),
            'assistant_kind': assistant_kind,
            'site_id': self._site_id(payload),
        }
        updated = issue.model_copy(
            update={
                'summary': parsed['summary'] or issue.summary,
                'probable_cause': parsed['probable_cause'] or issue.probable_cause,
                'unresolved_reason': parsed['recommended_change'] or issue.unresolved_reason,
                'recommended_change': parsed['recommended_change'] or issue.recommended_change,
                'suggested_tests': suggested_tests[:8],
                'evidence_refs': evidence_refs[:12],
                'metadata': metadata,
            }
        )
        return self.pending_issue_repository.save(updated)

    def _attach_response_to_interaction_episode(self, *, result, response_metadata: dict[str, Any]) -> None:
        interaction_episode_id = str(result.metadata.get('interaction_episode_id') or '').strip()
        if not interaction_episode_id:
            return
        repository = self.tool_teach_service.memory.repository
        episode = repository.get_interaction_episode(interaction_episode_id)
        if episode is None:
            return
        updated_episode = episode.model_copy(
            update={
                'updated_at_utc': datetime.now(timezone.utc),
                'selector_reason': str(response_metadata.get('response_summary') or episode.selector_reason),
                'metadata': {
                    **dict(episode.metadata or {}),
                    'external_consult_response': response_metadata,
                    'audit_snapshot_id': str((episode.metadata or {}).get('audit_snapshot_id') or ''),
                },
            }
        )
        repository.save_interaction_episode(updated_episode)

    def _extract_named_value(self, text: str, labels: list[str]) -> str:
        lowered_labels = {label.lower() for label in labels}
        for match in self.SECTION_LINE_PATTERN.finditer(text):
            label = str(match.group('label') or '').strip().lower()
            if label in lowered_labels:
                value = str(match.group('value') or '').strip().strip('-').strip()
                trailing_match = re.search(
                    r"\s+(?:-\s*)?(?:Causa raiz probable|Probable cause|Cambio vertical recomendado|Cambio recomendado|Siguiente paso recomendado|Recommended change|Diagnostico breve|Resumen|Summary|Pruebas sugeridas|Suggested tests|Tests|file_scope)\s*:\s*",
                    value,
                    re.IGNORECASE,
                )
                if trailing_match:
                    value = value[: trailing_match.start()].strip()
                return value
        escaped_labels = '|'.join(re.escape(label) for label in labels)
        known_labels = (
            'Causa raiz probable',
            'Probable cause',
            'Cambio vertical recomendado',
            'Cambio recomendado',
            'Siguiente paso recomendado',
            'Recommended change',
            'Diagnostico breve',
            'Resumen',
            'Summary',
            'Pruebas sugeridas',
            'Suggested tests',
            'Tests',
            'file_scope',
        )
        all_labels = '|'.join(re.escape(label) for label in known_labels)
        inline_pattern = re.compile(
            rf"(?is)(?:^|[\s])(?:-\s*)?(?P<label>{escaped_labels})\s*:\s*(?P<value>.*?)(?=(?:\s+(?:-\s*)?(?:{all_labels})\s*:)|\Z)"
        )
        for match in inline_pattern.finditer(text):
            label = str(match.group('label') or '').strip().lower()
            if label in lowered_labels:
                return str(match.group('value') or '').strip().strip('-').strip()
        return ''

    def _first_meaningful_line(self, text: str) -> str:
        for raw_line in text.splitlines():
            line = raw_line.strip().strip('-').strip()
            if len(line) >= 12:
                return line
        return ''

    def _extract_file_scope(self, text: str) -> list[str]:
        found = []
        for match in self.FILE_SCOPE_PATTERN.findall(text):
            found.append(str(match).replace('\\', '/'))
        return self._merge_text_items([], found)

    def _extract_suggested_tests(self, text: str) -> list[str]:
        value = self._extract_named_value(text, ['Pruebas sugeridas', 'Suggested tests', 'Tests'])
        if not value:
            return []
        items = [item.strip(' -') for item in re.split(r'[,;]', value) if item.strip(' -')]
        return self._merge_text_items([], items)

    def _merge_text_items(self, base: list[str], extra: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for item in [*base, *extra]:
            value = str(item or '').strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            merged.append(value)
        return merged

    def _record_consultation_experiment(
        self,
        *,
        payload: dict[str, Any],
        user_goal: str,
        consultation: dict[str, Any],
        assistant_kind: str,
        parsed: dict[str, Any],
        response_validation: dict[str, Any],
        adoption_plan: dict[str, Any],
        source: str,
    ) -> dict[str, Any] | None:
        experiment_lab = getattr(self.tool_teach_service, 'experiment_lab', None)
        if experiment_lab is None:
            return None
        goal_parameters = self._goal_context(payload)
        diagnostic_category = str((payload.get('probe_diagnosis') or {}).get('category') or consultation.get('diagnostic_category') or parsed.get('response_kind') or '').strip()
        incident_kind = self._incident_kind(payload)
        subject_builder = getattr(self.tool_teach_service, '_external_lab_subject_keys', None)
        subject_keys: list[str] = []
        if callable(subject_builder):
            subject_keys = list(
                subject_builder(
                    goal_parameters=goal_parameters,
                    site_id=self._site_id(payload) or None,
                    diagnostic_category=diagnostic_category,
                    incident_kind=incident_kind,
                    assistant_preference=assistant_kind,
                )
            )
        if not subject_keys:
            site_id = self._site_id(payload)
            subject_keys = [site_id or 'general']
        domain = self._consultation_experiment_domain(
            assistant_kind=assistant_kind,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            response_kind=str(parsed.get('response_kind') or ''),
        )
        route = self._consultation_evaluation_route(assistant_kind=assistant_kind, consultation=consultation)
        validation_status = str(response_validation.get('status') or '')
        confidence = float(parsed.get('confidence') or response_validation.get('confidence') or 0.0)
        useful = bool(parsed.get('useful'))
        precision = self._consultation_precision(validation_status=validation_status, confidence=confidence, useful=useful)
        robustness = self._consultation_robustness(
            validation_status=validation_status,
            execution_lane=str(adoption_plan.get('execution_lane') or ''),
            sandbox_required=bool(response_validation.get('sandbox_required')),
            useful=useful,
        )
        progress_signal = self._consultation_progress_signal(
            validation_status=validation_status,
            execution_lane=str(adoption_plan.get('execution_lane') or ''),
            useful=useful,
        )
        evidence_refs = self._merge_text_items(
            [],
            [
                str(consultation.get('pending_issue_id') or ''),
                str(consultation.get('task_id') or ''),
                str(consultation.get('result_id') or ''),
                self._episode_id(payload),
                incident_kind,
            ],
        )
        run, recommendation = experiment_lab.record_outcome(
            domain=domain,
            objective=user_goal,
            subject_key=subject_keys[0],
            route=route,
            candidate_label=str(consultation.get('selected_tool_id') or assistant_kind or route.value),
            candidate_id=str(consultation.get('selected_tool_id') or consultation.get('result_id') or ''),
            success=validation_status in {'approved', 'review_needed'} and useful,
            observed_summary=str(parsed.get('summary') or parsed.get('recommended_change') or parsed.get('detail') or ''),
            expected_summary=user_goal,
            precision=precision,
            robustness=robustness,
            operational_cost=self._consultation_operational_cost(route),
            reuse_score=self._consultation_reuse_score(validation_status=validation_status, consultation=consultation),
            user_progress=progress_signal,
            execution_ms=int(consultation.get('execution_ms') or 0),
            evidence_refs=evidence_refs,
            metadata={
                'source': source,
                'assistant_kind': assistant_kind,
                'assistant_configuration': dict(consultation.get('assistant_configuration') or {}),
                'config_signature': str(consultation.get('config_signature') or ''),
                'selected_tool_id': str(consultation.get('selected_tool_id') or ''),
                'response_kind': str(parsed.get('response_kind') or ''),
                'validation_status': validation_status,
                'execution_lane': str(adoption_plan.get('execution_lane') or ''),
                'adoption_status': str(adoption_plan.get('status') or ''),
                'site_id': self._site_id(payload),
                'incident_kind': incident_kind,
                'diagnostic_category': diagnostic_category,
                'subject_keys': subject_keys,
                'goal_parameters': goal_parameters,
                'goal_progress_signal': progress_signal,
                'reused_later': bool(consultation.get('reuse_guard_active', False)),
                'trace_id': str((consultation.get('ia_trace_entry') or {}).get('trace_id') or ''),
                'comparison_scope_key': str(consultation.get('comparison_scope_key') or ''),
                'source_trace_ids': list(consultation.get('source_trace_ids') or []),
                'proposal_summary': str(consultation.get('proposal_summary') or '')[:240],
                'outcome_summary': str(parsed.get('summary') or parsed.get('recommended_change') or '')[:240],
            },
            suite_name='external_consultation',
        )
        return {
            'run_id': run.run_id,
            'recommendation_id': recommendation.recommendation_id,
            'trace_id': str((consultation.get('ia_trace_entry') or {}).get('trace_id') or ''),
            'comparison_scope_key': str(consultation.get('comparison_scope_key') or ''),
            'domain': domain.value,
            'subject_key': subject_keys[0],
            'subject_keys': subject_keys[:5],
            'route': route.value,
            'recommended_route': recommendation.recommended_route.value,
            'recommended_assistant_kind': recommendation.recommended_assistant_kind,
            'recommended_config_signature': recommendation.recommended_config_signature,
            'score': recommendation.score,
            'confidence': recommendation.confidence,
        }

    def _consultation_experiment_domain(
        self,
        *,
        assistant_kind: str,
        diagnostic_category: str,
        incident_kind: str,
        response_kind: str,
    ) -> ExperimentDomain:
        technical_incidents = {'bridge_lag', 'navigation_stall', 'session_restore_weak', 'visual_alignment_weak', 'critical_object_missing'}
        technical_categories = {'need_codex_fix', 'need_adapter'}
        if assistant_kind == 'codex' or diagnostic_category in technical_categories or incident_kind in technical_incidents or response_kind in {'code_fix', 'runtime_tuning'}:
            return ExperimentDomain.CODE
        return ExperimentDomain.LANGUAGE

    def _consultation_evaluation_route(self, *, assistant_kind: str, consultation: dict[str, Any]) -> EvaluationRoute:
        tool_id = str(consultation.get('selected_tool_id') or consultation.get('tool_id') or '').strip()
        if tool_id in {'chatgpt_web_assisted', 'claude_web_assisted'}:
            return EvaluationRoute.UI
        if assistant_kind == 'codex':
            return EvaluationRoute.CODE_AGENT
        if assistant_kind == 'ollama':
            return EvaluationRoute.LOCAL
        if assistant_kind in {'chatgpt', 'claude'}:
            return EvaluationRoute.LANGUAGE_UNDERSTANDING
        return EvaluationRoute.FALLBACK

    def _consultation_precision(self, *, validation_status: str, confidence: float, useful: bool) -> float:
        if validation_status == 'approved':
            return round(max(0.65, confidence), 4)
        if validation_status == 'review_needed':
            return round(max(0.42, confidence * 0.78), 4)
        return round(max(0.05, min(confidence * 0.25, 0.25)) if useful else 0.05, 4)

    def _consultation_robustness(self, *, validation_status: str, execution_lane: str, sandbox_required: bool, useful: bool) -> float:
        if validation_status == 'approved':
            if execution_lane == 'runtime_self_test':
                return 0.78
            if execution_lane == 'teaching_replay':
                return 0.74
            return 0.7
        if validation_status == 'review_needed':
            return 0.56 if sandbox_required else 0.5
        return 0.12 if useful else 0.05

    def _consultation_progress_signal(self, *, validation_status: str, execution_lane: str, useful: bool) -> float:
        if validation_status == 'approved':
            if execution_lane == 'teaching_replay':
                return 0.25
            if execution_lane == 'runtime_self_test':
                return 0.22
            return 0.18
        if validation_status == 'review_needed':
            return 0.1 if useful else 0.0
        return 0.0

    def _consultation_operational_cost(self, route: EvaluationRoute) -> float:
        costs = {
            EvaluationRoute.LOCAL: 0.06,
            EvaluationRoute.UI: 0.12,
            EvaluationRoute.LANGUAGE_UNDERSTANDING: 0.18,
            EvaluationRoute.CODE_AGENT: 0.28,
            EvaluationRoute.FALLBACK: 0.35,
        }
        return float(costs.get(route, 0.2))

    def _consultation_reuse_score(self, *, validation_status: str, consultation: dict[str, Any]) -> float:
        base = 0.6 if validation_status == 'approved' else 0.35 if validation_status == 'review_needed' else 0.08
        if bool(consultation.get('reuse_guard_active')):
            base = min(base + 0.1, 0.9)
        return round(base, 4)

    def _pending_category(self, raw_category: Any, assistant_kind: str) -> DiagnosticCategory:
        value = str(raw_category or '').strip()
        if value:
            try:
                return DiagnosticCategory(value)
            except ValueError:
                pass
        return DiagnosticCategory.NEED_CODEX_FIX if assistant_kind == 'codex' else DiagnosticCategory.NEED_TEACHING

    def _suggested_tests(self, payload: dict[str, Any], user_goal: str) -> list[str]:
        tests = [user_goal or 'Repetir objetivo actual en Centro de Control', 'Revisar Centro Evolutivo']
        if self._site_id(payload) == 'wplay':
            tests.insert(0, 'abre Wplay e inicia sesion')
        return tests[:4]

    def _goal_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        governance = dict(decision_context.get('governance') or {})
        context = dict(payload.get('context') or {})
        goal_context = dict(decision_context.get('goal_context') or context.get('goal_context') or metadata.get('goal_context') or {})
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        assistant_kind = str(governance.get('assistant_kind') or metadata.get('explicit_assistant_preference') or '').strip().lower()
        consultation_retry = dict(metadata.get('consultation_retry') or {})
        reingest_existing_response = bool(
            metadata.get('reingest_existing_response')
            or consultation_retry.get('reingest_only')
        )
        return {
            'objective_id': str(objective.get('objective_id') or ''),
            'objective_title': str(objective.get('title') or ''),
            'project_id': str(project.get('objective_id') or ''),
            'project_title': str(project.get('title') or ''),
            'task_id': str(task.get('objective_id') or ''),
            'task_title': str(task.get('title') or ''),
            'goal_status': str(goal_context.get('status') or ''),
            'goal_progress': float(goal_context.get('progress') or 0.0),
            'goal_blocker': str(goal_context.get('blocker') or ''),
            'goal_confidence': float(goal_context.get('confidence') or 0.0),
            'assistant_preference': assistant_kind,
            'assistant_kind': assistant_kind,
            'explicit_external_consultation': str(governance.get('diagnostic_category') or '').strip().lower() == 'explicit_external_consultation',
            'reingest_existing_response': reingest_existing_response,
        }


    def _live_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = dict(payload.get('context') or {})
        metadata = dict(payload.get('metadata') or {})
        return dict(context.get('live_audit') or metadata.get('live_audit') or {})

    def _site_id(self, payload: dict[str, Any]) -> str:
        context = dict(payload.get('context') or {})
        intent = dict(payload.get('intent') or {})
        return str(context.get('site_id') or intent.get('site_hint') or '').strip()

    def _incident_kind(self, payload: dict[str, Any]) -> str:
        if payload.get('incident_kind'):
            return str(payload.get('incident_kind') or '').strip()
        context = dict(payload.get('context') or {})
        readiness = dict(context.get('session_readiness') or {})
        recent = list(context.get('recent_incidents') or [])
        if readiness.get('dominant_incident'):
            return str(readiness.get('dominant_incident') or '').strip()
        if recent:
            first = recent[0]
            if isinstance(first, dict):
                return str(first.get('incident_kind') or '').strip()
        diagnosis_metadata = dict((payload.get('probe_diagnosis') or {}).get('metadata') or {})
        if diagnosis_metadata.get('incident_kind'):
            return str(diagnosis_metadata.get('incident_kind') or '').strip()
        return str(payload.get('root_issue') or '').strip()

    def _episode_id(self, payload: dict[str, Any]) -> str:
        if payload.get('episode_id'):
            return str(payload.get('episode_id') or '').strip()
        context = dict(payload.get('context') or {})
        teachings = list(context.get('recent_teachings') or [])
        if teachings and isinstance(teachings[0], dict):
            return str(teachings[0].get('episode_id') or '').strip()
        return ''











