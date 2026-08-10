"""Verify the P0.212 handoff record and demonstrate analysis capabilities."""
from pathlib import Path

from iabv_v15.domain.models import AuthorizationStatus
from iabv_v15.services.evolution.agent_handoff_trail import AgentHandoffTrail


def verify_p0_212_handoff():
    """Verify and analyze the P0.212 handoff record."""
    handoff_trail = AgentHandoffTrail(data_root=Path.home() / 'IABV_v1.5' / 'data')

    # Get the P0.212 handoff
    p0212_records = handoff_trail.get_by_task("P0.212")
    print(f"Found {len(p0212_records)} P0.212 handoff records")

    if p0212_records:
        latest = p0212_records[-1]
        print(f"\nLatest P0.212 handoff:")
        print(f"  Handoff ID: {latest.handoff_id}")
        print(f"  Task: {latest.task_id} - {latest.task_name}")
        print(f"  Executor: {latest.executor_agent}")
        print(f"  Auditor: {latest.auditor_agent}")
        print(f"  Timestamp: {latest.timestamp_utc}")
        print(f"  Repository: {latest.repository}")
        print(f"  Baseline SHA: {latest.baseline_sha}")
        print(f"  HEAD SHA: {latest.head_sha}")
        print(f"  Local branch: {latest.local_branch}")
        print(f"  Public branch: {latest.public_branch}")
        print(f"  Task commits: {latest.task_commits}")
        print(f"  Changed files: {latest.changed_files}")
        print(f"  Sync verified: {latest.sync_verified}")
        print(f"  Tests executed: {len(latest.tests_executed)}")
        print(f"  Tests status: {latest.tests_status}")
        print(f"  Inherited failures: {latest.inherited_failures}")
        print(f"  New failures: {latest.new_failures}")
        print(f"  Authority: {latest.authority}")
        print(f"  Audit verdict: {latest.audit_verdict}")
        print(f"  Next agent: {latest.next_agent}")
        print(f"  Next agent authorization: {latest.next_agent_authorization}")
        print(f"  Next action: {latest.next_action}")
        print(f"  Next action authorization: {latest.next_action_authorization}")

        # Verify consistency
        issues = handoff_trail.verify_consistency(latest)
        print(f"\nConsistency verification:")
        print(f"  Is consistent: {issues['is_consistent']}")
        print(f"  SHA mismatch: {issues['sha_mismatch']}")
        print(f"  Test declared but not verified: {issues['test_declared_but_not_verified']}")
        print(f"  Audit based on different SHA: {issues['audit_based_on_different_sha']}")
        print(f"  Inconsistent evidence: {issues['inconsistent_evidence']}")
        print(f"  Unauthorized next agent: {issues['unauthorized_next_agent']}")
        print(f"  Unauthorized next action: {issues['unauthorized_next_action']}")
        print(f"  Self marked reproduced: {issues['self_marked_reproduced']}")

        # Analyze agent performance
        devin_analysis = handoff_trail.analyze_agent_performance("Devin")
        print(f"\nDevin performance analysis:")
        print(f"  Total handoffs: {devin_analysis['total_handoffs']}")
        print(f"  Successful handoffs: {devin_analysis['successful_handoffs']}")
        print(f"  Failure count: {devin_analysis['failure_count']}")
        print(f"  Failure rate: {devin_analysis['failure_rate']}")
        print(f"  Failure modes: {devin_analysis['failure_modes']}")

        # Analyze tool+agent combination
        pytest_analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin")
        print(f"\nDevin + pytest combination analysis:")
        print(f"  Total handoffs: {pytest_analysis['total_handoffs']}")
        print(f"  Success rate: {pytest_analysis['success_rate']}")
        print(f"  Recommendation: {pytest_analysis['recommendation']}")

        print(f"\nLearning signals from P0.212:")
        for key, value in latest.learning_signals.items():
            print(f"  {key}: {value}")

        print(f"\nMetadata from P0.212:")
        for key, value in latest.metadata.items():
            print(f"  {key}: {value}")

    else:
        print("No P0.212 handoff records found")


if __name__ == "__main__":
    verify_p0_212_handoff()
