from __future__ import annotations

from datetime import datetime, timezone

from iabv_v15.domain.models import AdaptiveSession, DiagnosticCategory, DiagnosticEpisode, RunRecord, ScenarioRun
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.self_teach.execution_probe_service import ExecutionProbeService
from iabv_v15.services.self_teach.pending_issue_service import PendingIssueService
from iabv_v15.services.self_teach.runtime_tuner import RuntimeTuner
from iabv_v15.services.self_teach.scenario_registry import ScenarioRegistry


class ScenarioAutoTestService:
    def __init__(
        self,
        *,
        scenario_registry: ScenarioRegistry,
        execution_probe_service: ExecutionProbeService,
        runtime_tuner: RuntimeTuner,
        pending_issue_service: PendingIssueService,
        scenario_run_repository: ScenarioRunRepository,
        adaptive_session_repository: AdaptiveSessionRepository,
        dossier_repository: ExecutionDossierRepository,
        task_outcome_recorder: TaskOutcomeRecorder,
    ) -> None:
        self.scenario_registry = scenario_registry
        self.execution_probe_service = execution_probe_service
        self.runtime_tuner = runtime_tuner
        self.pending_issue_service = pending_issue_service
        self.scenario_run_repository = scenario_run_repository
        self.adaptive_session_repository = adaptive_session_repository
        self.dossier_repository = dossier_repository
        self.task_outcome_recorder = task_outcome_recorder

    def run(self, *, run_record: RunRecord, session: AdaptiveSession) -> tuple[ScenarioRun, AdaptiveSession]:
        scenario = self.scenario_registry.resolve_for_request(run_record.request, session.intent)
        diagnosis = self.execution_probe_service.analyze_result(run_record=run_record, session=session, scenario=scenario)
        runtime_adjustments = self.runtime_tuner.evaluate_and_apply(diagnosis=diagnosis, session=session)
        pending_issue = None
        if diagnosis.category in {DiagnosticCategory.NEED_ADAPTER, DiagnosticCategory.NEED_CODEX_FIX}:
            pending_issue = self.pending_issue_service.enqueue(
                scenario=scenario,
                run_record=run_record,
                session=session,
                diagnosis=diagnosis,
                runtime_adjustments=runtime_adjustments,
            )
        observed_signals = list((diagnosis.metadata or {}).get('observed_signals') or [])
        expected_signals = list((diagnosis.metadata or {}).get('expected_signals') or [])
        diagnostic_episode = DiagnosticEpisode(
            scenario_id=scenario.scenario_id,
            goal=run_record.request.user_goal,
            expected_signals=expected_signals,
            observed_signals=observed_signals,
            interpretation=diagnosis.summary,
            diagnosis=diagnosis,
            run_id=run_record.run_id,
            session_id=session.session_id,
            episode_id=next((item.last_episode_id for item in session.capability_readiness if item.last_episode_id), None),
            metadata={'pack_id': session.chosen_pack_id, 'intent_key': session.intent.intent_key},
        )
        scenario_run = ScenarioRun(
            scenario=scenario,
            goal=run_record.request.user_goal,
            mode=scenario.mode,
            status=run_record.status,
            summary=diagnosis.summary,
            run_id=run_record.run_id,
            session_id=session.session_id,
            diagnosis=diagnosis,
            runtime_adjustments=runtime_adjustments,
            diagnostic_episode=diagnostic_episode,
            pending_issue_id=pending_issue.issue_id if pending_issue is not None else None,
            metadata={'pack_id': session.chosen_pack_id, 'intent_key': session.intent.intent_key},
        )
        saved_run = self.scenario_run_repository.save(scenario_run)

        session.scenario_id = scenario.scenario_id
        session.scenario_mode = scenario.mode
        session.probe_diagnosis = diagnosis
        session.runtime_adjustments = runtime_adjustments
        session.pending_issue_id = pending_issue.issue_id if pending_issue is not None else None
        session.updated_at_utc = datetime.now(timezone.utc)
        session.metadata['self_teach'] = {
            'scenario_run_id': saved_run.scenario_run_id,
            'diagnosis_category': diagnosis.category.value,
            'runtime_adjustment_count': len(runtime_adjustments),
            'pending_issue_id': pending_issue.issue_id if pending_issue is not None else '',
        }
        saved_session = self.task_outcome_recorder.record(session)
        self._update_dossier(run_record=run_record, saved_run=saved_run, saved_session=saved_session)
        return saved_run, saved_session

    def _update_dossier(self, *, run_record: RunRecord, saved_run: ScenarioRun, saved_session: AdaptiveSession) -> None:
        dossiers = self.dossier_repository.find_by_run(run_record.run_id)
        if not dossiers:
            return
        dossier = dossiers[0]
        dossier.scenario_run_id = saved_run.scenario_run_id
        dossier.probe_diagnosis = saved_run.diagnosis
        dossier.runtime_adjustments = list(saved_run.runtime_adjustments)
        dossier.pending_issue_id = saved_run.pending_issue_id
        dossier.metrics['scenario_id'] = saved_run.scenario.scenario_id
        dossier.metrics['scenario_mode'] = saved_run.mode.value
        dossier.metrics['runtime_adjustment_count'] = len(saved_run.runtime_adjustments)
        dossier.metrics['self_teach_summary'] = saved_run.summary
        dossier.next_action = saved_run.diagnosis.recommended_action if saved_run.diagnosis is not None else dossier.next_action
        dossier.metadata['self_teach'] = {
            'scenario_run_id': saved_run.scenario_run_id,
            'diagnosis_category': saved_run.diagnosis.category.value if saved_run.diagnosis is not None else '',
            'pending_issue_id': saved_run.pending_issue_id or '',
            'session_id': saved_session.session_id,
        }
        self.dossier_repository.save(dossier)
