from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    ExecutionState,
    ExecutionPlaybook,
    EvaluationRoute,
    ExperimentDomain,
    GoalContext,
    PlaybookStep,
    PostconditionExpectation,
    PostconditionObservation,
    RunRecord,
    RunStatus,
    TaskRole,
    TaskContext,
    TaskIntent,
    TaskOutcome,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.execution_playbook_service import (
    ExecutionPlaybookService,
    OperationalExecutorResult,
)
from iabv_v15.services.adaptive.postcondition_verification import PostconditionVerificationService
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.tools.tool_operational_executor import ToolOperationalExecutor
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector


class SequenceObserver:
    def __init__(self, observations: list[PostconditionObservation]) -> None:
        self.observations = observations
        self.calls: list[str] = []

    def observe(self, expectation: PostconditionExpectation, *, execution_id: str) -> PostconditionObservation:
        self.calls.append(execution_id)
        item = self.observations.pop(0)
        return item.model_copy(deep=True)


class ClaimingExecutor:
    name = "claims_success"

    def supports(self, session: AdaptiveSession) -> bool:
        return True

    def describe(self, session: AdaptiveSession) -> str:
        return "ready"

    def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
        return OperationalExecutorResult(True, RunStatus.SUCCESS, "executor claims success")


def observation(satisfied: bool, *, matches: list[dict] | None = None, caused_by: str | None = None) -> PostconditionObservation:
    return PostconditionObservation(
        source="independent_test_source",
        observed_at_utc=datetime.now(timezone.utc),
        satisfied=satisfied,
        matches=list(matches or ([{"title": "Target", "pid": 7}] if satisfied else [])),
        caused_by_execution_id=caused_by,
        evidence_ref="source-evidence",
    )


def operational_session() -> AdaptiveSession:
    return AdaptiveSession(
        user_goal="Open target window",
        intent=TaskIntent(intent_key="tool.use"),
        chosen_pack_id="test.pack",
        status=AdaptiveSessionStatus.READY_TO_EXECUTE,
        playbook=ExecutionPlaybook(
            goal="Open target window",
            pack_id="test.pack",
            status=AdaptiveSessionStatus.READY_TO_EXECUTE,
            steps=[PlaybookStep(
                phase_key="execute",
                title="Open target",
                description="Execute the operation",
                executable=True,
                capability_id="visible_desktop_execution",
                postcondition=PostconditionExpectation(kind="window_present", title="Target"),
            )],
        ),
        context=TaskContext(goal_context=GoalContext(
            task={"objective_id": "task-objective-1"},
            project={"objective_id": "project-objective-1"},
            active_node_id="active-node-1",
        )),
    )


def execute_with(observations: list[PostconditionObservation]) -> tuple[AdaptiveSession, SequenceObserver]:
    observer = SequenceObserver(observations)
    service = ExecutionPlaybookService(
        executor=ClaimingExecutor(),
        postcondition_verifier=PostconditionVerificationService(observer),
    )
    return service.execute(operational_session()), observer


def test_a1_executor_success_without_postcondition_is_not_verified() -> None:
    updated, _ = execute_with([observation(False), observation(False)])
    assert updated.outcome is not None
    assert updated.outcome.postcondition_verification.verdict == "not_verified"
    assert updated.outcome.status == RunStatus.PARTIAL


def test_a2_preexisting_state_is_not_a_new_attributable_transition() -> None:
    updated, _ = execute_with([observation(True), observation(True)])
    assert updated.outcome.postcondition_verification.verdict == "not_verified"
    assert updated.outcome.postcondition_verification.attribution == "not_attributable"


def test_a3_post_action_change_without_correlation_is_temporal_only() -> None:
    updated, _ = execute_with([observation(False), observation(True)])
    verification = updated.outcome.postcondition_verification
    assert verification.verdict == "observation_only"
    assert verification.attribution == "temporally_associated"
    assert updated.outcome.status == RunStatus.PARTIAL


def test_a4_multiple_matching_actors_are_ambiguous() -> None:
    updated, _ = execute_with([
        observation(False),
        observation(True, matches=[{"title": "Target", "pid": 7}, {"title": "Target", "pid": 8}]),
    ])
    verification = updated.outcome.postcondition_verification
    assert verification.verdict == "ambiguous"
    assert verification.attribution == "ambiguous_due_to_competing_causes"


