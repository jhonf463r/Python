from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import threading
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    AutonomousValidationSnapshot,
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ProposalValidationResult,
    SandboxExperiment,
    SandboxExperimentVerdict,
    ToolEvolutionDecisionLog,
    ToolEvolutionProposal,
    ToolEvolutionStatus,
    WorldModelSnapshot,
)  # noqa: F401  (ProposalValidationResult used as type hint in _maybe_publish_promotion)
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.self_teach.sandbox_experiment_service import SandboxExperimentService


class AutonomousValidationCycleService:
    def __init__(
        self,
        *,
        experiment_lab: ExperimentLab,
        experiment_lab_repository: ExperimentLabRepository,
        sandbox_experiment_service: SandboxExperimentService,
        world_model_service: Any | None = None,
        environment_self_awareness_service: Any | None = None,
        tool_evolution_monitor: Any | None = None,
        storage: ArtifactStorage | None = None,
        auto_start: bool | None = None,
        interval_seconds: float = 180.0,
        promotion_pr_publisher: Any | None = None,
        tool_registry: Any | None = None,
        autonomy_governance_policy: Any | None = None,
        research_backlog_root: str | Path | None = None,
        git_sync_service: Any | None = None,
    ) -> None:
        self.experiment_lab = experiment_lab
        self.experiment_lab_repository = experiment_lab_repository
        self.sandbox_experiment_service = sandbox_experiment_service
        self.world_model_service = world_model_service
        self.environment_self_awareness_service = environment_self_awareness_service
        self.tool_evolution_monitor = tool_evolution_monitor
        self.storage = storage
        self.git_sync_service = git_sync_service
        # F2.3 (thin): cuando se promueve un candidato, este publisher abre un
        # PR documental en una rama ``iabv-auto/*``. El ciclo no decide nada
        # distinto por tenerlo; solo delega la traza en git. Cualquier fallo
        # del publisher se captura y no rompe el ciclo de validacion.
        self.promotion_pr_publisher = promotion_pr_publisher
        # Auto-research wiring (PR J): el ciclo lee backlog abierto y lanza
        # sandbox experiments sobre ``research_backlog_root`` / teaching gaps
        # del repositorio. ``tool_registry`` y ``autonomy_governance_policy``
        # son opcionales: si faltan, el filtro correspondiente no bloquea.
        self.tool_registry = tool_registry
        self.autonomy_governance_policy = autonomy_governance_policy
        self.research_backlog_root = Path(research_backlog_root) if research_backlog_root else None
        self.interval_seconds = max(float(interval_seconds), 60.0)
        self._auto_start = (not self._in_test_mode()) if auto_start is None else bool(auto_start)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._decision_log = self._load_decision_log() or ToolEvolutionDecisionLog()
        self._current_snapshot = AutonomousValidationSnapshot(
            status='bootstrapping',
            summary='Ciclo de validacion autonoma iniciando; a la espera del primer tick.',
        )
        if self._auto_start:
            self.start()

    def set_promotion_pr_publisher(self, publisher: Any | None) -> None:
        """Wire (o des-wire) el publisher de PRs documentales de promocion.

        Expuesto como metodo para permitir que ``bootstrap`` arme el
        publisher despues de crear el ciclo (el publisher depende de
        ``GitHubRemoteService`` que se construye mas tarde en el wiring).
        """

        self.promotion_pr_publisher = publisher

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._wake_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name='iabv-autonomous-validation', daemon=True)
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 1.0) -> None:
        self._stop_event.set()
        self._wake_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(timeout_seconds, 0.1))

    def current_snapshot(self) -> AutonomousValidationSnapshot:
        with self._lock:
            return self._current_snapshot.model_copy(deep=True)

    def current_decision_log(self, *, refresh: bool = False) -> ToolEvolutionDecisionLog:
        with self._lock:
            if refresh:
                self._decision_log = self._load_decision_log() or self._decision_log or ToolEvolutionDecisionLog()
            if self._decision_log is None:
                self._decision_log = ToolEvolutionDecisionLog()
            return self._decision_log.model_copy(deep=True)

    def decision_log_summary(self, log: ToolEvolutionDecisionLog | None = None) -> dict[str, Any]:
        resolved = log or self.current_decision_log()
        latest = resolved.entries[-1] if resolved.entries else None
        winning_by_problem: dict[str, str] = {}
        in_validation: list[str] = []
        discarded_proposals: list[dict[str, Any]] = []
        recent_decisions: list[dict[str, Any]] = []
        for entry in resolved.entries:
            if entry.decision == 'promoted':
                winning_by_problem[entry.subject_key] = entry.candidate_assistant_kind or entry.candidate_route.value
            elif entry.decision == 'discarded':
                winning_by_problem[entry.subject_key] = entry.current_assistant_kind or entry.current_route.value
                discarded_proposals.append(
                    {
                        'subject_key': entry.subject_key,
                        'proposal_key': entry.proposal_key,
                        'assistant_kind': entry.candidate_assistant_kind,
                        'route': entry.candidate_route.value,
                        'reason': entry.reason,
                        'status': entry.decision,
                    }
                )
            elif entry.decision == 'deferred' and entry.proposal_key:
                in_validation.append(entry.proposal_key)
            recent_decisions.append(
                {
                    'subject_key': entry.subject_key,
                    'proposal_key': entry.proposal_key,
                    'decision': entry.decision,
                    'winner': entry.winner,
                    'assistant_kind': entry.candidate_assistant_kind,
                    'route': entry.candidate_route.value,
                    'reason': entry.reason,
                }
            )
        return {
            'winning_by_problem': winning_by_problem,
            'degraded_tools': [tool for tool, state in resolved.summary_by_tool.items() if state == 'degradado'],
            'in_validation': list(dict.fromkeys(in_validation))[:8],
            'discarded_proposals': discarded_proposals[-6:],
            'recent_decisions': recent_decisions[-6:],
            'last_decision': (
                {
                    'subject_key': latest.subject_key,
                    'proposal_key': latest.proposal_key,
                    'decision': latest.decision,
                    'winner': latest.winner,
                    'reason': latest.reason,
                }
                if latest is not None
                else {}
            ),
            'summary_by_tool': dict(resolved.summary_by_tool or {}),
            'summary_by_problem': dict(resolved.summary_by_problem or {}),
            'unresolved_fields': list(resolved.unresolved_fields or []),
            'package_path': resolved.package_path,
            'markdown_path': resolved.markdown_path,
            'pending_auto_probes': self._load_pending_auto_probes(),
        }

    def get_status(self) -> dict[str, Any]:
        return self.decision_log_summary()

    def request_run(self, *, reason: str = 'manual') -> None:
        with self._lock:
            self._current_snapshot = self._current_snapshot.model_copy(
                update={'metadata': {**dict(self._current_snapshot.metadata or {}), 'requested_reason': reason}}
            )
        self._wake_event.set()

    # Ventana de decisiones recientes consideradas para detectar inercia
    # de ruta. Un valor bajo reacciona rapido a loops; uno alto ignora
    # senales debiles. 5 es suficiente para captar una rafaga de
    # validaciones repetidas sin invalidar historial legitimo.
    _SCOPE_INERTIA_WINDOW = 5
    # Minimo de decisiones en la ventana que deben coincidir en
    # (subject_key, candidate_assistant_kind) para disparar cooldown.
    # 3 de 5 deja margen a una variacion puntual pero corta un patron
    # sostenido.
    _SCOPE_INERTIA_THRESHOLD = 3

    def _scope_inertia_cooldown_reason(
        self,
        *,
        proposal: ToolEvolutionProposal,
    ) -> str:
        """H2: cortar loops de validacion cuando el mismo scope ya
        consumio ciclos con el mismo ganador.

        Sin este freno, cuando el orquestador no tiene input nuevo del
        usuario el ciclo sigue procesando challengers contra un scope
        cuyo ganador ya esta consolidado, acumulando decisiones casi
        identicas en el decision_log mientras StrategySelector
        recomienda siempre lo mismo. Eso es exploitation pura, no
        exploracion.

        Este helper mira las ultimas ``_SCOPE_INERTIA_WINDOW`` decisiones
        del log en memoria y, si ``_SCOPE_INERTIA_THRESHOLD`` o mas
        comparten ``subject_key`` y ``current_assistant_kind`` (el
        ganador vigente), devuelve una razon de cooldown. Ese cooldown
        se aplica SOLO al nuevo candidato; no pausa el ciclo global ni
        bloquea otros scopes. Tampoco decide ruta: solo aplaza esa
        evaluacion puntual y deja la evidencia visible.
        """
        subject_key = str(proposal.subject_key or '').strip()
        if not subject_key:
            return ''
        log = self._decision_log or ToolEvolutionDecisionLog()
        entries = list(log.entries or [])[-self._SCOPE_INERTIA_WINDOW:]
        if len(entries) < self._SCOPE_INERTIA_THRESHOLD:
            return ''
        matching_winners: dict[str, int] = {}
        for entry in entries:
            if str(entry.subject_key or '').strip() != subject_key:
                continue
            if entry.decision != 'promoted':
                continue
            winner_kind = str(entry.current_assistant_kind or '').strip()
            if not winner_kind:
                continue
            matching_winners[winner_kind] = matching_winners.get(winner_kind, 0) + 1
        for winner_kind, count in matching_winners.items():
            if count >= self._SCOPE_INERTIA_THRESHOLD:
                return (
                    f'scope_inertia_cooldown: {count} de las ultimas '
                    f'{len(entries)} decisiones para {subject_key} '
                    f'promovieron {winner_kind}; forzando cooldown de '
                    f'exploracion hasta nueva evidencia.'
                )
        return ''

    def run_once(self, *, reason: str = 'manual') -> AutonomousValidationSnapshot:
        monitor_status = self._current_tool_evolution_status()
        proposal_candidate = self._next_tool_evolution_candidate(monitor_status=monitor_status)
        environment_model = self._current_environment_model()
        world_model = self._current_world_model()
        paused_reason = self._pause_reason(environment_model=environment_model, world_model=world_model)
        if not paused_reason and proposal_candidate is not None:
            inertia_reason = self._scope_inertia_cooldown_reason(proposal=proposal_candidate[0])
            if inertia_reason:
                paused_reason = inertia_reason
        if paused_reason:
            if proposal_candidate is not None:
                proposal, priority_score = proposal_candidate
                result = self._record_proposal_validation_result(
                    proposal=proposal,
                    decision='deferred',
                    winner='tie',
                    reason=f'La validacion de la propuesta se aplazo porque {paused_reason}',
                    sandbox_experiment=None,
                    metrics={'priority_score': round(priority_score, 4)},
                    metadata={'decision_source': 'tool_evolution_monitor', 'paused_reason': paused_reason},
                )
                return self._store_snapshot(
                    AutonomousValidationSnapshot(
                        cycle_id=self._current_snapshot.cycle_id,
                        last_checked_at_utc=datetime.now(timezone.utc),
                        status='deferred',
                        summary=result.reason,
                        paused_reason=paused_reason,
                        pending_candidates=max(self._pending_candidate_count(monitor_status=monitor_status) - 1, 0),
                        promoted_count=self._promoted_count(),
                        last_experiment_id='',
                        unresolved_fields=[],
                        metadata={
                            'reason': reason,
                            'decision_source': 'tool_evolution_monitor',
                            'proposal_key': proposal.proposal_key,
                            'proposal_kind': proposal.proposal_kind,
                            'decision': result.decision,
                            'priority_score': round(priority_score, 4),
                        },
                    )
                )
            return self._store_snapshot(
                AutonomousValidationSnapshot(
                    cycle_id=self._current_snapshot.cycle_id,
                    last_checked_at_utc=datetime.now(timezone.utc),
                    status='paused',
                    summary='La validacion autonoma se pauso porque el entorno no esta en condiciones seguras para validar.',
                    paused_reason=paused_reason,
                    pending_candidates=self._pending_candidate_count(monitor_status=monitor_status),
                    promoted_count=self._promoted_count(),
                    last_experiment_id=str(self._current_snapshot.last_experiment_id or ''),
                    metadata={
                        'reason': reason,
                        'environment_scan_status': str(getattr(environment_model, 'scan_status', '') or ''),
                        'world_model_confidence': float(getattr(world_model, 'confidence', 0.0) or 0.0),
                    },
                )
            )
        if proposal_candidate is not None:
            proposal, priority_score = proposal_candidate
            recommendation = self._recommendation_from_proposal(proposal)
            try:
                experiment = self.sandbox_experiment_service.validate_recommendation(
                    recommendation,
                    world_model=world_model,
                    environment_model=environment_model,
                    reason=f'{reason}:{proposal.proposal_kind}',
                )
            except Exception as exc:
                result = self._record_proposal_validation_result(
                    proposal=proposal,
                    decision='unresolved',
                    winner='unresolved',
                    reason='La validacion de la propuesta fallo antes de completar el sandbox.',
                    sandbox_experiment=None,
                    metrics={'priority_score': round(priority_score, 4)},
                    metadata={'decision_source': 'tool_evolution_monitor', 'error': repr(exc)},
                )
                return self._store_snapshot(
                    AutonomousValidationSnapshot(
                        cycle_id=self._current_snapshot.cycle_id,
                        last_checked_at_utc=datetime.now(timezone.utc),
                        status='unresolved',
                        summary=result.reason,
                        pending_candidates=max(self._pending_candidate_count(monitor_status=monitor_status) - 1, 0),
                        promoted_count=self._promoted_count(),
                        last_experiment_id='',
                        unresolved_fields=['UNRESOLVED:tool_evolution_validation'],
                        metadata={
                            'reason': reason,
                            'decision_source': 'tool_evolution_monitor',
                            'proposal_key': proposal.proposal_key,
                            'proposal_kind': proposal.proposal_kind,
                            'decision': result.decision,
                            'priority_score': round(priority_score, 4),
                        },
                    )
                )
            result = self._result_from_experiment(proposal=proposal, experiment=experiment, priority_score=priority_score)
            promotion_meta = self._maybe_publish_promotion(
                experiment=experiment,
                proposal=proposal,
                result=result,
            )
            snapshot_metadata = {
                'reason': reason,
                'decision_source': 'tool_evolution_monitor',
                'proposal_key': proposal.proposal_key,
                'proposal_kind': proposal.proposal_kind,
                'decision': result.decision,
                'winner': result.winner,
                'priority_score': round(priority_score, 4),
            }
            if promotion_meta:
                snapshot_metadata['promotion_pr'] = promotion_meta
            return self._store_snapshot(
                AutonomousValidationSnapshot(
                    cycle_id=self._current_snapshot.cycle_id,
                    last_checked_at_utc=datetime.now(timezone.utc),
                    status=result.decision,
                    summary=result.reason,
                    pending_candidates=max(self._pending_candidate_count(monitor_status=monitor_status) - 1, 0),
                    promoted_count=self._promoted_count(),
                    last_experiment_id=experiment.experiment_id,
                    current_experiment=experiment,
                    unresolved_fields=[] if result.decision != 'unresolved' else ['UNRESOLVED:tool_evolution_validation'],
                    metadata=snapshot_metadata,
                )
            )
        recommendation = self._next_candidate()
        if recommendation is None:
            pending = self._pending_candidate_count(monitor_status=monitor_status)
            if pending > 0:
                status = 'validating'
                summary = (
                    'Hay propuestas pendientes de validacion pero todavia no son '
                    'candidatas accionables para sandbox en este tick.'
                )
            else:
                # M3: cuando no hay propuestas, intentar consumir probes
                # pendientes de SelfExamination para cerrar el loop P4.
                auto_probes = self._load_pending_auto_probes()
                if auto_probes:
                    status = 'consuming_probes'
                    consumed = self._consume_auto_probes(auto_probes, world_model=world_model, environment_model=environment_model)
                    summary = (
                        f'No hay propuestas candidatas; se consumieron {consumed} '
                        f'probe(s) de autoexaminacion pendientes.'
                    )
                else:
                    status = 'idle_empty'
                    summary = (
                        'No hay propuestas ni recomendaciones candidatas para validar; '
                        'el ciclo autonomo esta al dia.'
                    )
            probes_consumed = consumed if 'consumed' in locals() else 0
            return self._store_snapshot(
                AutonomousValidationSnapshot(
                    cycle_id=self._current_snapshot.cycle_id,
                    last_checked_at_utc=datetime.now(timezone.utc),
                    status=status,
                    summary=summary,
                    pending_candidates=pending,
                    promoted_count=self._promoted_count(),
                    last_experiment_id=str(self._current_snapshot.last_experiment_id or ''),
                    metadata={'reason': reason, 'auto_probes_consumed': probes_consumed},
                )
            )
        experiment = self.sandbox_experiment_service.validate_recommendation(
            recommendation,
            world_model=world_model,
            environment_model=environment_model,
            reason=reason,
        )
        promoted_count = self._promoted_count() + (1 if experiment.promote_to_primary else 0)
        status = 'validated'
        if experiment.verdict == SandboxExperimentVerdict.UNRESOLVED:
            status = 'unresolved'
        elif experiment.promote_to_primary:
            status = 'promoted'
        promotion_meta = self._maybe_publish_promotion(
            experiment=experiment,
            proposal=None,
            result=None,
        )
        snapshot_metadata = {
            'reason': reason,
            'promoted_count': promoted_count,
            'last_subject_key': experiment.subject_key,
            'last_verdict': experiment.verdict.value,
        }
        if promotion_meta:
            snapshot_metadata['promotion_pr'] = promotion_meta
        return self._store_snapshot(
            AutonomousValidationSnapshot(
                cycle_id=self._current_snapshot.cycle_id,
                last_checked_at_utc=datetime.now(timezone.utc),
                status=status,
                summary=experiment.summary,
                pending_candidates=max(self._pending_candidate_count(monitor_status=monitor_status) - 1, 0),
                promoted_count=promoted_count,
                last_experiment_id=experiment.experiment_id,
                current_experiment=experiment,
                unresolved_fields=[] if experiment.verdict != SandboxExperimentVerdict.UNRESOLVED else ['UNRESOLVED:sandbox_validation'],
                metadata=snapshot_metadata,
            )
        )

    def _monitor_loop(self) -> None:
        self._safe_tick(reason='bootstrap_validation')
        tick_count = 0
        while not self._stop_event.wait(self.interval_seconds):
            self._safe_tick(reason='scheduled_validation')
            tick_count += 1
            if tick_count % self._SYNC_PULSE_EVERY_N_TICKS == 0:
                self._safe_sync_pulse()
            self._wake_event.wait(timeout=0.05)
            self._wake_event.clear()

    def _safe_tick(self, *, reason: str) -> None:
        try:
            self.run_once(reason=reason)
        except Exception as exc:
            self._store_error_snapshot(reason=reason, exc=exc)
        # PR J: despues del review de candidatos existentes, el ciclo intenta
        # auto-iniciar investigacion sobre backlog abierto. Cualquier fallo
        # queda aislado para no romper el loop de validacion.
        try:
            self._auto_research_pass(reason=reason)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # P4: Heartbeat de sincronización
    # ------------------------------------------------------------------

    _SYNC_PULSE_EVERY_N_TICKS = 3

    def _safe_sync_pulse(self) -> None:
        try:
            self._sync_pulse()
        except Exception:
            pass

    def _sync_pulse(self) -> None:
        """Periodic synchronization pulse across services.

        Every ``_SYNC_PULSE_EVERY_N_TICKS`` ticks, read the latest state
        from self-examination, strategy recommendations, and world model
        availability.  Consolidate into a ``sync_snapshot`` deposited in
        the decision log so downstream consumers (orchestrator, portable
        context, UI) see a coordinated view of all services.

        This is purely descriptive — no routes are decided here.  The
        pulse enables the "living organism" effect where all services
        synchronize their knowledge periodically.
        """
        sync_data: dict[str, Any] = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'ia_availability': {},
            'top_recommendations': [],
            'active_proposals': [],
            'coordination_status': 'synced',
        }

        if self.world_model_service is not None:
            try:
                wm = self.world_model_service.current_model()
                if wm is not None:
                    ia_status: dict[str, str] = {}
                    for tool_status in (wm.tool_live_status or []):
                        kind = str(tool_status.assistant_kind or '').strip().lower()
                        if kind:
                            ia_status[kind] = 'available' if tool_status.available else 'unavailable'
                    sync_data['ia_availability'] = ia_status
            except Exception:
                sync_data['ia_availability'] = {'status': 'UNRESOLVED:world_model_read_failed'}

        try:
            recent_runs = list(self.experiment_lab_repository.list_runs(limit=20))
            if recent_runs:
                kind_success_scores: dict[str, list[float]] = {}
                kind_total_counts: dict[str, int] = {}
                for run in recent_runs:
                    kind = str(run.assistant_kind or '').strip().lower()
                    if not kind:
                        continue
                    kind_total_counts[kind] = kind_total_counts.get(kind, 0) + 1
                    if bool(run.success):
                        kind_success_scores.setdefault(kind, []).append(float(run.metrics.total_score or 0.0))
                top_recs = sorted(
                    (
                        {
                            'assistant_kind': k,
                            'avg_score': round(sum(v) / max(len(v), 1), 4),
                            'runs': len(v),
                            'total_runs': kind_total_counts.get(k, len(v)),
                            'success_rate': round(len(v) / max(kind_total_counts.get(k, 1), 1), 4),
                        }
                        for k, v in kind_success_scores.items()
                        if len(v) >= 2
                    ),
                    key=lambda x: (
                        x['avg_score'] * x['success_rate'],
                        x['runs'],
                    ),
                    reverse=True,
                )[:3]
                sync_data['top_recommendations'] = top_recs
        except Exception:
            pass

        if self.storage is not None:
            try:
                if self.storage.exists('self_examination/latest.json'):
                    se_payload = self.storage.load_json('self_examination/latest.json')
                    se_meta = dict((se_payload or {}).get('metadata') or {})
                    proposals = list(se_meta.get('solution_proposals') or [])
                    sync_data['active_proposals'] = [
                        {
                            'type': p.get('type', ''),
                            'title': p.get('title', ''),
                            'action_plan': p.get('action_plan'),
                            'estimated_confidence': float(p.get('estimated_confidence') or 0.0),
                            'primary_ia': str((p.get('action_plan') or [{}])[0].get('ia') or '') if isinstance(p.get('action_plan'), list) and p.get('action_plan') else '',
                            'secondary_ia': str((p.get('action_plan') or [{}])[1].get('ia') or '') if isinstance(p.get('action_plan'), list) and len(p.get('action_plan') or []) >= 2 else '',
                        }
                        for p in proposals[:4]
                        if isinstance(p, dict)
                    ]
            except Exception:
                pass

        # Determine coordination_status based on actionability
        available_ias = [
            k for k, v in (sync_data.get('ia_availability') or {}).items()
            if v == 'available'
        ]
        actionable_proposals = [
            p for p in sync_data.get('active_proposals', [])
            if isinstance(p, dict) and float(p.get('estimated_confidence') or 0.0) >= 0.5
            and p.get('primary_ia') in available_ias
        ]
        if actionable_proposals and len(available_ias) >= 2:
            sync_data['coordination_status'] = 'action_ready'
            sync_data['actionable_proposals'] = actionable_proposals[:2]
            sync_data['available_ia_count'] = len(available_ias)
        elif sync_data.get('active_proposals'):
            sync_data['coordination_status'] = 'proposals_pending'
        else:
            sync_data['coordination_status'] = 'synced'

        # E: Auto-pull gobernado — si hay commits nuevos en origin/main,
        # sincronizar automáticamente para aplicar auto-modificaciones.
        git_sync_status = self._maybe_git_auto_sync()
        if git_sync_status:
            sync_data['git_sync'] = git_sync_status

        with self._lock:
            current_snapshot = self._current_snapshot
            metadata = dict(current_snapshot.metadata or {})
            metadata['sync_pulse'] = sync_data
            self._current_snapshot = current_snapshot.model_copy(update={'metadata': metadata})

        # G1: Auto-ejecución proactiva de propuestas — cuando el heartbeat
        # detecta ``action_ready`` y hay propuestas con confianza >= 0.6,
        # iniciar la ejecución coordinada sin esperar request del usuario.
        # Esto cierra el loop: introspección → acción autónoma.
        self._maybe_auto_execute_proposals(sync_data)

    def _maybe_git_auto_sync(self) -> dict[str, Any] | None:
        """Check for remote updates and auto-pull when safe.

        Reasoning: if the system auto-modified itself (created a PR that was
        merged), those changes exist in origin/main but not locally. The
        system must be aware of this gap and close it autonomously —
        just like a living organism integrates new DNA after replication.

        Returns a status dict for the sync_pulse, or None if no git_sync_service.
        """
        service = self.git_sync_service
        if service is None:
            return None

        try:
            status = service.check()
        except Exception:
            return {'state': 'check_failed', 'reason': 'git fetch error'}

        result: dict[str, Any] = {
            'state': 'up_to_date' if not status.has_new_commits else 'behind',
            'commits_behind': status.commits_behind,
            'commits_ahead': status.commits_ahead,
            'tree_dirty': status.tree_dirty,
            'can_sync': status.can_sync,
        }

        if not status.has_new_commits:
            return result

        if not status.can_sync:
            result['state'] = 'blocked'
            result['block_reason'] = status.block_reason
            return result

        # Auto-sync: pull the new commits
        try:
            sync_result = service.sync()
        except Exception:
            result['state'] = 'sync_failed'
            return result

        if sync_result.applied:
            result['state'] = 'updated'
            result['commits_applied'] = sync_result.commits_applied
            result['new_head'] = sync_result.new_head
            # Signal hot-reload by touching a marker file.
            # mcp_hot_reload.py watches src/iabv_v15/*.py mtimes —
            # a git pull that changes .py files will trigger reload naturally.
            # For extra safety, log the event so the system knows WHY it updated.
            if self.storage is not None:
                try:
                    self.storage.save_json('git_sync/last_auto_pull.json', {
                        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                        'commits_applied': sync_result.commits_applied,
                        'new_head': sync_result.new_head,
                        'reason': 'auto_evolution_sync',
                        'detail': (
                            f'Detecté {sync_result.commits_applied} commit(s) nuevos en origin/main. '
                            f'Auto-pull aplicado para integrar auto-modificaciones. '
                            f'HEAD ahora en {sync_result.new_head or "unknown"}.'
                        ),
                    })
                except Exception:
                    pass
        elif sync_result.pull_error:
            result['state'] = 'pull_failed'
            result['error'] = sync_result.pull_error
        elif sync_result.blocked_reasons:
            result['state'] = 'blocked'
            result['can_sync'] = False
            result['block_reason'] = ' | '.join(sync_result.blocked_reasons)

        return result

    # ------------------------------------------------------------------
    # G1: Auto-ejecución proactiva de propuestas
    # ------------------------------------------------------------------

    _AUTO_EXEC_MIN_CONFIDENCE = 0.6

    def _maybe_auto_execute_proposals(self, sync_data: dict[str, Any]) -> None:
        """G1: Execute actionable proposals proactively from sync_pulse.

        When ``coordination_status == 'action_ready'`` and at least one
        proposal has ``estimated_confidence >= 0.6``, delegate execution
        to the orchestrator without waiting for a user request.  Uses the
        existing orchestrator as mediator — no new brain is created.

        Results are deposited back into the snapshot metadata so the
        portable context and UI can see what was auto-executed.
        """
        if str(sync_data.get('coordination_status') or '') != 'action_ready':
            return
        orchestrator = getattr(self, 'adaptive_task_orchestrator', None)
        if orchestrator is None:
            return
        actionable = [
            p for p in (sync_data.get('actionable_proposals') or [])
            if isinstance(p, dict)
            and float(p.get('estimated_confidence') or 0.0) >= self._AUTO_EXEC_MIN_CONFIDENCE
        ]
        if not actionable:
            return
        auto_exec_method = getattr(orchestrator, 'auto_execute_from_sync_pulse', None)
        if not callable(auto_exec_method):
            return
        try:
            exec_result = auto_exec_method(actionable)
        except Exception:
            exec_result = None
        if exec_result and self.storage is not None:
            try:
                self.storage.save_json('sync_pulse/last_auto_execution.json', {
                    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'proposals_executed': len(actionable),
                    'result_status': str(exec_result.get('coordination_status') or 'unknown'),
                    'proposal_titles': [str(p.get('title') or '') for p in actionable[:2]],
                })
            except Exception:
                pass
        with self._lock:
            current_snapshot = self._current_snapshot
            metadata = dict(current_snapshot.metadata or {})
            pulse = dict(metadata.get('sync_pulse') or {})
            pulse['auto_execution'] = {
                'executed': bool(exec_result),
                'proposals_count': len(actionable),
                'status': str((exec_result or {}).get('coordination_status') or 'no_result'),
            }
            metadata['sync_pulse'] = pulse
            self._current_snapshot = current_snapshot.model_copy(update={'metadata': metadata})

    # ------------------------------------------------------------------
    # G2: Persistir feedback de validación para SelfExamination
    # ------------------------------------------------------------------

    def _persist_validation_feedback(
        self,
        *,
        proposal_key: str,
        proposal_kind: str,
        subject_key: str,
        decision: str,
        winner: str,
        reason: str,
        candidate_assistant_kind: str = '',
        current_assistant_kind: str = '',
    ) -> None:
        """G2: Persist validation result so SelfExamination filters future proposals.

        Writes each validation outcome to a JSONL file that
        ``OperationalSelfExaminationService`` reads when generating
        ``_solution_proposals()``.  This prevents re-proposing strategies
        that have already been tried and failed or found unresolved.
        """
        if self.storage is None:
            return
        entry = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'proposal_key': proposal_key,
            'proposal_kind': proposal_kind,
            'subject_key': subject_key,
            'decision': decision,
            'winner': winner,
            'reason': reason,
            'candidate_assistant_kind': candidate_assistant_kind,
            'current_assistant_kind': current_assistant_kind,
        }
        try:
            feedback_path = Path(self.storage.root) / 'validation_feedback' / 'history.jsonl'
            feedback_path.parent.mkdir(parents=True, exist_ok=True)
            with open(feedback_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # PR J: Auto-iniciar investigacion desde backlog
    # ------------------------------------------------------------------
    _AUTO_RESEARCH_MAX_PER_SCAN = 3
    _AUTO_RESEARCH_MAX_PER_TICK = 1
    _AUTO_RESEARCH_CAPABILITY_TOOLS: dict[str, tuple[str, ...]] = {
        'hardware_gpu': (),
        'local_model': ('ollama',),
        'external_account': (),
        'local_runtime': (),
    }

    def _auto_research_enabled(self) -> bool:
        raw = os.getenv('IABV_AUTO_RESEARCH_ENABLED', '1').strip().lower()
        return raw not in {'', '0', 'false', 'no', 'off'}

    def _auto_research_pass(self, *, reason: str) -> list[SandboxExperiment]:
        """Scan backlog and initiate at most ``_AUTO_RESEARCH_MAX_PER_TICK`` experiments.

        Devuelve la lista de experimentos sandbox iniciados. No decide rutas
        por su cuenta: delega en ``sandbox_experiment_service`` la evaluacion
        efectiva. El sandbox permanece aislado del sistema vivo.
        """
        if not self._auto_research_enabled():
            return []
        initiated: list[SandboxExperiment] = []
        items = self._scan_research_backlog()
        for item in items:
            if len(initiated) >= self._AUTO_RESEARCH_MAX_PER_TICK:
                break
            experiment = self._auto_initiate_research(item)
            if experiment is not None:
                initiated.append(experiment)
        return initiated

    def _scan_research_backlog(self) -> list[dict[str, Any]]:
        """Return top ``_AUTO_RESEARCH_MAX_PER_SCAN`` actionable research items.

        Orden de prioridad: TeachingGaps primero (mayor score), luego entries
        del backlog de capacidades (mas recientes primero). Cada item es
        filtrado por disponibilidad de herramientas, policy de gobernanza y
        ausencia de investigacion activa para el mismo subject_key.
        """
        if not self._auto_research_enabled():
            return []
        actionable: list[dict[str, Any]] = []
        for gap in self._open_teaching_gaps():
            if self._research_item_is_actionable(gap):
                actionable.append(gap)
            if len(actionable) >= self._AUTO_RESEARCH_MAX_PER_SCAN:
                return actionable[: self._AUTO_RESEARCH_MAX_PER_SCAN]
        for entry in self._open_capability_entries():
            if self._research_item_is_actionable(entry):
                actionable.append(entry)
            if len(actionable) >= self._AUTO_RESEARCH_MAX_PER_SCAN:
                break
        return actionable[: self._AUTO_RESEARCH_MAX_PER_SCAN]

    def _open_teaching_gaps(self) -> list[dict[str, Any]]:
        """Read open teaching gaps from ``experiment_lab_repository``.

        El repo actual no expone ``list_teaching_gaps``; este helper lo
        invoca con duck-typing para que PR H pueda agregar la lectura sin
        acoplar este servicio a una firma concreta. Si el metodo no existe,
        devuelve lista vacia.
        """
        repo = self.experiment_lab_repository
        reader = getattr(repo, 'list_teaching_gaps', None)
        if not callable(reader):
            return []
        try:
            try:
                raw = list(reader(status='open') or [])
            except TypeError:
                raw = [
                    gap
                    for gap in (reader() or [])
                    if str(self._gap_attr(gap, 'status') or 'open').lower() == 'open'
                ]
        except Exception:
            return []
        items: list[dict[str, Any]] = []
        for gap in raw:
            subject_key = str(
                self._gap_attr(gap, 'subject_key')
                or self._gap_attr(gap, 'label')
                or 'teaching_gap'
            ).strip()
            hypothesis = str(
                self._gap_attr(gap, 'hypothesis')
                or self._gap_attr(gap, 'reason')
                or ''
            ).strip()
            priority = float(self._gap_attr(gap, 'priority') or self._gap_attr(gap, 'score') or 0.0)
            required_tools = list(self._gap_attr(gap, 'required_tools') or [])
            items.append(
                {
                    'source': 'teaching_gap',
                    'subject_key': f'teaching_gap:{subject_key}' if not subject_key.startswith('teaching_gap:') else subject_key,
                    'label': str(self._gap_attr(gap, 'label') or subject_key),
                    'hypothesis': hypothesis,
                    'required_tools': [str(t) for t in required_tools if t],
                    'priority': priority,
                    'raw': gap,
                }
            )
        items.sort(key=lambda it: float(it.get('priority') or 0.0), reverse=True)
        return items

    @staticmethod
    def _gap_attr(gap: Any, key: str) -> Any:
        if isinstance(gap, dict):
            return gap.get(key)
        return getattr(gap, key, None)

    def _open_capability_entries(self) -> list[dict[str, Any]]:
        """Read ``status='open'`` entries from ``data/chat_research_backlog/*.jsonl``."""
        root = self.research_backlog_root
        if root is None:
            return []
        backlog_dir = Path(root) / 'chat_research_backlog'
        if not backlog_dir.exists():
            return []
        collected: list[dict[str, Any]] = []
        for path in sorted(backlog_dir.glob('*.jsonl')):
            try:
                with path.open('r', encoding='utf-8') as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if str(payload.get('status') or 'open').lower() != 'open':
                            continue
                        kind = str(payload.get('kind') or '').strip()
                        matched = str(payload.get('matched_text') or '').strip().lower()
                        subject_key = f'capability:{kind}:{matched}' if matched else f'capability:{kind}'
                        collected.append(
                            {
                                'source': 'capability_research',
                                'subject_key': subject_key,
                                'label': str(payload.get('label') or ''),
                                'hypothesis': str(payload.get('research_hint') or ''),
                                'kind': kind,
                                'matched_text': str(payload.get('matched_text') or ''),
                                'required_tools': list(
                                    self._AUTO_RESEARCH_CAPABILITY_TOOLS.get(kind, ())
                                ),
                                'session_id': str(payload.get('session_id') or ''),
                                'detected_at_utc': str(payload.get('detected_at_utc') or ''),
                                'backlog_path': str(path),
                            }
                        )
            except OSError:
                continue
        collected.sort(key=lambda it: str(it.get('detected_at_utc') or ''), reverse=True)
        return collected

    def _research_item_is_actionable(self, item: dict[str, Any]) -> bool:
        required = [str(t) for t in (item.get('required_tools') or []) if str(t).strip()]
        if required and not self._required_tools_available(required):
            return False
        if self._governance_blocks_auto_research():
            return False
        subject_key = str(item.get('subject_key') or '').strip()
        if not subject_key:
            return False
        if self._has_active_investigation(subject_key):
            return False
        return True

    def _required_tools_available(self, required: list[str]) -> bool:
        registry = self.tool_registry
        if registry is None:
            # Without a registry we cannot verify; bloquea por precaucion solo
            # cuando el item declara herramientas requeridas explicitamente.
            return False
        available: set[str] = set()
        try:
            cards = list(registry.list_cards() or [])
        except Exception:
            return False
        for card in cards:
            if not bool(getattr(card, 'available', False)):
                continue
            for key in (getattr(card, 'tool_id', None), getattr(card, 'adapter_key', None)):
                if key:
                    available.add(str(key).lower())
            for cap in getattr(card, 'capabilities', None) or []:
                if cap:
                    available.add(str(cap).lower())
        for needed in required:
            if str(needed).lower() not in available:
                return False
        return True

    def _governance_blocks_auto_research(self) -> bool:
        policy = self.autonomy_governance_policy
        if policy is None:
            return False
        for name in ('allow_auto_research', 'allows_auto_research', 'should_allow_auto_research'):
            check = getattr(policy, name, None)
            if callable(check):
                try:
                    return not bool(check())
                except Exception:
                    return True
        return False

    def _has_active_investigation(self, subject_key: str) -> bool:
        sandbox_key = f'sandbox:{subject_key}'
        try:
            recent_runs = self.experiment_lab_repository.list_runs(
                subject_key=sandbox_key, limit=5
            )
        except Exception:
            return False
        for run in recent_runs:
            metadata = dict(getattr(run, 'metadata', None) or {})
            source = str(metadata.get('learning_source') or '')
            if source in {'auto_research_initiation', 'sandbox_experiment'}:
                return True
        return False

    def _auto_initiate_research(self, item: dict[str, Any]) -> SandboxExperiment | None:
        subject_key = str(item.get('subject_key') or '').strip()
        if not subject_key:
            return None
        hypothesis = str(item.get('hypothesis') or '').strip() or (
            f'Investigar {item.get("label") or subject_key}'
        )
        recommendation = ExperimentRecommendation(
            domain=ExperimentDomain.LANGUAGE,
            subject_key=subject_key,
            recommended_route=EvaluationRoute.FALLBACK,
            recommended_assistant_kind='auto_research',
            recommended_config_signature=f'auto_research:{item.get("source", "")}',
            rationale=hypothesis,
            confidence=0.4,
            metadata={
                'auto_research_source': item.get('source'),
                'auto_research_label': item.get('label'),
                'auto_research_hypothesis': hypothesis,
                'auto_research_kind': item.get('kind'),
                'auto_research_matched_text': item.get('matched_text'),
                'auto_research_session_id': item.get('session_id'),
            },
        )
        try:
            experiment = self.sandbox_experiment_service.validate_recommendation(
                recommendation,
                world_model=self._current_world_model(),
                environment_model=self._current_environment_model(),
                reason=f'auto_research:{item.get("source", "")}',
            )
        except Exception:
            return None
        if item.get('source') == 'capability_research':
            self._mark_capability_entry_in_progress(item)
        elif item.get('source') == 'teaching_gap':
            self._mark_teaching_gap_in_progress(item)
        return experiment

    def _mark_capability_entry_in_progress(self, item: dict[str, Any]) -> None:
        path_str = item.get('backlog_path')
        if not path_str:
            return
        path = Path(str(path_str))
        if not path.exists():
            return
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except OSError:
            return
        session_id = str(item.get('session_id') or '')
        kind = str(item.get('kind') or '')
        matched_text = str(item.get('matched_text') or '')
        detected_at_utc = str(item.get('detected_at_utc') or '')
        new_lines: list[str] = []
        updated = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if (
                not updated
                and str(payload.get('session_id') or '') == session_id
                and str(payload.get('kind') or '') == kind
                and str(payload.get('matched_text') or '') == matched_text
                and str(payload.get('detected_at_utc') or '') == detected_at_utc
                and str(payload.get('status') or 'open') == 'open'
            ):
                payload['status'] = 'in_progress'
                updated = True
            new_lines.append(json.dumps(payload, ensure_ascii=False))
        if updated:
            try:
                path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
            except OSError:
                pass

    def _mark_teaching_gap_in_progress(self, item: dict[str, Any]) -> None:
        repo = self.experiment_lab_repository
        updater = getattr(repo, 'update_teaching_gap_status', None)
        if not callable(updater):
            return
        try:
            updater(item.get('raw'), status='in_progress')
        except Exception:
            return

    def _store_error_snapshot(self, *, reason: str, exc: BaseException) -> None:
        with self._lock:
            previous = self._current_snapshot
        self._store_snapshot(
            AutonomousValidationSnapshot(
                cycle_id=previous.cycle_id,
                last_checked_at_utc=datetime.now(timezone.utc),
                status='error',
                summary=f'Fallo el ciclo de validacion autonoma: {exc!r}',
                pending_candidates=previous.pending_candidates,
                promoted_count=previous.promoted_count,
                last_experiment_id=str(previous.last_experiment_id or ''),
                unresolved_fields=['UNRESOLVED:autonomous_validation_cycle_error'],
                metadata={
                    'reason': reason,
                    'error': repr(exc),
                },
            )
        )

    def _current_environment_model(self) -> EnvironmentSelfModel | None:
        service = self.environment_self_awareness_service
        if service is None or not hasattr(service, 'current_model'):
            return None
        try:
            return service.current_model()
        except Exception:
            return None

    def _current_world_model(self) -> WorldModelSnapshot | None:
        service = self.world_model_service
        if service is None or not hasattr(service, 'current_model'):
            return None
        try:
            return service.current_model()
        except Exception:
            return None

    def _current_tool_evolution_status(self) -> ToolEvolutionStatus | None:
        service = self.tool_evolution_monitor
        if service is None or not hasattr(service, 'current_status'):
            return None
        try:
            return service.current_status(refresh=True)
        except Exception:
            return None

    def _pause_reason(self, *, environment_model: Any | None, world_model: Any | None) -> str:
        for risk in getattr(environment_model, 'risk_signals', []) or []:
            kind = str(getattr(risk, 'kind', '') or '').strip().lower()
            severity = str(getattr(getattr(risk, 'severity', ''), 'value', getattr(risk, 'severity', '')) or '').strip().lower()
            if severity in {'high', 'critical'} and kind in {'cpu_pressure', 'ram_pressure', 'ram_critical', 'throttling_detected', 'gpu_pressure'}:
                return f'El entorno reporta {kind} con severidad {severity}.'
        for block in getattr(world_model, 'block_records', []) or []:
            if str(getattr(block, 'target_scope', '') or '').strip().lower() == 'heavy_local_model':
                return str(getattr(block, 'detail', '') or getattr(block, 'reason', '') or 'Hay un bloqueo activo para carga pesada.')
        for process in getattr(world_model, 'background_processes', []) or []:
            state = str(getattr(process, 'state', '') or '').strip().lower()
            if state in {'cpu_heavy', 'memory_heavy'}:
                return f'Hay un proceso en segundo plano bajo estado {state}.'
        return ''

    def _next_tool_evolution_candidate(self, *, monitor_status: ToolEvolutionStatus | None) -> tuple[ToolEvolutionProposal, float] | None:
        if monitor_status is None:
            return None
        ranked: list[tuple[float, ToolEvolutionProposal]] = []
        for proposal in list(monitor_status.proposals or []):
            if not self._proposal_is_actionable(proposal):
                continue
            latest = self._latest_result_for_proposal(proposal)
            if latest is not None and latest.decision in {'promoted', 'discarded'} and not self._proposal_has_new_evidence(proposal, latest):
                continue
            priority = self._proposal_priority(proposal=proposal, monitor_status=monitor_status)
            ranked.append((priority, proposal))
        if not ranked:
            return None
        ranked.sort(key=lambda item: item[0], reverse=True)
        priority, proposal = ranked[0]
        return proposal, priority

    def _proposal_is_actionable(self, proposal: ToolEvolutionProposal) -> bool:
        kind = str(proposal.proposal_kind or '').strip().lower()
        return kind == 'compare_again' or kind.startswith('validate_')

    def _proposal_priority(self, *, proposal: ToolEvolutionProposal, monitor_status: ToolEvolutionStatus) -> float:
        baseline_profile = dict((proposal.metadata or {}).get('baseline_profile') or {})
        if not baseline_profile:
            baseline_profile = self._matching_performance_profile(proposal=proposal, monitor_status=monitor_status)
        success_rate = float(baseline_profile.get('success_rate') or 0.0)
        blocked_rate = float(baseline_profile.get('blocked_rate') or 0.0)
        fallback_rate = float(baseline_profile.get('fallback_rate') or 0.0)
        trend_score = float(baseline_profile.get('trend_score') or 0.0)
        sample_count = int(baseline_profile.get('sample_count') or 0)
        severity = (
            blocked_rate * 0.35
            + fallback_rate * 0.2
            + max(-trend_score, 0.0) * 0.4
            + max(1.0 - success_rate, 0.0) * 0.2
        )
        confidence = float(proposal.confidence or 0.0)
        frequency = min(sample_count / 5.0, 1.0)
        impact = max(float((proposal.metadata or {}).get('score_margin') or 0.0), 0.0)
        if bool((proposal.metadata or {}).get('local_first_candidate')):
            impact += 0.08
        if proposal.proposal_kind == 'validate_discovery':
            impact += min(
                0.18,
                float((proposal.metadata or {}).get('impact_score') or 0.0) * 0.08
                + float((proposal.metadata or {}).get('compatibility_score') or 0.0) * 0.05
                + float((proposal.metadata or {}).get('cost_score') or 0.0) * 0.03,
            )
        kind_bonus = 0.0
        if proposal.proposal_kind == 'validate_replacement':
            kind_bonus = 0.08
        elif proposal.proposal_kind == 'validate_local_first':
            kind_bonus = 0.06
        elif proposal.proposal_kind == 'validate_discovery':
            kind_bonus = 0.05
        elif proposal.proposal_kind == 'compare_again':
            kind_bonus = 0.04
        return severity * 0.38 + confidence * 0.26 + frequency * 0.18 + impact * 0.18 + kind_bonus

    def _matching_performance_profile(self, *, proposal: ToolEvolutionProposal, monitor_status: ToolEvolutionStatus) -> dict[str, Any]:
        for item in list(monitor_status.performance or []):
            if (
                item.subject_key == proposal.subject_key
                and item.route == proposal.current_route
                and str(item.assistant_kind or '').strip().lower() == str(proposal.current_assistant_kind or '').strip().lower()
                and str(item.config_signature or '').strip() == str(proposal.current_config_signature or '').strip()
            ):
                return item.model_dump(mode='json')
        return {}

    def _proposal_has_new_evidence(self, proposal: ToolEvolutionProposal, latest: ProposalValidationResult) -> bool:
        current_refs = {str(item).strip() for item in (proposal.evidence_refs or []) if str(item).strip()}
        previous_refs = {str(item).strip() for item in (latest.evidence_refs or []) if str(item).strip()}
        if not previous_refs:
            return True
        return not current_refs.issubset(previous_refs)

    def _recommendation_from_proposal(self, proposal: ToolEvolutionProposal) -> ExperimentRecommendation:
        metadata = dict(proposal.metadata or {})
        ranked = [dict(item) for item in (metadata.get('ranked_configurations') or []) if isinstance(item, dict)]
        if not ranked:
            ranked = [
                {
                    'route': proposal.current_route.value,
                    'assistant_kind': proposal.current_assistant_kind,
                    'config_signature': proposal.current_config_signature,
                    'weighted_score': float(metadata.get('baseline_weighted_score') or 0.0),
                    'score': float(metadata.get('baseline_weighted_score') or 0.0),
                    'samples': int(dict(metadata.get('baseline_profile') or {}).get('sample_count') or 0),
                },
                {
                    'route': proposal.candidate_route.value,
                    'assistant_kind': proposal.candidate_assistant_kind,
                    'config_signature': proposal.candidate_config_signature,
                    'weighted_score': float(metadata.get('alternative_weighted_score') or 0.0),
                    'score': float(metadata.get('alternative_weighted_score') or 0.0),
                    'samples': int(dict(metadata.get('candidate_profile') or {}).get('sample_count') or 0),
                },
            ]
        return ExperimentRecommendation(
            domain=proposal.domain,
            subject_key=proposal.subject_key,
            recommended_route=proposal.current_route,
            recommended_assistant_kind=proposal.current_assistant_kind,
            recommended_config_signature=proposal.current_config_signature,
            score=float(metadata.get('baseline_weighted_score') or 0.0),
            confidence=float(proposal.confidence or 0.0),
            rationale=str(proposal.rationale or proposal.summary or ''),
            supporting_run_ids=list(proposal.evidence_refs or [])[:8],
            metadata={
                'comparison_scope_keys': list(proposal.comparison_scope_keys or []),
                'ranked_configurations': ranked[:4],
                'adaptive_learning_summary': {
                    'reasons': list(metadata.get('degradation_reasons') or []),
                },
                'proposal_key': proposal.proposal_key,
                'proposal_kind': proposal.proposal_kind,
            },
        )

    def _result_from_experiment(
        self,
        *,
        proposal: ToolEvolutionProposal,
        experiment: SandboxExperiment,
        priority_score: float,
    ) -> ProposalValidationResult:
        if experiment.promote_to_primary:
            decision = 'promoted'
            winner = 'proposed_tool'
            reason = experiment.summary or 'La propuesta gano en sandbox y se promovio.'
        elif experiment.verdict == SandboxExperimentVerdict.UNRESOLVED:
            decision = 'unresolved'
            winner = 'unresolved'
            reason = experiment.summary or 'La validacion no pudo cerrarse con evidencia suficiente.'
        elif experiment.verdict == SandboxExperimentVerdict.DOUBTFUL:
            decision = 'deferred'
            winner = 'tie'
            reason = experiment.summary or 'La comparacion no mostro una mejora suficientemente fuerte para cerrar la decision.'
        else:
            decision = 'discarded'
            winner = 'current_tool'
            reason = experiment.summary or 'La herramienta actual se mantiene porque la propuesta no supero la linea base.'
        result = self._record_proposal_validation_result(
            proposal=proposal,
            decision=decision,
            winner=winner,
            reason=reason,
            sandbox_experiment=experiment,
            metrics={
                'priority_score': round(priority_score, 4),
                'baseline_weighted_score': float((proposal.metadata or {}).get('baseline_weighted_score') or 0.0),
                'candidate_weighted_score': float((proposal.metadata or {}).get('alternative_weighted_score') or 0.0),
                'score_margin': float((proposal.metadata or {}).get('score_margin') or 0.0),
                'evidence_strength': float(getattr(experiment, 'evidence_strength', 0.0) or 0.0),
                'observed_blockers': list(getattr(experiment, 'observed_blockers', []) or []),
            },
            metadata={
                'decision_source': 'tool_evolution_monitor',
                'validation_verdict': experiment.verdict.value,
            },
        )
        # G2: persist feedback so SelfExamination can filter future proposals
        self._persist_validation_feedback(
            proposal_key=proposal.proposal_key,
            proposal_kind=proposal.proposal_kind,
            subject_key=proposal.subject_key,
            decision=decision,
            winner=winner,
            reason=reason,
            candidate_assistant_kind=str(proposal.candidate_assistant_kind or ''),
            current_assistant_kind=str(proposal.current_assistant_kind or ''),
        )
        return result

    def _maybe_publish_promotion(
        self,
        *,
        experiment: SandboxExperiment,
        proposal: ToolEvolutionProposal | None,
        result: ProposalValidationResult | None,
    ) -> dict[str, Any] | None:
        """F2.3 (thin): si se promueve, abre un PR documental en iabv-auto/*.

        El ciclo no debe caer por fallos de publicacion: cualquier error se
        captura y solo queda en el metadata de la snapshot. Si no hay
        publisher wireado o el experimento no promueve, retorna ``None``
        sin tocar nada.
        """

        if self.promotion_pr_publisher is None:
            return None
        if experiment is None or not bool(getattr(experiment, 'promote_to_primary', False)):
            return None
        subject_key = str(
            (result.subject_key if result is not None else None)
            or (proposal.subject_key if proposal is not None else None)
            or experiment.subject_key
            or 'unknown'
        )
        current_route = str(
            (proposal.current_route.value if proposal is not None and proposal.current_route is not None else None)
            or experiment.baseline_route.value
        )
        current_assistant_kind = str(
            (proposal.current_assistant_kind if proposal is not None else None)
            or experiment.baseline_assistant_kind
            or ''
        )
        candidate_route = str(
            (proposal.candidate_route.value if proposal is not None and proposal.candidate_route is not None else None)
            or experiment.candidate_route.value
        )
        candidate_assistant_kind = str(
            (proposal.candidate_assistant_kind if proposal is not None else None)
            or experiment.candidate_assistant_kind
            or ''
        )
        proposal_kind = str(proposal.proposal_kind if proposal is not None else '') or ''
        proposal_id = str(proposal.proposal_id if proposal is not None else '') or ''
        metrics = dict(result.metrics) if (result is not None and getattr(result, 'metrics', None)) else {}
        metrics.setdefault('evidence_strength', float(getattr(experiment, 'evidence_strength', 0.0) or 0.0))
        evidence_refs = list(result.evidence_refs) if (result is not None and getattr(result, 'evidence_refs', None)) else []
        if not evidence_refs and getattr(experiment, 'supporting_run_ids', None):
            evidence_refs = list(experiment.supporting_run_ids)
        try:
            publish_result = self.promotion_pr_publisher.publish_promotion(
                subject_key=subject_key,
                proposal_kind=proposal_kind,
                current_route=current_route,
                current_assistant_kind=current_assistant_kind,
                candidate_route=candidate_route,
                candidate_assistant_kind=candidate_assistant_kind,
                verdict=str(experiment.verdict.value if experiment.verdict is not None else ''),
                summary=str(getattr(experiment, 'summary', '') or ''),
                metrics=metrics,
                evidence_refs=evidence_refs,
                sandbox_experiment_id=str(getattr(experiment, 'experiment_id', '') or ''),
                proposal_id=proposal_id,
            )
        except Exception as exc:  # pragma: no cover - defensivo
            return {
                'success': False,
                'error': repr(exc),
                'subject_key': subject_key,
            }
        return {
            'success': bool(getattr(publish_result, 'success', False)),
            'subject_key': subject_key,
            'branch': str(getattr(publish_result, 'branch', '') or ''),
            'pr_number': getattr(publish_result, 'pr_number', None),
            'pr_url': str(getattr(publish_result, 'pr_url', '') or ''),
            'markdown_path': str(getattr(publish_result, 'markdown_path', '') or ''),
            'evidence_path': str(getattr(publish_result, 'evidence_path', '') or ''),
            'blocked_by_policy': bool(getattr(publish_result, 'blocked_by_policy', False)),
            'required_approval': bool(getattr(publish_result, 'required_approval', False)),
            'skipped': bool(getattr(publish_result, 'skipped', False)),
            'error': str(getattr(publish_result, 'error', '') or ''),
        }

    def _record_proposal_validation_result(
        self,
        *,
        proposal: ToolEvolutionProposal,
        decision: str,
        winner: str,
        reason: str,
        sandbox_experiment: SandboxExperiment | None,
        metrics: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ProposalValidationResult:
        result = ProposalValidationResult(
            proposal_id=proposal.proposal_id,
            proposal_key=str(proposal.proposal_key or '').strip() or self._proposal_key(proposal),
            domain=proposal.domain,
            subject_key=proposal.subject_key,
            proposal_kind=proposal.proposal_kind,
            decision=decision,
            winner=winner,
            reason=reason,
            current_route=proposal.current_route,
            current_assistant_kind=proposal.current_assistant_kind,
            current_config_signature=proposal.current_config_signature,
            candidate_route=proposal.candidate_route,
            candidate_assistant_kind=proposal.candidate_assistant_kind,
            candidate_config_signature=proposal.candidate_config_signature,
            sandbox_experiment_id=str(getattr(sandbox_experiment, 'experiment_id', '') or ''),
            confidence=float(proposal.confidence or 0.0),
            evidence_refs=list(dict.fromkeys([*(proposal.evidence_refs or []), *list(getattr(sandbox_experiment, 'supporting_run_ids', []) or [])]))[:8],
            comparison_scope_keys=list(proposal.comparison_scope_keys or []),
            metrics=dict(metrics or {}),
            metadata={
                **dict(proposal.metadata or {}),
                **dict(metadata or {}),
            },
        )
        self._append_decision_log(result)
        return result

    def _append_decision_log(self, result: ProposalValidationResult) -> None:
        with self._lock:
            log = self._decision_log or ToolEvolutionDecisionLog()
            entries = [*list(log.entries or []), result]
            summary_by_tool = self._summary_by_tool(entries)
            summary_by_problem = self._summary_by_problem(entries)
            unresolved_fields = ['UNRESOLVED:tool_evolution_decision'] if any(item.decision == 'unresolved' for item in entries) else []
            updated = ToolEvolutionDecisionLog(
                log_id=log.log_id,
                updated_at_utc=datetime.now(timezone.utc),
                entries=entries[-40:],
                summary_by_tool=summary_by_tool,
                summary_by_problem=summary_by_problem,
                unresolved_fields=unresolved_fields,
                metadata={
                    'last_decision': result.decision,
                    'last_proposal_key': result.proposal_key,
                    'promoted_count': sum(1 for item in entries if item.decision == 'promoted'),
                    'discarded_count': sum(1 for item in entries if item.decision == 'discarded'),
                    'deferred_count': sum(1 for item in entries if item.decision == 'deferred'),
                    'unresolved_count': sum(1 for item in entries if item.decision == 'unresolved'),
                },
            )
            self._decision_log = self._persist_decision_log(updated)

    def _persist_decision_log(self, log: ToolEvolutionDecisionLog) -> ToolEvolutionDecisionLog:
        if self.storage is None:
            return log
        result_dir = f'tool_evolution/validated_proposals/{log.entries[-1].result_id}.json' if log.entries else ''
        if result_dir:
            self.storage.save_json_atomic(result_dir, log.entries[-1].model_dump(mode='json'))
        markdown = self._render_decision_log(log)
        latest_json_rel = 'tool_evolution/decision_log.json'
        latest_md_rel = 'tool_evolution/decision_log.md'
        archive_json_rel = f'tool_evolution/decision_history/{log.log_id}.json'
        archive_md_rel = f'tool_evolution/decision_history/{log.log_id}.md'
        self.storage.save_json_atomic(archive_json_rel, log.model_dump(mode='json'))
        self.storage.save_bytes(archive_md_rel, markdown.encode('utf-8'))
        self.storage.save_json_atomic(latest_json_rel, log.model_dump(mode='json'))
        self.storage.save_bytes(latest_md_rel, markdown.encode('utf-8'))
        log = log.model_copy(
            update={
                'package_path': str(self.storage.resolve(latest_json_rel)),
                'markdown_path': str(self.storage.resolve(latest_md_rel)),
                'metadata': {
                    **dict(log.metadata or {}),
                    'archive_json_path': str(self.storage.resolve(archive_json_rel)),
                    'archive_markdown_path': str(self.storage.resolve(archive_md_rel)),
                },
            }
        )
        self.storage.save_json_atomic(latest_json_rel, log.model_dump(mode='json'))
        return log

    def _load_decision_log(self) -> ToolEvolutionDecisionLog | None:
        if self.storage is None:
            return None
        try:
            if not self.storage.exists('tool_evolution/decision_log.json'):
                return None
            return ToolEvolutionDecisionLog.model_validate(self.storage.load_json('tool_evolution/decision_log.json'))
        except Exception:
            return None

    def _render_decision_log(self, log: ToolEvolutionDecisionLog) -> str:
        lines = [
            '# IABV v1.5 - Tool Evolution Decision Log',
            '',
            f'Actualizado: {log.updated_at_utc.isoformat()}',
            '',
            '## Ultimas decisiones',
        ]
        for entry in list(log.entries or [])[-8:]:
            lines.append(
                f"- {entry.subject_key}: {entry.decision} | ganador={entry.winner} | "
                f"actual={entry.current_assistant_kind or entry.current_route.value} | "
                f"propuesta={entry.candidate_assistant_kind or entry.candidate_route.value} | {entry.reason}"
            )
        if log.unresolved_fields:
            lines.append('')
            lines.append(f"UNRESOLVED: {', '.join(log.unresolved_fields)}")
        return '\n'.join(lines).strip()

    def _summary_by_tool(self, entries: list[ProposalValidationResult]) -> dict[str, str]:
        summary: dict[str, str] = {}
        for entry in entries:
            current_tool = str(entry.current_assistant_kind or '').strip().lower()
            candidate_tool = str(entry.candidate_assistant_kind or '').strip().lower()
            if entry.decision == 'promoted':
                if current_tool and current_tool != candidate_tool:
                    summary[current_tool] = 'degradado'
                if candidate_tool:
                    summary[candidate_tool] = 'ganando'
            elif entry.decision == 'discarded':
                if current_tool:
                    summary[current_tool] = summary.get(current_tool, 'estable')
                if candidate_tool:
                    summary[candidate_tool] = 'descartado'
            elif entry.decision == 'deferred' and candidate_tool:
                summary[candidate_tool] = 'en_validacion'
            elif entry.decision == 'unresolved' and candidate_tool:
                summary[candidate_tool] = 'inconcluso'
        return summary

    def _summary_by_problem(self, entries: list[ProposalValidationResult]) -> dict[str, str]:
        summary: dict[str, str] = {}
        for entry in entries:
            if entry.decision == 'promoted':
                summary[entry.subject_key] = entry.candidate_assistant_kind or entry.candidate_route.value
            elif entry.decision == 'discarded':
                summary[entry.subject_key] = entry.current_assistant_kind or entry.current_route.value
            elif entry.decision == 'deferred':
                summary[entry.subject_key] = f'en_validacion:{entry.candidate_assistant_kind or entry.candidate_route.value}'
            elif entry.decision == 'unresolved':
                summary[entry.subject_key] = 'UNRESOLVED'
        return summary

    def _proposal_key(self, proposal: ToolEvolutionProposal) -> str:
        return '|'.join(
            [
                str(proposal.subject_key or '').strip(),
                str(proposal.proposal_kind or '').strip(),
                proposal.current_route.value,
                str(proposal.current_assistant_kind or '').strip().lower(),
                str(proposal.current_config_signature or '').strip(),
                proposal.candidate_route.value,
                str(proposal.candidate_assistant_kind or '').strip().lower(),
                str(proposal.candidate_config_signature or '').strip(),
            ]
        )

    def _latest_result_for_proposal(self, proposal: ToolEvolutionProposal) -> ProposalValidationResult | None:
        proposal_key = str(proposal.proposal_key or '').strip() or self._proposal_key(proposal)
        entries = list(self.current_decision_log().entries or [])
        for entry in reversed(entries):
            if str(entry.proposal_key or '').strip() == proposal_key:
                return entry
        return None

    def _next_candidate(self) -> ExperimentRecommendation | None:
        recommendations = [
            item
            for item in self.experiment_lab_repository.list_recommendations(limit=8)
            if not str(getattr(item, 'subject_key', '') or '').startswith('sandbox:')
        ]
        for recommendation in recommendations:
            if self._recently_validated(str(recommendation.subject_key or '')):
                continue
            return recommendation
        return None

    def _recently_validated(self, subject_key: str) -> bool:
        sandbox_key = f'sandbox:{str(subject_key or "").strip() or "general"}'
        recent_runs = self.experiment_lab_repository.list_runs(subject_key=sandbox_key, limit=3)
        return any(str((run.metadata or {}).get('learning_source') or '') == 'sandbox_experiment' for run in recent_runs)

    def _pending_candidate_count(self, *, monitor_status: ToolEvolutionStatus | None) -> int:
        pending_proposals = 0
        if monitor_status is not None:
            for proposal in list(monitor_status.proposals or []):
                if not self._proposal_is_actionable(proposal):
                    continue
                latest = self._latest_result_for_proposal(proposal)
                if latest is not None and latest.decision in {'promoted', 'discarded'} and not self._proposal_has_new_evidence(proposal, latest):
                    continue
                pending_proposals += 1
        recommendation_candidates = len(
            [
                item
                for item in self.experiment_lab_repository.list_recommendations(limit=8)
                if not str(getattr(item, 'subject_key', '') or '').startswith('sandbox:')
                and not self._recently_validated(str(getattr(item, 'subject_key', '') or ''))
            ]
        )
        return pending_proposals + recommendation_candidates

    def _promoted_count(self) -> int:
        decision_promoted = sum(1 for item in self.current_decision_log().entries if item.decision == 'promoted')
        current_promoted = int((self._current_snapshot.metadata or {}).get('promoted_count') or 0)
        return max(decision_promoted, current_promoted)

    _PENDING_AUTO_PROBES_CAP = 6

    def _load_pending_auto_probes(self) -> list[dict[str, Any]]:
        """Read structured probe requests emitted by OperationalSelfExamination.

        El self-exam deja ``pending_auto_probes`` en
        ``self_examination/latest.json`` cuando detecta findings HIGH con
        confianza >= 0.85. Este ciclo de validación es el consumidor natural
        porque ya tiene un tick periódico y ya surface decisiones al log y
        a la UI. Al surfacear los probes en cada tick cerramos el loop P4:
        el testigo ya no se pierde en silencio.

        Sólo se consume la señal estructurada; la ejecución real del probe
        sigue siendo responsabilidad del orquestador / ToolTeachService /
        runner de pytest. Aquí no se decide ruta ni se dispara nada.
        """
        storage = self.storage
        if storage is None:
            return []
        try:
            if not storage.exists('self_examination/latest.json'):
                return []
            payload = storage.load_json('self_examination/latest.json')
        except Exception:
            return []
        metadata = dict((payload or {}).get('metadata') or {})
        raw_probes = metadata.get('pending_auto_probes')
        if not isinstance(raw_probes, list):
            return []
        probes: list[dict[str, Any]] = []
        for probe in raw_probes[: self._PENDING_AUTO_PROBES_CAP]:
            if isinstance(probe, dict) and probe.get('finding_id'):
                probes.append(dict(probe))
        return probes

    def _consume_auto_probes(
        self,
        probes: list[dict[str, Any]],
        *,
        world_model: Any | None = None,
        environment_model: Any | None = None,
    ) -> int:
        """M3: ejecutar probes de SelfExamination como validaciones diagnosticas.

        Cada probe se registra en el decision_log como ``probe_consumed``
        para que la UI y el self-exam vean que el ciclo actuo sobre los
        hallazgos. No se modifica estado real; solo se surfacea la senal.

        Sigue el patron de ``_append_decision_log``: hold ``self._lock``,
        build a new entries list (no in-place mutation), y persistir.
        """
        already_consumed: set[str] = set()
        with self._lock:
            log = self._decision_log or ToolEvolutionDecisionLog()
            for entry in (log.entries or []):
                if entry.decision == 'probe_consumed':
                    already_consumed.add(str(entry.subject_key or ''))
        new_entries: list[ProposalValidationResult] = []
        for probe in probes[:self._PENDING_AUTO_PROBES_CAP]:
            finding_id = str(probe.get('finding_id') or '').strip()
            if not finding_id or finding_id in already_consumed:
                continue
            probe_type = str(probe.get('probe_type') or 'diagnostic').strip()
            description = str(probe.get('description') or '').strip()[:240]
            new_entries.append(
                ProposalValidationResult(
                    decision='probe_consumed',
                    subject_key=finding_id,
                    current_assistant_kind='self_examination',
                    reason=f'Auto-probe consumido: {probe_type} — {description}',
                    metadata={
                        'finding_id': finding_id,
                        'probe_type': probe_type,
                        'source': 'operational_self_examination',
                        'consumed_by': 'autonomous_validation_cycle',
                    },
                )
            )
        if not new_entries:
            return 0
        with self._lock:
            log = self._decision_log or ToolEvolutionDecisionLog()
            entries = [*list(log.entries or []), *new_entries]
            unresolved_fields = ['UNRESOLVED:tool_evolution_decision'] if any(item.decision == 'unresolved' for item in entries) else []
            updated = ToolEvolutionDecisionLog(
                log_id=log.log_id,
                updated_at_utc=datetime.now(timezone.utc),
                entries=entries[-40:],
                summary_by_tool=self._summary_by_tool(entries),
                summary_by_problem=self._summary_by_problem(entries),
                unresolved_fields=unresolved_fields,
                metadata={
                    'last_decision': 'probe_consumed',
                    'probe_consumed_count': len(new_entries),
                },
            )
            self._decision_log = self._persist_decision_log(updated)
        return len(new_entries)

    def _store_snapshot(self, snapshot: AutonomousValidationSnapshot) -> AutonomousValidationSnapshot:
        probes = self._load_pending_auto_probes()
        if probes:
            merged_metadata = dict(snapshot.metadata or {})
            merged_metadata['pending_auto_probes'] = probes
            snapshot = snapshot.model_copy(update={'metadata': merged_metadata})
        with self._lock:
            self._current_snapshot = snapshot
            return self._current_snapshot.model_copy(deep=True)

    def _in_test_mode(self) -> bool:
        return bool(os.getenv('PYTEST_CURRENT_TEST'))
