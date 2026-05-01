from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    AssistantConfigurationSnapshot,
    EvaluationRoute,
    ExperimentDomain,
    RoleRoute,
    RunRecord,
    RunStatus,
    TaskRole,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.services.lab.experiment_lab import ExperimentLab


# Maps AdaptiveSession terminal status -> ControlMasterService.mark_objective
# status string. Non-terminal statuses are not propagated so in-flight runs
# don't flip objectives to 'active' over and over.
_TERMINAL_STATUS_MAP: dict[AdaptiveSessionStatus, str] = {
    AdaptiveSessionStatus.COMPLETED: "completed",
    AdaptiveSessionStatus.ABORTED: "paused",
    AdaptiveSessionStatus.FAILED: "blocked",
}

# M2: umbral de confianza por debajo del cual se intenta re-clasificar
# el intent post-ejecucion si la sesion fallo.
_INTENT_CORRECTION_CONFIDENCE_THRESHOLD = 0.75


class TaskOutcomeRecorder:
    def __init__(
        self,
        *,
        adaptive_session_repository: AdaptiveSessionRepository,
        capability_repository: CapabilityRepository,
        approval_checkpoint_repository: ApprovalCheckpointRepository,
        experiment_lab: ExperimentLab | None = None,
        adaptive_weight_layer: Any | None = None,
        control_master_service: Any | None = None,
        intent_understanding_service: Any | None = None,
    ) -> None:
        self.adaptive_session_repository = adaptive_session_repository
        self.capability_repository = capability_repository
        self.approval_checkpoint_repository = approval_checkpoint_repository
        self.experiment_lab = experiment_lab
        self.adaptive_weight_layer = adaptive_weight_layer
        self.control_master_service = control_master_service
        self.intent_understanding_service = intent_understanding_service

    def record(self, session: AdaptiveSession, run_record: RunRecord | None = None) -> AdaptiveSession:
        if run_record is not None and self.experiment_lab is not None:
            session = self._record_learning(session=session, run_record=run_record)
            self._check_intent_correction(session=session, run_record=run_record)
        if session.capability_readiness:
            self.capability_repository.save_many(session.capability_readiness)
        if session.approval_checkpoints:
            self.approval_checkpoint_repository.save_many(session.approval_checkpoints)
        saved = self.adaptive_session_repository.save(session)
        self._propagate_to_control_master(saved)
        return saved

    def _propagate_to_control_master(self, session: AdaptiveSession) -> None:
        """Close the learning loop: if the session opted in by tagging its
        metadata with `control_master_objective_id` (string) or
        `control_master_unresolved` (list[str]), mirror the outcome into the
        ControlMasterService so any future session reading the digest sees
        real progress without human intervention.

        Silent no-op when the service wasn't wired (keeps unit tests and
        legacy bootstraps working). Any failure here must NOT break outcome
        recording.
        """
        service = self.control_master_service
        if service is None:
            return
        metadata = session.metadata or {}
        if not isinstance(metadata, dict):
            return

        objective_id = metadata.get("control_master_objective_id")
        if isinstance(objective_id, str) and objective_id.strip():
            mapped = _TERMINAL_STATUS_MAP.get(session.status)
            if mapped is not None:
                note = metadata.get("control_master_note") or ""
                if not isinstance(note, str):
                    note = str(note)
                try:
                    service.mark_objective(objective_id.strip(), mapped, note=note)
                except Exception:  # noqa: BLE001 - learning loop must not break recorder
                    pass

        unresolved = metadata.get("control_master_unresolved")
        if isinstance(unresolved, list):
            evidence_raw = metadata.get("control_master_unresolved_evidence") or []
            evidence = [str(e) for e in evidence_raw if str(e).strip()] if isinstance(evidence_raw, list) else []
            for item in unresolved:
                if not isinstance(item, str):
                    continue
                stripped = item.strip()
                if not stripped:
                    continue
                try:
                    service.mark_unresolved(stripped, evidence=list(evidence))
                except Exception:  # noqa: BLE001
                    pass

    def _record_learning(self, *, session: AdaptiveSession, run_record: RunRecord) -> AdaptiveSession:
        if self.experiment_lab is None:
            return session
        domain = self._experiment_domain(session=session, run_record=run_record)
        route = self._evaluation_route(session=session, run_record=run_record)
        assistant_kind = self._assistant_kind(session=session, run_record=run_record, route=route)
        assistant_configuration = self._assistant_configuration(
            session=session,
            run_record=run_record,
            assistant_kind=assistant_kind,
            route=route,
        )
        config_signature = self._config_signature(assistant_configuration)
        comparison_scope_key = self._comparison_scope_key(session=session, run_record=run_record)
        subject_keys = self._subject_keys(session=session, comparison_scope_key=comparison_scope_key)
        observed_summary = self._compact_summary(
            (
                run_record.result.summary
                or run_record.error_summary
                or run_record.result.error_summary
                or (session.outcome.summary if session.outcome is not None else '')
            )
        )
        expected_summary = self._compact_summary(
            session.playbook.goal if session.playbook is not None and str(session.playbook.goal).strip() else session.user_goal
        )
        external_state_flags = self._external_state_flags(session=session, run_record=run_record)
        source_trace_ids = self._source_trace_ids(session)
        metadata = {
            'assistant_kind': assistant_kind,
            'assistant_configuration': assistant_configuration.model_dump(mode='json'),
            'config_signature': config_signature,
            'comparison_scope_key': comparison_scope_key,
            'source_trace_ids': source_trace_ids,
            'proposal_summary': self._compact_summary(
                (session.playbook.summary if session.playbook is not None else '')
                or str((session.metadata.get('assistant_guidance') or {}).get('prompt') or '')
                or session.user_goal
            ),
            'outcome_summary': observed_summary,
            'used_fallback': bool(run_record.result.used_fallback or getattr(run_record.route, 'used_fallback', False)),
            'fallback_used': bool(run_record.result.used_fallback or getattr(run_record.route, 'used_fallback', False)),
            'blocked': bool(external_state_flags),
            'governance_blocked': False,
            'external_state_flags': external_state_flags,
            'health_flags': list(run_record.result.health_flags or []),
            'diagnostic_flags': list(run_record.result.diagnostic_flags or []),
            'environment_scan_status': str(
                (dict(session.metadata.get('decision_context') or {}).get('metadata') or {}).get('environment_scan_status')
                or ''
            ),
            'network_status': str(
                (dict((dict(session.metadata.get('decision_context') or {}).get('metadata') or {}).get('world_model_summary') or {}).get('network_status') or '')
            ),
            'dominant_incident': str(session.context.session_readiness.get('dominant_incident') or ''),
            'time_bucket': self._time_bucket(run_record),
            'task_type': session.intent.intent_key,
            'site_id': session.context.site_id or session.intent.site_hint or '',
            'goal_progress_signal': float(session.context.goal_context.progress or 0.0),
            'learning_source': 'adaptive_session_finalize',
            'linked_run_id': run_record.run_id,
            'selected_worker': dict(dict(session.metadata.get('worker_gate') or {}).get('top_worker') or {}),
            'ranked_worker_count': int(dict(session.metadata.get('worker_gate') or {}).get('available_count') or 0),
            'blocked_reason': str(dict(session.metadata.get('worker_gate') or {}).get('reason') or ''),
        }
        learning_records: list[dict[str, Any]] = []
        for subject_key in subject_keys:
            previous = self.experiment_lab.repository.latest_recommendation(domain=domain.value, subject_key=subject_key)
            run, recommendation = self.experiment_lab.record_outcome(
                domain=domain,
                objective=session.user_goal,
                subject_key=subject_key,
                route=route,
                candidate_label=assistant_kind or str(getattr(run_record.route, 'provider_name', '') or run_record.result.provider_name or route.value),
                candidate_id=run_record.run_id,
                success=run_record.status == RunStatus.SUCCESS,
                observed_summary=observed_summary,
                expected_summary=expected_summary,
                precision=self._precision(run_record),
                robustness=self._robustness(run_record=run_record, external_state_flags=external_state_flags),
                operational_cost=self._operational_cost(route=route, assistant_kind=assistant_kind),
                reuse_score=min(1.0, len(source_trace_ids) / 4.0),
                user_progress=self._user_progress(run_record),
                execution_ms=int(run_record.duration_ms or 0),
                evidence_refs=list(dict.fromkeys([*session.evidence_refs, *source_trace_ids]))[:8],
                metadata={**metadata, 'subject_key': subject_key},
                suite_name='adaptive_session_finalize',
            )
            weight_snapshot = (
                self.adaptive_weight_layer.update_weights(
                    historical_runs=self.experiment_lab.repository.list_runs(domain=domain.value, subject_key=subject_key, limit=20),
                    latest_run=run,
                )
                if self.adaptive_weight_layer is not None
                else {}
            )
            change_reason = (
                self.adaptive_weight_layer.explain_shift(previous=previous, current=recommendation)
                if self.adaptive_weight_layer is not None
                else ''
            )
            learning_records.append(
                {
                    'subject_key': subject_key,
                    'domain': domain.value,
                    'lab_run_id': run.run_id,
                    'recommendation_id': recommendation.recommendation_id,
                    'recommended_route': recommendation.recommended_route.value,
                    'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                    'recommended_config_signature': recommendation.recommended_config_signature,
                    'changed': bool(change_reason),
                    'change_reason': change_reason,
                    'adaptive_learning_summary': dict((recommendation.metadata or {}).get('adaptive_learning_summary') or {}),
                    'weight_snapshot': weight_snapshot,
                }
            )
        session.metadata['adaptive_learning'] = {
            'domain': domain.value,
            'comparison_scope_key': comparison_scope_key,
            'subject_keys': subject_keys,
            'records': learning_records[:6],
        }
        return session

    def _experiment_domain(self, *, session: AdaptiveSession, run_record: RunRecord) -> ExperimentDomain:
        if session.context.experiment_insights:
            raw = str(session.context.experiment_insights[0].get('domain') or '').strip().lower()
            for domain in ExperimentDomain:
                if domain.value == raw:
                    return domain
        text = ' '.join(
            [
                session.user_goal,
                session.intent.intent_key,
                str(run_record.result.summary or ''),
                str(run_record.error_summary or ''),
            ]
        ).lower()
        if any(token in text for token in ('codigo', 'code', 'bug', 'patch', 'incidente tecnico', 'bridge', 'adapter')):
            return ExperimentDomain.CODE
        if any(token in text for token in ('ocr', 'vision', 'objeto', 'captura')):
            return ExperimentDomain.OCR
        if any(token in text for token in ('algoritmo', 'algorithm')):
            return ExperimentDomain.ALGORITHM
        return ExperimentDomain.LANGUAGE

    def _evaluation_route(self, *, session: AdaptiveSession, run_record: RunRecord) -> EvaluationRoute:
        assistant_kind = self._assistant_kind(session=session, run_record=run_record, route=EvaluationRoute.FALLBACK)
        if assistant_kind == 'codex':
            return EvaluationRoute.CODE_AGENT
        if assistant_kind == 'ollama':
            return EvaluationRoute.LOCAL
        if assistant_kind in {'chatgpt', 'claude'}:
            return EvaluationRoute.LANGUAGE_UNDERSTANDING
        tools = {getattr(tool, 'value', str(tool)).strip().lower() for tool in (run_record.result.used_tools or [])}
        if {'browser_observation', 'desktop_automation'} & tools:
            return EvaluationRoute.UI
        if isinstance(run_record.route, RoleRoute):
            role = run_record.route.task_role
            if role == TaskRole.VISUAL:
                return EvaluationRoute.UI
            if role in {TaskRole.PROJECT_EVOLUTION, TaskRole.TOOL_USE, TaskRole.TOOL_SANDBOX}:
                return EvaluationRoute.LOCAL
        return EvaluationRoute.LANGUAGE_UNDERSTANDING

    def _assistant_kind(self, *, session: AdaptiveSession, run_record: RunRecord, route: EvaluationRoute) -> str:
        decision_metadata = dict((dict(session.metadata.get('decision_context') or {}).get('metadata') or {}))
        governance = dict((dict(session.metadata.get('decision_context') or {}).get('governance') or {}))
        for candidate in (
            run_record.result.raw_output.get('assistant_kind') if isinstance(run_record.result.raw_output, dict) else '',
            run_record.result.provider_name,
            getattr(run_record.route, 'provider_name', ''),
            decision_metadata.get('preferred_assistant_kind'),
            governance.get('assistant_kind'),
            next((item.get('recommended_assistant_kind') for item in session.context.experiment_insights if item.get('recommended_assistant_kind')), ''),
        ):
            normalized = str(candidate or '').strip().lower()
            if 'codex' in normalized:
                return 'codex'
            if 'claude' in normalized:
                return 'claude'
            if 'chatgpt' in normalized or 'openai' in normalized:
                return 'chatgpt'
            if 'ollama' in normalized or normalized == 'local':
                return 'ollama'
        if route == EvaluationRoute.CODE_AGENT:
            return 'codex'
        if route == EvaluationRoute.LOCAL:
            return 'ollama'
        return ''

    def _assistant_configuration(
        self,
        *,
        session: AdaptiveSession,
        run_record: RunRecord,
        assistant_kind: str,
        route: EvaluationRoute,
    ) -> AssistantConfigurationSnapshot:
        for insight in session.context.experiment_insights:
            if str(insight.get('recommended_assistant_kind') or '').strip().lower() != assistant_kind:
                continue
            payload = insight.get('recommended_assistant_configuration')
            if isinstance(payload, dict) and payload:
                return AssistantConfigurationSnapshot.model_validate(payload)
        origin_mode = 'local' if assistant_kind == 'ollama' or route == EvaluationRoute.LOCAL else 'external'
        browser_mode = 'with_browser' if route == EvaluationRoute.UI or assistant_kind in {'chatgpt', 'claude'} else 'without_browser'
        tools_mode = 'with_tools' if route in {EvaluationRoute.CODE_AGENT, EvaluationRoute.LOCAL, EvaluationRoute.UI} else 'without_tools'
        reasoning_level = 'extended' if session.intent.multi_step or run_record.result.confidence < 0.6 else 'normal'
        return AssistantConfigurationSnapshot(
            planning_mode='with_plan' if bool(run_record.request.enable_planning or session.intent.multi_step) else 'without_plan',
            attachments_mode='without_files',
            reasoning_level=reasoning_level,
            context_mode='long' if len(session.user_goal) > 120 else 'short',
            tools_mode=tools_mode,
            browser_mode=browser_mode,
            assistant_mode='code' if assistant_kind == 'codex' or route == EvaluationRoute.CODE_AGENT else 'general',
            origin_mode=origin_mode,
        )

    def _config_signature(self, configuration: AssistantConfigurationSnapshot) -> str:
        return '|'.join(
            [
                configuration.planning_mode,
                configuration.attachments_mode,
                configuration.reasoning_level,
                configuration.context_mode,
                configuration.tools_mode,
                configuration.browser_mode,
                configuration.assistant_mode,
                configuration.origin_mode,
            ]
        )

    def _comparison_scope_key(self, *, session: AdaptiveSession, run_record: RunRecord) -> str:
        decision_metadata = dict((dict(session.metadata.get('decision_context') or {}).get('metadata') or {}))
        perception_metadata = dict((dict(session.metadata.get('perception_snapshot') or {}).get('metadata') or {}))
        for candidate in (
            decision_metadata.get('comparison_scope_key'),
            perception_metadata.get('comparison_scope_key'),
        ):
            probe = str(candidate or '').strip()
            if probe:
                return probe
        site_prefix = session.context.site_id or session.intent.site_hint or run_record.request.site_hint or 'general'
        compact = '-'.join(
            token
            for token in (
                ''.join(character for character in raw if character.isalnum())
                for raw in session.user_goal.lower().split()
            )
            if token
        )[:72].strip('-')
        return f'{site_prefix}:{compact or "general"}'

    def _subject_keys(self, *, session: AdaptiveSession, comparison_scope_key: str) -> list[str]:
        goal_context = session.context.goal_context
        primary_context = next(
            (
                str(candidate).strip()
                for candidate in (
                    goal_context.task.get('objective_id') if isinstance(goal_context.task, dict) else '',
                    goal_context.project.get('objective_id') if isinstance(goal_context.project, dict) else '',
                    goal_context.objective.get('objective_id') if isinstance(goal_context.objective, dict) else '',
                    goal_context.active_node_id,
                    session.context.site_id or session.intent.site_hint or '',
                )
                if str(candidate or '').strip()
            ),
            '',
        )
        keys: list[str] = []
        for candidate in (comparison_scope_key, primary_context, 'general'):
            probe = str(candidate or '').strip()
            if probe and probe not in keys:
                keys.append(probe)
        return keys[:3]

    def _precision(self, run_record: RunRecord) -> float:
        confidence = max(0.0, min(float(run_record.result.confidence or 0.0), 1.0))
        if run_record.status == RunStatus.SUCCESS:
            value = confidence or 0.72
        elif run_record.status == RunStatus.PARTIAL:
            value = max(0.18, confidence * 0.72)
        else:
            value = max(0.05, confidence * 0.35)
        if run_record.result.used_fallback:
            value *= 0.82
        if run_record.error_summary or run_record.result.error_summary:
            value *= 0.75
        return round(max(0.0, min(value, 1.0)), 4)

    def _robustness(self, *, run_record: RunRecord, external_state_flags: list[str]) -> float:
        if run_record.status == RunStatus.SUCCESS:
            value = 0.82
        elif run_record.status == RunStatus.PARTIAL:
            value = 0.52
        else:
            value = 0.24
        if external_state_flags:
            value -= min(0.32, len(external_state_flags) * 0.08)
        if run_record.result.used_fallback:
            value -= 0.12
        if run_record.error_summary:
            value -= 0.18
        return round(max(0.0, min(value, 1.0)), 4)

    def _operational_cost(self, *, route: EvaluationRoute, assistant_kind: str) -> float:
        base = {
            EvaluationRoute.LOCAL: 0.06,
            EvaluationRoute.UI: 0.12,
            EvaluationRoute.LANGUAGE_UNDERSTANDING: 0.18,
            EvaluationRoute.CODE_AGENT: 0.28,
            EvaluationRoute.FALLBACK: 0.35,
        }.get(route, 0.2)
        if assistant_kind in {'chatgpt', 'claude', 'codex'}:
            base += 0.04
        return round(base, 4)

    def _user_progress(self, run_record: RunRecord) -> float:
        if run_record.status == RunStatus.SUCCESS:
            value = 0.82
        elif run_record.status == RunStatus.PARTIAL:
            value = 0.46
        else:
            value = 0.14
        if run_record.result.used_fallback:
            value -= 0.08
        return round(max(0.0, min(value, 1.0)), 4)

    def _external_state_flags(self, *, session: AdaptiveSession, run_record: RunRecord) -> list[str]:
        flags: list[str] = []
        for source in (
            run_record.result.raw_output.get('external_state_flags') if isinstance(run_record.result.raw_output, dict) else [],
            run_record.result.health_flags,
            run_record.result.diagnostic_flags,
            (dict(session.metadata.get('decision_context') or {}).get('metadata') or {}).get('external_state_flags'),
        ):
            for item in source or []:
                value = str(item or '').strip()
                if value and value not in flags:
                    flags.append(value)
        return flags[:8]

    def _source_trace_ids(self, session: AdaptiveSession) -> list[str]:
        decision_metadata = dict((dict(session.metadata.get('decision_context') or {}).get('metadata') or {}))
        ia_trace_summary = dict(decision_metadata.get('ia_trace_summary') or {})
        return [
            str(item)
            for item in (
                ia_trace_summary.get('reusable_trace_ids')
                or ia_trace_summary.get('winning_trace_ids')
                or decision_metadata.get('supporting_trace_ids')
                or []
            )
            if str(item).strip()
        ][:8]

    def _time_bucket(self, run_record: RunRecord) -> str:
        hour = int(run_record.created_at_utc.hour)
        if 5 <= hour < 12:
            return 'morning'
        if 12 <= hour < 18:
            return 'afternoon'
        if 18 <= hour < 23:
            return 'evening'
        return 'night'

    def _compact_summary(self, text: str, *, limit: int = 240) -> str:
        return ' '.join(str(text or '').split())[:limit]

    # ------------------------------------------------------------------
    # M2: Intent correction loop
    # ------------------------------------------------------------------

    def _check_intent_correction(self, *, session: AdaptiveSession, run_record: RunRecord) -> None:
        """Re-classify intent post-execution when a low-confidence intent led to failure.

        If the re-classification produces a different intent_key, record
        an ``intent_mismatch`` event in ExperimentLab so that
        StrategySelector can learn from the misrouting over time.
        """
        service = self.intent_understanding_service
        if service is None or self.experiment_lab is None:
            return
        if run_record.status == RunStatus.SUCCESS:
            return
        original_confidence = float(session.intent.confidence or 0.0)
        if original_confidence >= _INTENT_CORRECTION_CONFIDENCE_THRESHOLD:
            return
        try:
            from iabv_v15.domain.models import InferenceRequest
            recheck_request = InferenceRequest(
                user_goal=session.user_goal,
                site_hint=session.intent.site_hint or session.context.site_id,
                goal_parameters=dict(session.metadata.get('goal_parameters') or {}),
                conversation_context=list(session.metadata.get('conversation_context') or []),
                metadata={
                    'intent_correction_recheck': True,
                    'conversation_history': list(session.metadata.get('conversation_history') or []),
                },
            )
            new_intent, _ = service.classify(recheck_request)
        except Exception:
            return
        if new_intent.intent_key == session.intent.intent_key:
            return
        # M4: registrar el fallo del patron original para confidence decay
        try:
            from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
            IntentUnderstandingService.register_pattern_failure(session.intent.intent_key)
        except Exception:
            pass
        session.metadata['intent_correction'] = {
            'original_intent_key': session.intent.intent_key,
            'original_confidence': original_confidence,
            'corrected_intent_key': new_intent.intent_key,
            'corrected_confidence': float(new_intent.confidence or 0.0),
            'run_status': run_record.status.value,
        }
        try:
            self.experiment_lab.record_outcome(
                domain=ExperimentDomain.LANGUAGE,
                objective=f'intent_correction:{session.user_goal[:120]}',
                subject_key=f'intent_mismatch:{session.intent.intent_key}',
                route=EvaluationRoute.LOCAL,
                candidate_label='intent_correction',
                candidate_id=session.session_id,
                success=False,
                observed_summary=f'Intent original {session.intent.intent_key} (conf={original_confidence:.2f}) fallo; re-clasificacion sugiere {new_intent.intent_key} (conf={new_intent.confidence:.2f})',
                expected_summary=session.user_goal[:240],
                precision=0.3,
                robustness=0.4,
                reuse_score=0.0,
                user_progress=0.1,
                execution_ms=0,
                evidence_refs=[session.session_id],
                metadata={
                    'learning_source': 'intent_correction',
                    'original_intent_key': session.intent.intent_key,
                    'corrected_intent_key': new_intent.intent_key,
                    'blocked': False,
                    'external_state_flags': [],
                },
                suite_name='intent_correction',
            )
        except Exception:
            pass
