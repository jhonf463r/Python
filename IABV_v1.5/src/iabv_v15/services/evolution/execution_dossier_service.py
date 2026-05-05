from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    DossierScope,
    EvidenceKind,
    EvidenceRef,
    ExecutionDossier,
    HiddenIncident,
    ImprovementProposal,
    IssueCandidate,
    IssueSeverity,
    RunRecord,
    RunStatus,
    SessionArtifact,
    SessionHealthSnapshot,
    TaskRole,
    UserClue,
)
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.evolution.self_check_orchestrator import SelfCheckOrchestrator
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


class ExecutionDossierService:
    def __init__(
        self,
        *,
        repository: ExecutionDossierRepository,
        hidden_incident_repository: HiddenIncidentRepository,
        user_clue_repository: UserClueRepository,
        self_check_orchestrator: SelfCheckOrchestrator,
        role_router: LocalRoleRouter,
    ) -> None:
        self.repository = repository
        self.hidden_incident_repository = hidden_incident_repository
        self.user_clue_repository = user_clue_repository
        self.self_check_orchestrator = self_check_orchestrator
        self.role_router = role_router

    def build_for_run(self, run_record: RunRecord) -> ExecutionDossier:
        hidden_incidents = self.hidden_incident_repository.find_by_run(run_record.run_id)
        user_clues = self.user_clue_repository.find_by_run(run_record.run_id)
        evidence_refs = self._build_run_evidence(run_record)
        evidence_refs.extend(self._build_hidden_incident_evidence(hidden_incidents, user_clues))
        self_checks = self.self_check_orchestrator.run_light_checks_for_run(run_record, evidence_refs)
        issue_candidates = self._issues_for_run(run_record, self_checks) + self._issues_from_hidden_incidents(hidden_incidents)
        proposals = self._proposals_for_issues(issue_candidates, run_record.result.improvement_hints)
        proposals.extend(self._proposals_for_hidden_incidents(hidden_incidents))
        scope = self._scope_from_run(run_record)
        summary = run_record.result.summary.strip() or run_record.error_summary or 'La corrida termino sin resumen visible.'
        adaptive_payload = run_record.result.raw_output.get('adaptive_session') if isinstance(run_record.result.raw_output, dict) else None
        dossier = ExecutionDossier(
            scope=scope,
            title=run_record.request.user_goal.strip() or run_record.result.inferred_task or 'Ejecucion local',
            summary=summary,
            run_id=run_record.run_id,
            status=run_record.status,
            severity=self._severity_from_status(run_record.status, run_record.result.confidence, bool(issue_candidates)),
            issue_hint_text=issue_candidates[0].issue_hint if issue_candidates else '',
            detected_role=run_record.result.detected_role or getattr(run_record.route, 'task_role', None),
            model_used=run_record.result.executor_model or getattr(run_record.route, 'model_name', ''),
            planner_used=run_record.result.planner_used,
            tools_used=list(run_record.result.used_tools),
            duration_ms=run_record.duration_ms,
            error_summary=run_record.error_summary or run_record.result.error_summary,
            stack_health=[item.model_dump(mode='json') for item in self.role_router.health_snapshot()],
            metrics={
                'confidence': run_record.result.confidence,
                'used_fallback': run_record.result.used_fallback,
                'sources_count': len(run_record.result.sources),
                'clarifications_count': len(run_record.result.clarifications),
                'diagnostic_flags': list(run_record.result.diagnostic_flags),
                'approval_count': len(run_record.result.approval_checkpoints),
                'playbook_step_count': len((run_record.result.playbook or {}).get('steps', [])) if isinstance(run_record.result.playbook, dict) else 0,
                'next_actions_count': len(run_record.result.next_actions),
            },
            evidence_refs=evidence_refs,
            issue_candidates=issue_candidates,
            improvement_proposals=proposals,
            self_checks=self_checks,
            hidden_incidents=hidden_incidents,
            session_health=self._session_health_from_metrics(run_id=run_record.run_id, metrics=run_record.result.raw_output.get('session_health') if isinstance(run_record.result.raw_output, dict) else {}, hidden_incidents=hidden_incidents),
            user_clues=user_clues,
            incident_summary=self._incident_summary(hidden_incidents, user_clues),
            next_action=proposals[0].recommended_change if proposals else 'Revisar el dossier y confirmar si hace falta una prueba reproducible.',
            codex_brief=self._build_codex_brief(summary, issue_candidates, proposals, hidden_incidents, user_clues),
            metadata={
                'report_kind': run_record.result.report_kind.value,
                'route_reason': getattr(run_record.route, 'reason', ''),
                'reasoning_mode': run_record.result.reasoning_mode.value,
                'adaptive_session': adaptive_payload or {},
                'intent_key': (run_record.result.intent or {}).get('intent_key', '') if isinstance(run_record.result.intent, dict) else '',
                'chosen_pack_id': (run_record.result.chosen_pack or {}).get('pack_id', '') if isinstance(run_record.result.chosen_pack, dict) else '',
            },
        )
        return self.repository.save(dossier)

    def build_for_teaching_session(
        self,
        *,
        episode_id: str,
        title: str,
        status: RunStatus,
        metrics: dict[str, Any],
        steps: list[Any],
        artifacts: list[SessionArtifact],
        summary: str = '',
        error_summary: str = '',
    ) -> ExecutionDossier:
        hidden_incidents = self.hidden_incident_repository.find_by_episode(episode_id)
        user_clues = self.user_clue_repository.find_by_episode(episode_id)
        evidence_refs = self._build_teaching_evidence(episode_id, steps, artifacts)
        evidence_refs.extend(self._build_hidden_incident_evidence(hidden_incidents, user_clues))
        teaching_metrics = {
            **metrics,
            'has_recoverable_replay': bool(metrics.get('has_recoverable_replay', bool(steps or artifacts))),
        }
        self_checks = self.self_check_orchestrator.run_light_checks_for_teaching(teaching_metrics, evidence_refs)
        issue_candidates = self._issues_for_teaching(status, teaching_metrics, self_checks) + self._issues_from_hidden_incidents(hidden_incidents)
        proposals = self._proposals_for_teaching(issue_candidates, teaching_metrics)
        proposals.extend(self._proposals_for_hidden_incidents(hidden_incidents))
        summary_text = summary.strip() or self._teaching_summary_from_metrics(teaching_metrics)
        dossier = ExecutionDossier(
            scope=DossierScope.TEACHING,
            title=title,
            summary=summary_text,
            run_id=episode_id,
            episode_id=episode_id,
            status=status,
            severity=self._severity_from_status(status, 0.75, bool(issue_candidates)),
            issue_hint_text=issue_candidates[0].issue_hint if issue_candidates else '',
            detected_role=TaskRole.TRAINING,
            model_used='browser_teach_session',
            planner_used=False,
            tools_used=[],
            duration_ms=metrics.get('duration_ms'),
            error_summary=error_summary,
            stack_health=[item.model_dump(mode='json') for item in self.role_router.health_snapshot()],
            metrics=teaching_metrics,
            evidence_refs=evidence_refs,
            issue_candidates=issue_candidates,
            improvement_proposals=proposals,
            self_checks=self_checks,
            hidden_incidents=hidden_incidents,
            session_health=self._session_health_from_metrics(episode_id=episode_id, metrics=teaching_metrics, hidden_incidents=hidden_incidents),
            user_clues=user_clues,
            incident_summary=self._incident_summary(hidden_incidents, user_clues),
            next_action=proposals[0].recommended_change if proposals else 'Abrir el replay guiado y validar que los pasos sean reutilizables.',
            codex_brief=self._build_codex_brief(summary_text, issue_candidates, proposals, hidden_incidents, user_clues),
            metadata={'replay_available': bool(teaching_metrics.get('has_recoverable_replay'))},
        )
        return self.repository.save(dossier)

    def _scope_from_run(self, run_record: RunRecord) -> DossierScope:
        role = run_record.result.detected_role or getattr(run_record.route, 'task_role', None)
        if role == TaskRole.VISUAL:
            return DossierScope.VISUAL
        if role == TaskRole.PROJECT_EVOLUTION:
            return DossierScope.PROJECT_REVIEW
        return DossierScope.CHAT

    def _build_run_evidence(self, run_record: RunRecord) -> list[EvidenceRef]:
        evidence = [
            EvidenceRef(
                kind=EvidenceKind.RUN_RECORD,
                label='Run record principal',
                ref_id=run_record.run_id,
                metadata={'status': run_record.status.value, 'created_at_utc': run_record.created_at_utc.isoformat()},
            )
        ]
        for index, screenshot in enumerate(run_record.request.screenshots[:5], start=1):
            evidence.append(
                EvidenceRef(
                    kind=EvidenceKind.SCREENSHOT,
                    label=f'Screenshot de entrada {index}',
                    ref_id=f'{run_record.run_id}:screenshot:{index}',
                    path=screenshot,
                )
            )
        return evidence

    def _build_teaching_evidence(self, episode_id: str, steps: list[Any], artifacts: list[SessionArtifact]) -> list[EvidenceRef]:
        evidence = [
            EvidenceRef(kind=EvidenceKind.EPISODE, label='Episodio de ensenanza', ref_id=episode_id),
        ]
        screenshot_paths: list[str] = []
        for step in steps:
            if getattr(step, 'screenshot_path', None):
                screenshot_paths.append(str(step.screenshot_path))
        for index, screenshot in enumerate(screenshot_paths[:8], start=1):
            evidence.append(
                EvidenceRef(
                    kind=EvidenceKind.SCREENSHOT,
                    label=f'Captura visible {index}',
                    ref_id=f'{episode_id}:screenshot:{index}',
                    path=screenshot,
                )
            )
        for artifact in artifacts[:16]:
            evidence.append(
                EvidenceRef(
                    kind=EvidenceKind.ARTIFACT,
                    label=artifact.kind,
                    ref_id=artifact.artifact_id,
                    path=artifact.path,
                    metadata={'capture_channel': artifact.metadata.get('capture_channel', '')},
                )
            )
        return evidence

    def _build_hidden_incident_evidence(self, hidden_incidents: list[HiddenIncident], user_clues: list[UserClue]) -> list[EvidenceRef]:
        evidence: list[EvidenceRef] = []
        for incident in hidden_incidents[:6]:
            evidence.append(
                EvidenceRef(
                    kind=EvidenceKind.INCIDENT,
                    label=incident.incident_kind,
                    ref_id=incident.incident_id,
                    metadata={'severity': incident.severity.value, 'status': incident.status.value, 'affected_url': incident.affected_url},
                )
            )
        for clue in user_clues[:4]:
            evidence.append(
                EvidenceRef(
                    kind=EvidenceKind.USER_CLUE,
                    label='Pista del usuario',
                    ref_id=clue.clue_id,
                    metadata={'linked_incident_id': clue.linked_incident_id or '', 'text': clue.text[:120]},
                )
            )
        return evidence

    def _issues_from_hidden_incidents(self, hidden_incidents: list[HiddenIncident]) -> list[IssueCandidate]:
        issues: list[IssueCandidate] = []
        seen: set[str] = set()
        for incident in hidden_incidents:
            if incident.incident_kind in seen:
                continue
            seen.add(incident.incident_kind)
            issues.append(
                IssueCandidate(
                    title=incident.summary,
                    summary=incident.detail or incident.summary,
                    probable_cause=incident.probable_cause,
                    severity=incident.severity,
                    issue_hint=incident.incident_kind,
                    evidence_ids=list(incident.evidence_ids or [incident.incident_id]),
                )
            )
        return issues

    def _proposals_for_hidden_incidents(self, hidden_incidents: list[HiddenIncident]) -> list[ImprovementProposal]:
        proposals: list[ImprovementProposal] = []
        for incident in hidden_incidents:
            if incident.incident_kind == 'navigation_stall':
                proposals.append(
                    ImprovementProposal(
                        title='Instrumentar navegacion multitab',
                        rationale=incident.summary,
                        recommended_change='Revisar tiempos de carga, pestana activa y drenado de eventos al abrir nuevas pestanas durante la ensenanza.',
                        suggested_tests=['Ensenanza con 3-4 pestanas', 'Busqueda en pestana nueva'],
                        tradeoffs=['Mas instrumentacion de pestanas anade algo de ruido de runtime.'],
                        priority_score=90,
                    )
                )
            elif incident.incident_kind == 'capture_starvation':
                proposals.append(
                    ImprovementProposal(
                        title='Reforzar captura visible cuando hay heartbeat sin evidencia',
                        rationale=incident.summary,
                        recommended_change='Verificar bridge, checkpoints visuales y si el flujo quedo en iframe o pagina sin progreso visible.',
                        suggested_tests=['Sesion con heartbeat y sin clicks', 'Replay guiado'],
                        tradeoffs=['Mas checkpoints incrementan I/O.'],
                        priority_score=88,
                    )
                )
            elif incident.incident_kind == 'bridge_lag':
                proposals.append(
                    ImprovementProposal(
                        title='Reducir atraso del bridge',
                        rationale=incident.summary,
                        recommended_change='Ajustar sondeo, tamano de cola y ritmo de drenado sin volver a bloquear la pagina.',
                        suggested_tests=['Captura con escritura rapida', 'Varias pestanas'],
                        tradeoffs=['Sondear mas seguido aumenta trabajo local.'],
                        priority_score=82,
                    )
                )
            elif incident.incident_kind == 'replay_incomplete':
                proposals.append(
                    ImprovementProposal(
                        title='Garantizar replay suficiente',
                        rationale=incident.summary,
                        recommended_change='Asegurar checkpoints visibles o artefactos minimos antes de cerrar la sesion.',
                        suggested_tests=['Detener y recopilar', 'Abrir replay desde historial'],
                        tradeoffs=['Mas persistencia de checkpoints.'],
                        priority_score=86,
                    )
                )
        return proposals

    def _incident_summary(self, hidden_incidents: list[HiddenIncident], user_clues: list[UserClue]) -> str:
        if not hidden_incidents and not user_clues:
            return ''
        fragments: list[str] = []
        if hidden_incidents:
            lead = hidden_incidents[0]
            fragments.append(f"Incidente dominante: {lead.incident_kind} ({lead.severity.value}).")
        if user_clues:
            fragments.append(f"Pistas del usuario enlazadas: {len(user_clues)}.")
        return ' '.join(fragments)

    def _session_health_from_metrics(self, *, metrics: dict[str, Any], hidden_incidents: list[HiddenIncident], episode_id: str | None = None, run_id: str | None = None) -> SessionHealthSnapshot | None:
        if not metrics and not hidden_incidents:
            return None
        flags = [incident.incident_kind for incident in hidden_incidents]
        label = 'Sin incidencias'
        detail = 'Sin alertas invisibles dominantes.'
        if hidden_incidents:
            label = hidden_incidents[0].incident_kind.replace('_', ' ')
            detail = hidden_incidents[0].summary
        return SessionHealthSnapshot(
            episode_id=episode_id,
            run_id=run_id,
            site_id=str(metrics.get('site_id', 'generic_web') or 'generic_web'),
            health_label=label,
            health_flags=flags,
            status=str(metrics.get('status', 'idle') or 'idle'),
            visible_step_count=int(metrics.get('visible_step_count', 0) or 0),
            screenshot_count=int(metrics.get('screenshot_count', 0) or 0),
            api_seen_count=int(metrics.get('api_seen_count', 0) or 0),
            api_saved_count=int(metrics.get('api_saved_count', 0) or 0),
            api_dropped_count=int(metrics.get('api_dropped_count', 0) or 0),
            page_count=int(metrics.get('page_count', 0) or 0),
            observed_page_count=int(metrics.get('observed_page_count', 0) or 0),
            queue_depth=int(metrics.get('queue_depth', 0) or 0),
            frames_detected=int(metrics.get('frames_detected', 0) or 0),
            heartbeat_count=int(metrics.get('heartbeat_count', 0) or 0),
            last_active_url=str(metrics.get('last_active_url', '') or ''),
            recent_urls=list(metrics.get('recent_urls', []))[:3],
            detail=detail,
            metrics={k: v for k, v in metrics.items() if k in {'seconds_since_last_visible_progress', 'active_navigation_stall_seconds', 'poll_without_progress_count', 'replay_quality'}},
        )

    def _issues_for_run(self, run_record: RunRecord, self_checks: list[Any]) -> list[IssueCandidate]:
        issues: list[IssueCandidate] = []
        if run_record.status == RunStatus.FAILED:
            route = run_record.route
            provider_name = ''
            if hasattr(route, 'provider_name'):
                provider_name = str(route.provider_name or '').strip().lower()
            elif hasattr(route, 'primary_provider'):
                provider_name = str(route.primary_provider or '').strip().lower()
            error_category = str(run_record.error_summary or run_record.result.error_summary or '').strip().lower()[:60]
            hint_parts = ['failure']
            if provider_name:
                hint_parts.append(provider_name)
            if 'timeout' in error_category:
                hint_parts.append('timeout')
            elif 'connection' in error_category or 'network' in error_category:
                hint_parts.append('network')
            elif 'auth' in error_category or 'permission' in error_category or '403' in error_category or '401' in error_category:
                hint_parts.append('auth')
            elif 'rate' in error_category or 'limit' in error_category or 'quota' in error_category:
                hint_parts.append('rate_limit')
            specific_hint = '_'.join(hint_parts)
            issues.append(
                IssueCandidate(
                    title='Ejecucion fallida',
                    summary=run_record.error_summary or run_record.result.error_summary or 'La corrida termino con error.',
                    probable_cause='Fallo en provider, routing o herramienta local.',
                    severity=IssueSeverity.HIGH,
                    issue_hint=specific_hint,
                )
            )
        elif run_record.status == RunStatus.PARTIAL or run_record.result.used_fallback:
            issues.append(
                IssueCandidate(
                    title='Ejecucion parcial o degradada',
                    summary='La corrida respondio, pero uso fallback o redujo confianza.',
                    probable_cause='Stack local parcial o prompt ambiguo.',
                    severity=IssueSeverity.MEDIUM,
                    issue_hint='partial_execution',
                )
            )
        if not run_record.result.summary.strip():
            issues.append(
                IssueCandidate(
                    title='Respuesta final vacia',
                    summary='El modelo no devolvio una respuesta visible util.',
                    probable_cause='Prompt interno o provider sin salida final.',
                    severity=IssueSeverity.HIGH,
                    issue_hint='empty_response',
                )
            )
        failing_checks = [check for check in self_checks if check.status != RunStatus.SUCCESS]
        if failing_checks and not issues:
            issues.append(
                IssueCandidate(
                    title='Autochequeos con advertencias',
                    summary='La corrida completo, pero dejo alertas de consistencia o evidencia.',
                    probable_cause='Ejecucion con trazabilidad incompleta.',
                    severity=IssueSeverity.LOW,
                    issue_hint='light_checks_warning',
                )
            )
        return issues

    def _issues_for_teaching(self, status: RunStatus, metrics: dict[str, Any], self_checks: list[Any]) -> list[IssueCandidate]:
        issues: list[IssueCandidate] = []
        if status == RunStatus.PARTIAL or metrics.get('status') == 'partial_recovery':
            issues.append(
                IssueCandidate(
                    title='Ensenanza con recuperacion parcial',
                    summary='La sesion no cerro limpia, pero dejo replay o artefactos recuperables.',
                    probable_cause='Cierre pesado, ruido API o evidencia visible incompleta.',
                    severity=IssueSeverity.MEDIUM,
                    issue_hint='partial_recovery',
                )
            )
        if int(metrics.get('screenshot_count', 0) or 0) == 0 and int(metrics.get('visible_step_count', 0) or 0) == 0:
            issues.append(
                IssueCandidate(
                    title='Falta captura visible',
                    summary='No hay pasos visibles ni screenshots en el replay.',
                    probable_cause='Bridge inactivo, politica de screenshots o flujo embebido.',
                    severity=IssueSeverity.HIGH,
                    issue_hint='missing_visible_capture',
                )
            )
        if not bool(metrics.get('has_recoverable_replay')):
            issues.append(
                IssueCandidate(
                    title='Replay no recuperable',
                    summary='La sesion no dejo suficiente evidencia para reconstruir el replay.',
                    probable_cause='Cierre abrupto o artefactos insuficientes.',
                    severity=IssueSeverity.HIGH,
                    issue_hint='missing_replay',
                )
            )
        failing_checks = [check for check in self_checks if check.status != RunStatus.SUCCESS]
        for check in failing_checks:
            if check.check_name == 'visible_capture' and not any(issue.issue_hint == 'missing_visible_capture' for issue in issues):
                issues.append(
                    IssueCandidate(
                        title='Captura visible debilitada',
                        summary=check.detail,
                        probable_cause='Politica de screenshots o pasos visibles no entraron.',
                        severity=IssueSeverity.MEDIUM,
                        issue_hint='weak_visible_capture',
                    )
                )
        return issues

    def _proposals_for_issues(self, issues: list[IssueCandidate], improvement_hints: list[str]) -> list[ImprovementProposal]:
        proposals: list[ImprovementProposal] = []
        for issue in issues:
            if issue.issue_hint.startswith('failure'):
                proposals.append(
                    ImprovementProposal(
                        title='Construir prueba reproducible del fallo',
                        rationale=issue.summary,
                        recommended_change='Tomar el run_id del dossier y reproducirlo con autodiagnostico ligero activado.',
                        suggested_tests=['pytest -q -p no:cacheprovider -p no:tmpdir', 'consulta local equivalente desde Centro de Control'],
                        tradeoffs=['Puede requerir depurar el proveedor o el prompt antes de tocar UI.'],
                        priority_score=92,
                    )
                )
            elif issue.issue_hint == 'partial_execution':
                proposals.append(
                    ImprovementProposal(
                        title='Reducir degradaciones del stack local',
                        rationale=issue.summary,
                        recommended_change='Verificar salud de proveedores y ajustar routing o planner para bajar el uso de fallback.',
                        suggested_tests=['Actualizar stack local', 'consulta simple y consulta compleja'],
                        tradeoffs=['Si el fallback es aceptable, bajar demasiada tolerancia puede reducir resiliencia.'],
                        priority_score=76,
                    )
                )
            elif issue.issue_hint == 'empty_response':
                proposals.append(
                    ImprovementProposal(
                        title='Separar mejor diagnostico interno y respuesta final',
                        rationale=issue.summary,
                        recommended_change='Revisar el provider y asegurar que la salida visible siempre termine en respuesta final util.',
                        suggested_tests=['pregunta simple', 'pregunta de proyecto'],
                        tradeoffs=['Puede requerir retocar prompts por rol.'],
                        priority_score=85,
                    )
                )
        for hint in improvement_hints[:3]:
            proposals.append(
                ImprovementProposal(
                    title='Pista de mejora reportada por la ejecucion',
                    rationale=hint,
                    recommended_change=hint,
                    suggested_tests=['Validar el comportamiento despues del cambio vertical'],
                    tradeoffs=[],
                    priority_score=60,
                )
            )
        return proposals or [
            ImprovementProposal(
                title='Mantener evidencia verificable',
                rationale='La corrida fue estable, pero conviene seguir acumulando dossiers para detectar regresiones.',
                recommended_change='Revisar el dossier y marcar si la respuesta debe convertirse en prueba o ensenanza reusable.',
                suggested_tests=['Consultar historial de ejecuciones'],
                tradeoffs=[],
                priority_score=40,
            )
        ]

    def _proposals_for_teaching(self, issues: list[IssueCandidate], metrics: dict[str, Any]) -> list[ImprovementProposal]:
        proposals: list[ImprovementProposal] = []
        for issue in issues:
            if issue.issue_hint == 'missing_visible_capture':
                proposals.append(
                    ImprovementProposal(
                        title='Reforzar captura visible de la ensenanza',
                        rationale=issue.summary,
                        recommended_change='Revisar bridge, screenshots periodicos y si el flujo usa frames o contenido embebido.',
                        suggested_tests=['Nueva ensenanza corta', 'Ver replay guiado'],
                        tradeoffs=['Mas capturas aumentan almacenamiento y tiempo de cierre.'],
                        priority_score=88,
                    )
                )
            elif issue.issue_hint == 'partial_recovery':
                proposals.append(
                    ImprovementProposal(
                        title='Reducir cierre pesado al detener',
                        rationale=issue.summary,
                        recommended_change='Mantener API inteligente y revisar por que la sesion termino en recuperacion parcial.',
                        suggested_tests=['Ensenanza con trafico alto', 'Detener y recopilar'],
                        tradeoffs=['Guardar menos API puede reducir profundidad de auditoria.'],
                        priority_score=80,
                    )
                )
            elif issue.issue_hint == 'missing_replay':
                proposals.append(
                    ImprovementProposal(
                        title='Garantizar replay recuperable',
                        rationale=issue.summary,
                        recommended_change='Asegurar que al menos queden brief, screenshots o artefactos suficientes antes de cerrar.',
                        suggested_tests=['Finalizacion con error forzado', 'Historial de ensenanza'],
                        tradeoffs=['Mas checkpoints incrementan I/O.'],
                        priority_score=84,
                    )
                )
        if not proposals:
            proposals.append(
                ImprovementProposal(
                    title='Convertir demostracion en conocimiento reusable',
                    rationale='La ensenanza dejo suficiente evidencia para revision.',
                    recommended_change='Validar el replay y confirmar si la sesion debe pasar a tarea o conocimiento confirmado.',
                    suggested_tests=['Replay guiado', 'Payload de entrenamiento'],
                    tradeoffs=[],
                    priority_score=52,
                )
            )
        return proposals

    def _severity_from_status(self, status: RunStatus, confidence: float, has_issues: bool) -> IssueSeverity:
        if status == RunStatus.FAILED:
            return IssueSeverity.HIGH
        if status == RunStatus.PARTIAL:
            return IssueSeverity.MEDIUM
        if has_issues or confidence < 0.6:
            return IssueSeverity.LOW
        return IssueSeverity.LOW

    def _teaching_summary_from_metrics(self, metrics: dict[str, Any]) -> str:
        return (
            f"Replay {'recuperable' if metrics.get('has_recoverable_replay') else 'incompleto'} | "
            f"pasos visibles {int(metrics.get('visible_step_count', 0) or 0)} | "
            f"capturas {int(metrics.get('screenshot_count', 0) or 0)} | "
            f"API guardada {int(metrics.get('api_saved_count', 0) or 0)}"
        )

    def _build_codex_brief(
        self,
        summary: str,
        issues: list[IssueCandidate],
        proposals: list[ImprovementProposal],
        hidden_incidents: list[HiddenIncident] | None = None,
        user_clues: list[UserClue] | None = None,
    ) -> str:
        issue = issues[0] if issues else None
        hidden_incidents = hidden_incidents or []
        user_clues = user_clues or []
        proposal = proposals[0] if proposals else None
        incident_line = ''
        if hidden_incidents:
            incident_line = '\nIncidente invisible: ' + hidden_incidents[0].incident_kind + ' -> ' + hidden_incidents[0].summary
        clue_line = ''
        if user_clues:
            clue_line = '\nPista del usuario: ' + user_clues[0].text
        return (
            'Diagnostico breve: ' + summary + '\n'
            + 'Causa raiz probable: ' + (issue.probable_cause if issue else 'Sin causa raiz dominante.') + '\n'
            + 'Cambio vertical recomendado: ' + (proposal.recommended_change if proposal else 'Revisar el dossier y confirmar una hipotesis.') + '\n'
            + 'Pruebas sugeridas: ' + (', '.join(proposal.suggested_tests) if proposal else 'sin pruebas sugeridas') + '\n'
            + 'Riesgos o tradeoffs: ' + (', '.join(proposal.tradeoffs) if proposal and proposal.tradeoffs else 'sin tradeoffs fuertes')
            + incident_line
            + clue_line
        )

