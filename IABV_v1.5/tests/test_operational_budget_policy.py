from __future__ import annotations

from iabv_v15.services.adaptive.autonomy_governance_policy import (
    AutonomyGovernancePolicy,
    apply_operational_budget_calibration_to_runtime_tuning,
    record_operational_budget_experiment,
    summarize_operational_budget_calibration,
)
from iabv_v15.domain.models import RuntimeTuningProfile


class _RunRepo:
    def __init__(self) -> None:
        self.runs = []

    def save_run(self, run):
        self.runs.append(run)
        return run


class _RuntimeTuningRepo:
    def __init__(self) -> None:
        self.profile: RuntimeTuningProfile | None = None
        self.saved: list[RuntimeTuningProfile] = []

    def get(self, scope_key: str = 'global') -> RuntimeTuningProfile | None:
        return self.profile

    def save(self, profile: RuntimeTuningProfile) -> RuntimeTuningProfile:
        self.profile = profile
        self.saved.append(profile)
        return profile


def test_operational_budget_defers_background_work_while_user_waits() -> None:
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='autonomy_dock_refresh',
        source='timer',
        user_waiting=True,
        query_pending=True,
        rss_mb=300.0,
        idle_seconds=300.0,
    )

    assert budget['allowed'] is False
    assert budget['decision'] == 'defer'
    assert budget['reason'] == 'visible_query_wait_active'
    assert budget['decision_source'] == 'autonomy_governance_policy.operational_budget'


def test_operational_budget_allows_foreground_response_under_pressure() -> None:
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='foreground_response',
        source='chat',
        user_waiting=True,
        query_pending=True,
        rss_mb=7500.0,
        recent_stall_ms=9000.0,
        idle_seconds=0.0,
    )

    assert budget['allowed'] is True
    assert budget['decision'] == 'allow'
    assert budget['reason'] == 'budget_available'


def test_operational_budget_defers_routine_refresh_under_rss_pressure() -> None:
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='ui_refresh',
        source='timer',
        rss_mb=3200.0,
        idle_seconds=300.0,
    )

    assert budget['allowed'] is False
    assert budget['reason'] == 'resource_pressure_high'
    assert budget['evidence']['rss_mb'] == 3200.0


def test_operational_budget_requires_rest_window_for_timer_refreshes() -> None:
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='autonomy_dock_refresh',
        source='timer',
        rss_mb=250.0,
        idle_seconds=10.0,
    )

    assert budget['allowed'] is False
    assert budget['decision'] == 'defer'
    assert budget['reason'] == 'rest_window_not_reached'
    assert budget['recommended_mode'] == 'wait_for_idle'
    assert budget['defer_seconds'] == 110.0


def test_operational_budget_defers_background_while_ui_route_stabilizes() -> None:
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='metacognition',
        source='startup_evolution',
        rss_mb=250.0,
        idle_seconds=300.0,
        ui_route_stability_age_s=25.0,
        active_route='control',
    )

    assert budget['allowed'] is False
    assert budget['decision'] == 'defer'
    assert budget['reason'] == 'ui_route_stabilizing:control'
    assert budget['recommended_mode'] == 'wait_for_ui_route_stability'
    assert budget['evidence']['active_route'] == 'control'
    assert budget['evidence']['ui_route_stability_age_s'] == 25.0


def test_operational_budget_defers_metacognition_promotion_during_route_stability() -> None:
    """Post-chat OSES/PortableContext promotion is background metabolic work."""
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='metacognition_promotion',
        source='interaction_resolution',
        rss_mb=353.0,
        idle_seconds=0.3,
        ui_route_stability_age_s=21.4,
        active_route='control',
        confidence=0.86,
    )

    assert budget['allowed'] is False
    assert budget['decision'] == 'defer'
    assert budget['reason'] == 'ui_route_stabilizing:control'
    assert budget['recommended_mode'] == 'wait_for_ui_route_stability'


def test_operational_budget_defers_control_post_task_refresh_during_rest_window() -> None:
    """Chat-triggered secondary surfaces must not run right after a response."""
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='control_post_task_refresh',
        source='post_task:chat',
        rss_mb=400.0,
        idle_seconds=10.0,
        ui_route_stability_age_s=300.0,
        active_route='control',
        confidence=0.86,
    )

    assert budget['allowed'] is False
    assert budget['decision'] == 'defer'
    assert budget['reason'] == 'post_task_rest_window_not_reached'
    assert budget['recommended_mode'] == 'wait_for_deep_idle'


