"""Record the actual P0.212 handoff for cross-agent synchronization."""
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import AgentHandoffRecord, AuthorizationStatus, EvidenceStatus
from iabv_v15.services.evolution.agent_handoff_trail import AgentHandoffTrail


def record_p0_212_handoff():
    """Record the actual P0.212 handoff data."""
    handoff_trail = AgentHandoffTrail(data_root=Path.home() / 'IABV_v1.5' / 'data')

    record = AgentHandoffRecord(
        handoff_id=str(uuid4()),
        task_id="P0.212",
        task_name="GPU degradation detection and preservation of nvidia-smi stderr",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97", "bbaf42e6", "2c983339"],
        changed_files=[
            "src/iabv_v15/services/evolution/environment_self_awareness_service.py",
            "tests/test_environment_self_awareness_service.py"
        ],
        sync_verified=True,
        tests_executed=[
            "test_environment_self_awareness_service_persists_known_environment",
            "test_environment_self_awareness_service_surfaces_memory_pressure",
            "test_environment_self_awareness_light_scan_reuses_cached_provider_health",
            "test_gpu_degradation_when_nvidia_smi_fails_but_windows_detects_gpu",
            "test_gpu_healthy_when_nvidia_smi_succeeds",
            "test_gpu_degradation_preserves_real_stderr"
        ],
        tests_status=EvidenceStatus.REPRODUCED,
        inherited_failures=[
            "organism_state_snapshot.py test failure due to missing runtime_knowledge_snapshot module (P0.165 issue)"
        ],
        new_failures=[],
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS",
        audit_evidence={
            "audited_sha": "2c983339912567eb0c7e63af0dbb0f7de29ee2af",
            "tests_reproduced": 6,
            "all_passed": True,
            "gpu_authority_verified": True,
            "git_sync_commands": [
                "git status --short --branch",
                "git rev-parse HEAD",
                "git branch -vv",
                "git remote -v",
                "git ls-remote --heads origin devin/p0-212-gpu-minimal",
                "git ls-remote origin 2c983339912567eb0c7e63af0dbb0f7de29ee2af",
                "git show --stat --oneline --decorate 2c983339912567eb0c7e63af0dbb0f7de29ee2af",
                "git log --oneline --decorate --graph -10 devin/p0-212-gpu-minimal"
            ],
            "test_commands": [
                "python -m pytest tests/test_environment_self_awareness_service.py -xvs"
            ]
        },
        next_agent="Devin",
        next_agent_authorization=AuthorizationStatus.DECLARED,
        next_action="Fix inherited P0.165 runtime_knowledge_snapshot issue in organism_state_snapshot.py",
        next_action_authorization=AuthorizationStatus.DECLARED,
        learning_signals={
            "devin_pytest_success_rate": 1.0,
            "claude_audit_accuracy": 1.0,
            "gpu_integration_complexity": "medium",
            "sync_verification": "reliable"
        },
        metadata={
            "integration_phase": "GPU degradation detection",
            "timeout_changes": "_GPU_QUERY_TIMEOUT_SECONDS increased from 1.5 to 5.0s",
            "stderr_preservation": "Real stderr from nvidia-smi preserved in gpu_degradation_detail",
            "test_mocking": "Fixed shutil.which mocking for GPU tests",
            "authority_preserved": "EnvironmentSelfAwarenessService._gpu_snapshot() remains single source of truth",
            "files_modified": 2,
            "commits_created": 3,
            "push_performed": True,
            "pr_created": False,
            "remote_url": "https://github.com/jhonf463r/Python/tree/devin/p0-212-gpu-minimal"
        }
    )

    handoff_trail.record(record)
    print(f"Recorded P0.212 handoff: {record.handoff_id}")
    print(f"Task: {record.task_id} - {record.task_name}")
    print(f"Executor: {record.executor_agent}")
    print(f"Auditor: {record.auditor_agent}")
    print(f"Audit verdict: {record.audit_verdict}")
    print(f"Next agent: {record.next_agent} (authorization: {record.next_agent_authorization})")
    print(f"Next action: {record.next_action} (authorization: {record.next_action_authorization})")


if __name__ == "__main__":
    record_p0_212_handoff()
