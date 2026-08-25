from __future__ import annotations

from collections import Counter
import threading
import time

import logging

from iabv_v15.domain.models import (
    CodexPendingIssue,
    DiagnosticCategory,
    ImprovementProposal,
    RunStatus,
    EvolutionSnapshot,
    SelfExaminationFinding,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService


class EvolutionReviewService:
    _CACHE_MAX_AGE_SECONDS = 45.0

    def __init__(
        self,
        *,
        dossier_repository: ExecutionDossierRepository,
        hidden_incident_repository: HiddenIncidentRepository,
        analytics_service: AnalyticsStrategyService,
        teaching_gap_analyzer: TeachingGapAnalyzer,
        pbt_service: PBTControlService,
        adaptive_session_repository: AdaptiveSessionRepository | None = None,
        pending_issue_repository: PendingIssueRepository | None = None,
        scenario_run_repository: ScenarioRunRepository | None = None,
    ) -> None:
        self.dossier_repository = dossier_repository
        self.hidden_incident_repository = hidden_incident_repository
        self.analytics_service = analytics_service
        self.teaching_gap_analyzer = teaching_gap_analyzer
        self.pbt_service = pbt_service
        self.adaptive_session_repository = adaptive_session_repository
        self.pending_issue_repository = pending_issue_repository
        self.scenario_run_repository = scenario_run_repository
        self._cache_lock = threading.RLock()
        self._project_health_cache: EvolutionSnapshot | None = None
        self._project_health_cache_at = 0.0
        self._improvement_backlog_cache: list[ImprovementProposal] = []
        self._improvement_backlog_cache_at = 0.0

    def build_project_health(
        self,
        *,
        refresh: bool = False,
        max_age_seconds: float = _CACHE_MAX_AGE_SECONDS,
    ) -> EvolutionSnapshot:
        if not refresh:
            with self._cache_lock:
                if (
                    self._project_health_cache is not None
                    and (time.monotonic() - self._project_health_cache_at) <= max(float(max_age_seconds), 0.0)
                ):
                    return self._project_health_cache.model_copy(deep=True)
        recent = self.dossier_repository.list_recent(limit=40)
        incidents = self.hidden_incident_repository.list_recent(limit=40)
        adaptive_sessions = self.adaptive_session_repository.list_recent(limit=40) if self.adaptive_session_repository is not None else []
        scenario_runs = self.scenario_run_repository.list_recent(limit=40) if self.scenario_run_repository is not None else []
        pending_issues = self.pending_issue_repository.list_recent(limit=40) if self.pending_issue_repository is not None else []
        failures = [d for d in recent if d.status == RunStatus.FAILED]
        partials = [d for d in recent if d.status == RunStatus.PARTIAL]
        repeated = Counter(d.issue_hint_text for d in recent if d.issue_hint_text)
        repeated.update(item.incident_kind for item in incidents if item.incident_kind)
        repeated.update(session.chosen_pack_id for session in adaptive_sessions if session.status.value in {'need_info', 'waiting_approval', 'ready_to_execute'})
        repeated.update(run.scenario.scenario_id for run in scenario_runs if getattr(run.diagnosis, 'category', None) is not None)
        repeated.update(issue.category.value for issue in pending_issues)
        analytics = self.analytics_service.build_report()
        backlog = self.build_improvement_backlog(limit=8, refresh=refresh, max_age_seconds=max_age_seconds)
        snapshot = EvolutionSnapshot(
            summary=(
                f'Dossiers recientes: {len(recent)} | fallos: {len(failures)} | parciales: {len(partials)} | '
                f'incidentes invisibles: {len(incidents)} | sesiones adaptativas: {len(adaptive_sessions)} | '                f'autotests: {len(scenario_runs)} | pendientes Codex: {len(pending_issues)}. '
                f"Prioridad sugerida: {analytics.get('priority_focus', 'seguir reforzando evidencia y conocimiento local.')}"
            ),
            status_cards=[
                {'title': 'Dossiers', 'value': len(recent), 'detail': 'Ejecuciones con evidencia indexada.'},
                {'title': 'Fallos', 'value': len(failures), 'detail': 'Corridas fallidas con paquete verificable.'},
                {'title': 'Parciales', 'value': len(partials), 'detail': 'Ejecuciones recuperadas o degradadas.'},
                {'title': 'Incidentes', 'value': len(incidents), 'detail': 'Alertas invisibles detectadas por captura y navegador.'},
                {'title': 'Adaptativo', 'value': len(adaptive_sessions), 'detail': 'Sesiones por fases con packs, approvals y evidencia.'},
                {'title': 'Autotest', 'value': len(scenario_runs), 'detail': 'Pruebas internas estructuradas del Self-Teacher.'},
                {'title': 'Pendientes Codex', 'value': len(pending_issues), 'detail': 'Casos que ya no bastan con tuning runtime.'},
                {'title': 'PBT', 'value': self.pbt_service.load_state().get('generation', 0), 'detail': self.pbt_service.load_state().get('summary', 'Sin PBT aun.')},
            ],
            recent_failures=[
                {
                    'dossier_id': dossier.dossier_id,
                    'title': dossier.title,
                    'summary': dossier.summary,
                    'severity': dossier.severity.value,
                    'run_id': dossier.run_id or '',
                    'episode_id': dossier.episode_id or '',
                }
                for dossier in failures[:8]
            ],
            repeated_issues=[
                {'issue_hint': hint, 'count': count}
                for hint, count in repeated.most_common(10)
                if hint
            ],
            backlog=backlog,
            latest_packet_preview=(recent[0].codex_brief if recent else ''),
        )
        with self._cache_lock:
            self._project_health_cache = snapshot.model_copy(deep=True)
            self._project_health_cache_at = time.monotonic()
        return snapshot

    def build_improvement_backlog(
        self,
        limit: int = 8,
        *,
        refresh: bool = False,
        max_age_seconds: float = _CACHE_MAX_AGE_SECONDS,
    ) -> list[ImprovementProposal]:
        capped_limit = max(int(limit), 0)
        if not refresh:
            with self._cache_lock:
                if (
                    self._improvement_backlog_cache
                    and (time.monotonic() - self._improvement_backlog_cache_at) <= max(float(max_age_seconds), 0.0)
                ):
                    return [item.model_copy(deep=True) for item in self._improvement_backlog_cache[:capped_limit]]
        recent = self.dossier_repository.list_recent(limit=60)
        incidents = self.hidden_incident_repository.list_recent(limit=80)
        adaptive_sessions = self.adaptive_session_repository.list_recent(limit=40) if self.adaptive_session_repository is not None else []
        pending_issues = self.pending_issue_repository.list_recent(limit=20) if self.pending_issue_repository is not None else []
        scored: dict[str, ImprovementProposal] = {}
        for dossier in recent:
            for proposal in dossier.improvement_proposals:
                existing = scored.get(proposal.recommended_change)
                boost = 20 if dossier.status == RunStatus.FAILED else 10 if dossier.status == RunStatus.PARTIAL else 0
                proposal_copy = proposal.model_copy(update={'priority_score': proposal.priority_score + boost})
                if existing is None or proposal_copy.priority_score > existing.priority_score:
                    scored[proposal.recommended_change] = proposal_copy
        repeated_incidents = Counter(f"{item.site_id}:{item.incident_kind}" for item in incidents)
        for key, count in repeated_incidents.items():
            site_id, incident_kind = key.split(':', 1)
            lead = next(item for item in incidents if item.site_id == site_id and item.incident_kind == incident_kind)
            priority = 96 if incident_kind in {'navigation_stall', 'capture_starvation'} else 92 if incident_kind in {'replay_incomplete', 'critical_object_missing'} else 86 if incident_kind in {'visual_alignment_weak', 'annotation_conflict'} else 78 if incident_kind == 'manual_correction_hotspot' else 72
            proposal = ImprovementProposal(
                title=f"Incidente repetido: {incident_kind}",
                rationale=lead.summary,
                recommended_change=self._recommended_change_for_incident(incident_kind),
                suggested_tests=self._tests_for_incident(incident_kind),
                tradeoffs=['Incrementar observabilidad puede aumentar almacenamiento o ruido de diagnostico.'],
                priority_score=priority + min(count * 4, 20),
            )
            existing = scored.get(proposal.recommended_change)
            if existing is None or proposal.priority_score > existing.priority_score:
                scored[proposal.recommended_change] = proposal
        if adaptive_sessions:
            pack_counts = Counter(session.chosen_pack_id for session in adaptive_sessions if session.status.value in {'need_info', 'waiting_approval'})
            for pack_id, count in pack_counts.most_common(5):
                proposal = ImprovementProposal(
                    title=f'Pack adaptativo requiere ajuste: {pack_id}',
                    rationale='Hay sesiones por fases que siguen quedando en need_info o waiting_approval sin cerrar bien la tarea.',
                    recommended_change=f'Revisar prompts, criterios de readiness y defaults del pack {pack_id}.',
                    suggested_tests=['Consulta simple', 'Consulta multi-etapa', 'Aprobaciones y simulacion'],
                    tradeoffs=['Mas heuristica reduce flexibilidad si se exagera.'],
                    priority_score=70 + min(count * 5, 20),
                )
                existing = scored.get(proposal.recommended_change)
                if existing is None or proposal.priority_score > existing.priority_score:
                    scored[proposal.recommended_change] = proposal
        for issue in pending_issues[:8]:
            proposal = ImprovementProposal(
                title=f'Pendiente Codex: {issue.scenario_id}',
                rationale=issue.summary,
                recommended_change=issue.recommended_change or 'Revisar el caso pendiente para Codex.',
                suggested_tests=list(issue.suggested_tests or ['prueba reproducible']),
                tradeoffs=['Escalar a codigo lleva mas tiempo que tuning runtime, pero evita seguir iterando a ciegas.'],
                priority_score=98,
            )
            existing = scored.get(proposal.recommended_change)
            if existing is None or proposal.priority_score > existing.priority_score:
                scored[proposal.recommended_change] = proposal
        backlog = sorted(scored.values(), key=lambda item: item.priority_score, reverse=True)
        if backlog:
            cached_backlog = [item.model_copy(deep=True) for item in backlog]
        else:
            cached_backlog = [
                ImprovementProposal(
                    title='Seguir capturando evidencia evolutiva',
                    rationale='Todavia no hay suficientes dossiers o incidentes para priorizar backlog fino.',
                    recommended_change='Ejecutar consultas, ensenanzas y autodiagnosticos para poblar la capa evolutiva.',
                    suggested_tests=['Centro Evolutivo', 'Historial de Ejecuciones'],
                    tradeoffs=[],
                    priority_score=35,
                )
            ]
        with self._cache_lock:
            self._improvement_backlog_cache = [item.model_copy(deep=True) for item in cached_backlog]
            self._improvement_backlog_cache_at = time.monotonic()
        return [item.model_copy(deep=True) for item in cached_backlog[:capped_limit]]

    def _recommended_change_for_incident(self, incident_kind: str) -> str:
        mapping = {
            'navigation_stall': 'Priorizar diagnostico de navegacion multitab y progreso visible por pestana.',
            'capture_starvation': 'Reforzar checkpoints visibles y deteccion de bridge sin evidencia.',
            'bridge_lag': 'Ajustar backlog y cadencia de drenado del bridge.',
            'tab_attach_gap': 'Verificar adopcion de paginas nuevas y observacion de pestanas.',
            'finalize_slow': 'Reducir trabajo pesado al detener y recopilar.',
            'replay_incomplete': 'Garantizar replay minimo recuperable antes de cerrar.',
            'session_restore_weak': 'Revisar storage state y persistencia de sesion por sitio.',
            'visual_alignment_weak': 'Mejorar overlays, rectangulos y coherencia visual del replay para pasos criticos.',
            'critical_object_missing': 'Detectar o corregir manualmente objetos criticos como correo, contrasena y submit.',
            'manual_correction_hotspot': 'Convertir correcciones humanas repetidas en reglas, heuristicas o anotaciones preferidas.',
            'annotation_conflict': 'Resolver conflictos entre evidencia capturada e interpretacion manual del replay.',
        }
        return mapping.get(incident_kind, 'Revisar el incidente, convertirlo en prueba y ajustar la ruta afectada.')

    def _tests_for_incident(self, incident_kind: str) -> list[str]:
        mapping = {
            'navigation_stall': ['Ensenanza con 3-4 pestanas', 'Busqueda en pestana nueva'],
            'capture_starvation': ['Sesion con heartbeat sin clicks', 'Replay guiado'],
            'bridge_lag': ['Escritura rapida durante captura', 'Varias pestanas'],
            'tab_attach_gap': ['Abrir pestanas nuevas y validar conteo observado'],
            'finalize_slow': ['Detener y recopilar con trafico alto'],
            'replay_incomplete': ['Abrir replay desde historial', 'Detener sesion con evidencia minima'],
            'session_restore_weak': ['Reabrir sitio autenticado con storage state'],
            'visual_alignment_weak': ['Abrir replay visual', 'Validar overlays verdes/naranjas/rojos'],
            'critical_object_missing': ['Revisar login en galeria', 'Corregir correo, contrasena o submit manualmente'],
            'manual_correction_hotspot': ['Corregir el mismo objeto en varias sesiones', 'Verificar si el learning bundle sube de calidad'],
            'annotation_conflict': ['Crear anotacion manual sobre un objeto ya detectado', 'Verificar precedencia y coherencia del replay'],
        }
        return mapping.get(incident_kind, ['Validar el caso reproducible'])

    # ------------------------------------------------------------------
    # Task-packet → pending issues: close the auto-improvement loop.
    # ------------------------------------------------------------------

    _TASK_PACKET_CATEGORIES: dict[str, str] = {
        'task_packet_high_unresolved': 'task_packet:high_unresolved',
        'task_packet_recurring_approval': 'task_packet:recurring_approval',
        'task_packet_no_worker': 'task_packet:no_worker',
        'task_packet_gate_unusable': 'task_packet:gate_unusable',
    }

    _TASK_PACKET_RECOMMENDED: dict[str, str] = {
        'task_packet:high_unresolved': (
            'Investigar por que evidence_basis permanece unresolved. '
            'Verificar world model, environment_id y learning persistido.'
        ),
        'task_packet:recurring_approval': (
            'Revisar governance policies: approval_required se activa con '
            'demasiada frecuencia. Considerar ajustar umbrales para rutas '
            'locales ya validadas.'
        ),
        'task_packet:no_worker': (
            'Verificar que hay workers configurados y disponibles. '
            'Si todas las rutas son locales, este issue puede resolverse '
            'marcandolo como esperado.'
        ),
        'task_packet:gate_unusable': (
            'Revisar worker_health_gate y estado de cuentas externas. '
            'ranked_worker_count == 0 de forma recurrente indica que '
            'ninguna cuenta tiene cuota o esta habilitada.'
        ),
    }

    _TASK_PACKET_TESTS: dict[str, list[str]] = {
        'task_packet:high_unresolved': [
            'Ejecutar una sesion con world model activo y verificar que evidence_basis cambia a observed',
            'Revisar Centro Evolutivo',
        ],
        'task_packet:recurring_approval': [
            'Lanzar tarea de bajo riesgo por ruta local y verificar que no pide aprobacion',
            'Revisar governance thresholds',
        ],
        'task_packet:no_worker': [
            'Verificar que al menos una cuenta externa tiene cuota disponible',
            'Revisar Centro Evolutivo > Workers',
        ],
        'task_packet:gate_unusable': [
            'Verificar estado de cuentas en account_resource_scanner',
            'Revisar rotacion de tokens',
        ],
    }

    def materialize_task_packet_issues(
        self,
        findings: list[SelfExaminationFinding],
    ) -> list[CodexPendingIssue]:
        """Convert qualifying task_packet OSES findings into pending issues.

        Uses stable ``scenario_id`` keys per pattern to avoid duplicates.
        Only creates a new issue if no open issue with the same scenario_id
        exists.  Returns the list of newly created issues (may be empty).
        """
        log = logging.getLogger(__name__)
        repo = self.pending_issue_repository
        if repo is None or not hasattr(repo, 'save'):
            return []

        created: list[CodexPendingIssue] = []
        for finding in findings:
            scenario_id = self._TASK_PACKET_CATEGORIES.get(finding.category)
            if scenario_id is None:
                continue

            if hasattr(repo, 'find_by_scenario_id'):
                existing = repo.find_by_scenario_id(scenario_id)
                if existing:
                    log.debug(
                        'task_packet_issue: skip %s — already exists (%s)',
                        scenario_id, existing[0].issue_id,
                    )
                    continue

            issue = CodexPendingIssue(
                scenario_id=scenario_id,
                goal=f'Auto-mejora: resolver patron repetido {scenario_id}',
                category=DiagnosticCategory.NEED_CODEX_FIX,
                summary=finding.summary,
                probable_cause=finding.title,
                recommended_change=self._TASK_PACKET_RECOMMENDED.get(
                    scenario_id, finding.recommendation or '',
                ),
                suggested_tests=self._TASK_PACKET_TESTS.get(
                    scenario_id, ['Revisar Centro Evolutivo'],
                ),
                evidence_refs=list(finding.source_refs or []),
                metadata={
                    'source': 'oses_task_packet_pattern',
                    'finding_category': finding.category,
                    'pattern_metadata': dict(finding.metadata or {}),
                    'confidence': finding.confidence,
                },
            )
            saved = repo.save(issue)
            created.append(saved)
            log.info(
                'task_packet_issue: created %s for %s',
                saved.issue_id, scenario_id,
            )

        return created