def test_operational_budget_defers_post_task_autonomy_dock_longer_than_timer() -> None:
    """Post-consultation dock refreshes are more conservative than routine timers."""
    policy = AutonomyGovernancePolicy()

    timer_budget = policy.evaluate_operational_budget(
        work_class='autonomy_dock_refresh',
        source='timer',
        rss_mb=400.0,
        idle_seconds=180.0,
        ui_route_stability_age_s=300.0,
        active_route='control',
        confidence=0.86,
    )
    post_task_budget = policy.evaluate_operational_budget(
        work_class='autonomy_dock_refresh',
        source='post_task:external_consultation',
        rss_mb=400.0,
        idle_seconds=180.0,
        ui_route_stability_age_s=300.0,
        active_route='control',
        confidence=0.86,
    )

    assert timer_budget['allowed'] is True
    assert post_task_budget['allowed'] is False
    assert post_task_budget['reason'] == 'post_task_rest_window_not_reached'
    assert post_task_budget['defer_seconds'] == 420.0


def test_operational_budget_defers_post_task_refresh_on_lower_memory_pressure() -> None:
    """A post-task refresh should not start when the UI process is already large."""
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='autonomy_dock_refresh',
        source='post_task:external_consultation',
        rss_mb=1800.0,
        idle_seconds=900.0,
        ui_route_stability_age_s=900.0,
        active_route='control',
        confidence=0.86,
    )

    assert budget['allowed'] is False
    assert budget['reason'] == 'post_task_resource_pressure_high'
    assert budget['recommended_mode'] == 'wait_for_lower_memory'


def test_operational_budget_defers_post_task_refresh_after_small_stall() -> None:
    """A post-task refresh must wait after even a moderate UI stall."""
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='control_post_task_refresh',
        source='post_task:chat',
        rss_mb=400.0,
        recent_stall_ms=2500.0,
        idle_seconds=900.0,
        ui_route_stability_age_s=900.0,
        active_route='control',
        confidence=0.86,
    )

    assert budget['allowed'] is False
    assert budget['reason'] == 'post_task_recent_ui_stall:2500ms'
    assert budget['recommended_mode'] == 'wait_for_stable_ui'


def test_operational_budget_defers_post_task_refresh_during_route_settle_after_idle() -> None:
    """Deep idle is not enough if the visible route itself is still settling."""
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='autonomy_dock_refresh',
        source='post_task:external_consultation',
        rss_mb=400.0,
        idle_seconds=900.0,
        ui_route_stability_age_s=180.0,
        active_route='evolution',
        confidence=0.86,
    )

    assert budget['allowed'] is False
    assert budget['reason'] == 'post_task_ui_route_stabilizing:evolution'
    assert budget['recommended_mode'] == 'wait_for_ui_route_stability'


def test_operational_budget_allows_idle_self_test_only_in_rest_window() -> None:
    policy = AutonomyGovernancePolicy()

    early = policy.evaluate_operational_budget(
        work_class='idle_self_test',
        source='timer',
        rss_mb=250.0,
        idle_seconds=30.0,
    )
    rested = policy.evaluate_operational_budget(
        work_class='idle_self_test',
        source='timer',
        rss_mb=250.0,
        idle_seconds=180.0,
        ui_route_stability_age_s=180.0,
    )

    assert early['allowed'] is False
    assert early['reason'] == 'rest_window_not_reached'
    assert rested['allowed'] is True
    assert rested['recommended_mode'] == 'background_idle'


def test_operational_budget_asks_user_for_low_confidence_destructive_action() -> None:
    policy = AutonomyGovernancePolicy()

    budget = policy.evaluate_operational_budget(
        work_class='destructive_action',
        source='auto',
        confidence=0.3,
        idle_seconds=300.0,
    )

    assert budget['allowed'] is False
    assert budget['decision'] == 'ask_user'
    assert budget['reason'] == 'confidence_too_low_for_action'


def test_operational_budget_records_experiment_run_with_budget_metadata() -> None:
    policy = AutonomyGovernancePolicy()
    repo = _RunRepo()
    budget = policy.evaluate_operational_budget(
        work_class='tool_scan',
        source='deferred_auto_install',
        background_active=True,
        rss_mb=370.0,
        idle_seconds=7.0,
        confidence=0.82,
    )

    run = record_operational_budget_experiment(
        repository=repo,
        budget=budget,
        observed_summary='deferred_auto_install -> defer',
        evidence_refs=['runtime_audit'],
    )

    assert run is repo.runs[0]
    assert run.suite_name == 'operational_budget'
    assert run.domain.value == 'algorithm'
    assert run.subject_key == 'operational_budget:tool_scan'
    assert run.metadata['budget_decision'] == 'defer'
    assert run.metadata['budget_reason'] == 'startup_or_background_active'
    assert run.metadata['operational_budget']['decision_source'] == 'autonomy_governance_policy.operational_budget'
    assert run.metrics.total_score > 0