def test_a5_verifier_reads_independent_source_not_executor_status() -> None:
    observer = SequenceObserver([observation(False), observation(False)])

    class OrderingExecutor(ClaimingExecutor):
        def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
            assert len(observer.calls) == 1, "baseline observation must precede the action"
            return super().execute(session)

    service = ExecutionPlaybookService(
        executor=OrderingExecutor(),
        postcondition_verifier=PostconditionVerificationService(observer),
    )
    updated = service.execute(operational_session())
    assert len(observer.calls) == 2
    assert observer.calls[0] == observer.calls[1] == updated.metadata["operational_execution_id"]
    assert updated.outcome.postcondition_verification.observation.source == "independent_test_source"
    assert updated.outcome.postcondition_verification.verdict == "not_verified"


def test_a6_exact_task_marker_in_generic_observation_field_is_directly_attributable() -> None:
    started = datetime.now(timezone.utc)
    expectation = PostconditionExpectation(
        kind="window_present",
        title="Target",
        correlation_id="nonce-1",
        correlation_field="resource_key",
    )
    observer = SequenceObserver([
        PostconditionObservation(
            source="independent_test_source",
            observed_at_utc=started,
            satisfied=False,
            matches=[],
            evidence_ref="baseline-source-ref",
        ),
        PostconditionObservation(
            source="independent_test_source",
            observed_at_utc=started + timedelta(milliseconds=1),
            satisfied=True,
            matches=[{"resource_key": "nonce-1", "object_id": "observed-1"}],
            evidence_ref="post-source-ref",
        ),
    ])
    verifier = PostconditionVerificationService(observer)
    baseline = verifier.capture_baseline(expectation, execution_id="exec-6")
    verification = verifier.verify(
        execution_id="exec-6",
        expectation=expectation,
        baseline=baseline,
        causal_correlation={
            "task_id": "task-6",
            "action_ids": ["action-6"],
            "correlation_id": "nonce-1",
            "correlation_field": "resource_key",
        },
    )

    assert verification.verdict == "verified"
    assert verification.attribution == "directly_attributable"
    assert verification.observation.caused_by_execution_id is None
    assert "baseline-source-ref" in verification.evidence_refs
    assert "post-source-ref" in verification.evidence_refs
    assert any(ref.startswith("causal-correlation:task-6:action-6:resource_key:nonce-1") for ref in verification.evidence_refs)


def test_a7_temporal_observation_without_matching_task_correlation_stays_unverified() -> None:
    started = datetime.now(timezone.utc)
    expectation = PostconditionExpectation(
        kind="window_present",
        title="Target",
        correlation_id="nonce-7",
        correlation_field="resource_key",
    )
    observer = SequenceObserver([
        PostconditionObservation(source="independent_test_source", observed_at_utc=started, satisfied=False),
        PostconditionObservation(
            source="independent_test_source",
            observed_at_utc=started + timedelta(milliseconds=1),
            satisfied=True,
            matches=[{"resource_key": "other-nonce"}],
        ),
    ])
    verifier = PostconditionVerificationService(observer)
    baseline = verifier.capture_baseline(expectation, execution_id="exec-7")
    verification = verifier.verify(
        execution_id="exec-7",
        expectation=expectation,
        baseline=baseline,
        causal_correlation={
            "task_id": "task-7",
            "action_ids": ["action-7"],
            "correlation_id": "nonce-7",
            "correlation_field": "resource_key",
        },
    )
    assert verification.verdict == "observation_only"
    assert verification.attribution == "temporally_associated"


def test_a8_multiple_observed_matches_remain_ambiguous_even_if_one_has_marker() -> None:
    started = datetime.now(timezone.utc)
    expectation = PostconditionExpectation(
        kind="window_present",
        title="Target",
        correlation_id="nonce-8",
        correlation_field="resource_key",
    )
    observer = SequenceObserver([
        PostconditionObservation(source="independent_test_source", observed_at_utc=started, satisfied=False),
        PostconditionObservation(
            source="independent_test_source",
            observed_at_utc=started + timedelta(milliseconds=1),
            satisfied=True,
            matches=[{"resource_key": "nonce-8"}, {"resource_key": "unrelated"}],
        ),
    ])
    verifier = PostconditionVerificationService(observer)
    baseline = verifier.capture_baseline(expectation, execution_id="exec-8")
    verification = verifier.verify(
        execution_id="exec-8",
        expectation=expectation,
        baseline=baseline,
        causal_correlation={
            "task_id": "task-8",
            "action_ids": ["action-8"],
            "correlation_id": "nonce-8",
            "correlation_field": "resource_key",
        },
    )
    assert verification.verdict == "ambiguous"
    assert verification.attribution == "ambiguous_due_to_competing_causes"


