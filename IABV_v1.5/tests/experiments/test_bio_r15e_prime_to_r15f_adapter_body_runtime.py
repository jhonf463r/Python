from __future__ import annotations

import json
import hashlib
import platform
import sys
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from tempfile import mkdtemp
from types import SimpleNamespace

from iabv_v15.domain.models import (
    AppConfig, EvaluationRoute, ExperimentDomain, InferenceRequest,
    IntentRouteDecision, SandboxExperiment, SandboxExperimentVerdict,
    TaskIntent, TaskRole,
    ToolCard,
)
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.self_teach.sandbox_experiment_service import SandboxExperimentService
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_validator import ToolValidator


BASE_COMMIT = '23f17bd2a1895fe12412f20884951cc0b5ccebfa'
GOAL = 'code bio r15d learned preference tooltask'
SOURCE_SUBJECT = 'general:code-bio-r15d-learned-preference-tooltask'
SANDBOX_SUBJECT = f'sandbox:{SOURCE_SUBJECT}'
SITE = 'sandbox:general'
TEST_COMMAND = r"$env:PYTHONPATH='<worktree>\IABV_v1.5\src'; & 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider 'IABV_v1.5\tests\experiments\test_bio_r15e_prime_to_r15f_adapter_body_runtime.py' -q -s"


class _SafeRecordingRunner:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def capture_response_from_app(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs, default=str)))
        return {
            'response_captured': True,
            'captured_text': '[BIO-R15E-PRIME-R15F-SYNTHETIC]',
            'capture_source': 'synthetic_runner',
            'metadata': {'synthetic_runner': True},
        }


class _FixedRouter:
    def build_decision_from_intent(self, *, request, intent):
        return IntentRouteDecision(detected_role=intent.detected_role, reason='BIO-R15E matched route fixture')


def _lab(root: Path):
    storage = ArtifactStorage(str(root / 'evolution'))
    repo = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), storage)
    lab = ExperimentLab(
        repository=repo,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer()),
    )
    return lab, repo, storage


def _assembler(root: Path, repo: ExperimentLabRepository, storage: ArtifactStorage) -> TaskContextAssembler:
    db = repo.db
    return TaskContextAssembler(
        episode_repository=EpisodeRepository(str(root / 'episodes'), db),
        knowledge_repository=KnowledgeRepository(db),
        run_repository=RunRepository(db),
        dossier_repository=ExecutionDossierRepository(db, storage),
        hidden_incident_repository=HiddenIncidentRepository(db, storage),
        site_policy_registry=SitePolicyRegistry(str(root / 'policies')),
        capability_repository=CapabilityRepository(db, storage),
        adaptive_session_repository=AdaptiveSessionRepository(db, storage),
        experiment_lab_repository=repo,
    )


def _tool_teach(root: Path, lab: ExperimentLab, runner: _SafeRecordingRunner):
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    records = ToolRecordRepository(db, storage)
    card_root = Path(__file__).resolve().parents[2] / 'data' / 'tool_teaching' / 'cards'
    for tool_id in ('chatgpt_web_assisted', 'chatgpt_installed', 'codex_installed'):
        persisted_card = ToolCard.model_validate(json.loads((card_root / f'{tool_id}.json').read_text(encoding='utf-8')))
        records.save_card(persisted_card)
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: runner)
    adapters = {'external_assistant': adapter}
    registry = ToolRegistry(records, adapters)
    learning = InteractionLearningService(records)
    validator = ToolValidator()
    service = ToolTeachService(
        registry=registry,
        memory=ToolMemory(records, learning),
        sandbox=ToolSandbox(validator),
        validator=validator,
        approval_policy=ToolApprovalPolicy(),
        rollback_manager=ToolRollbackManager(),
        adapters=adapters,
        workspace_root=str(root),
        interaction_learning_service=learning,
        mode_selector=InteractionModeSelector(registry, records),
        experiment_lab=lab,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=records, experiment_lab=lab),
    )
    return service, records, adapter


