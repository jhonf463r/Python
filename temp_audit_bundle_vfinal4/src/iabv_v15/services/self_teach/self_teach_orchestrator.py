from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    AssistantConfigurationSnapshot,
    DiagnosticCategory,
    EnvironmentSelfModel,
    ExperimentDomain,
    EvaluationRoute,
    GuidedImprovementCycle,
    GuidedImprovementFinding,
    GuidedImprovementProposal,
    IATraceEntry,
    IssueSeverity,
    RunRecord,
    ScenarioRun,
    canonical_external_state_flag,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.services.self_teach.scenario_auto_test_service import ScenarioAutoTestService


class SelfTeachOrchestrator:
    def __init__(
        self,
        *,
        adaptive_session_repository: AdaptiveSessionRepository,
        pending_issue_repository: PendingIssueRepository,
        scenario_auto_test_service: ScenarioAutoTestService,
        scenario_run_repository: ScenarioRunRepository | None = None,
        experiment_lab: Any | None = None,
        tool_memory: Any | None = None,
        environment_self_awareness_service: Any | None = None,
    ) -> None:
        self.adaptive_session_repository = adaptive_session_repository
        self.pending_issue_repository = pending_issue_repository
        self.scenario_auto_test_service = scenario_auto_test_service
        self.scenario_run_repository = scenario_run_repository
        self.experiment_lab = experiment_lab
        self.tool_memory = tool_memory
        self.environment_self_awareness_service = environment_self_awareness_service

    def run_diagnostic(self, run_record: RunRecord) -> dict[str, object]:
        return self.run_guided_cycle(run_record)

    def run_guided_cycle(self, run_record: RunRecord) -> dict[str, object]:
        sessions = self.adaptive_session_repository.find_by_run(run_record.run_id)
        session = sessions[0] if sessions else self._fallback_session()
        if session is None:
            raise ValueError('No encontre una sesion adaptativa ligada a la corrida para ejecutar autotest.')
        scenario_run, updated_session = self.scenario_auto_test_service.run(run_record=run_record, session=session)
        pending_issue = self.pending_issue_repository.get(scenario_run.pending_issue_id) if scenario_run.pending_issue_id else None
        environment_model = self._current_environment_model()
        comparison_scope_key = self._comparison_scope_key(run_record=run_record, session=updated_session, scenario_run=scenario_run)
        source_trace_ids = self._source_trace_ids(run_record.result.raw_output)
        tool_history = self._recent_tool_history(
            user_goal=run_record.request.user_goal,
            site_id=updated_session.context.site_id or updated_session.intent.site_hint,
        )
        external_state_flags = self._collect_external_state_flags(
            raw_output=dict(run_record.result.raw_output or {}),
            tool_history=tool_history,
            pending_issue=pending_issue,
        )
        findings = self._detect_blockages(
            scenario_run=scenario_run,
            pending_issue=pending_issue,
            environment_model=environment_model,
            tool_history=tool_history,
            external_state_flags=external_state_flags,
        )
        proposals = self._propose_corrections(
            scenario_run=scenario_run,
            pending_issue=pending_issue,
            environment_model=environment_model,
            findings=findings,
            external_state_flags=external_state_flags,
        )
        cycle = GuidedImprovementCycle(
            run_id=run_record.run_id,
            session_id=updated_session.session_id,
            scenario_run_id=scenario_run.scenario_run_id,
            scenario_id=scenario_run.scenario.scenario_id,
            comparison_scope_key=comparison_scope_key,
            status=self._cycle_status(findings=findings, proposals=proposals, diagnosis_category=scenario_run.diagnosis.category if scenario_run.diagnosis else None),
            detected_blockages=findings,
            proposed_corrections=proposals,
            notifications=self._notifications(findings=findings, proposals=proposals),
            external_state_flags=external_state_flags,
            applied_count=sum(1 for proposal in proposals if proposal.applied),
            requires_user_decision=any(proposal.requires_user_decision for proposal in proposals),
            metadata={
                'source_trace_ids': source_trace_ids,
                'environment_id': str(environment_model.environment_id or ''),
                'environment_scan_status': str(environment_model.scan_status or ''),
                'pending_issue_id': pending_issue.issue_id if pending_issue is not None else '',
                'diagnosis_category': scenario_run.diagnosis.category.value if scenario_run.diagnosis is not None else '',
            },
        )
        trace_entry = self._guided_trace_entry(
            cycle=cycle,
            scenario_run=scenario_run,
            external_state_flags=external_state_flags,
            source_trace_ids=source_trace_ids,
        )
        learning_registered = self._register_learning(
            cycle=cycle,
            trace_entry=trace_entry,
            run_record=run_record,
            scenario_run=scenario_run,
            findings=findings,
            proposals=proposals,
            pending_issue=pending_issue,
        )
        cycle = cycle.model_copy(
            update={
                'trace_id': trace_entry.trace_id,
                'lab_run_id': str(learning_registered.get('lab_run_id') or ''),
                'lab_recommendation_id': str(learning_registered.get('lab_recommendation_id') or ''),
            }
        )
        audit_log_id = self._register_cycle_log(cycle=cycle, trace_entry=trace_entry)
        cycle = cycle.model_copy(update={'metadata': {**dict(cycle.metadata or {}), 'audit_log_id': audit_log_id}})
        scenario_run = scenario_run.model_copy(update={'metadata': {**dict(scenario_run.metadata or {}), 'guided_improvement_cycle': cycle.model_dump(mode='json')}})
        if self.scenario_run_repository is not None:
            self.scenario_run_repository.save(scenario_run)
        updated_session = updated_session.model_copy(update={'metadata': {**dict(updated_session.metadata or {}), 'guided_improvement_cycle': cycle.model_dump(mode='json')}})
        self.adaptive_session_repository.save(updated_session)
        return {
            'scenario_run': scenario_run.model_dump(mode='json'),
            'adaptive_session': updated_session.model_dump(mode='json'),
            'probe_diagnosis': scenario_run.diagnosis.model_dump(mode='json') if scenario_run.diagnosis is not None else None,
            'runtime_adjustments': [item.model_dump(mode='json') for item in scenario_run.runtime_adjustments],
            'pending_issue': pending_issue.model_dump(mode='json') if pending_issue is not None else None,
            'guided_improvement_cycle': cycle.model_dump(mode='json'),
            'learning_registered': learning_registered,
            'environment_self_model': environment_model.model_dump(mode='json'),
            'ia_trace_entry': trace_entry.model_dump(mode='json'),
        }

    def _detect_blockages(
        self,
        *,
        scenario_run: ScenarioRun,
        pending_issue: Any | None,
        environment_model: EnvironmentSelfModel,
        tool_history: list[dict[str, Any]],
        external_state_flags: list[str],
    ) -> list[GuidedImprovementFinding]:
        findings = self._repeated_error_findings(scenario_run=scenario_run)
        findings.extend(self._tool_findings(tool_history=tool_history))
        findings.extend(self._hardware_findings(environment_model=environment_model))
        if external_state_flags:
            findings.append(GuidedImprovementFinding(kind='external_blocked', severity=IssueSeverity.HIGH, summary='La ruta externa quedo bloqueada o sin verificacion suficiente.', repeated_count=len(external_state_flags), source='external_state_flags', safe_to_apply=True, external_state_flags=external_state_flags, evidence_refs=list(external_state_flags[:4])))
        if pending_issue is not None:
            findings.append(GuidedImprovementFinding(kind='pending_issue_open', severity=IssueSeverity.MEDIUM, summary='Ya existe un pending issue tecnico abierto para este escenario.', repeated_count=1, source='pending_issue_repository', safe_to_apply=True, evidence_refs=[pending_issue.issue_id], metadata={'issue_id': pending_issue.issue_id}))
        if scenario_run.diagnosis is not None and scenario_run.diagnosis.category == DiagnosticCategory.NEED_TEACHING and not scenario_run.runtime_adjustments:
            findings.append(GuidedImprovementFinding(kind='teaching_gap', severity=IssueSeverity.MEDIUM, summary='La ruta sigue debil por evidencia o ensenanza insuficiente.', repeated_count=1, source='probe_diagnosis', safe_to_apply=False, evidence_refs=list(scenario_run.diagnosis.evidence_refs[:4])))
        return findings or [GuidedImprovementFinding(kind='no_blocker_confirmed', severity=IssueSeverity.LOW, summary='No encontre un bloqueo nuevo reproducible; solo registre el estado actual.', source='guided_self_improvement')]

    def _repeated_error_findings(self, *, scenario_run: ScenarioRun) -> list[GuidedImprovementFinding]:
        if self.scenario_run_repository is None or scenario_run.diagnosis is None:
            return []
        recent = [item for item in self.scenario_run_repository.list_recent(limit=12) if item.scenario.scenario_id == scenario_run.scenario.scenario_id and item.diagnosis is not None]
        same_category = [item for item in recent if item.diagnosis is not None and item.diagnosis.category == scenario_run.diagnosis.category]
        findings: list[GuidedImprovementFinding] = []
        if len(same_category) >= 2:
            findings.append(GuidedImprovementFinding(kind='repeated_error', severity=IssueSeverity.HIGH if len(same_category) >= 3 else IssueSeverity.MEDIUM, summary=f'El mismo diagnostico ({scenario_run.diagnosis.category.value}) se repitio {len(same_category)} veces.', repeated_count=len(same_category), source='scenario_run_repository', safe_to_apply=bool(scenario_run.runtime_adjustments), evidence_refs=[item.scenario_run_id for item in same_category[:4]], metadata={'scenario_id': scenario_run.scenario.scenario_id}))
        stuck_runs = [item for item in recent[:3] if item.diagnosis is not None and item.diagnosis.category != DiagnosticCategory.READY_FOR_GUIDED_LIVE]
        if len(stuck_runs) >= 2:
            findings.append(GuidedImprovementFinding(kind='route_stuck', severity=IssueSeverity.HIGH, summary='La ruta viene atascada en varias corridas recientes y ya no parece un fallo aislado.', repeated_count=len(stuck_runs), source='scenario_run_repository', safe_to_apply=False, evidence_refs=[item.scenario_run_id for item in stuck_runs[:4]], metadata={'scenario_id': scenario_run.scenario.scenario_id}))
        return findings

    def _tool_findings(self, *, tool_history: list[dict[str, Any]]) -> list[GuidedImprovementFinding]:
        findings: list[GuidedImprovementFinding] = []
        missing: dict[str, dict[str, Any]] = {}
        failures: dict[str, dict[str, Any]] = {}
        for item in tool_history:
            tool_id = str(item.get('tool_id') or '')
            if not tool_id:
                continue
            state = str(item.get('state') or '')
            bucket = missing if state in {'missing_tool', 'adapter_missing'} else failures if not item.get('success', False) else None
            if bucket is None:
                continue
            current = bucket.setdefault(tool_id, {'count': 0, 'title': item.get('title') or tool_id, 'state': state, 'evidence_refs': []})
            current['count'] += 1
            if item.get('result_id'):
                current['evidence_refs'].append(item['result_id'])
        for tool_id, payload in missing.items():
            if payload['count'] >= 2:
                findings.append(GuidedImprovementFinding(kind='tool_missing', severity=IssueSeverity.MEDIUM, summary=f"La herramienta {payload['title']} viene faltando o sin adaptador real en {payload['count']} corridas.", repeated_count=int(payload['count']), source='tool_record_repository', safe_to_apply=False, evidence_refs=list(payload['evidence_refs'][:4]), metadata={'tool_id': tool_id}))
        for tool_id, payload in failures.items():
            if payload['count'] >= 2:
                findings.append(GuidedImprovementFinding(kind='tool_failure', severity=IssueSeverity.MEDIUM, summary=f"La herramienta {payload['title']} se repitio en fallo ({payload['state'] or 'failed'}) {payload['count']} veces.", repeated_count=int(payload['count']), source='tool_record_repository', safe_to_apply=False, evidence_refs=list(payload['evidence_refs'][:4]), metadata={'tool_id': tool_id, 'state': payload['state']}))
        return findings

    def _hardware_findings(self, *, environment_model: EnvironmentSelfModel) -> list[GuidedImprovementFinding]:
        severe_risks = [risk for risk in environment_model.risk_signals if risk.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL}]
        if not severe_risks:
            return []
        severity = IssueSeverity.CRITICAL if any(risk.severity == IssueSeverity.CRITICAL for risk in severe_risks) else IssueSeverity.HIGH
        return [
            GuidedImprovementFinding(
                kind='hardware_pressure',
                severity=severity,
                summary='El entorno esta bajo presion y no conviene lanzar mas carga pesada hasta estabilizar CPU, RAM o GPU.',
                repeated_count=len(severe_risks),
                source='environment_self_model',
                safe_to_apply=False,
                evidence_refs=[risk.kind for risk in severe_risks[:4]],
                metadata={'risk_kinds': [risk.kind for risk in severe_risks[:6]], 'environment_id': environment_model.environment_id},
            )
        ]

    def _propose_corrections(
        self,
        *,
        scenario_run: ScenarioRun,
        pending_issue: Any | None,
        environment_model: EnvironmentSelfModel,
        findings: list[GuidedImprovementFinding],
        external_state_flags: list[str],
    ) -> list[GuidedImprovementProposal]:
        proposals: list[GuidedImprovementProposal] = []
        for adjustment in scenario_run.runtime_adjustments:
            proposals.append(GuidedImprovementProposal(action_key='runtime_tuning_applied', title='Ajuste runtime aplicado', summary='El autotest encontro un ajuste runtime seguro y ya lo aplico.', rationale=adjustment.reason, safe_to_apply=True, reversible=bool(adjustment.reversible), verifiable=True, applied=True, verification_steps=['Repetir autotest', 'Revisar Centro Evolutivo'], evidence_refs=list(adjustment.evidence_refs[:4]), metadata={'adjustment_id': adjustment.adjustment_id, 'target_key': adjustment.target_key}))
        if pending_issue is not None:
            proposals.append(GuidedImprovementProposal(action_key='preserve_pending_issue', title='Escalado tecnico ya registrado', summary='El caso ya quedo formalizado como pending issue para no repetir el mismo fallo como si fuera nuevo.', rationale='Registrar el issue es seguro y deja trazabilidad clara.', safe_to_apply=True, reversible=True, verifiable=True, applied=True, verification_steps=list(pending_issue.suggested_tests[:3]), evidence_refs=[pending_issue.issue_id], metadata={'issue_id': pending_issue.issue_id}))
        if external_state_flags:
            proposals.append(GuidedImprovementProposal(action_key='record_external_block_and_penalize_route', title='Bloqueo externo registrado', summary='Se puede dejar trazado el bloqueo formal y penalizar esa ruta para no fingir exito ni insistir a ciegas.', rationale='Esta correccion solo registra aprendizaje reutilizable.', safe_to_apply=True, reversible=True, verifiable=True, applied=True, verification_steps=['Repetir la consulta y revisar recommendation del laboratorio'], evidence_refs=list(external_state_flags[:4]), metadata={'external_state_flags': external_state_flags}))
        if any(finding.kind in {'tool_missing', 'tool_failure'} for finding in findings):
            proposals.append(GuidedImprovementProposal(action_key='repair_or_replace_missing_tool', title='Reparar o reemplazar herramienta fallida', summary='Hace falta una decision humana para reparar la herramienta o confirmar una alternativa.', rationale='Instalar o reemplazar herramientas no es seguro sin confirmar el contexto exacto.', safe_to_apply=False, reversible=True, verifiable=True, requires_user_decision=True, verification_steps=['Confirmar herramienta alternativa', 'Repetir autotest despues de la reparacion']))
        severe_risks = [risk for risk in environment_model.risk_signals if risk.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL}]
        if severe_risks:
            proposals.append(GuidedImprovementProposal(action_key='protect_hardware_before_heavy_retry', title='Proteger hardware antes de reintentar', summary='El entorno actual pide bajar carga antes de repetir una ruta pesada.', rationale='Cuando CPU, RAM o GPU estan tensos conviene estabilizar el equipo antes de seguir.', safe_to_apply=False, reversible=True, verifiable=True, requires_user_decision=True, blocked_reason='hardware_pressure', verification_steps=['Esperar a que baje la presion', 'Revisar panel de entorno en Evolutivo'], evidence_refs=[risk.kind for risk in severe_risks[:4]]))
        return proposals or [GuidedImprovementProposal(action_key='observe_only', title='Sin correccion minima segura', summary='En esta pasada no encontre una correccion automatica segura; deje la evidencia lista para la siguiente decision.', rationale='No conviene tocar mas si no hay una mejora minima, reversible y verificable.', safe_to_apply=False, reversible=True, verifiable=True)]

    def _cycle_status(self, *, findings: list[GuidedImprovementFinding], proposals: list[GuidedImprovementProposal], diagnosis_category: DiagnosticCategory | None) -> str:
        if diagnosis_category == DiagnosticCategory.READY_FOR_GUIDED_LIVE and not any(f.kind in {'external_blocked', 'hardware_pressure'} for f in findings):
            return 'ready_for_guided_live'
        if any(proposal.requires_user_decision for proposal in proposals):
            return 'needs_user'
        if any(proposal.applied for proposal in proposals):
            return 'applied'
        return 'observed'

    def _notifications(self, *, findings: list[GuidedImprovementFinding], proposals: list[GuidedImprovementProposal]) -> list[str]:
        notes: list[str] = []
        if any(finding.kind == 'hardware_pressure' for finding in findings):
            notes.append('Detecte riesgo de hardware: voy a evitar reintentos pesados hasta que el entorno baje de presion.')
        if any(finding.kind == 'external_blocked' for finding in findings):
            notes.append('La ruta externa quedo bloqueada formalmente; el sistema la deja trazada y evitara contarla como exito.')
        if any(proposal.action_key == 'runtime_tuning_applied' and proposal.applied for proposal in proposals):
            notes.append('Aplique un ajuste runtime seguro y verificable para no repetir el mismo tuning manual.')
        if any(finding.kind == 'route_stuck' for finding in findings):
            notes.append('La ruta ya se ve atascada en varias corridas; no la voy a tratar como un fallo aislado.')
        return notes[:6]

    def _guided_trace_entry(
        self,
        *,
        cycle: GuidedImprovementCycle,
        scenario_run: ScenarioRun,
        external_state_flags: list[str],
        source_trace_ids: list[str],
    ) -> IATraceEntry:
        lead_proposal = next((item for item in cycle.proposed_corrections if item.applied), None) or next(iter(cycle.proposed_corrections), None)
        outcome_summary = next((item.summary for item in cycle.detected_blockages if item.kind != 'no_blocker_confirmed'), cycle.detected_blockages[0].summary if cycle.detected_blockages else 'Sin hallazgos nuevos.')
        return IATraceEntry(
            assistant_kind='self_teach',
            requested_assistant_kind='self_teach',
            actual_assistant_kind='self_teach',
            assistant_configuration=AssistantConfigurationSnapshot(planning_mode='with_plan', tools_mode='with_tools', assistant_mode='general', origin_mode='local', metadata={'trace_role': 'guided_improvement'}),
            config_signature='with_plan|without_files|normal|short|with_tools|without_browser|general|local',
            comparison_scope_key=cycle.comparison_scope_key,
            source_trace_ids=source_trace_ids,
            route='guided_self_improvement',
            tool_id='self_teach_orchestrator',
            task_id=cycle.run_id,
            session_scope='guided_self_improvement',
            state=cycle.status,
            detail=' | '.join(cycle.notifications[:2])[:240],
            proposal_summary=str(lead_proposal.summary if lead_proposal is not None else 'Sin correccion minima segura')[:240],
            outcome_summary=str(outcome_summary)[:240],
            result_label=scenario_run.diagnosis.category.value if scenario_run.diagnosis is not None else cycle.status,
            success=bool(scenario_run.runtime_adjustments) and not any(flag in external_state_flags for flag in {'account_limited', 'session_expired', 'wrong_thread'}),
            confidence=round(min(0.98, 0.55 + (0.08 * len([item for item in cycle.proposed_corrections if item.applied]))), 2),
            evidence_refs=list(dict.fromkeys([cycle.scenario_run_id, *[item for item in cycle.external_state_flags[:4]]]))[:8],
            external_state_flags=external_state_flags,
            metadata={'trace_role': 'guided_improvement', 'scenario_id': cycle.scenario_id, 'applied_count': cycle.applied_count, 'requires_user_decision': cycle.requires_user_decision},
        )

    def _register_learning(
        self,
        *,
        cycle: GuidedImprovementCycle,
        trace_entry: IATraceEntry,
        run_record: RunRecord,
        scenario_run: ScenarioRun,
        findings: list[GuidedImprovementFinding],
        proposals: list[GuidedImprovementProposal],
        pending_issue: Any | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {'trace_id': trace_entry.trace_id, 'comparison_scope_key': trace_entry.comparison_scope_key, 'source_trace_ids': list(trace_entry.source_trace_ids), 'subject_key': f'guided_improvement:{scenario_run.scenario.scenario_id or run_record.request.site_hint or "general"}'}
        if self.experiment_lab is None:
            return payload
        applied = [proposal for proposal in proposals if proposal.applied]
        learning_success = (scenario_run.diagnosis is not None and scenario_run.diagnosis.category == DiagnosticCategory.READY_FOR_GUIDED_LIVE) or (bool(applied) and not any(finding.kind in {'route_stuck', 'tool_missing', 'hardware_pressure'} for finding in findings))
        domain = ExperimentDomain.CODE if scenario_run.diagnosis and scenario_run.diagnosis.category in {DiagnosticCategory.NEED_CODEX_FIX, DiagnosticCategory.NEED_ADAPTER, DiagnosticCategory.NEED_RUNTIME_TUNING} else ExperimentDomain.LANGUAGE
        run, recommendation = self.experiment_lab.record_outcome(
            domain=domain,
            objective=run_record.request.user_goal,
            subject_key=payload['subject_key'],
            route=self._learning_route(scenario_run),
            candidate_label='guided_self_improvement',
            success=learning_success,
            observed_summary=' | '.join([*(finding.summary for finding in findings[:2]), *(proposal.summary for proposal in applied[:1])])[:240],
            expected_summary='Detectar, corregir si es seguro y registrar aprendizaje.',
            precision=0.78 if learning_success else 0.34,
            robustness=0.72 if applied else 0.41,
            reuse_score=min(1.0, len(trace_entry.source_trace_ids) / 3.0),
            user_progress=0.65 if applied else 0.35,
            execution_ms=0,
            evidence_refs=list(dict.fromkeys([scenario_run.scenario_run_id, *(finding.evidence_refs[0] for finding in findings if finding.evidence_refs)]))[:8],
            metadata={
                'assistant_kind': 'self_teach',
                'assistant_configuration': trace_entry.assistant_configuration.model_dump(mode='json'),
                'config_signature': trace_entry.config_signature,
                'trace_id': trace_entry.trace_id,
                'comparison_scope_key': trace_entry.comparison_scope_key,
                'source_trace_ids': list(trace_entry.source_trace_ids),
                'proposal_summary': trace_entry.proposal_summary,
                'outcome_summary': trace_entry.outcome_summary,
                'trace_role': 'guided_improvement',
                'pending_issue_id': pending_issue.issue_id if pending_issue is not None else '',
                'external_state_flags': list(cycle.external_state_flags),
                'applied_count': cycle.applied_count,
            },
            suite_name='guided_self_improvement',
        )
        payload.update({'lab_run_id': run.run_id, 'lab_recommendation_id': recommendation.recommendation_id, 'lab_recommended_route': recommendation.recommended_route.value})
        return payload

    def _register_cycle_log(self, *, cycle: GuidedImprovementCycle, trace_entry: IATraceEntry) -> str:
        if self.tool_memory is None:
            return ''
        return self.tool_memory.audit_event(
            tool_id='self_teach_orchestrator',
            task_id=cycle.run_id or None,
            action_type='guided_self_improvement',
            state=cycle.status,
            payload={'guided_improvement_cycle': cycle.model_dump(mode='json'), 'ia_trace_entry': trace_entry.model_dump(mode='json')},
        )

    def _recent_tool_history(self, *, user_goal: str, site_id: str | None) -> list[dict[str, Any]]:
        if self.tool_memory is None:
            return []
        repository = self.tool_memory.repository
        goal_tokens = self._tokens(user_goal)
        items: list[dict[str, Any]] = []
        for task in repository.list_tasks(limit=20):
            if site_id and task.site_id and task.site_id != site_id:
                continue
            objective_tokens = self._tokens(task.objective)
            if goal_tokens and objective_tokens and not goal_tokens.intersection(objective_tokens):
                continue
            result = next(iter(repository.list_results(task_id=task.task_id, limit=1)), None)
            if result is None:
                continue
            items.append(
                {
                    'tool_id': task.tool_id,
                    'title': task.title or task.tool_id,
                    'task_id': task.task_id,
                    'result_id': result.result_id,
                    'state': str(result.execution_state.state or ''),
                    'success': bool(result.success),
                    'error_message': result.error_message,
                    'external_state_flags': self._normalize_external_flags(
                        [
                            result.metadata.get('external_state_flags'),
                            result.execution_state.metadata,
                            result.execution_state.state,
                            result.execution_state.detail,
                            result.error_message,
                        ]
                    ),
                }
            )
        return items

    def _collect_external_state_flags(self, *, raw_output: dict[str, Any], tool_history: list[dict[str, Any]], pending_issue: Any | None) -> list[str]:
        perception = dict(raw_output.get('perception_snapshot') or {})
        decision_context = dict(raw_output.get('decision_context') or {})
        values: list[Any] = [
            raw_output.get('external_state_flags'),
            perception.get('external_state_flags'),
            perception.get('metadata'),
            decision_context.get('metadata'),
            raw_output.get('health_flags'),
        ]
        if pending_issue is not None:
            values.append(pending_issue.metadata)
        for item in tool_history:
            values.append(item.get('external_state_flags') or [])
            values.append(item.get('state') or '')
            values.append(item.get('error_message') or '')
        return self._normalize_external_flags(values)

    def _normalize_external_flags(self, values: list[Any]) -> list[str]:
        flags: list[str] = []
        for value in values:
            for candidate in self._iter_external_state_values(value):
                normalized = canonical_external_state_flag(candidate)
                if normalized and normalized not in flags:
                    flags.append(normalized)
        return flags

    def _iter_external_state_values(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, dict):
            items: list[Any] = []
            for key in ('external_state_flags', 'health_flags', 'coherence_flags'):
                if key in value:
                    items.extend(self._iter_external_state_values(value.get(key)))
            for key in ('state', 'detail', 'error_message', 'status', 'quota_status', 'account_status', 'thread_verification'):
                if key in value:
                    items.append(value.get(key))
            for nested in ('metadata', 'autonomous_consultation'):
                if nested in value and value.get(nested) is not value:
                    items.extend(self._iter_external_state_values(value.get(nested)))
            return items
        if isinstance(value, (list, tuple, set)):
            items: list[Any] = []
            for entry in value:
                items.extend(self._iter_external_state_values(entry))
            return items
        return [value]

    def _comparison_scope_key(self, *, run_record: RunRecord, session: AdaptiveSession, scenario_run: ScenarioRun) -> str:
        raw_output = dict(run_record.result.raw_output or {})
        perception_meta = dict((raw_output.get('perception_snapshot') or {}).get('metadata') or {})
        decision_meta = dict((raw_output.get('decision_context') or {}).get('metadata') or {})
        for candidate in (
            perception_meta.get('comparison_scope_key'),
            decision_meta.get('comparison_scope_key'),
            session.metadata.get('comparison_scope_key') if isinstance(session.metadata, dict) else '',
        ):
            if str(candidate or '').strip():
                return str(candidate).strip()
        site_id = session.context.site_id or session.intent.site_hint or run_record.request.site_hint or 'general'
        return f'guided_improvement:{site_id}:{scenario_run.scenario.scenario_id or session.intent.intent_key or "general"}'

    def _source_trace_ids(self, raw_output: dict[str, Any] | None) -> list[str]:
        payload = dict(raw_output or {})
        perception_meta = dict((payload.get('perception_snapshot') or {}).get('metadata') or {})
        decision_meta = dict((payload.get('decision_context') or {}).get('metadata') or {})
        summary = dict(perception_meta.get('ia_trace_summary') or decision_meta.get('ia_trace_summary') or {})
        return [
            str(item)
            for item in (
                summary.get('reusable_trace_ids')
                or summary.get('supporting_trace_ids')
                or summary.get('latest_trace_ids')
                or []
            )
            if str(item).strip()
        ][:8]

    def _learning_route(self, scenario_run: ScenarioRun) -> EvaluationRoute:
        if scenario_run.diagnosis is None:
            return EvaluationRoute.FALLBACK
        if scenario_run.diagnosis.category == DiagnosticCategory.NEED_TEACHING:
            return EvaluationRoute.UI
        if scenario_run.diagnosis.category in {DiagnosticCategory.NEED_CODEX_FIX, DiagnosticCategory.NEED_ADAPTER}:
            return EvaluationRoute.CODE_AGENT
        if scenario_run.diagnosis.category == DiagnosticCategory.NEED_RUNTIME_TUNING:
            return EvaluationRoute.LOCAL
        return EvaluationRoute.FALLBACK

    def _current_environment_model(self) -> EnvironmentSelfModel:
        if self.environment_self_awareness_service is None:
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            model = self.environment_self_awareness_service.current_model()
            self.environment_self_awareness_service.request_refresh(reason='guided_self_improvement', full=False)
            return model
        except Exception:
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _tokens(self, text: str) -> set[str]:
        return {token for token in str(text or '').lower().split() if len(token) >= 4}

    def _fallback_session(self) -> AdaptiveSession | None:
        recent = self.adaptive_session_repository.list_recent(limit=1)
        return recent[0] if recent else None
