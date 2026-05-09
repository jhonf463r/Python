from __future__ import annotations

from iabv_v15.services.adaptive.autonomy_governance_policy import (
    AutonomyGovernancePolicy,
    record_operational_budget_experiment,
)


class _RunRepo:
    def __init__(self) -> None:
        self.runs = []

    def save_run(self, run):
        self.runs.append(run)
        return run


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