def test_operational_budget_experiment_recording_is_throttled_by_signature() -> None:
    policy = AutonomyGovernancePolicy()
    repo = _RunRepo()
    throttle: dict[str, float] = {}
    budget = policy.evaluate_operational_budget(
        work_class='metacognition',
        source='startup_evolution',
        idle_seconds=10.0,
    )

    first = record_operational_budget_experiment(
        repository=repo,
        budget=budget,
        throttle_state=throttle,
        throttle_seconds=60.0,
    )
    second = record_operational_budget_experiment(
        repository=repo,
        budget=budget,
        throttle_state=throttle,
        throttle_seconds=60.0,
    )

    assert first is not None
    assert second is None
    assert len(repo.runs) == 1


def test_operational_budget_calibration_requires_minimum_sample() -> None:
    policy = AutonomyGovernancePolicy()
    repo = _RunRepo()
    for idx in range(3):
        budget = policy.evaluate_operational_budget(
            work_class='tool_scan',
            source=f'timer_{idx}',
            idle_seconds=10.0,
        )
        record_operational_budget_experiment(repository=repo, budget=budget)

    summary = summarize_operational_budget_calibration(repo.runs, min_sample=10)

    assert summary['status'] == 'insufficient_sample'
    assert summary['sample_count'] == 3
    assert summary['minimum_sample'] == 10
    assert summary['recommendation'] == 'collect_more_evidence_before_tuning'
    assert summary['current_thresholds']['idle_rest_window_s'] == 120.0


def test_operational_budget_calibration_reports_stable_guardrails_with_mixed_sample() -> None:
    policy = AutonomyGovernancePolicy()
    repo = _RunRepo()
    for idx in range(6):
        budget = policy.evaluate_operational_budget(
            work_class='idle_self_test',
            source=f'timer_allow_{idx}',
            idle_seconds=180.0,
        )
        record_operational_budget_experiment(repository=repo, budget=budget)
    for idx in range(5):
        budget = policy.evaluate_operational_budget(
            work_class='tool_scan',
            source=f'timer_defer_{idx}',
            idle_seconds=20.0,
        )
        record_operational_budget_experiment(repository=repo, budget=budget)

    summary = summarize_operational_budget_calibration(repo.runs, min_sample=10)

    assert summary['status'] == 'stable_guardrails'
    assert summary['sample_count'] == 11
    assert summary['by_decision']['allow'] == 6
    assert summary['by_decision']['defer'] == 5
    assert summary['recommended_thresholds'] == summary['current_thresholds']
    assert summary['confidence'] > 0.0


def test_operational_budget_calibration_does_not_tune_without_allow_samples() -> None:
    policy = AutonomyGovernancePolicy()
    repo = _RunRepo()
    for idx in range(10):
        budget = policy.evaluate_operational_budget(
            work_class='metacognition',
            source=f'startup_evolution_{idx}',
            idle_seconds=5.0,
        )
        record_operational_budget_experiment(repository=repo, budget=budget)

    summary = summarize_operational_budget_calibration(repo.runs, min_sample=10)

    assert summary['status'] == 'needs_allow_samples'
    assert summary['recommendation'] == 'collect_post_rest_allow_evidence_before_tuning'
    assert summary['by_reason']['rest_window_not_reached'] == 10


def test_operational_budget_policy_uses_runtime_tuning_thresholds() -> None:
    profile = RuntimeTuningProfile(
        scope_key='global',
        metadata={
            'operational_budget_thresholds': {
                'thresholds': {
                    'high_rss_mb': 1000.0,
                    'critical_rss_mb': 3000.0,
                    'stall_ms': 5000.0,
                    'idle_rest_window_s': 60.0,
                }
            }
        },
    )
    policy = AutonomyGovernancePolicy()
    policy.apply_runtime_tuning_profile(profile)

    budget = policy.evaluate_operational_budget(
        work_class='ui_refresh',
        source='timer',
        rss_mb=1200.0,
        idle_seconds=90.0,
    )

    assert budget['decision'] == 'defer'
    assert budget['reason'] == 'resource_pressure_high'
    assert budget['threshold_source'] == 'runtime_tuning_profile'
    assert budget['effective_thresholds']['high_rss_mb'] == 1000.0