def test_a9_tool_executor_manifest_uses_the_task_action_identity() -> None:
    marker = "nonce-9"
    expectation = PostconditionExpectation(
        kind="window_present",
        title="Target",
        correlation_id=marker,
        correlation_field="title",
    )
    session = operational_session()
    session.chosen_pack_id = "tools.desktop_human_runner"
    session.playbook.steps[0].postcondition = expectation
    task = ToolTask(
        task_id="task-9",
        tool_id="any-tool-id",
        title="Produce correlated effect",
        objective="Produce correlated effect",
        actions=[ToolAction(
            action_id="action-9",
            action_type=ToolActionType.LAUNCH_APP,
            label="Launch",
            correlation_id=marker,
        )],
    )

    class FakeRegistry:
        def get_card(self, tool_id):
            return SimpleNamespace(tool_id=tool_id, title="Fake tool", capabilities=[])

        def pick_card_for_task(self, task):
            return SimpleNamespace(adapter_key="adapter")

    class FakeAdapter:
        def is_available(self, card):
            return True

    class FakeToolTeachService:
        registry = FakeRegistry()
        adapters = {"adapter": FakeAdapter()}

        def build_task_for_session(self, session):
            return task

        def execute_task(self, task, *, approved):
            return SimpleNamespace(
                execution_state=SimpleNamespace(state="executed", detail="", executor_name="adapter"),
                tool_id=task.tool_id,
                task_id=task.task_id,
                tool_type=SimpleNamespace(value="custom"),
                validation_status=SimpleNamespace(value="approved"),
                result_id="result-9",
                rollback_state=None,
                success=True,
                output_text="",
                error_message="",
                metadata={},
            )

    result = ToolOperationalExecutor(FakeToolTeachService()).execute(session)
    assert result.metadata["causal_correlation"] == {
        "task_id": "task-9",
        "action_ids": ["action-9"],
        "correlation_id": marker,
        "correlation_field": "title",
    }


def test_a10_execution_playbook_forwards_correlation_to_independent_verifier() -> None:
    started = datetime.now(timezone.utc)
    marker = "nonce-10"
    session = operational_session()
    session.playbook.steps[0].postcondition = PostconditionExpectation(
        kind="window_present",
        title=marker,
        correlation_id=marker,
        correlation_field="title",
    )
    observer = SequenceObserver([
        PostconditionObservation(source="independent_test_source", observed_at_utc=started, satisfied=False),
        PostconditionObservation(
            source="independent_test_source",
            observed_at_utc=started + timedelta(milliseconds=1),
            satisfied=True,
            matches=[{"title": marker}],
        ),
    ])

    class ManifestExecutor(ClaimingExecutor):
        def execute(self, session: AdaptiveSession) -> OperationalExecutorResult:
            return OperationalExecutorResult(
                True,
                RunStatus.SUCCESS,
                "executor claims success",
                metadata={
                    "causal_correlation": {
                        "task_id": "task-10",
                        "action_ids": ["action-10"],
                        "correlation_id": marker,
                        "correlation_field": "title",
                    }
                },
            )

    updated = ExecutionPlaybookService(
        executor=ManifestExecutor(),
        postcondition_verifier=PostconditionVerificationService(observer),
    ).execute(session)
    assert updated.outcome.postcondition_verification.verdict == "verified"
    assert updated.outcome.postcondition_verification.attribution == "directly_attributable"
    assert updated.outcome.postcondition_verification.observation.caused_by_execution_id is None


class FakeExperimentRepository:
    def __init__(self) -> None:
        self.runs: dict[str, object] = {}

    def find_operational_run(self, *, execution_id: str):
        return self.runs.get(execution_id)