def _evolution_service(root: Path, tool_teach: ToolTeachService, records: ToolRecordRepository):
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'evolution'))
    pending = PendingIssueRepository(db, storage)
    packets = IncidentPacketService(
        dossier_repository=ExecutionDossierRepository(db, storage),
        hidden_incident_repository=HiddenIncidentRepository(db, storage),
        user_clue_repository=UserClueRepository(db, storage),
        workspace_root=str(root),
        pending_issue_repository=pending,
        tool_record_repository=records,
    )
    config = AppConfig(
        workspace_root=str(root), data_dir=str(root / 'data'), episodes_dir=str(root / 'episodes'),
        screenshots_dir=str(root / 'screenshots'), replay_annotations_dir=str(root / 'replay'),
        tool_teaching_dir=str(root / 'tool_teaching'), browser_profiles_dir=str(root / 'profiles'),
        browser_states_dir=str(root / 'browser_states'), browser_artifacts_dir=str(root / 'browser_artifacts'),
        site_policies_dir=str(root / 'policies'), payloads_dir=str(root / 'payloads'),
        models_dir=str(root / 'models'), logs_dir=str(root / 'logs'), evolution_dir=str(root / 'evolution'),
        sqlite_path=str(root / 'app.sqlite'), autonomous_external_launch=False,
    )
    return AutonomousEvolutionService(
        config=config, tool_teach_service=tool_teach, incident_packet_service=packets,
        pending_issue_repository=pending,
    )


def _instrument(tool_teach: ToolTeachService, adapter: ExternalAssistantToolAdapter) -> dict:
    observations = {'picks': [], 'refreshes': [], 'availability': [], 'adapter_runs': []}
    registry = tool_teach.registry
    original_pick = registry.pick_card_for_task
    original_refresh = registry.refresh_card
    original_available = adapter.is_available

    @wraps(original_refresh)
    def observed_refresh(card, *args, **kwargs):
        before = card
        result = original_refresh(card, *args, **kwargs)
        if before.tool_id in {'chatgpt_web_assisted', 'chatgpt_installed', 'codex_installed'}:
            observations['refreshes'].append({
                'tool_id': before.tool_id,
                'available_before': before.available,
                'available_after': result.available,
                'launch_mode': before.metadata.get('launch_mode', ''),
                'response_capture_mode': before.metadata.get('response_capture_mode', ''),
            })
        return result

    @wraps(original_pick)
    def observed_pick(task, *args, **kwargs):
        start = len(observations['refreshes'])
        result = original_pick(task, *args, **kwargs)
        task_meta = dict(task.metadata or {})
        observations['picks'].append({
            'input_task_id': task.task_id,
            'input_tool_id': task.tool_id,
            'preferred_assistant_kind': kwargs.get('preferred_assistant_kind', ''),
            'returned_card': None if result is None else {
                'tool_id': result.tool_id,
                'assistant_kind': result.metadata.get('assistant_kind', ''),
                'adapter_key': result.adapter_key,
                'available': result.available,
                'launch_mode': result.metadata.get('launch_mode', ''),
                'response_capture_mode': result.metadata.get('response_capture_mode', ''),
            },
            'task_metadata': {key: task_meta.get(key) for key in (
                'requested_assistant_kind', 'assistant_kind', 'actual_assistant_kind', 'config_signature',
                'lab_recommendation', 'synaptic_preferred_assistant_kind', 'comparison_scope_key', 'source_trace_ids',
            )},
            'refresh_events': observations['refreshes'][start:],
        })
        return result

    @wraps(original_available)
    def observed_available(card, *args, **kwargs):
        value = original_available(card, *args, **kwargs)
        observations['availability'].append({
            'tool_id': card.tool_id,
            'adapter_class': type(adapter).__name__,
            'adapter_key': card.adapter_key,
            'result': bool(value),
            'force': kwargs.get('force', False),
        })
        return value

    registry.refresh_card = observed_refresh
    registry.pick_card_for_task = observed_pick
    adapter.is_available = observed_available
    return observations


