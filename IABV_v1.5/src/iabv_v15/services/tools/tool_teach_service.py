from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    ApprovalDecision,
    ExecutionState,
    ExternalStateFlag,
    EvaluationRoute,
    ExperimentDomain,
    InferenceRequest,
    InferenceResult,
    IATraceEntry,
    InteractionMode,
    InteractionPattern,
    ModeSelectionDecision,
    ReasoningMode,
    ReportKind,
    RoleRoute,
    TaskRole,
    ToolAction,
    ToolActionType,
    ToolCapability,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
    canonical_external_state_flags,
)
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_adapters import ToolAdapter
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_validator import ToolValidator


class ToolTeachService:
    URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        memory: ToolMemory,
        sandbox: ToolSandbox,
        validator: ToolValidator,
        approval_policy: ToolApprovalPolicy,
        rollback_manager: ToolRollbackManager,
        adapters: dict[str, ToolAdapter],
        workspace_root: str,
        interaction_learning_service: InteractionLearningService | None = None,
        mode_selector: InteractionModeSelector | None = None,
        experiment_lab: ExperimentLab | None = None,
        live_audit_supervisor: LiveAuditSupervisor | None = None,
        synaptic_router: Any | None = None,
        intent_scoped_briefing_service: Any | None = None,
    ) -> None:
        self.registry = registry
        self.memory = memory
        self.sandbox = sandbox
        self.validator = validator
        self.approval_policy = approval_policy
        self.rollback_manager = rollback_manager
        self.adapters = adapters
        self.workspace_root = Path(workspace_root)
        self.interaction_learning_service = interaction_learning_service
        self.mode_selector = mode_selector
        self.experiment_lab = experiment_lab
        self.live_audit_supervisor = live_audit_supervisor
        self.synaptic_router = synaptic_router
        self.intent_scoped_briefing_service = intent_scoped_briefing_service

    def _assistant_configuration_snapshot(
        self,
        *,
        request: InferenceRequest | None = None,
        task: ToolTask | None = None,
        result: ToolResult | None = None,
        tool_id: str = '',
        assistant_kind: str = '',
        metadata: dict[str, Any] | None = None,
        context_pack: str = '',
    ) -> AssistantConfigurationSnapshot:
        payload = dict(metadata or {})
        if request is not None:
            payload = {**dict(request.metadata or {}), **payload}
        goal_parameters = dict(request.goal_parameters or {}) if request is not None else {}
        if task is not None:
            payload = {**dict(task.metadata or {}), **payload}
            goal_parameters = {**dict(task.metadata.get('goal_parameters') or {}), **goal_parameters}
        if result is not None:
            payload = {**dict(result.metadata or {}), **dict(result.execution_state.metadata or {}), **payload}
        resolved_tool_id = str(tool_id or (task.tool_id if task is not None else '') or payload.get('tool_id') or goal_parameters.get('tool_id') or '').strip()
        resolved_assistant_kind = str(
            assistant_kind
            or payload.get('actual_assistant_kind')
            or payload.get('assistant_kind')
            or payload.get('requested_assistant_kind')
            or goal_parameters.get('assistant_kind')
            or goal_parameters.get('assistant_preference')
            or self._assistant_family_for_tool_id(resolved_tool_id)
        ).strip().lower()
        goal_context_pack = str(context_pack or payload.get('context_pack') or goal_parameters.get('context_pack') or '').strip()
        unresolved_fields: list[str] = []
        attachments_mode = 'without_files'
        attachments_support = 'UNRESOLVED'
        unresolved_fields.append('attachments_mode')
        planning_mode = 'with_plan' if bool(goal_parameters.get('enable_planning', request.enable_planning if request is not None else False) or payload.get('enable_planning')) else 'without_plan'
        reasoning_level = 'extended' if bool((request.deep_reasoning if request is not None else False) or payload.get('deep_reasoning') or str(payload.get('diagnostic_category') or '') in {'need_codex_fix', 'need_adapter', 'code_fix', 'runtime_tuning'}) else 'normal'
        context_mode = 'long' if len(goal_context_pack) > 1200 else 'short'
        tools_mode = 'with_tools' if resolved_tool_id else 'without_tools'
        launch_mode = str(payload.get('launch_mode') or '').strip().lower()
        browser_mode = 'with_browser' if resolved_tool_id.endswith('_web_assisted') or launch_mode in {'browser', 'web_assisted'} else 'without_browser'
        assistant_mode = 'code' if resolved_assistant_kind in {'codex'} or str(payload.get('diagnostic_category') or '') in {'need_codex_fix', 'need_adapter', 'code_fix', 'runtime_tuning'} else 'general'
        origin_mode = 'local' if resolved_tool_id == 'ollama_llm' or resolved_assistant_kind == 'ollama' else 'external'
        return AssistantConfigurationSnapshot(
            planning_mode=planning_mode,
            attachments_mode=attachments_mode,
            reasoning_level=reasoning_level,
            context_mode=context_mode,
            tools_mode=tools_mode,
            browser_mode=browser_mode,
            assistant_mode=assistant_mode,
            origin_mode=origin_mode,
            unresolved_fields=unresolved_fields,
            metadata={
                'assistant_kind': resolved_assistant_kind,
                'tool_id': resolved_tool_id,
                'attachments_support': attachments_support,
                'context_pack_length': len(goal_context_pack),
            },
        )

    def _config_signature(self, config: AssistantConfigurationSnapshot) -> str:
        return '|'.join(
            (
                config.planning_mode,
                config.attachments_mode,
                config.reasoning_level,
                config.context_mode,
                config.tools_mode,
                config.browser_mode,
                config.assistant_mode,
                config.origin_mode,
            )
        )

    def _comparison_scope_key(
        self,
        *,
        user_goal: str = '',
        site_id: str | None = None,
        goal_parameters: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        subject_key: str = '',
    ) -> str:
        payload = {**dict(goal_parameters or {}), **dict(metadata or {})}
        objective = dict(payload.get('objective') or {})
        project = dict(payload.get('project') or {})
        task = dict(payload.get('task') or {})
        for candidate in (
            str(payload.get('pending_issue_id') or ''),
            str(task.get('objective_id') or ''),
            str(project.get('objective_id') or ''),
            str(objective.get('objective_id') or ''),
            str(payload.get('task_id') or ''),
            str(payload.get('project_id') or ''),
            str(payload.get('objective_id') or ''),
            str(subject_key or ''),
        ):
            probe = candidate.strip()
            if probe:
                return probe
        site_prefix = str(site_id or payload.get('site_id') or payload.get('site_hint') or 'general').strip() or 'general'
        compact = '-'.join(
            token
            for token in (
                ''.join(character for character in raw if character.isalnum())
                for raw in str(user_goal or payload.get('title') or '').lower().split()
            )
            if token
        )[:72].strip('-')
        return f'{site_prefix}:{compact or "general"}'

    def _source_trace_ids_from_payload(
        self,
        *,
        request: InferenceRequest | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        payload = dict(metadata or {})
        sources: list[Any] = [
            payload.get('ia_trace'),
            payload.get('source_trace_ids'),
            dict(payload.get('perception_snapshot') or {}).get('ia_trace'),
        ]
        if request is not None:
            request_metadata = dict(request.metadata or {})
            sources.extend(
                [
                    request_metadata.get('ia_trace'),
                    request_metadata.get('source_trace_ids'),
                    dict(request_metadata.get('perception_snapshot') or {}).get('ia_trace'),
                ]
            )
        trace_ids: list[str] = []
        for source in sources:
            if isinstance(source, dict):
                source = [source]
            if isinstance(source, (list, tuple, set)):
                for item in source:
                    probe = str((item or {}).get('trace_id') if isinstance(item, dict) else item or '').strip()
                    if probe and probe not in trace_ids:
                        trace_ids.append(probe)
            else:
                probe = str(source or '').strip()
                if probe and probe not in trace_ids:
                    trace_ids.append(probe)
        return trace_ids[:8]

    def _compact_summary(self, text: Any, *, limit: int = 240) -> str:
        return ' '.join(str(text or '').split())[:limit]

    def _proposal_summary(
        self,
        *,
        user_goal: str = '',
        title: str = '',
        context_pack: str = '',
        metadata: dict[str, Any] | None = None,
    ) -> str:
        payload = dict(metadata or {})
        return self._compact_summary(
            context_pack
            or payload.get('proposal_summary')
            or payload.get('context_pack')
            or title
            or user_goal
            or payload.get('objective')
            or ''
        )

    def _outcome_summary(
        self,
        *,
        result: ToolResult | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        payload = dict(metadata or {})
        execution_metadata = dict(result.execution_state.metadata or {}) if result is not None else {}
        return self._compact_summary(
            payload.get('outcome_summary')
            or payload.get('response_summary')
            or (result.output_text if result is not None else '')
            or payload.get('adoption_status')
            or payload.get('validation_status')
            or execution_metadata.get('detail')
            or payload.get('detail')
            or ''
        )

    def _trace_route(self, *, tool_id: str, assistant_kind: str) -> str:
        resolved_tool_id = str(tool_id or '').strip().lower()
        resolved_assistant = str(assistant_kind or '').strip().lower()
        if resolved_tool_id in {'chatgpt_web_assisted', 'claude_web_assisted'}:
            return EvaluationRoute.UI.value
        if resolved_assistant == 'codex':
            return EvaluationRoute.CODE_AGENT.value
        if resolved_assistant == 'ollama':
            return EvaluationRoute.LOCAL.value
        if resolved_assistant in {'chatgpt', 'claude'}:
            return EvaluationRoute.LANGUAGE_UNDERSTANDING.value
        return EvaluationRoute.FALLBACK.value

    def _external_state_flags_for_trace(
        self,
        *,
        task: ToolTask | None = None,
        result: ToolResult | None = None,
    ) -> list[str]:
        task_metadata = dict(task.metadata or {}) if task is not None else {}
        result_metadata = dict(result.metadata or {}) if result is not None else {}
        execution_metadata = dict(result.execution_state.metadata or {}) if result is not None else {}
        flags = canonical_external_state_flags(
            [
                *(task_metadata.get('external_state_flags') or []),
                *(result_metadata.get('external_state_flags') or []),
                *(execution_metadata.get('external_state_flags') or []),
                *(result_metadata.get('coherence_flags') or []),
                *(execution_metadata.get('coherence_flags') or []),
            ]
        )
        # Verificar expiración de awaiting_response (más de 5 minutos = expirado)
        awaiting_response_expired = False
        last_capture_attempt = str(execution_metadata.get('last_capture_attempt_utc') or task_metadata.get('last_capture_attempt_utc') or '').strip()
        if last_capture_attempt:
            try:
                from datetime import datetime, timezone, timedelta
                attempt_time = datetime.fromisoformat(last_capture_attempt.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) - attempt_time > timedelta(minutes=5):
                    awaiting_response_expired = True
            except Exception:
                pass

        if str((result.execution_state.state if result is not None else '') or task_metadata.get('status') or '').strip().lower() == ExternalStateFlag.AWAITING_RESPONSE.value:
            if not awaiting_response_expired and ExternalStateFlag.AWAITING_RESPONSE.value not in flags:
                flags.append(ExternalStateFlag.AWAITING_RESPONSE.value)
        if bool(execution_metadata.get('response_capture_pending')):
            if not awaiting_response_expired and ExternalStateFlag.AWAITING_RESPONSE.value not in flags:
                flags.append(ExternalStateFlag.AWAITING_RESPONSE.value)
        # Si expiró, marcar como session_expired para limpiar bloqueos
        if awaiting_response_expired and ExternalStateFlag.SESSION_EXPIRED.value not in flags:
            flags.append(ExternalStateFlag.SESSION_EXPIRED.value)
        capture_error = str(
            execution_metadata.get('auto_capture_reason')
            or execution_metadata.get('error_message')
            or result_metadata.get('error_message')
            or ''
        ).strip().lower()
        if bool(execution_metadata.get('assistant_login_required')):
            if ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value not in flags:
                flags.append(ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value)
        if bool(execution_metadata.get('missing_thread_tracking')) or capture_error == 'codex_state_missing':
            if ExternalStateFlag.MISSING_THREAD_TRACKING.value not in flags:
                flags.append(ExternalStateFlag.MISSING_THREAD_TRACKING.value)
        thread_verification = str(execution_metadata.get('thread_verification') or '').strip().lower()
        if thread_verification in {ExternalStateFlag.WRONG_THREAD.value, 'thread_mismatch', 'mismatch'} or bool(execution_metadata.get('thread_mismatch')):
            if ExternalStateFlag.WRONG_THREAD.value not in flags:
                flags.append(ExternalStateFlag.WRONG_THREAD.value)
        if bool(execution_metadata.get('session_expired')) or str(execution_metadata.get('session_status') or '').strip().lower() == 'expired':
            if ExternalStateFlag.SESSION_EXPIRED.value not in flags:
                flags.append(ExternalStateFlag.SESSION_EXPIRED.value)
        quota_status = str(execution_metadata.get('quota_status') or '').strip().lower()
        rate_limit_status = str(execution_metadata.get('rate_limit_status') or '').strip().lower()
        plan_status = str(execution_metadata.get('plan_status') or '').strip().lower()
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
        response_capture_mode = str(execution_metadata.get('response_capture_mode') or task_metadata.get('response_capture_mode') or '').strip().lower()
        launched = bool(execution_metadata.get('launched'))
        response_captured = bool(execution_metadata.get('response_captured'))
        if (
            capture_error in {'browser_dom_unavailable', 'browser_dom_launch_failed', 'browser_dom_capture_pending'}
            or (
                response_capture_mode in {'clipboard_capture', 'dom_capture', 'browser_dom'}
                and (launched or bool(execution_metadata.get('auto_capture_attempted')))
                and not response_captured
                and not bool(execution_metadata.get('assistant_login_required'))
            )
        ):
            if ExternalStateFlag.CAPTURE_UNVERIFIED.value not in flags:
                flags.append(ExternalStateFlag.CAPTURE_UNVERIFIED.value)
        if ExternalStateFlag.WRONG_THREAD.value in flags and ExternalStateFlag.CAPTURE_UNVERIFIED.value not in flags:
            flags.append(ExternalStateFlag.CAPTURE_UNVERIFIED.value)
        return flags

    def _build_ia_trace_entry(
        self,
        *,
        task: ToolTask,
        result: ToolResult | None = None,
        assistant_kind: str = '',
    ) -> IATraceEntry:
        task_metadata = dict(task.metadata or {})
        result_metadata = dict(result.metadata or {}) if result is not None else {}
        execution_metadata = dict(result.execution_state.metadata or {}) if result is not None else {}
        resolved_assistant_kind = str(
            assistant_kind
            or execution_metadata.get('assistant_kind')
            or result_metadata.get('assistant_kind')
            or task_metadata.get('actual_assistant_kind')
            or task_metadata.get('assistant_kind')
            or self._assistant_family_for_tool_id(task.tool_id)
        ).strip().lower()
        assistant_configuration = self._assistant_configuration_snapshot(
            task=task,
            result=result,
            tool_id=task.tool_id,
            assistant_kind=resolved_assistant_kind,
            metadata={**task_metadata, **result_metadata, **execution_metadata},
            context_pack=str(task_metadata.get('context_pack') or ''),
        )
        config_signature = self._config_signature(assistant_configuration)
        external_state_flags = self._external_state_flags_for_trace(task=task, result=result)
        comparison_scope_key = self._comparison_scope_key(
            user_goal=str(task.objective or ''),
            site_id=task.site_id,
            goal_parameters=dict(task_metadata.get('goal_parameters') or {}),
            metadata={**task_metadata, **result_metadata, **execution_metadata},
            subject_key=str(task_metadata.get('subject_key') or ''),
        )
        source_trace_ids = self._source_trace_ids_from_payload(metadata={**task_metadata, **result_metadata, **execution_metadata})
        return IATraceEntry(
            assistant_kind=resolved_assistant_kind,
            requested_assistant_kind=str(task_metadata.get('requested_assistant_kind') or task_metadata.get('assistant_kind') or resolved_assistant_kind),
            actual_assistant_kind=str(task_metadata.get('actual_assistant_kind') or resolved_assistant_kind),
            assistant_configuration=assistant_configuration,
            config_signature=config_signature,
            comparison_scope_key=comparison_scope_key,
            source_trace_ids=source_trace_ids,
            route=self._trace_route(tool_id=task.tool_id, assistant_kind=resolved_assistant_kind),
            tool_id=str(task.tool_id or ''),
            task_id=task.task_id,
            result_id=result.result_id if result is not None else '',
            session_scope=str(execution_metadata.get('session_scope') or task_metadata.get('session_scope') or ''),
            thread_key=str(execution_metadata.get('thread_key') or task_metadata.get('thread_key') or ''),
            thread_title=str(execution_metadata.get('thread_title') or task_metadata.get('thread_title') or ''),
            capture_lane=str(execution_metadata.get('capture_lane') or task_metadata.get('capture_lane') or ''),
            state=str((result.execution_state.state if result is not None else '') or task.status.value),
            detail=str((result.execution_state.detail if result is not None else '') or result_metadata.get('awaiting_reason') or task_metadata.get('awaiting_reason') or ''),
            proposal_summary=self._proposal_summary(
                user_goal=str(task.objective or ''),
                title=str(task.title or ''),
                context_pack=str(task_metadata.get('context_pack') or ''),
                metadata={**task_metadata, **result_metadata, **execution_metadata},
            ),
            outcome_summary=self._outcome_summary(result=result, metadata={**task_metadata, **result_metadata, **execution_metadata}),
            result_label=str((result.output_text if result is not None else '') or task.title or task.objective)[:240],
            success=bool(result.success) if result is not None else False,
            execution_ms=int((result.execution_ms if result is not None else 0) or execution_metadata.get('execution_ms') or 0),
            confidence=float(result_metadata.get('response_confidence') or result_metadata.get('confidence') or execution_metadata.get('confidence') or 0.0),
            evidence_refs=[
                item
                for item in [
                    str(task.site_id or ''),
                    task.task_id,
                    result.result_id if result is not None else '',
                    str(task_metadata.get('pending_issue_id') or ''),
                    str(task_metadata.get('interaction_episode_id') or ''),
                ]
                if str(item).strip()
            ],
            reused_later=bool(task_metadata.get('reuse_guard_active', False) or result_metadata.get('reused_later', False)),
            verdict=str(result_metadata.get('validation_status') or result_metadata.get('adoption_status') or (result.execution_state.state if result is not None else '') or ''),
            coherence_flags=list(result_metadata.get('coherence_flags') or execution_metadata.get('coherence_flags') or task_metadata.get('coherence_flags') or []),
            external_state_flags=external_state_flags,
            metadata={
                'response_capture_mode': str(execution_metadata.get('response_capture_mode') or task_metadata.get('response_capture_mode') or ''),
                'background_capture_mode': str(execution_metadata.get('background_capture_mode') or task_metadata.get('background_capture_mode') or ''),
                'comparison_scope_key': comparison_scope_key,
            },
        )

    def preview_request(self, request: InferenceRequest) -> dict[str, Any]:
        task = self.build_task_from_request(request)
        card = self.registry.pick_card_for_task(
            task,
            preferred_assistant_kind=str(task.metadata.get('synaptic_preferred_assistant_kind') or ''),
        )
        if card is None:
            return {'available': False, 'summary': 'No encontre una herramienta local registrada para esta tarea.'}
        task = task.model_copy(update={'tool_id': card.tool_id})
        task = self._sync_external_consultation_task(task, card)
        assistant_configuration = self._assistant_configuration_snapshot(
            task=task,
            tool_id=card.tool_id,
            assistant_kind=str(task.metadata.get('assistant_kind') or self._assistant_family_for_tool_id(card.tool_id)),
            metadata={'launch_mode': str((card.metadata or {}).get('launch_mode') or '')},
            context_pack=str(task.metadata.get('context_pack') or ''),
        )
        task = task.model_copy(
            update={
                'metadata': {
                    **dict(task.metadata or {}),
                    'assistant_configuration': assistant_configuration.model_dump(mode='json'),
                    'config_signature': self._config_signature(assistant_configuration),
                }
            }
        )
        task = self.approval_policy.evaluate(card=card, task=task)
        adapter = self.adapters.get(card.adapter_key)
        interaction_patterns: list[dict[str, Any]] = []
        if self.interaction_learning_service is not None:
            interaction_patterns = [
                self.interaction_learning_service.pattern_summary(item)
                for item in self.interaction_learning_service.match_patterns(card=card, task=task, limit=3)
            ]
        mode_selection = dict(task.metadata.get('mode_selection') or {})
        return {
            'available': bool(adapter and card.available),
            'tool_card': card.model_dump(mode='json'),
            'tool_task': task.model_dump(mode='json'),
            'interaction_patterns': interaction_patterns,
            'mode_selection': mode_selection,
            'summary': self._preview_summary(card, task, interaction_patterns, mode_selection),
        }

    def handle(self, request: InferenceRequest) -> tuple[RoleRoute, InferenceResult]:
        preview = self.preview_request(request)
        detected_role = request.task_role if request.task_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} else TaskRole.TOOL_USE
        summary = str(preview.get('summary') or 'No pude preparar la herramienta local.')
        route = RoleRoute(
            task_role=detected_role,
            role_title='Tool Teaching local-first',
            provider_name='Tool local-first runtime',
            model_profile_id='general-qwen',
            model_name='tool-local-runtime',
            tool_chain=[ToolCapability.TOOL_EXECUTION, ToolCapability.TOOL_SANDBOX, ToolCapability.LOCAL_LLM],
            reason='Ruta local-first de herramientas reutilizando el runtime desktop existente.',
        )
        result = InferenceResult(
            request_id=request.request_id,
            provider_name='Tool local-first runtime',
            reasoning_mode=ReasoningMode.LOCAL,
            summary=summary,
            inferred_task=request.user_goal,
            confidence=0.78 if preview.get('available') else 0.42,
            used_tools=route.tool_chain,
            sources=['tool_registry', 'tool_memory'],
            report_kind=ReportKind.TOOL_EXECUTION,
            detected_role=detected_role,
            executor_model='tool-local-runtime',
            next_actions=['Simular herramienta', 'Revisar herramientas conocidas'],
            raw_output={'tool_preview': preview},
        )
        return route, result

    def build_task_from_request(self, request: InferenceRequest) -> ToolTask:
        goal_parameters = request.goal_parameters or {}
        suggested_tool_id = str(goal_parameters.get('tool_id') or self._suggest_tool_id(request.user_goal))
        title = str(request.goal_parameters.get('title') or request.user_goal[:80])
        expected = str(request.goal_parameters.get('expected_outcome') or 'Resultado validado de la herramienta.')
        site_id = str(request.goal_parameters.get('site_id') or request.site_hint or '') or None
        selection = self._select_mode(request=request, suggested_tool_id=suggested_tool_id, site_id=site_id)
        synaptic_decision = self._synaptic_decision_for_request(request)
        synaptic_preferred_assistant_kind = str(synaptic_decision.get('selected_assistant_kind') or '')
        if synaptic_preferred_assistant_kind and not str(goal_parameters.get('tool_id') or '').strip():
            preferred_card = self.registry.pick_card_for_task(
                ToolTask(
                    tool_id='',
                    title=title,
                    objective=request.user_goal,
                    requested_by_role=request.task_role if request.task_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} else TaskRole.TOOL_USE,
                ),
                preferred_assistant_kind=synaptic_preferred_assistant_kind,
            )
            if preferred_card is not None:
                suggested_tool_id = preferred_card.tool_id
                selection = self._select_mode(request=request, suggested_tool_id=suggested_tool_id, site_id=site_id)
        selection = self._enforce_explicit_external_selection(request=request, selection=selection, suggested_tool_id=suggested_tool_id)
        tool_id = str(selection.selected_tool_id or suggested_tool_id)
        reusable_pattern = self._pattern_from_selection(selection)
        actions = self._build_actions(request, tool_id, reusable_pattern)

        # Cognitive bootstrap: apply IABV context via IntentScopedBriefingService
        context_pack = str(goal_parameters.get('context_pack') or '')
        if self.intent_scoped_briefing_service is not None and not context_pack:
            try:
                assistant_id = self._assistant_family_for_tool_id(tool_id)
                force_impact = str(request.metadata.get('force_impact') or goal_parameters.get('force_impact') or '')
                briefing_result = self.intent_scoped_briefing_service.compose_for_assistant(
                    assistant_id=assistant_id,
                    user_prompt=request.user_goal,
                    intent=None,
                    task_context=None,
                    force_impact=force_impact if force_impact in ('high', 'low') else None,
                )
                if briefing_result.used_briefing:
                    context_pack = briefing_result.composed_prompt
            except Exception:
                context_pack = str(goal_parameters.get('context_pack') or '')

        now = datetime.now(timezone.utc).isoformat()
        assistant_configuration = self._assistant_configuration_snapshot(
            request=request,
            tool_id=tool_id,
            assistant_kind=str(goal_parameters.get('assistant_kind') or goal_parameters.get('assistant_preference') or self._assistant_family_for_tool_id(tool_id)),
            metadata={'diagnostic_category': str(goal_parameters.get('diagnostic_category') or ''), 'launch_mode': str(goal_parameters.get('launch_mode') or '')},
            context_pack=context_pack,
        )
        config_signature = self._config_signature(assistant_configuration)
        comparison_scope_key = self._comparison_scope_key(
            user_goal=request.user_goal,
            site_id=site_id,
            goal_parameters=dict(goal_parameters),
            metadata=dict(request.metadata or {}),
            subject_key=str(goal_parameters.get('subject_key') or ''),
        )
        source_trace_ids = self._source_trace_ids_from_payload(request=request, metadata=dict(goal_parameters))
        proposal_summary = self._proposal_summary(
            user_goal=request.user_goal,
            title=title,
            context_pack=context_pack,
            metadata={**dict(request.metadata or {}), **dict(goal_parameters)},
        )
        task = ToolTask(
            tool_id=tool_id,
            title=title,
            objective=request.user_goal,
            requested_by_role=request.task_role if request.task_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} else TaskRole.TOOL_USE,
            actions=actions,
            rollback_actions=self._build_rollback_actions(request, tool_id),
            execution_scope=str(request.goal_parameters.get('execution_scope') or 'read_only'),
            sandbox_first=True,
            site_id=site_id,
            expected_outcome=expected,
            metadata={
                'goal_parameters': dict(request.goal_parameters),
                'created_at_utc': now,
                'updated_at_utc': now,
                'mode_selection': selection.model_dump(mode='json'),
                'synaptic_routing_decision': synaptic_decision,
                'synaptic_preferred_assistant_kind': synaptic_preferred_assistant_kind,
                'already_resolved': selection.already_resolved,
                'equivalent_pattern_exists': selection.equivalent_pattern_exists,
                'improvement_already_implemented': selection.improvement_already_implemented,
                'reuse_guard_active': bool(selection.already_resolved or selection.equivalent_pattern_exists),
                'reused_pattern_id': selection.reusable_pattern_id or '',
                'reused_episode_id': selection.reusable_episode_id or '',
                'adapter_exists': selection.adapter_exists,
                'selected_mode': selection.selected_mode.value,
                'selector_reason': selection.reason,
                'requested_tool_id': suggested_tool_id,
                'reused_actions_from_pattern': bool(reusable_pattern is not None and actions and all(item.metadata.get('reused_from_pattern') for item in actions)),
                'requested_assistant_kind': str(goal_parameters.get('assistant_preference') or goal_parameters.get('assistant_kind') or ''),
                'assistant_kind': str(goal_parameters.get('assistant_kind') or goal_parameters.get('assistant_preference') or ''),
                'actual_assistant_kind': self._assistant_family_for_tool_id(tool_id),
                'consultation_scope': str(goal_parameters.get('consultation_scope') or ''),
                'response_capture_mode': str(goal_parameters.get('response_capture_mode') or ''),
                'requires_manual_pasteback': bool(goal_parameters.get('requires_manual_pasteback', False)),
                'diagnostic_category': str(goal_parameters.get('diagnostic_category') or ''),
                'incident_kind': str(goal_parameters.get('incident_kind') or ''),
                'dry_run_launch': bool(goal_parameters.get('dry_run_launch', False)),
                'lab_recommendation': dict(goal_parameters.get('lab_recommendation') or {}),
                'context_pack': str(goal_parameters.get('context_pack') or ''),
                'comparison_scope_key': comparison_scope_key,
                'source_trace_ids': source_trace_ids,
                'proposal_summary': proposal_summary,
                'thread_key': str(goal_parameters.get('thread_key') or ''),
                'thread_title': str(goal_parameters.get('thread_title') or ''),
                'capture_lane': str(goal_parameters.get('capture_lane') or ''),
                'lane_priority': list(goal_parameters.get('lane_priority') or []),
                'awaiting_reason': str(goal_parameters.get('awaiting_reason') or ''),
                'last_capture_attempt_utc': str(goal_parameters.get('last_capture_attempt_utc') or ''),
                'reused_thread': bool(goal_parameters.get('reused_thread', False)),
                'session_profile_dir': str(goal_parameters.get('session_profile_dir') or ''),
                'session_scope': str(goal_parameters.get('session_scope') or ''),
                'session_label': str(goal_parameters.get('session_label') or ''),
                'isolated_session_required': bool(goal_parameters.get('isolated_session_required', False)),
                'background_capture_mode': str(goal_parameters.get('background_capture_mode') or ''),
                'assistant_configuration': assistant_configuration.model_dump(mode='json'),
                'config_signature': config_signature,
            },
        )
        trace_entry = self._build_ia_trace_entry(task=task)
        return task.model_copy(
            update={
                'metadata': {
                    **dict(task.metadata or {}),
                    'ia_trace_entry': trace_entry.model_dump(mode='json'),
                }
            }
        )

    def build_task_for_session(self, session) -> ToolTask:
        goal_parameters = dict(session.metadata.get('goal_parameters') or {})
        request = InferenceRequest(
            user_goal=session.user_goal,
            prompt=session.user_goal,
            task_role=session.intent.detected_role,
            goal_parameters=goal_parameters,
            site_hint=session.intent.site_hint,
            metadata={'adaptive_session_id': session.session_id},
        )
        task = self.build_task_from_request(request)
        return task.model_copy(
            update={
                'session_id': session.session_id,
                'run_id': session.run_id,
                'pack_id': session.chosen_pack_id,
                'site_id': session.context.site_id or session.intent.site_hint,
            }
        )

    def preview_external_consultation(
        self,
        *,
        user_goal: str,
        assistant_preference: str,
        context_pack: str,
        site_id: str | None = None,
        diagnostic_category: str = '',
        incident_kind: str = '',
        launch_dry_run: bool = False,
        allow_local_automatic_consultation: bool = False,
        goal_parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = self._build_external_consultation_request(
            user_goal=user_goal,
            assistant_preference=assistant_preference,
            context_pack=context_pack,
            site_id=site_id,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            launch_dry_run=launch_dry_run,
            allow_local_automatic_consultation=allow_local_automatic_consultation,
            goal_parameters=goal_parameters,
        )
        preview = self.preview_request(request)
        preview['context_pack'] = context_pack
        preview['assistant_preference'] = assistant_preference
        return preview

    def execute_external_consultation(
        self,
        *,
        user_goal: str,
        assistant_preference: str,
        context_pack: str,
        site_id: str | None = None,
        diagnostic_category: str = '',
        incident_kind: str = '',
        approved: bool = True,
        launch_dry_run: bool = False,
        allow_local_automatic_consultation: bool = False,
        goal_parameters: dict[str, Any] | None = None,
    ) -> tuple[ToolTask, ToolResult, dict[str, Any]]:
        request = self._build_external_consultation_request(
            user_goal=user_goal,
            assistant_preference=assistant_preference,
            context_pack=context_pack,
            site_id=site_id,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            launch_dry_run=launch_dry_run,
            allow_local_automatic_consultation=allow_local_automatic_consultation,
            goal_parameters=goal_parameters,
        )
        preview = self.preview_request(request)
        task = self.build_task_from_request(request)
        result = self.execute_task(task, approved=approved)
        stored_task = self.memory.repository.get_task(task.task_id) or task
        return stored_task, result, preview

    def execute_task(self, task: ToolTask, *, approved: bool = False) -> ToolResult:
        card = self.registry.pick_card_for_task(
            task,
            preferred_assistant_kind=str(task.metadata.get('synaptic_preferred_assistant_kind') or ''),
        )
        if card is None:
            result = ToolResult(
                task_id=task.task_id,
                tool_id=task.tool_id,
                tool_type=self._tool_type_for_unknown(task.tool_id),
                success=False,
                validation_status=ToolValidationStatus.BLOCKED,
                execution_state=ExecutionState(state='missing_tool', detail='No encontre una ToolCard registrada para esta tarea.', destructive_blocked=True),
                error_message='tool_card_missing',
            )
            self.memory.audit_event(
                tool_id=task.tool_id or 'unknown_tool',
                task_id=task.task_id,
                action_type='preflight',
                state='missing_tool',
                payload={'reason': 'tool_card_missing', 'objective': task.objective},
            )
            if self.live_audit_supervisor is not None:
                result = self.live_audit_supervisor.audit_tool_result(card=None, task=task, result=result)
            self.memory.repository.save_result(result)
            return result
        adapter = self.adapters.get(card.adapter_key)
        if adapter is None or not adapter.is_available(card):
            result = ToolResult(
                task_id=task.task_id,
                tool_id=card.tool_id,
                tool_type=card.tool_type,
                success=False,
                validation_status=ToolValidationStatus.BLOCKED,
                execution_state=ExecutionState(state='adapter_missing', detail='La herramienta existe pero el adaptador local no esta disponible.', destructive_blocked=True, metadata={'adapter_key': card.adapter_key}),
                error_message='adapter_missing',
            )
            self.memory.audit_event(
                tool_id=card.tool_id,
                task_id=task.task_id,
                action_type='preflight',
                state='adapter_missing',
                payload={'adapter_key': card.adapter_key, 'available': False},
            )
            if self.live_audit_supervisor is not None:
                result = self.live_audit_supervisor.audit_tool_result(card=card, task=task, result=result)
            self.memory.repository.save_result(result)
            return result
        task = task.model_copy(update={'tool_id': card.tool_id})
        task = self._sync_external_consultation_task(task, card)
        task = task.model_copy(
            update={
                'metadata': {
                    **dict(task.metadata or {}),
                    'ia_trace_entry': self._build_ia_trace_entry(task=task).model_dump(mode='json'),
                }
            }
        )
        task = self.approval_policy.evaluate(card=card, task=task)
        if approved and task.approval_decision == ApprovalDecision.PENDING:
            task = task.model_copy(update={'approval_decision': ApprovalDecision.APPROVED})
        self.memory.remember_task(task)
        sandbox_result = self.sandbox.run(card=card, task=task, adapter=adapter)
        sandbox_result = self.memory.remember_result(card, task, sandbox_result)
        approval_required = bool(task.metadata.get('approval_required'))
        if not sandbox_result.success:
            return sandbox_result
        if approval_required and task.approval_decision not in {ApprovalDecision.APPROVED, ApprovalDecision.SKIPPED}:
            waiting = sandbox_result.model_copy(
                update={
                    'execution_state': sandbox_result.execution_state.model_copy(
                        update={
                            'state': 'waiting_approval',
                            'detail': 'La sandbox paso, pero la herramienta requiere aprobacion humana antes de ejecutar fuera del sandbox.',
                            'approval_decision': task.approval_decision,
                        }
                    )
                }
            )
            self.memory.audit_event(
                tool_id=card.tool_id,
                task_id=task.task_id,
                action_type='approval_gate',
                state='waiting_approval',
                payload={'approval_decision': task.approval_decision.value, 'tool_id': card.tool_id},
            )
            if self.live_audit_supervisor is not None:
                waiting = self.live_audit_supervisor.audit_tool_result(card=card, task=task, result=waiting)
                self.memory.repository.save_result(waiting)
            return waiting
        payload = adapter.run(card, task, sandbox=False)
        payload_metadata = dict(payload.get('metadata') or {})
        state_hint = str(payload_metadata.get('state_hint') or '').strip()
        execution_state_name = state_hint or ('executed' if payload.get('success') else 'failed')
        execution_detail = str(payload.get('error_message') or 'Fallo en la herramienta.') if not payload.get('success') else str(
            payload_metadata.get('detail') or ('Ejecucion simulada; el adaptador no pudo interactuar con el entorno real.' if execution_state_name == 'simulated' else 'Herramienta ejecutada por el adaptador local.')
        )
        result = ToolResult(
            task_id=task.task_id,
            tool_id=card.tool_id,
            tool_type=card.tool_type,
            success=bool(payload.get('success')),
            execution_state=ExecutionState(
                state=execution_state_name,
                detail=execution_detail,
                executor_name=card.adapter_key,
                sandboxed=False,
                destructive_blocked=bool(payload_metadata.get('blocked')),
                approval_decision=task.approval_decision,
                metadata=payload_metadata,
            ),
            output_text=str(payload.get('output_text') or ''),
            extracted_data=dict(payload.get('extracted_data') or {}),
            artifacts=list(payload.get('artifacts') or []),
            error_message=str(payload.get('error_message') or ''),
            execution_ms=int(payload.get('execution_ms') or 0),
            metadata={
                'sandbox': False,
                'assistant_kind': str(task.metadata.get('assistant_kind') or self._assistant_family_for_tool_id(card.tool_id)),
                'assistant_configuration': dict(task.metadata.get('assistant_configuration') or {}),
                'config_signature': str(task.metadata.get('config_signature') or ''),
            },
        )
        if bool(payload_metadata.get('capture_unverified')) or str(payload_metadata.get('thread_verification') or '').strip().lower() == 'wrong_thread':
            result = result.model_copy(
                update={
                    'success': False,
                    'validation_status': ToolValidationStatus.UNVALIDATED,
                    'execution_state': result.execution_state.model_copy(
                        update={
                            'state': 'failed',
                            'detail': str(payload.get('error_message') or payload_metadata.get('auto_capture_reason') or 'capture_unverified'),
                            'metadata': {
                                **dict(result.execution_state.metadata or {}),
                                'response_captured': False,
                            },
                        }
                    ),
                    'output_text': '',
                    'error_message': str(payload.get('error_message') or payload_metadata.get('auto_capture_reason') or 'capture_unverified'),
                }
            )
        result = self.validator.validate(card=card, task=task, result=result, sandbox=False)
        trace_entry = self._build_ia_trace_entry(task=task, result=result)
        result = result.model_copy(
            update={
                'metadata': {
                    **dict(result.metadata or {}),
                    'external_state_flags': list(trace_entry.external_state_flags or []),
                    'ia_trace_entry': trace_entry.model_dump(mode='json'),
                }
            }
        )
        if self._should_attempt_rollback(task, result):
            rollback_state = self.rollback_manager.attempt(card=card, task=task, result=result, adapter=adapter)
            result = result.model_copy(update={'rollback_state': rollback_state})
            self.memory.audit_event(
                tool_id=card.tool_id,
                task_id=task.task_id,
                action_type='rollback',
                state=rollback_state.state,
                payload={'detail': rollback_state.detail, 'metadata': dict(rollback_state.metadata or {})},
            )
        result = self.memory.remember_result(card, task, result)
        if self.live_audit_supervisor is not None:
            result = self.live_audit_supervisor.audit_tool_result(card=card, task=task, result=result)
            self.memory.repository.save_result(result)
        return result

    def _build_actions(self, request: InferenceRequest, tool_id: str, reusable_pattern: InteractionPattern | None = None) -> list[ToolAction]:
        goal_parameters = request.goal_parameters or {}
        if goal_parameters.get('actions'):
            return [ToolAction.model_validate(item) for item in goal_parameters['actions']]
        pattern_actions = self._actions_from_pattern(reusable_pattern)
        if pattern_actions:
            return pattern_actions
        if goal_parameters.get('consultation_scope') == 'external_assistant' and tool_id in {'codex_installed', 'chatgpt_installed', 'chatgpt_web_assisted', 'claude_installed', 'claude_web_assisted', 'ollama_llm'}:
            prompt_text = str(goal_parameters.get('context_pack') or request.prompt or request.user_goal)
            assistant_kind = str(goal_parameters.get('assistant_kind') or goal_parameters.get('assistant_preference') or tool_id.split('_')[0])
            response_capture_mode = str(goal_parameters.get('response_capture_mode') or 'manual_pasteback')
            if tool_id == 'ollama_llm':
                return [
                    ToolAction(
                        action_type=ToolActionType.LLM_QUERY,
                        label='Consulta automatica local',
                        value=prompt_text,
                        expected_signal='tool_result',
                        metadata={
                            'assistant_kind': assistant_kind,
                            'consultation_scope': 'external_assistant',
                            'response_capture_mode': response_capture_mode,
                            'reused_from_pattern': False,
                        },
                    )
                ]
            launch_target = str(goal_parameters.get('web_url') or goal_parameters.get('executable_path') or '')
            actions = [
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Abrir asistente externo',
                    target=launch_target,
                    requires_approval=True,
                    metadata={
                        'assistant_kind': assistant_kind,
                        'consultation_scope': 'external_assistant',
                        'response_capture_mode': response_capture_mode,
                    },
                ),
                ToolAction(
                    action_type=ToolActionType.LLM_QUERY,
                    label='Contexto redactado',
                    value=prompt_text,
                    expected_signal='manual_pasteback' if response_capture_mode == 'manual_pasteback' else 'tool_result',
                    metadata={
                        'assistant_kind': assistant_kind,
                        'consultation_scope': 'external_assistant',
                        'reused_from_pattern': False,
                    },
                ),
            ]
            return actions
        if tool_id == 'playwright_browser':
            url = str(goal_parameters.get('url') or self._extract_url(request.user_goal) or '')
            actions: list[ToolAction] = []
            if url:
                actions.append(ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir URL', target=url))
            if 'captura' in request.user_goal.lower() or 'screenshot' in request.user_goal.lower():
                shot_path = str(self.workspace_root / 'data' / 'tool_teaching' / 'playwright_last.png')
                actions.append(ToolAction(action_type=ToolActionType.SCREENSHOT, label='Tomar captura', parameters={'path': shot_path}))
            if not actions:
                actions.append(ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir URL', target=url or 'https://example.com'))
            return actions
        if tool_id == 'desktop_human_runner':
            if goal_parameters.get('actions'):
                return [ToolAction.model_validate(item) for item in goal_parameters['actions']]
            actions: list[ToolAction] = []
            launch_target = str(goal_parameters.get('app_path') or goal_parameters.get('launch_target') or '')
            window_title = str(goal_parameters.get('window_title') or '')
            if launch_target:
                actions.append(
                    ToolAction(
                        action_type=ToolActionType.LAUNCH_APP,
                        label='Abrir aplicacion',
                        target=launch_target,
                        requires_approval=True,
                        parameters={'wait_seconds': float(goal_parameters.get('wait_seconds') or 1.2)},
                    )
                )
            if window_title:
                actions.append(
                    ToolAction(
                        action_type=ToolActionType.WAIT_FOR_WINDOW,
                        label='Esperar ventana',
                        target=window_title,
                        parameters={'timeout_seconds': float(goal_parameters.get('timeout_seconds') or 8.0)},
                    )
                )
                actions.append(
                    ToolAction(
                        action_type=ToolActionType.FOCUS_WINDOW,
                        label='Enfocar ventana',
                        target=window_title,
                    )
                )
            if goal_parameters.get('x') is not None and goal_parameters.get('y') is not None:
                actions.append(
                    ToolAction(
                        action_type=ToolActionType.CLICK_POINT,
                        label='Clic humano',
                        parameters={'x': goal_parameters.get('x'), 'y': goal_parameters.get('y')},
                        requires_approval=True,
                    )
                )
            if goal_parameters.get('text'):
                actions.append(
                    ToolAction(
                        action_type=ToolActionType.TYPE_TEXT,
                        label='Escribir texto',
                        value=str(goal_parameters.get('text') or ''),
                        requires_approval=True,
                        parameters={'submit_after': bool(goal_parameters.get('submit_after', False))},
                    )
                )
            if not actions:
                actions.append(ToolAction(action_type=ToolActionType.SCREENSHOT, label='Captura de estado'))
            return actions
        if tool_id == 'shell_command':
            command = str(goal_parameters.get('command') or request.metadata.get('command') or request.user_goal)
            return [ToolAction(action_type=ToolActionType.RUN_COMMAND, label='Comando local', value=command)]
        if tool_id == 'aider_coder':
            return [ToolAction(action_type=ToolActionType.EDIT_CODE, label='Editar codigo', value=request.user_goal, requires_approval=True)]
        if tool_id == 'mcp_client':
            return [ToolAction(action_type=ToolActionType.MCP_CALL, label='Llamada MCP', value=request.user_goal, requires_approval=True)]
        return [ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta local', value=request.user_goal)]

    def _build_rollback_actions(self, request: InferenceRequest, tool_id: str) -> list[ToolAction]:
        goal_parameters = request.goal_parameters or {}
        if goal_parameters.get('rollback_actions'):
            return [ToolAction.model_validate(item) for item in goal_parameters['rollback_actions']]
        if tool_id == 'shell_command' and goal_parameters.get('rollback_command'):
            return [
                ToolAction(
                    action_type=ToolActionType.RUN_COMMAND,
                    label='Rollback comando',
                    value=str(goal_parameters.get('rollback_command') or ''),
                )
            ]
        if tool_id == 'playwright_browser' and goal_parameters.get('rollback_url'):
            return [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    label='Rollback URL',
                    target=str(goal_parameters.get('rollback_url') or ''),
                )
            ]
        return []

    def _should_attempt_rollback(self, task: ToolTask, result: ToolResult) -> bool:
        if result.success or result.execution_state.destructive_blocked:
            return False
        if task.rollback_actions:
            return True
        if task.execution_scope in {'write', 'destructive'}:
            return True
        return any(action.destructive for action in task.actions)

    def _suggest_tool_id(self, goal: str) -> str:
        text = goal.lower()
        if 'playwright' in text or 'pagina' in text or 'url' in text or self._extract_url(goal):
            return 'playwright_browser'
        if 'aider' in text or 'edita' in text or 'patch' in text or 'codigo' in text:
            return 'aider_coder'
        if 'mcp' in text or 'api' in text:
            return 'mcp_client'
        if 'codex' in text:
            return 'codex_installed'
        if 'chatgpt' in text:
            return 'chatgpt_installed'
        if 'claude' in text:
            return 'claude_installed'
        if 'powershell' in text or 'comando' in text or 'shell' in text or 'script' in text:
            return 'shell_command'
        return 'ollama_llm'

    def _extract_url(self, text: str) -> str | None:
        match = self.URL_PATTERN.search(text)
        return match.group(0) if match else None

    def _sync_external_consultation_task(self, task: ToolTask, card: ToolCard) -> ToolTask:
        if task.metadata.get('consultation_scope') != 'external_assistant':
            return task
        response_capture_mode = str(card.metadata.get('response_capture_mode') or task.metadata.get('response_capture_mode') or 'manual_pasteback')
        background_capture_mode = str(card.metadata.get('background_capture_mode') or task.metadata.get('background_capture_mode') or '')
        direct_response_text = str(card.metadata.get('direct_response_text') or task.metadata.get('direct_response_text') or '').strip()
        direct_capture = response_capture_mode.strip().lower() in {'direct_text', 'tool_result'} and bool(direct_response_text)
        requested_assistant_kind = str(task.metadata.get('requested_assistant_kind') or ((task.metadata.get('goal_parameters') or {}).get('assistant_preference') if isinstance(task.metadata.get('goal_parameters'), dict) else '') or task.metadata.get('assistant_kind') or '')
        assistant_kind = str(card.metadata.get('assistant_kind') or task.metadata.get('actual_assistant_kind') or task.metadata.get('assistant_kind') or '')
        session_scope = str(card.metadata.get('session_scope') or task.metadata.get('session_scope') or '')
        session_label = str(card.metadata.get('session_label') or task.metadata.get('session_label') or '')
        isolated_session_required = bool(card.metadata.get('isolated_session_required', task.metadata.get('isolated_session_required', False)))
        session_profile_dir = str(task.metadata.get('session_profile_dir') or self._session_profile_dir_for_tool(tool_id=card.tool_id, assistant_kind=assistant_kind, background_capture_mode=background_capture_mode, isolated_session_required=isolated_session_required))
        capture_lane = str(task.metadata.get('capture_lane') or self._lane_for_consultation(response_capture_mode=response_capture_mode, background_capture_mode=background_capture_mode))
        metadata = {
            **dict(task.metadata or {}),
            'requested_assistant_kind': requested_assistant_kind,
            'assistant_kind': assistant_kind,
            'actual_assistant_kind': assistant_kind,
            'response_capture_mode': response_capture_mode,
            'requires_manual_pasteback': False if direct_capture else bool(card.metadata.get('requires_manual_pasteback', task.metadata.get('requires_manual_pasteback', True))),
            'session_scope': session_scope,
            'session_label': session_label,
            'isolated_session_required': isolated_session_required,
            'background_capture_mode': background_capture_mode,
            'background_headless': bool(card.metadata.get('background_headless', task.metadata.get('background_headless', True))),
            'thread_key': str(task.metadata.get('thread_key') or ''),
            'thread_title': str(task.metadata.get('thread_title') or ''),
            'capture_lane': capture_lane,
            'lane_priority': list(task.metadata.get('lane_priority') or ['background', 'app', 'manual']),
            'awaiting_reason': str(task.metadata.get('awaiting_reason') or self._awaiting_reason_for_lane(capture_lane=capture_lane, response_capture_mode=response_capture_mode, background_capture_mode=background_capture_mode)),
            'reused_thread': bool(task.metadata.get('reused_thread', self._has_session_content(session_profile_dir))),
            'session_profile_dir': session_profile_dir,
        }
        if direct_capture:
            metadata['direct_response_available'] = True
        return task.model_copy(update={'metadata': metadata})

    def _preview_summary(self, card, task: ToolTask, interaction_patterns: list[dict[str, Any]] | None = None, mode_selection: dict[str, Any] | None = None) -> str:
        if task.metadata.get('consultation_scope') == 'external_assistant':
            if card.tool_id == 'ollama_llm':
                base = f'Preparare una consulta automatica local con {card.title}. Primero validare la via elegida y luego ejecutare el contexto redactado sin salir de IABV.'
            else:
                base = f'Preparare una consulta externa guiada con {card.title}. Primero validare la via elegida y luego abrire el asistente con un contexto redactado y copiable.'
        elif bool(task.metadata.get('approval_required')):
            base = f'Use {card.title} primero en sandbox y luego pedire aprobacion antes de ejecutar fuera del sandbox.'
        else:
            base = f'Use {card.title} en modo local-first. Primero validare la herramienta en sandbox y luego podre ejecutar la tarea.'
        if task.rollback_actions:
            base += ' Tambien dejare un rollback basico disponible si la ejecucion falla.'
        if interaction_patterns:
            base += f' Ya tengo {len(interaction_patterns)} patron(es) reutilizable(s) de interaccion para este flujo.'
        if mode_selection:
            selected_mode = str(mode_selection.get('selected_mode') or '')
            if selected_mode:
                base += f' Selector universal: {selected_mode}.'
            if mode_selection.get('already_resolved'):
                base += ' Ya hay un episodio resuelto equivalente; no hace falta reensenar este flujo.'
            elif mode_selection.get('equivalent_pattern_exists'):
                base += ' Ya existe un patron equivalente reutilizable.'
            if mode_selection.get('improvement_already_implemented'):
                base += ' La mejora pedida parece ya implementada en el historial aprendido.'
            selection_metadata = dict(mode_selection.get('metadata') or {})
            if selection_metadata.get('assistant_preference_blocked'):
                requested_family = str(selection_metadata.get('requested_assistant_preference') or '').strip()
                reason = str(selection_metadata.get('preference_unavailable_reason') or '').strip()
                if requested_family and reason:
                    base += f' No pude respetar tu preferencia explicita de {requested_family}: {reason}'
                elif requested_family:
                    base += f' No pude respetar tu preferencia explicita de {requested_family}; use la mejor alternativa disponible.'
                elif reason:
                    base += f' {reason}'
            elif mode_selection.get('fallback_used'):
                base += ' El selector cayo en fallback porque no encontro una via mejor disponible.'
        if task.metadata.get('consultation_scope') == 'external_assistant':
            assistant_kind = str(task.metadata.get('assistant_kind') or card.metadata.get('assistant_kind') or card.title)
            capture_mode = str(task.metadata.get('response_capture_mode') or card.metadata.get('response_capture_mode') or '').strip().lower()
            thread_title = str(task.metadata.get('thread_title') or '').strip()
            thread_key = str(task.metadata.get('thread_key') or '').strip()
            capture_lane = str(task.metadata.get('capture_lane') or '').strip()
            base += f' Asistente elegido: {assistant_kind}.'
            if thread_title or thread_key:
                base += f' Hilo dedicado IABV: {thread_title or thread_key}.'
            if capture_lane:
                base += f' Lane prioritaria: {capture_lane}.'
            if capture_mode == 'clipboard_capture':
                if str(card.metadata.get('background_capture_mode') or '').strip().lower() == 'codex_rollout':
                    base += ' Intentare capturar la respuesta automaticamente desde la sesion de Codex en segundo plano, luego por clipboard y solo al final por pegado manual.'
                else:
                    base += ' Intentare capturar la respuesta automaticamente desde la app; si no aparece texto util, quedara fallback guiado por pegado manual.'
            elif capture_mode in {'dom_capture', 'browser_dom'}:
                base += ' Intentare resolver la consulta en una sesion aislada del programa, usando un chat especial separado del navegador normal y capturando la respuesta en segundo plano.'
            elif task.metadata.get('requires_manual_pasteback'):
                base += ' La respuesta vuelve por pegado manual confirmado por el usuario.'
            else:
                base += ' La respuesta vuelve por captura automatica o por resultado directo de la herramienta.'
        return base

    def _select_mode(self, *, request: InferenceRequest, suggested_tool_id: str, site_id: str | None) -> ModeSelectionDecision:
        if self.mode_selector is None:
            return ModeSelectionDecision(selected_tool_id=suggested_tool_id, reason='Mode selector no configurado; se uso heuristica local.')
        draft_task = ToolTask(
            tool_id=suggested_tool_id,
            title=str(request.goal_parameters.get('title') or request.user_goal[:80]),
            objective=request.user_goal,
            requested_by_role=request.task_role if request.task_role in {TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX} else TaskRole.TOOL_USE,
            execution_scope=str(request.goal_parameters.get('execution_scope') or 'read_only'),
            site_id=site_id,
            expected_outcome=str(request.goal_parameters.get('expected_outcome') or ''),
            metadata={'goal_parameters': dict(request.goal_parameters)},
        )
        allowed_tool_ids = [str(item) for item in (request.goal_parameters.get('allowed_tool_ids') or []) if str(item)]
        if not allowed_tool_ids and request.task_role == TaskRole.TOOL_SANDBOX and suggested_tool_id:
            allowed_tool_ids = [suggested_tool_id]
        return self.mode_selector.select(
            request=request,
            draft_task=draft_task,
            suggested_tool_id=suggested_tool_id,
            allowed_tool_ids=allowed_tool_ids or None,
        )

    def _synaptic_decision_for_request(self, request: InferenceRequest) -> dict[str, Any]:
        if self.synaptic_router is None:
            return {}
        goal_parameters = dict(request.goal_parameters or {})
        raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds') or []
        candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
        task_kind = str(
            goal_parameters.get('task_kind')
            or goal_parameters.get('diagnostic_category')
            or request.task_role.value
            or request.user_goal
        )
        try:
            decision = self.synaptic_router.decide(
                task_kind=task_kind,
                candidate_assistant_kinds=candidate_assistant_kinds,
            )
        except Exception:
            return {'error': 'synaptic_router_failed'}
        return decision.model_dump(mode='json')

    def _enforce_explicit_external_selection(
        self,
        *,
        request: InferenceRequest,
        selection: ModeSelectionDecision,
        suggested_tool_id: str,
    ) -> ModeSelectionDecision:
        goal_parameters = dict(request.goal_parameters or {})
        if str(goal_parameters.get('consultation_scope') or '').strip().lower() != 'external_assistant':
            return selection
        requested_assistant = str(goal_parameters.get('assistant_preference') or goal_parameters.get('assistant_kind') or '').strip().lower()
        if not requested_assistant:
            return selection
        selected_tool_id = str(selection.selected_tool_id or suggested_tool_id or '').strip()
        if self._assistant_family_for_tool_id(selected_tool_id) == requested_assistant:
            return selection
        preferred_tool_id = str(goal_parameters.get('tool_id') or suggested_tool_id or '').strip()
        # If the upstream layer already steered us towards a deliberate
        # cross-family route (e.g. lab_recommendation=LOCAL pinning
        # preferred_tool_id='ollama_llm') and the selector honored it,
        # respect that decision instead of forcing the requested family.
        if preferred_tool_id and selected_tool_id == preferred_tool_id:
            return selection
        if bool(goal_parameters.get('allow_local_automatic_consultation')) and selected_tool_id == 'ollama_llm':
            return selection
        if preferred_tool_id and self._assistant_family_for_tool_id(preferred_tool_id) == requested_assistant:
            override_card = self._resolve_available_family_card(
                tool_id=preferred_tool_id,
                request=request,
            )
            if override_card is not None:
                return self._override_selection_with_card(
                    selection=selection,
                    card=override_card,
                    policy='explicit_assistant_override',
                    reason_tag='override_ia_explicita',
                    metadata_overrides={
                        'override_reason': 'La preferencia explicita del usuario debe mantenerse en la misma familia de asistente.',
                        'requested_assistant_preference': requested_assistant,
                    },
                )
        fallback_card = self._resolve_family_fallback_card(
            requested_assistant=requested_assistant,
            request=request,
            exclude_tool_id=preferred_tool_id,
        )
        if fallback_card is not None:
            return self._override_selection_with_card(
                selection=selection,
                card=fallback_card,
                policy='explicit_assistant_override_family_fallback',
                reason_tag='override_ia_explicita_fallback_familia',
                metadata_overrides={
                    'override_reason': 'La preferencia explicita del usuario se respeto con un fallback dentro de la misma familia.',
                    'requested_assistant_preference': requested_assistant,
                    'preferred_tool_id_unavailable': preferred_tool_id,
                },
            )
        return self._block_selection_for_unavailable_preference(
            selection=selection,
            requested_assistant=requested_assistant,
            preferred_tool_id=preferred_tool_id,
        )

    def _resolve_available_family_card(self, *, tool_id: str, request: InferenceRequest):
        if not tool_id:
            return None
        card = self.registry.get_card(tool_id)
        if card is None:
            return None
        card = self.registry.refresh_card(card, force=True)
        adapter_exists = card.adapter_key in self.registry.adapters
        if not card.available or not adapter_exists:
            return None
        if self._tool_has_repeated_blocked_failures(
            tool_id=card.tool_id,
            mode_used=self._selection_mode_for_tool_type(card.tool_type).value,
            site_id=request.site_hint,
            goal=request.user_goal,
        ):
            return None
        return card

    def _resolve_family_fallback_card(
        self,
        *,
        requested_assistant: str,
        request: InferenceRequest,
        exclude_tool_id: str,
    ):
        for candidate in self.registry.list_cards():
            if candidate.tool_id == exclude_tool_id:
                continue
            if self._assistant_family_for_tool_id(candidate.tool_id) != requested_assistant:
                continue
            card = self._resolve_available_family_card(tool_id=candidate.tool_id, request=request)
            if card is not None:
                return card
        return None

    def _override_selection_with_card(
        self,
        *,
        selection: ModeSelectionDecision,
        card,
        policy: str,
        reason_tag: str,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> ModeSelectionDecision:
        metadata = dict(selection.metadata or {})
        metadata['selection_policy'] = policy
        if metadata_overrides:
            metadata.update(metadata_overrides)
        adapter_exists = card.adapter_key in self.registry.adapters
        return selection.model_copy(
            update={
                'selected_mode': self._selection_mode_for_tool_type(card.tool_type),
                'selected_tool_id': card.tool_id,
                'selected_tool_type': card.tool_type,
                'adapter_exists': adapter_exists,
                'available': card.available,
                'fallback_used': False,
                'reason': (selection.reason + ' | ' + reason_tag).strip(' |'),
                'metadata': metadata,
            }
        )

    def _block_selection_for_unavailable_preference(
        self,
        *,
        selection: ModeSelectionDecision,
        requested_assistant: str,
        preferred_tool_id: str,
    ) -> ModeSelectionDecision:
        # Keep whatever the base selector already chose (cross-family fallback
        # is legitimate when the requested family is completely unavailable).
        # Annotate telemetry so the UI / audit layer can surface that the
        # user's explicit preference could not be honored.
        metadata = dict(selection.metadata or {})
        existing_policy = str(metadata.get('selection_policy') or '')
        metadata['selection_policy'] = existing_policy or 'explicit_assistant_preference_unavailable'
        metadata['assistant_preference_blocked'] = True
        metadata['requested_assistant_preference'] = requested_assistant
        metadata['preferred_tool_id'] = preferred_tool_id
        metadata['preference_unavailable_reason'] = (
            'La preferencia explicita del usuario no pudo respetarse porque ningun miembro de la '
            f"familia '{requested_assistant}' esta disponible en este momento."
        )
        return selection.model_copy(
            update={
                'fallback_used': True,
                'reason': (selection.reason + ' | preferencia_explicita_no_disponible').strip(' |'),
                'metadata': metadata,
            }
        )

    def _selection_mode_for_tool_type(self, tool_type: ToolType) -> InteractionMode:
        if tool_type in {ToolType.BROWSER, ToolType.LLM_WEB_UI}:
            return InteractionMode.UI
        if tool_type == ToolType.MCP_CLIENT:
            return InteractionMode.API
        return InteractionMode.BACKGROUND

    def _assistant_family_for_tool_id(self, tool_id: str) -> str:
        normalized = str(tool_id or '').strip().lower()
        for family in ('chatgpt', 'claude', 'codex', 'ollama', 'devin'):
            if normalized.startswith(family):
                return family
        return normalized.split('_', 1)[0]

    def _tool_has_repeated_blocked_failures(
        self,
        *,
        tool_id: str,
        mode_used: str,
        site_id: str | None,
        goal: str,
    ) -> bool:
        episodes = self.memory.repository.list_interaction_episodes(tool_id=tool_id, mode_used=mode_used, site_id=site_id, limit=8) if site_id else self.memory.repository.list_interaction_episodes(tool_id=tool_id, mode_used=mode_used, limit=8)
        goal_tokens = set(str(goal or '').lower().split())
        signatures: Counter[str] = Counter()
        for episode in episodes:
            objective_tokens = set(str(episode.objective or '').lower().split())
            if goal_tokens and objective_tokens and len(goal_tokens.intersection(objective_tokens)) == 0:
                continue
            result = episode.result
            if result is None or result.success:
                continue
            signature = self._blocked_failure_signature(result=result)
            if signature:
                signatures[signature] += 1
        if not signatures:
            return False
        _signature, count = signatures.most_common(1)[0]
        return count >= 2

    def _blocked_failure_signature(self, *, result: ToolResult) -> str:
        state = str(result.execution_state.state or '').strip().lower()
        error_message = str(getattr(result, 'error_message', '') or '').strip()
        summary = str(getattr(result, 'summary', '') or '').strip()
        errors = ' '.join(str(item or '').strip() for item in list(getattr(result, 'errors', []) or []))
        metadata = dict(getattr(result, 'metadata', {}) or {})
        detail = ' '.join(
            part
            for part in (
                error_message,
                str(result.execution_state.detail or '').strip(),
                summary,
                errors,
                str(metadata.get('error_message') or '').strip(),
                str(metadata.get('detail') or '').strip(),
            )
            if part
        ).lower()
        if 'acceso denegado' in detail or 'access denied' in detail:
            return 'access_denied'
        if 'session expired' in detail or 'sesion expirada' in detail or 'assistant_login_required' in detail:
            return 'session_unavailable'
        if 'wrong_thread' in detail or 'wrong thread' in detail:
            return 'wrong_thread'
        if 'quota' in detail or 'rate limit' in detail or 'credits exhausted' in detail or 'plan upgrade required' in detail:
            return 'account_limited'
        if state in {'adapter_missing', 'missing_tool'}:
            return state
        return ''
    def _build_external_consultation_request(
        self,
        *,
        user_goal: str,
        assistant_preference: str,
        context_pack: str,
        site_id: str | None,
        diagnostic_category: str,
        incident_kind: str,
        launch_dry_run: bool,
        allow_local_automatic_consultation: bool,
        goal_parameters: dict[str, Any] | None = None,
    ) -> InferenceRequest:
        assistant = (assistant_preference or '').strip().lower() or 'codex'
        goal_payload = dict(goal_parameters or {})
        lab_recommendation = self._external_lab_recommendation(
            assistant_preference=assistant,
            site_id=site_id,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            goal_parameters=goal_payload,
        )
        preferred_tool_id = self._preferred_external_tool_id(
            assistant_preference=assistant,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            lab_recommendation=lab_recommendation,
            allow_local_automatic_consultation=allow_local_automatic_consultation,
            explicit_external_consultation=bool(goal_payload.get('explicit_external_consultation', False)),
        )
        background_capture_mode = ''
        if preferred_tool_id == 'ollama_llm':
            assistant_title = 'Ollama local'
            assistant_kind = 'ollama'
            prompt_template_id = 'local_consult_v1'
            response_capture_mode = 'tool_result'
            requires_manual_pasteback = False
            session_scope = 'local_runtime'
            isolated_session_required = False
            expected_outcome = 'Consulta local automatica ejecutada y respuesta ya disponible para IABV.'
        else:
            preferred_card = self.registry.get_card(preferred_tool_id)
            preferred_metadata = dict(preferred_card.metadata or {}) if preferred_card is not None else {}
            desktop_capture = preferred_tool_id in {'codex_installed', 'chatgpt_installed', 'claude_installed'}
            background_capture_mode = str(preferred_metadata.get('background_capture_mode') or '')
            if preferred_tool_id.startswith('codex'):
                assistant_title = 'Codex'
                assistant_kind = 'codex'
                prompt_template_id = 'codex_consult_v1'
            elif preferred_tool_id.startswith('claude'):
                assistant_title = 'Claude'
                assistant_kind = 'claude'
                prompt_template_id = 'claude_consult_v1' if preferred_tool_id == 'claude_installed' else 'claude_web_consult_v1'
            else:
                assistant_title = 'ChatGPT'
                assistant_kind = 'chatgpt'
                prompt_template_id = 'chatgpt_consult_v1' if preferred_tool_id == 'chatgpt_installed' else 'chatgpt_web_consult_v1'
            response_capture_mode = str(preferred_metadata.get('response_capture_mode') or ('clipboard_capture' if desktop_capture else 'manual_pasteback'))
            requires_manual_pasteback = bool(preferred_metadata.get('requires_manual_pasteback', False if desktop_capture else True))
            session_scope = str(preferred_metadata.get('session_scope') or ('program_chat' if preferred_tool_id.endswith('_web_assisted') else 'external_app'))
            isolated_session_required = bool(preferred_metadata.get('isolated_session_required', False))
            if response_capture_mode in {'clipboard_capture', 'dom_capture'} and not requires_manual_pasteback:
                expected_outcome = 'Consulta externa preparada con captura automatica y aprendizaje reutilizable si la respuesta es util.'
            else:
                expected_outcome = 'Consulta externa preparada, via abierta y contexto listo para devolver la respuesta a IABV.'
        consultation_metadata = self._build_external_consultation_metadata(
            assistant_kind=assistant_kind,
            assistant_title=assistant_title,
            preferred_tool_id=preferred_tool_id,
            site_id=site_id,
            user_goal=user_goal,
            goal_payload=goal_payload,
            context_pack=context_pack,
            response_capture_mode=response_capture_mode,
            background_capture_mode=background_capture_mode,
            session_scope=session_scope,
            session_label=f'{assistant_title} especial de IABV' if isolated_session_required else assistant_title,
            isolated_session_required=isolated_session_required,
        )
        return InferenceRequest(
            user_goal=f'Consultar {assistant_title} sobre: {user_goal}',
            prompt=consultation_metadata['context_pack'],
            task_role=TaskRole.TOOL_USE,
            offline_only=True,
            site_hint=site_id,
            execution_scope='read_only',
            goal_parameters={
                **goal_payload,
                'tool_id': preferred_tool_id,
                'allowed_tool_ids': self._external_tool_ids(assistant_preference=assistant, allow_local_automatic_consultation=allow_local_automatic_consultation),
                'title': f'Consultar {assistant_title}',
                'expected_outcome': expected_outcome,
                'context_pack': consultation_metadata['context_pack'],
                'assistant_preference': assistant,
                'assistant_kind': assistant_kind,
                'consultation_scope': 'external_assistant',
                'response_capture_mode': response_capture_mode,
                'requires_manual_pasteback': requires_manual_pasteback,
                'prompt_template_id': prompt_template_id,
                'execution_scope': 'read_only',
                'diagnostic_category': diagnostic_category,
                'incident_kind': incident_kind,
                'site_id': site_id or '',
                'lab_recommendation': lab_recommendation.model_dump(mode='json') if lab_recommendation is not None else {},
                'dry_run_launch': launch_dry_run,
                'allow_local_automatic_consultation': allow_local_automatic_consultation,
                'session_scope': session_scope,
                'isolated_session_required': isolated_session_required,
                'session_label': consultation_metadata['session_label'],
                'thread_key': consultation_metadata['thread_key'],
                'thread_title': consultation_metadata['thread_title'],
                'capture_lane': consultation_metadata['capture_lane'],
                'lane_priority': consultation_metadata['lane_priority'],
                'awaiting_reason': consultation_metadata['awaiting_reason'],
                'last_capture_attempt_utc': '',
                'reused_thread': consultation_metadata['reused_thread'],
                'session_profile_dir': consultation_metadata['session_profile_dir'],
            },
            metadata={'external_consultation': True},
        )

    def _build_external_consultation_metadata(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        preferred_tool_id: str,
        site_id: str | None,
        user_goal: str,
        goal_payload: dict[str, Any],
        context_pack: str,
        response_capture_mode: str,
        background_capture_mode: str,
        session_scope: str,
        session_label: str,
        isolated_session_required: bool,
    ) -> dict[str, Any]:
        goal_context = dict(goal_payload or {})
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        scope_title = str(task.get('title') or project.get('title') or objective.get('title') or user_goal or 'consulta').strip()
        site_fragment = self._slug_fragment(site_id or 'general')
        scope_fragment = self._slug_fragment(scope_title or user_goal or 'consulta')
        thread_key = str(goal_payload.get('thread_key') or f'iabv::{assistant_kind}::{site_fragment}::{scope_fragment}')
        thread_title = str(goal_payload.get('thread_title') or f'IABV {assistant_title} | {scope_title[:48]}')
        capture_lane = self._lane_for_consultation(
            response_capture_mode=response_capture_mode,
            background_capture_mode=background_capture_mode,
        )
        lane_priority = ['background', 'app', 'manual']
        session_profile_dir = self._session_profile_dir_for_tool(
            tool_id=preferred_tool_id,
            assistant_kind=assistant_kind,
            background_capture_mode=background_capture_mode,
            isolated_session_required=isolated_session_required,
        )
        awaiting_reason = self._awaiting_reason_for_lane(
            capture_lane=capture_lane,
            response_capture_mode=response_capture_mode,
            background_capture_mode=background_capture_mode,
        )
        reused_thread = self._has_session_content(session_profile_dir)
        enriched_context = str(context_pack or '').strip()
        marker_lines = [
            f'IABV_THREAD_KEY: {thread_key}',
            f'IABV_THREAD_TITLE: {thread_title}',
            'IABV_LANE_PRIORITY: background > app > manual',
            'Instruccion: usa o crea el hilo dedicado de IABV para este asistente y no reutilices un chat ajeno.',
        ]
        marker_block = '\n'.join(item for item in marker_lines if item)
        if enriched_context:
            if 'IABV_THREAD_KEY:' not in enriched_context:
                enriched_context = f"{enriched_context}\n\n{marker_block}".strip()
        else:
            enriched_context = marker_block
        return {
            'thread_key': thread_key,
            'thread_title': thread_title,
            'capture_lane': capture_lane,
            'lane_priority': lane_priority,
            'awaiting_reason': awaiting_reason,
            'reused_thread': reused_thread,
            'session_profile_dir': session_profile_dir,
            'session_scope': session_scope,
            'session_label': session_label,
            'context_pack': enriched_context,
        }

    def _lane_for_consultation(self, *, response_capture_mode: str, background_capture_mode: str) -> str:
        capture_mode = str(response_capture_mode or '').strip().lower()
        background_mode = str(background_capture_mode or '').strip().lower()
        if capture_mode in {'tool_result', 'direct_text', 'dom_capture', 'browser_dom'} or background_mode in {'browser_dom', 'codex_rollout'}:
            return 'background'
        if capture_mode == 'clipboard_capture':
            return 'app'
        return 'manual'

    def _awaiting_reason_for_lane(self, *, capture_lane: str, response_capture_mode: str, background_capture_mode: str) -> str:
        if capture_lane == 'background' and str(background_capture_mode or '').strip().lower() == 'codex_rollout':
            return 'Esperando captura desde la sesion y los rollouts dedicados de Codex.'
        if capture_lane == 'background' and str(response_capture_mode or '').strip().lower() in {'dom_capture', 'browser_dom'}:
            return 'Esperando respuesta en la sesion aislada del programa y su chat especial.'
        if capture_lane == 'background':
            return 'Esperando respuesta automatica de la herramienta local o externa.'
        if capture_lane == 'app':
            return 'Esperando texto util desde la app visible antes de caer a manual.'
        return 'Pendiente de pegar manualmente la respuesta en IABV.'

    def _session_profile_dir_for_tool(
        self,
        *,
        tool_id: str,
        assistant_kind: str,
        background_capture_mode: str,
        isolated_session_required: bool,
    ) -> str:
        root = self.workspace_root / 'data' / 'tool_teaching' / 'external_assistants'
        if tool_id == 'codex_installed' or str(background_capture_mode or '').strip().lower() == 'codex_rollout':
            profile_dir = root / 'codex_home'
        elif isolated_session_required:
            profile_dir = root / f'{assistant_kind}_program_session' / 'browser_profile'
        elif tool_id.endswith('_installed'):
            profile_dir = root / f'{assistant_kind}_desktop_session'
        else:
            return ''
        profile_dir.mkdir(parents=True, exist_ok=True)
        return str(profile_dir)

    def _has_session_content(self, path_value: str) -> bool:
        path_text = str(path_value or '').strip()
        if not path_text:
            return False
        path = Path(path_text)
        if not path.exists():
            return False
        try:
            return any(path.iterdir())
        except Exception:
            return False

    def _slug_fragment(self, value: str) -> str:
        normalized = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
        compact = '-'.join(part for part in normalized.split('-') if part)
        return compact[:48] or 'general'

    def _external_tool_ids(self, *, assistant_preference: str = '', allow_local_automatic_consultation: bool = False) -> list[str]:
        assistant = str(assistant_preference or '').strip().lower()
        if assistant == 'chatgpt':
            tool_ids = ['chatgpt_installed', 'chatgpt_web_assisted']
        elif assistant == 'claude':
            tool_ids = ['claude_installed', 'claude_web_assisted']
        elif assistant == 'codex' and allow_local_automatic_consultation:
            # User explicitly asked for codex + opted in to the local automatic
            # consultation fallback: restrict the allowed set so the selector
            # only considers codex (preferred family) or the local route,
            # never a cross-family assisted web route the user did not ask for.
            tool_ids = ['codex_installed']
        elif assistant == 'devin':
            tool_ids = ['devin_api']
        elif assistant in {'ollama', 'local', 'local_first'}:
            tool_ids = ['ollama_llm']
        else:
            tool_ids = ['codex_installed', 'chatgpt_installed', 'chatgpt_web_assisted', 'claude_installed', 'claude_web_assisted', 'devin_api']
        if allow_local_automatic_consultation and 'ollama_llm' not in tool_ids:
            tool_ids.append('ollama_llm')
        return tool_ids

    def _preferred_external_tool_id(

        self,
        *,
        assistant_preference: str,
        diagnostic_category: str,
        incident_kind: str,
        lab_recommendation,
        allow_local_automatic_consultation: bool,
        explicit_external_consultation: bool,
    ) -> str:
        technical_incidents = {'bridge_lag', 'navigation_stall', 'session_restore_weak', 'visual_alignment_weak', 'critical_object_missing'}
        technical_categories = {'need_codex_fix', 'need_adapter'}
        assistant = str(assistant_preference or '').strip().lower()

        explicit_family = {
            'ollama': 'ollama_llm',
            'local': 'ollama_llm',
            'local_first': 'ollama_llm',
            'codex': 'codex_installed',
            'claude': 'claude_web_assisted',
            'chatgpt': 'chatgpt_web_assisted',
            'devin': 'devin_api',
        }.get(assistant, '')
        if explicit_family:
            preferred_tool_id = explicit_family
        elif diagnostic_category in technical_categories or incident_kind in technical_incidents:
            preferred_tool_id = 'codex_installed'
        else:
            preferred_tool_id = 'chatgpt_installed'

        if lab_recommendation is not None:
            recommended_assistant = str(getattr(lab_recommendation, 'recommended_assistant_kind', '') or '').strip().lower()
            recommended_config = getattr(lab_recommendation, 'recommended_assistant_configuration', None)
            if allow_local_automatic_consultation and lab_recommendation.recommended_route == EvaluationRoute.LOCAL and not explicit_external_consultation:
                return 'ollama_llm'
            if recommended_assistant == 'ollama' and not explicit_external_consultation:
                preferred_tool_id = 'ollama_llm'
            elif recommended_assistant == 'codex':
                preferred_tool_id = 'codex_installed'
            elif recommended_assistant == 'claude':
                preferred_tool_id = 'claude_web_assisted'
            elif recommended_assistant == 'chatgpt':
                preferred_tool_id = 'chatgpt_web_assisted'
            if recommended_config is not None:
                browser_mode = str(getattr(recommended_config, 'browser_mode', '') or '').strip().lower()
                origin_mode = str(getattr(recommended_config, 'origin_mode', '') or '').strip().lower()
                if browser_mode == 'with_browser' and preferred_tool_id.startswith('chatgpt'):
                    preferred_tool_id = 'chatgpt_web_assisted'
                elif browser_mode == 'with_browser' and preferred_tool_id.startswith('claude'):
                    preferred_tool_id = 'claude_web_assisted'
                if origin_mode == 'local' and allow_local_automatic_consultation and not explicit_external_consultation:
                    preferred_tool_id = 'ollama_llm'
            if explicit_family:
                if preferred_tool_id == 'ollama_llm':
                    return preferred_tool_id
                if preferred_tool_id.startswith('claude'):
                    return 'claude_web_assisted' if lab_recommendation.recommended_route in {EvaluationRoute.UI, EvaluationRoute.LANGUAGE_UNDERSTANDING, EvaluationRoute.FALLBACK} else preferred_tool_id
                if preferred_tool_id.startswith('chatgpt'):
                    return 'chatgpt_web_assisted' if lab_recommendation.recommended_route in {EvaluationRoute.UI, EvaluationRoute.LANGUAGE_UNDERSTANDING, EvaluationRoute.FALLBACK} else preferred_tool_id
                return preferred_tool_id
            if lab_recommendation.recommended_route == EvaluationRoute.CODE_AGENT:
                preferred_tool_id = 'codex_installed'
            elif lab_recommendation.recommended_route == EvaluationRoute.UI:
                preferred_tool_id = 'chatgpt_web_assisted'
            elif lab_recommendation.recommended_route == EvaluationRoute.LANGUAGE_UNDERSTANDING:
                preferred_tool_id = 'chatgpt_web_assisted'
        return preferred_tool_id


    def _external_lab_subject_keys(
        self,
        *,
        goal_parameters: dict[str, Any] | None,
        site_id: str | None,
        diagnostic_category: str,
        incident_kind: str,
        assistant_preference: str,
    ) -> list[str]:
        payload = dict(goal_parameters or {})
        suffix = str(diagnostic_category or incident_kind or assistant_preference or 'consult').strip()
        keys: list[str] = []
        for base in (
            str(payload.get('task_id') or ''),
            str(payload.get('project_id') or ''),
            str(payload.get('objective_id') or ''),
            str(site_id or ''),
            'general',
        ):
            probe = base.strip()
            if not probe:
                continue
            composite = f"{probe}:{suffix}" if suffix else ''
            for candidate in (composite, probe):
                normalized = candidate.strip()
                if normalized and normalized not in keys:
                    keys.append(normalized)
        return keys

    def _external_lab_recommendation(self, *, assistant_preference: str, site_id: str | None, diagnostic_category: str, incident_kind: str, goal_parameters: dict[str, Any] | None = None):
        if self.experiment_lab is None:
            return None
        technical_incidents = {'bridge_lag', 'navigation_stall', 'session_restore_weak', 'visual_alignment_weak', 'critical_object_missing'}
        technical_categories = {'need_codex_fix', 'need_adapter'}
        domain = ExperimentDomain.CODE if assistant_preference == 'codex' or diagnostic_category in technical_categories or incident_kind in technical_incidents else ExperimentDomain.LANGUAGE
        for subject_key in self._external_lab_subject_keys(
            goal_parameters=goal_parameters,
            site_id=site_id,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            assistant_preference=assistant_preference,
        ):
            recommendation = self.experiment_lab.suggest_route(domain=domain, subject_key=subject_key)
            if recommendation is not None:
                return recommendation
        return None
    def _pattern_from_selection(self, selection: ModeSelectionDecision) -> InteractionPattern | None:
        if not selection.reusable_pattern_id:
            return None
        return self.registry.repository.get_interaction_pattern(selection.reusable_pattern_id)

    def _actions_from_pattern(self, pattern: InteractionPattern | None) -> list[ToolAction]:
        if pattern is None:
            return []
        actions: list[ToolAction] = []
        for step in pattern.operations:
            action = self._action_from_pattern_step(step.operation, step.target)
            if action is None:
                return []
            actions.append(action)
        return actions

    def _action_from_pattern_step(self, operation: str, target: str) -> ToolAction | None:
        if operation == ToolActionType.OPEN_URL.value:
            if not target:
                return None
            return ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir URL reutilizada', target=target, expected_signal='page_opened', metadata={'reused_from_pattern': True})
        if operation == ToolActionType.CLICK.value:
            if not target:
                return None
            return ToolAction(action_type=ToolActionType.CLICK, label='Click reutilizado', target=target, metadata={'reused_from_pattern': True})
        if operation == ToolActionType.EXTRACT_TEXT.value:
            if not target:
                return None
            return ToolAction(action_type=ToolActionType.EXTRACT_TEXT, label='Extraccion reutilizada', target=target, metadata={'reused_from_pattern': True})
        if operation == ToolActionType.SCREENSHOT.value:
            path = target or str(self.workspace_root / 'data' / 'tool_teaching' / 'playwright_reused.png')
            return ToolAction(action_type=ToolActionType.SCREENSHOT, label='Captura reutilizada', target=path, parameters={'path': path}, metadata={'reused_from_pattern': True})
        if operation == ToolActionType.VERIFY_STATE.value:
            return ToolAction(action_type=ToolActionType.VERIFY_STATE, label='Verificacion reutilizada', target=target, metadata={'reused_from_pattern': True})
        return None

    def _tool_type_for_unknown(self, tool_id: str):
        from iabv_v15.domain.models import ToolType

        if tool_id == 'playwright_browser':
            return ToolType.BROWSER
        if tool_id == 'aider_coder':
            return ToolType.CODE_EDITOR
        if tool_id == 'mcp_client':
            return ToolType.MCP_CLIENT
        if tool_id == 'shell_command':
            return ToolType.SHELL
        if tool_id in {'codex_installed', 'chatgpt_installed', 'claude_installed'}:
            return ToolType.CUSTOM
        if tool_id in {'chatgpt_web_assisted', 'claude_web_assisted'}:
            return ToolType.LLM_WEB_UI
        return ToolType.LLM_LOCAL