class FakeExperimentLab:
    def __init__(self) -> None:
        self.repository = FakeExperimentRepository()
        self.calls: list[dict] = []

    def record_outcome(self, **kwargs):
        self.calls.append(kwargs)
        self.repository.runs[kwargs["metadata"]["operational_execution_id"]] = SimpleNamespace(run_id=kwargs["metadata"]["operational_execution_id"])
        return SimpleNamespace(run_id=kwargs["candidate_id"]), SimpleNamespace()


def make_recorder(lab: FakeExperimentLab) -> TaskOutcomeRecorder:
    return TaskOutcomeRecorder(
        adaptive_session_repository=SimpleNamespace(save=lambda session: session),
        capability_repository=SimpleNamespace(save_many=lambda items: None),
        approval_checkpoint_repository=SimpleNamespace(save_many=lambda items: None),
        experiment_lab=lab,
    )


def real_lab(root) -> ExperimentLab:
    repository = ExperimentLabRepository(
        AppDatabase(str(root / "app.sqlite")),
        ArtifactStorage(str(root / "evolution")),
    )
    return ExperimentLab(
        repository=repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer()),
    )


def operational_tool_metadata() -> dict:
    return {
        "tool_id": "desktop_human_runner",
        "tool_label": "Desktop human runner",
        "tool_type": "custom",
        "adapter_key": "desktop_human",
        "tool_task_id": "tool-task-1",
        "tool_result_id": "tool-result-1",
        "required_capability_id": "visible_desktop_execution",
        "required_action_types": ["launch_app"],
        "tool_capabilities": ["launch_app", "focus_window", "screenshot"],
        "assistant_kind": "iabv_runtime",
        "assistant_configuration": {
            "planning_mode": "with_plan",
            "tools_mode": "with_tools",
            "assistant_mode": "general",
            "origin_mode": "external",
            "metadata": {"tool_id": "desktop_human_runner", "assistant_kind": "iabv_runtime"},
        },
        "config_signature": "with_plan|without_files|normal|short|with_tools|without_browser|general|external",
        # ToolTeachService's trace classifier reports FALLBACK for this family,
        # rather than incorrectly labelling the desktop realization LOCAL.
        "route": "fallback",
        "comparison_scope_key": "site:open-target-window",
    }


def directly_verified_outcome(execution_id: str = "exec-1", *, metadata: dict | None = None) -> TaskOutcome:
    verifier = PostconditionVerificationService(
        SequenceObserver([
            observation(False),
            observation(True, caused_by=execution_id),
        ])
    )
    baseline = verifier.capture_baseline(PostconditionExpectation(kind="window_present", title="Target"), execution_id=execution_id)
    verification = verifier.verify(
        execution_id=execution_id,
        expectation=PostconditionExpectation(kind="window_present", title="Target"),
        baseline=baseline,
    )
    return TaskOutcome(status=RunStatus.SUCCESS, postcondition_verification=verification, metadata=dict(metadata or {}))


def test_b1_verified_operational_outcome_reaches_experiment_lab_with_provenance(tmp_path) -> None:
    lab = real_lab(tmp_path)
    session = operational_session()
    session.outcome = directly_verified_outcome(metadata=operational_tool_metadata())
    make_recorder(lab).record(session)
    runs = lab.repository.list_runs(
        domain=ExperimentDomain.CODE.value,
        subject_key="site:open-target-window",
        limit=5,
    )
    assert len(runs) == 1
    run = runs[0]
    assert run.success is True
    assert run.candidate_id == "desktop_human_runner"
    assert run.candidate_label == "Desktop human runner"
    assert run.assistant_kind == "iabv_runtime"
    assert run.route == EvaluationRoute.FALLBACK
    assert run.expected_summary == "window_present:Target"
    assert run.observed_summary == "window_present:Target observed=True"
    assert run.evidence_refs == session.outcome.postcondition_verification.evidence_refs
    assert run.metadata["operational_execution_id"] == "exec-1"
    assert run.metadata["tool_id"] == run.candidate_id
    assert run.metadata["adapter_key"] == "desktop_human"
    assert run.metadata["capability_id"] == "visible_desktop_execution"
    assert run.metadata["required_action_types"] == ["launch_app"]
    assert run.metadata["tool_capabilities"] == ["launch_app", "focus_window", "screenshot"]
    assert run.metadata["tool_task_id"] == "tool-task-1"
    assert run.metadata["tool_result_id"] == "tool-result-1"
    assert run.assistant_configuration.metadata["tool_id"] == "desktop_human_runner"
    assert run.config_signature == operational_tool_metadata()["config_signature"]
    assert run.comparison_scope_key == "site:open-target-window"
    assert run.subject_key == "site:open-target-window"