def test_operational_budget_runtime_application_blocks_immature_calibration() -> None:
    runtime_repo = _RuntimeTuningRepo()
    result = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration={
            'status': 'insufficient_sample',
            'sample_count': 3,
            'minimum_sample': 10,
            'recommended_thresholds': {'idle_rest_window_s': 120.0},
        },
    )

    assert result['applied'] is False
    assert result['reason'] == 'minimum_sample_not_reached'
    assert runtime_repo.saved == []


def test_operational_budget_runtime_application_persists_reversible_profile() -> None:
    runtime_repo = _RuntimeTuningRepo()
    calibration = {
        'status': 'rest_window_dominant',
        'policy_version': 'operational_budget_v1',
        'sample_count': 11,
        'minimum_sample': 10,
        'recommendation': 'keep_idle_rest_window_and_collect_more_after_idle_samples',
        'confidence': 0.495,
        'recommended_thresholds': {
            'critical_rss_mb': 6000.0,
            'high_rss_mb': 2500.0,
            'stall_ms': 5000.0,
            'idle_rest_window_s': 120.0,
        },
    }

    result = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration=calibration,
        evidence_refs=['test:evidence'],
    )

    assert result['applied'] is True
    assert result['status'] == 'rest_window_dominant'
    assert runtime_repo.profile is not None
    payload = runtime_repo.profile.metadata['operational_budget_thresholds']
    assert payload['thresholds']['idle_rest_window_s'] == 120.0
    assert payload['recommendation'] == calibration['recommendation']
    assert len(runtime_repo.profile.adjustments) == 1
    adjustment = runtime_repo.profile.adjustments[0]
    assert adjustment.target_key == 'autonomy_governance_policy.operational_budget.thresholds'
    assert adjustment.reversible is True
    assert 'test:evidence' in adjustment.evidence_refs


def test_operational_budget_runtime_application_is_idempotent_for_same_calibration() -> None:
    runtime_repo = _RuntimeTuningRepo()
    calibration = {
        'status': 'stable_guardrails',
        'sample_count': 12,
        'minimum_sample': 10,
        'recommendation': 'keep_current_thresholds',
        'recommended_thresholds': {
            'critical_rss_mb': 6000.0,
            'high_rss_mb': 2500.0,
            'stall_ms': 5000.0,
            'idle_rest_window_s': 120.0,
        },
    }

    first = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration=calibration,
    )
    second = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration=calibration,
    )

    assert first['applied'] is True
    assert second['applied'] is False
    assert second['reason'] == 'already_effective'
    assert runtime_repo.profile is not None
    assert len(runtime_repo.profile.adjustments) == 1


def test_operational_budget_runtime_application_updates_evidence_without_duplicate_adjustment() -> None:
    runtime_repo = _RuntimeTuningRepo()
    calibration = {
        'status': 'rest_window_dominant',
        'sample_count': 11,
        'minimum_sample': 10,
        'recommendation': 'keep_idle_rest_window_and_collect_more_after_idle_samples',
        'recommended_thresholds': {
            'critical_rss_mb': 6000.0,
            'high_rss_mb': 2500.0,
            'stall_ms': 5000.0,
            'idle_rest_window_s': 120.0,
        },
    }
    first = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration=calibration,
    )
    second = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration={**calibration, 'sample_count': 13},
    )

    assert first['applied'] is True
    assert second['applied'] is False
    assert second['reason'] == 'already_effective'
    assert runtime_repo.profile is not None
    assert len(runtime_repo.profile.adjustments) == 1
    assert runtime_repo.profile.metadata['operational_budget_thresholds']['sample_count'] == 13


def test_operational_budget_runtime_application_waits_out_recent_stall() -> None:
    runtime_repo = _RuntimeTuningRepo()
    result = apply_operational_budget_calibration_to_runtime_tuning(
        repository=runtime_repo,
        calibration={
            'status': 'stable_guardrails',
            'sample_count': 12,
            'minimum_sample': 10,
            'recommendation': 'keep_current_thresholds',
            'recommended_thresholds': {
                'critical_rss_mb': 6000.0,
                'high_rss_mb': 2500.0,
                'stall_ms': 5000.0,
                'idle_rest_window_s': 120.0,
            },
        },
        recent_stall_ms=9000.0,
    )

    assert result['applied'] is False
    assert result['reason'] == 'recent_ui_stall:9000ms'
    assert runtime_repo.saved == []