def _run_case(root: Path, *, verdict: SandboxExperimentVerdict, promote: bool, trace_id: str, runner: _SafeRecordingRunner) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    lab, _, storage = _lab(root)
    lab.record_outcome(
        domain=ExperimentDomain.CODE, objective=GOAL, subject_key=SANDBOX_SUBJECT,
        route=EvaluationRoute.LANGUAGE_UNDERSTANDING, candidate_label='chatgpt', success=True,
        observed_summary='matched prior baseline', precision=.72, robustness=.8, reuse_score=.4, user_progress=.2,
        metadata={'assistant_kind': 'chatgpt', 'config_signature': 'chatgpt-baseline', 'comparison_scope_key': SANDBOX_SUBJECT, 'trace_id': trace_id},
    )
    experiment = SandboxExperiment(
        subject_key=SOURCE_SUBJECT, sandbox_subject_key=SANDBOX_SUBJECT, domain=ExperimentDomain.CODE,
        hypothesis='BIO-R15E controlled sandbox outcome', baseline_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
        baseline_assistant_kind='chatgpt', baseline_config_signature='chatgpt-baseline',
        candidate_route=EvaluationRoute.CODE_AGENT, candidate_assistant_kind='codex',
        candidate_config_signature='codex-sandbox', verdict=verdict, status='observed',
        promote_to_primary=promote, evidence_strength=.82, supporting_run_ids=['bio-r15d-evidence-a'],
    )
    SandboxExperimentService(experiment_lab=lab)._record_sandbox_run(experiment=experiment)

    fresh_storage = ArtifactStorage(str(root / 'evolution'))
    fresh_repo = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), fresh_storage)
    recommendations = fresh_repo.list_recommendations(domain=ExperimentDomain.CODE.value, subject_key=SANDBOX_SUBJECT, limit=3)
    request = InferenceRequest(user_goal=GOAL, site_hint=SITE)
    intent = TaskIntent(intent_key='bio.r15e', title='BIO-R15E', detected_role=TaskRole.PROJECT_EVOLUTION, site_hint=SITE, summary=GOAL)
    assembler = _assembler(root, fresh_repo, fresh_storage)
    context = assembler.build(request, intent)
    orchestrator = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
    orchestrator.autonomy_governance_policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)
    orchestrator.unified_memory_layer = None
    orchestrator.role_router = _FixedRouter()
    orchestrator.context_assembler = assembler
    session = SimpleNamespace(
        session_id='bio-r15e-fresh-session', intent=intent, context=context, evidence_refs=[],
        capability_readiness=[], approval_checkpoints=[], status=SimpleNamespace(value='planned'), metadata={},
    )
    decision = orchestrator._build_decision_context(
        request=request, session=session, pack=SimpleNamespace(pack_id='bio-r15e', title='BIO-R15E'),
        assistant_guidance={'mode': 'need_codex_fix', 'prompt': 'matched technical consultation trigger'},
    )

    tool_teach, records, adapter = _tool_teach(root, lab, runner)
    observations = _instrument(tool_teach, adapter)
    evolution = _evolution_service(root, tool_teach, records)
    runtime_profile: list[dict] = []
    adapter_code = ExternalAssistantToolAdapter.run.__code__
    previous_profile = sys.getprofile()
    def profile(frame, event, arg):
        if frame.f_code is adapter_code and event in {'call', 'return'}:
            card_arg, task_arg = frame.f_locals.get('card'), frame.f_locals.get('task')
            runtime_profile.append({
                'event': event, 'monotonic_ns': time.monotonic_ns(),
                'utc': datetime.now(timezone.utc).isoformat(),
                'method': 'ExternalAssistantToolAdapter.run',
                'sandbox': bool(frame.f_locals.get('sandbox')),
                'task_id': getattr(task_arg, 'task_id', ''),
                'task_tool_id': getattr(task_arg, 'tool_id', ''),
                'card_tool_id': getattr(card_arg, 'tool_id', ''),
                'approval_decision': getattr(getattr(task_arg, 'approval_decision', None), 'value', ''),
            })
        if previous_profile is not None:
            previous_profile(frame, event, arg)
    sys.setprofile(profile)
    try:
        consultation = evolution.plan_or_execute(
            adaptive_payload={'probe_diagnosis': {'category': 'need_codex_fix', 'summary': 'matched technical trigger'}},
            user_goal=GOAL, source='bio-r15e-prime', decision_context=decision,
        )
    finally:
        sys.setprofile(previous_profile)
    stored_task = tool_teach.memory.repository.get_task(consultation['task_id'])
    result = next((item for item in tool_teach.memory.repository.list_results(task_id=consultation['task_id'], limit=10) if item.result_id == consultation['result_id']), None)
    selected_card = observations['picks'][-1]['returned_card'] if observations['picks'] else None
    selected_id = stored_task.tool_id if stored_task is not None else str(consultation.get('selected_tool_id') or '')
    selected_refresh = [item for item in observations['refreshes'] if item['tool_id'] == selected_id]
    selected_availability = [item for item in observations['availability'] if item['tool_id'] == selected_id]
    metadata = dict(stored_task.metadata or {}) if stored_task is not None else {}
    task_path = root / 'tool_teaching' / 'tasks' / f"{stored_task.task_id}.json"
    card_path = root / 'tool_teaching' / 'cards' / f"{selected_id}.json"
    # Record the sandbox adapter body reached by the real AEV path. The
    # fixture remains in place for the immediately following approval probe.
    task_json = stored_task.model_dump(mode='json')
    card_json = records.get_card(selected_id).model_dump(mode='json')
    fixture_metadata = {
        'base_commit': BASE_COMMIT,
        'source_r15e_branch': 'codex/bio-r15e-toolfcard-adapter-runtime-2026-09-22',
        'source_r15e_commit': '7093802c141e46cecba2cebbb44d6ab966538d7d',
        'r15e_harness_blob': '463c8b0b9bf00488948d4d3cf4ef8e2b9bf9e6e1',
        'fixture_root': str(root.resolve()),
        'sqlite_path': str((root / 'app.sqlite').resolve()),
        'task_json_path': str(task_path.resolve()),
        'toolcard_path': str(card_path.resolve()),
        'task': task_json,
        'toolcard': card_json,
        'adapter_class': type(adapter).__name__,
        'adapter_key': 'external_assistant',
        'adapter_config': {'runner_factory': '_SafeRecordingRunner'},
        'before_approval': {
            'approval_decision': stored_task.approval_decision.value,
            'task_status': stored_task.status.value,
            'result_state': result.execution_state.state if result else '',
            'approval_required': bool(stored_task.metadata.get('approval_required')),
        },
        'r15e_prime_profile': runtime_profile,
        'runner_calls_so_far': runner.calls,
        'sha256_task_json': hashlib.sha256(task_path.read_bytes()).hexdigest() if task_path.exists() else '',
        'sha256_sqlite': hashlib.sha256((root / 'app.sqlite').read_bytes()).hexdigest(),
    }
    (root / 'fixture.json').write_text(json.dumps(fixture_metadata, indent=2, sort_keys=True), encoding='utf-8')
    return {
        'experiment': {'verdict': verdict.value, 'promote_to_primary': promote, 'trace_id': trace_id},
        'recommendation': {
            'assistant': recommendations[0].recommended_assistant_kind,
            'route': recommendations[0].recommended_route.value,
            'config_signature': recommendations[0].recommended_config_signature,
            'score': recommendations[0].score,
        },
        'insight': {
            'subject_key': context.experiment_insights[0]['subject_key'],
            'recommended_assistant_kind': context.experiment_insights[0]['recommended_assistant_kind'],
            'recommended_route': context.experiment_insights[0]['recommended_route'],
            'recommended_config_signature': context.experiment_insights[0]['recommended_config_signature'],
        },
        'decision': {
            'preferred_assistant_kind': decision.metadata.get('preferred_assistant_kind', ''),
            'governance_assistant_kind': decision.governance.get('assistant_kind', ''),
            'should_consult': decision.governance.get('should_consult'),
        },
        'consultation': {
            'requested_assistant_kind': consultation.get('requested_assistant_kind', ''),
            'selected_tool_id': consultation.get('selected_tool_id', ''),
            'decision_source': consultation.get('decision_source', ''),
            'status': consultation.get('status', ''),
            'execution_state': result.execution_state.state if result is not None else '',
            'validation_status': result.validation_status.value if result is not None else '',
            'success': result.success if result is not None else None,
            'error': result.error_message if result is not None else '',
            'approval_decision': result.execution_state.approval_decision.value if result is not None else '',
            'terminal_detail': result.execution_state.detail if result is not None else '',
        },
        'task': None if stored_task is None else {
            'task_id': stored_task.task_id,
            'tool_id': stored_task.tool_id,
            'requested_assistant_kind': metadata.get('requested_assistant_kind', ''),
            'assistant_kind': metadata.get('assistant_kind', ''),
            'actual_assistant_kind': metadata.get('actual_assistant_kind', ''),
            'config_signature': metadata.get('config_signature', ''),
            'lab_recommendation': metadata.get('lab_recommendation', {}),
            'synaptic_preferred_assistant_kind': metadata.get('synaptic_preferred_assistant_kind', ''),
            'comparison_scope_key': metadata.get('comparison_scope_key', ''),
            'source_trace_ids': metadata.get('source_trace_ids', []),
        },
        'toolcard': None if selected_card is None else {
            **selected_card,
            'available_before_first_refresh': selected_refresh[0]['available_before'] if selected_refresh else None,
            'available_after_last_refresh': selected_refresh[-1]['available_after'] if selected_refresh else selected_card['available'],
        },
        'availability_observations': selected_availability,
        'relevant_toolcard_runtime': {
            tool_id: {
                'declared_available_before_refresh': next((item['available_before'] for item in observations['refreshes'] if item['tool_id'] == tool_id), None),
                'refreshed_available': next((item['available_after'] for item in reversed(observations['refreshes']) if item['tool_id'] == tool_id), None),
                'adapter_key': 'external_assistant',
                'adapter_availability_results': [item['result'] for item in observations['availability'] if item['tool_id'] == tool_id],
            }
            for tool_id in ('chatgpt_web_assisted', 'chatgpt_installed', 'codex_installed')
        },
        'pick_observations': [{
            'input_task_id': item['input_task_id'],
            'input_tool_id': item['input_tool_id'],
            'preferred_assistant_kind': item['preferred_assistant_kind'],
            'returned_tool_id': (item['returned_card'] or {}).get('tool_id', ''),
            'returned_available': (item['returned_card'] or {}).get('available'),
        } for item in observations['picks']],
        'fixture': fixture_metadata,
        'adapter': {
            'class': type(adapter).__name__,
            'key': 'external_assistant',
            'present': 'external_assistant' in tool_teach.adapters,
            'run_observations': runtime_profile,
            'live_run_intercepted': False,
        },
    }