def test_b1b_semantic_operational_experience_uses_existing_reusable_subject_hierarchy(tmp_path) -> None:
    lab = real_lab(tmp_path)
    session = operational_session()
    session.outcome = directly_verified_outcome(metadata=operational_tool_metadata())
    make_recorder(lab).record(session)
    for subject_key in ("site:open-target-window", "task-objective-1", "general"):
        runs = lab.repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key=subject_key, limit=5)
        assert len(runs) == 1
        assert runs[0].candidate_id == "desktop_human_runner"
        assert runs[0].metadata["operational_execution_id"] == "exec-1"


def test_b1c_real_tool_task_semantics_survive_executor_outcome_and_lab_persistence(tmp_path) -> None:
    marker = "nonce-tool-task-1"
    card = ToolCard(
        tool_id="desktop_human_runner",
        title="Desktop human runner",
        tool_type=ToolType.CUSTOM,
        adapter_key="desktop_human",
        capabilities=["launch_app", "focus_window", "screenshot"],
        metadata={"assistant_kind": "iabv_runtime"},
    )
    task = ToolTask(
        task_id="tool-task-1",
        tool_id=card.tool_id,
        title="Open target",
        objective="Open target window",
        actions=[ToolAction(
            action_id="tool-action-1",
            action_type=ToolActionType.LAUNCH_APP,
            label="Open target",
            correlation_id=marker,
        )],
        metadata={
            "actual_assistant_kind": "iabv_runtime",
            "assistant_configuration": operational_tool_metadata()["assistant_configuration"],
            "config_signature": operational_tool_metadata()["config_signature"],
            "comparison_scope_key": "site:open-target-window",
        },
    )

    class FakeAdapter:
        def is_available(self, _card):
            return True

    class FakeRegistry:
        def get_card(self, tool_id):
            return card if tool_id == card.tool_id else None

        def pick_card_for_task(self, _task, **_kwargs):
            return card

    class FakeToolTeachService:
        registry = FakeRegistry()
        adapters = {"desktop_human": FakeAdapter()}

        def build_task_for_session(self, _session):
            return task

        def execute_task(self, actual_task, *, approved=False):
            trace = {
                "route": "fallback",
                "actual_assistant_kind": "iabv_runtime",
                "assistant_configuration": task.metadata["assistant_configuration"],
                "config_signature": task.metadata["config_signature"],
                "comparison_scope_key": task.metadata["comparison_scope_key"],
            }
            return ToolResult(
                task_id=actual_task.task_id,
                tool_id=card.tool_id,
                tool_type=card.tool_type,
                success=True,
                validation_status=ToolValidationStatus.APPROVED,
                execution_state=ExecutionState(state="executed", executor_name=card.adapter_key),
                metadata={
                    "assistant_kind": "iabv_runtime",
                    "assistant_configuration": task.metadata["assistant_configuration"],
                    "config_signature": task.metadata["config_signature"],
                    "ia_trace_entry": trace,
                },
            )

    session = operational_session()
    session.intent.detected_role = TaskRole.TOOL_USE
    session.playbook.steps[0].postcondition = PostconditionExpectation(
        kind="window_present",
        title="Target",
        correlation_id=marker,
        correlation_field="title",
    )
    session.playbook.steps[0].capability_id = "visible_desktop_execution"
    session.outcome = None
    observer = SequenceObserver([
        PostconditionObservation(source="independent_test_source", satisfied=False),
        PostconditionObservation(
            source="independent_test_source",
            satisfied=True,
            matches=[{"title": marker, "pid": 7}],
            evidence_ref="independent-post-observation",
        ),
    ])
    executed = ExecutionPlaybookService(
        executor=ToolOperationalExecutor(FakeToolTeachService()),
        postcondition_verifier=PostconditionVerificationService(observer),
    ).execute(session)
    assert executed.outcome is not None
    assert executed.outcome.postcondition_verification.verdict == "verified"
    assert executed.outcome.postcondition_verification.attribution == "directly_attributable"
    assert executed.outcome.metadata["tool_id"] == "desktop_human_runner"
    assert executed.outcome.metadata["adapter_key"] == "desktop_human"
    assert executed.outcome.metadata["tool_task_id"] == "tool-task-1"
    assert executed.outcome.metadata["tool_result_id"]

    lab = real_lab(tmp_path)
    make_recorder(lab).record(executed)
    runs = lab.repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key="site:open-target-window", limit=5)
    assert len(runs) == 1
    run = runs[0]
    assert run.candidate_id == "desktop_human_runner"
    assert run.metadata["capability_id"] == "visible_desktop_execution"
    assert run.metadata["adapter_key"] == "desktop_human"
    assert run.metadata["operational_execution_id"] == executed.outcome.postcondition_verification.execution_id
    assert "independent-post-observation" in run.evidence_refs


def test_b5_correlation_verified_outcome_reaches_experiment_lab_without_observer_claim(tmp_path) -> None:
    lab = real_lab(tmp_path)
    session = operational_session()
    started = datetime.now(timezone.utc)
    expectation = PostconditionExpectation(
        kind="window_present",
        title="Target",
        correlation_id="nonce-5",
        correlation_field="title",
    )
    verifier = PostconditionVerificationService(SequenceObserver([
        PostconditionObservation(source="independent_test_source", observed_at_utc=started, satisfied=False),
        PostconditionObservation(
            source="independent_test_source",
            observed_at_utc=started + timedelta(milliseconds=1),
            satisfied=True,
            matches=[{"title": "nonce-5", "pid": 5}],
            evidence_ref="independent-post-observation",
        ),
    ]))
    baseline = verifier.capture_baseline(expectation, execution_id="exec-5")
    session.outcome = TaskOutcome(
        status=RunStatus.SUCCESS,
        metadata=operational_tool_metadata(),
        postcondition_verification=verifier.verify(
            execution_id="exec-5",
            expectation=expectation,
            baseline=baseline,
            causal_correlation={
                "task_id": "task-5",
                "action_ids": ["action-5"],
                "correlation_id": "nonce-5",
                "correlation_field": "title",
            },
        ),
    )
    assert session.outcome.postcondition_verification.observation.caused_by_execution_id is None
    make_recorder(lab).record(session)
    runs = lab.repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key="site:open-target-window", limit=5)
    assert len(runs) == 1
    assert runs[0].candidate_id == "desktop_human_runner"
    assert runs[0].success is True
    assert "independent-post-observation" in runs[0].evidence_refs
    assert runs[0].metadata["operational_execution_id"] == "exec-5"


def test_b2_unverified_outcome_does_not_train_success() -> None:
    lab = FakeExperimentLab()
    session = operational_session()
    session.outcome = TaskOutcome(
        status=RunStatus.PARTIAL,
        postcondition_verification=PostconditionVerificationService(
            SequenceObserver([observation(False), observation(False)])
        ).verify(
            execution_id="exec-2",
            expectation=PostconditionExpectation(kind="window_present", title="Target"),
            baseline=observation(False),
        ),
    )
    make_recorder(lab).record(session)
    assert lab.calls == []


def test_b2b_verified_outcome_without_tool_identity_is_not_selectable() -> None:
    lab = FakeExperimentLab()
    session = operational_session()
    session.outcome = directly_verified_outcome()
    make_recorder(lab).record(session)
    assert lab.calls == []


def test_b3_repeated_record_of_same_execution_is_deduplicated(tmp_path) -> None:
    lab = real_lab(tmp_path)
    session = operational_session()
    session.outcome = directly_verified_outcome("exec-3", metadata=operational_tool_metadata())
    recorder = make_recorder(lab)
    recorder.record(session)
    recorder.record(session)
    assert len(lab.repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key="site:open-target-window", limit=10)) == 1
    assert len(lab.repository.list_runs(domain=ExperimentDomain.CODE.value, subject_key="task-objective-1", limit=10)) == 1
    assert session.metadata["operational_learning_deduplicated"] == "exec-3"


def test_b4_inference_run_record_path_remains_separate(monkeypatch) -> None:
    lab = FakeExperimentLab()
    recorder = make_recorder(lab)
    seen = []
    monkeypatch.setattr(recorder, "_record_learning", lambda *, session, run_record: seen.append(run_record) or session)
    run = SimpleNamespace(run_id="inference-1")
    recorder.record(operational_session(), run_record=run)
    assert seen == [run]
    assert lab.calls == []