def _stable(case: dict) -> dict:
    return {
        'recommendation': case['recommendation'],
        'decision': case['decision'],
        'requested_assistant_kind': case['consultation']['requested_assistant_kind'],
        'task_tool_id': case['task']['tool_id'] if case['task'] else '',
        'toolcard_tool_id': (case['toolcard'] or {}).get('tool_id', ''),
    }


def test_bio_r15e_learned_preference_to_real_toolcard_adapter_runtime() -> None:
    root = Path(__file__).resolve().parents[2] / 'docs' / 'history' / 'CHAT-ARCH' / 'BIO-R15E-PRIME-RUNTIME-2026-09-22'
    saved_fixture = root / 'control' / 'fixture.json'
    if saved_fixture.exists():
        # Read-back only: the preserved R15E′ runtime is never repeated.
        fixture = json.loads(saved_fixture.read_text(encoding='utf-8'))
        report = {
            'mode': 'report-only; fixture read-back; no experiment re-execution',
            'fixture': fixture,
            'r15f': 'NOT_RUN: ToolTask.status is pending, not waiting_approval; no task mutation or approved=True call permitted by protocol.',
            'first_broken_edge': 'sandbox completion → persisted ToolTask status waiting_approval',
            'causal_classification': 'OPEN',
            'negative_knowledge': {
                'adapter non-sandbox body': 'NOT_PROVEN',
                'runner invocation': 'NOT_PROVEN; safe runner call count is zero',
                'external launch, prompt delivery, response, effect, learning, development, evolution': 'NOT_PROVEN',
            },
        }
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
        assert fixture['before_approval']['approval_decision'] == 'pending'
        assert fixture['before_approval']['task_status'] == 'pending'
        return
    root.mkdir(parents=True, exist_ok=False)
    runner = _SafeRecordingRunner()
    control = _run_case(root / 'control', verdict=SandboxExperimentVerdict.FAILED, promote=False, trace_id='trace-control', runner=runner)
    assert control['insight']['recommended_assistant_kind'] == 'chatgpt'
    assert control['decision']['preferred_assistant_kind'] == 'chatgpt'
    assert control['fixture']['task']['approval_decision'] == 'pending'
    assert control['fixture']['task']['status'] == 'pending'
    assert control['consultation']['execution_state'] == 'waiting_approval'
    assert not runner.calls
    print(json.dumps({'runtime': {'base_commit': BASE_COMMIT, 'python': sys.version, 'platform': platform.platform(), 'test_command': TEST_COMMAND}, 'control': control, 'r15f': 'NOT_RUN: persisted task status is pending, not waiting_approval; no manual task-state mutation allowed', 'causal_result': 'OPEN', 'first_broken_edge': 'sandbox completion → persisted ToolTask status waiting_approval', 'fixture_root': str(root / 'control'), 'safety': {'runner_calls': 0, 'external_effects': False}}, sort_keys=True, default=str))
