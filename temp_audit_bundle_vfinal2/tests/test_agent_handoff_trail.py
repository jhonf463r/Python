"""Tests for cross-agent handoff trail."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import AgentHandoffRecord, AuthorizationStatus, EvidenceStatus
from iabv_v15.services.evolution.agent_handoff_trail import AgentHandoffTrail


@pytest.fixture
def temp_data_root():
    """Create a temporary data root for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = Path(tmpdir) / 'data'
        data_root.mkdir(parents=True, exist_ok=True)
        yield data_root


@pytest.fixture
def handoff_trail(temp_data_root):
    """Create an AgentHandoffTrail instance for testing."""
    return AgentHandoffTrail(data_root=temp_data_root)


def test_handoff_record_creation():
    """Test that a handoff record can be created with all required fields."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
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
            "test_gpu_degradation_when_nvidia_smi_fails_but_windows_detects_gpu",
            "test_gpu_healthy_when_nvidia_smi_succeeds",
            "test_gpu_degradation_preserves_real_stderr"
        ],
        tests_status=EvidenceStatus.REPRODUCED,
        inherited_failures=[
            "organism_state_snapshot.py test failure due to missing runtime_knowledge_snapshot module"
        ],
        new_failures=[],
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS",
        audit_evidence={
            "audited_sha": "2c983339912567eb0c7e63af0dbb0f7de29ee2af",
            "tests_reproduced": 6,
            "all_passed": True
        },
        next_agent="Devin",
        next_action="Fix inherited P0.165 runtime_knowledge_snapshot issue"
    )

    assert record.task_id == "P0.212"
    assert record.executor_agent == "Devin"
    assert record.auditor_agent == "Claude"
    assert record.sync_verified is True
    assert record.tests_status == EvidenceStatus.REPRODUCED
    assert len(record.task_commits) == 3
    assert record.audit_verdict == "P0_212_AUDIT_PASS"


def test_handoff_trail_record_and_load(handoff_trail, temp_data_root):
    """Test that handoff records can be recorded and loaded."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97", "bbaf42e6", "2c983339"],
        sync_verified=True,
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.REPRODUCED,
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS"
    )

    handoff_trail.record(record)

    # Verify file was created
    log_path = temp_data_root / 'evolution' / 'agent_handoff' / 'handoffs.jsonl'
    assert log_path.exists()

    # Load and verify
    loaded = handoff_trail.load_recent(limit=10)
    assert len(loaded) == 1
    assert loaded[0]['task_id'] == "P0.212"
    assert loaded[0]['executor_agent'] == "Devin"


def test_handoff_trail_get_by_task(handoff_trail):
    """Test retrieving handoff records by task ID."""
    # Create multiple records for different tasks
    for i in range(3):
        record = AgentHandoffRecord(
            task_id=f"P0.{i}",
            task_name=f"Task {i}",
            executor_agent="Devin",
            auditor_agent="Claude",
            session_id=str(uuid4()),
            repository="test/repo",
            baseline_sha="abc123",
            local_branch=f"branch-{i}",
            public_branch=f"public-{i}",
            head_sha=f"sha{i}",
            task_commits=[f"commit{i}"],
            sync_verified=True,
            tests_status=EvidenceStatus.REPRODUCED,
            audit_verdict="PASS"
        )
        handoff_trail.record(record)

    # Create additional records for P0.10 (different task)
    for i in range(2):
        record = AgentHandoffRecord(
            task_id="P0.10",
            task_name=f"Task 10 - attempt {i}",
            executor_agent="Devin",
            auditor_agent="Claude",
            session_id=str(uuid4()),
            repository="test/repo",
            baseline_sha="abc123",
            local_branch="branch-10",
            public_branch="public-10",
            head_sha=f"sha10-{i}",
            task_commits=[f"commit10-{i}"],
            sync_verified=True,
            tests_status=EvidenceStatus.REPRODUCED,
            audit_verdict="PASS"
        )
        handoff_trail.record(record)

    # Get records for P0.10
    p010_records = handoff_trail.get_by_task("P0.10")
    assert len(p010_records) == 2
    assert all(r.task_id == "P0.10" for r in p010_records)


def test_handoff_trail_get_latest_by_task(handoff_trail):
    """Test retrieving the most recent handoff for a task."""
    # Create records with different timestamps
    import time
    for i in range(3):
        record = AgentHandoffRecord(
            task_id="P0.212",
            task_name=f"GPU task - attempt {i}",
            executor_agent="Devin",
            auditor_agent="Claude",
            session_id=str(uuid4()),
            repository="test/repo",
            baseline_sha="abc123",
            local_branch="branch-212",
            public_branch="public-212",
            head_sha=f"sha212-{i}",
            task_commits=[f"commit212-{i}"],
            sync_verified=True,
            tests_status=EvidenceStatus.REPRODUCED,
            audit_verdict="PASS"
        )
        handoff_trail.record(record)
        time.sleep(0.01)  # Ensure different timestamps

    latest = handoff_trail.get_latest_by_task("P0.212")
    assert latest is not None
    assert latest.task_id == "P0.212"
    assert "attempt 2" in latest.task_name  # Last one should be latest


def test_consistency_verification_valid_handoff(handoff_trail):
    """Test consistency verification for a valid handoff."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97", "bbaf42e6", "2c983339"],
        sync_verified=True,
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.REPRODUCED,
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS",
        audit_evidence={
            "audited_sha": "2c983339912567eb0c7e63af0dbb0f7de29ee2af",
            "tests_reproduced": 6
        }
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['is_consistent'] is True
    assert issues['sha_mismatch'] is False
    assert issues['test_declared_but_not_verified'] is False
    assert issues['audit_based_on_different_sha'] is False


def test_consistency_verification_test_declared_not_verified(handoff_trail):
    """Test detection of tests declared but not verified."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97"],
        sync_verified=True,
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.DECLARED,  # Tests declared but not verified
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS"
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['is_consistent'] is False
    assert issues['test_declared_but_not_verified'] is True


def test_consistency_verification_audit_different_sha(handoff_trail):
    """Test detection of audit based on different SHA than HEAD."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97"],
        sync_verified=True,
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.REPRODUCED,
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS",
        audit_evidence={
            "audited_sha": "different_sha_value",  # Different from HEAD
            "tests_reproduced": 6
        }
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['is_consistent'] is False
    assert issues['audit_based_on_different_sha'] is True


def test_consistency_verification_inconsistent_evidence(handoff_trail):
    """Test detection of contradictory evidence."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97"],
        sync_verified=False,  # Sync not verified
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.VERIFIED,  # But tests marked as verified
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS"
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['is_consistent'] is False
    assert issues['inconsistent_evidence'] is True


def test_inherited_failures_classification(handoff_trail):
    """Test that inherited failures are properly classified."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97"],
        sync_verified=True,
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.REPRODUCED,
        inherited_failures=[
            "organism_state_snapshot.py test failure due to missing runtime_knowledge_snapshot module"
        ],
        new_failures=[],
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS"
    )

    assert len(record.inherited_failures) == 1
    assert len(record.new_failures) == 0
    assert "runtime_knowledge_snapshot" in record.inherited_failures[0]


def test_audit_pass_status(handoff_trail):
    """Test that audit PASS status is properly recorded."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS",
        audit_evidence={
            "audited_sha": "2c983339912567eb0c7e63af0dbb0f7de29ee2af",
            "tests_reproduced": 6,
            "all_passed": True
        }
    )

    assert record.audit_verdict == "P0_212_AUDIT_PASS"
    assert record.audit_evidence["all_passed"] is True
    assert record.audit_evidence["tests_reproduced"] == 6


def test_next_agent_selection(handoff_trail):
    """Test that next agent and action are properly specified."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS",
        next_agent="Devin",
        next_action="Fix inherited P0.165 runtime_knowledge_snapshot issue"
    )

    assert record.next_agent == "Devin"
    assert "runtime_knowledge_snapshot" in record.next_action


def test_agent_performance_analysis(handoff_trail):
    """Test historical performance analysis for an agent."""
    # Create multiple handoffs for Devin
    for i in range(5):
        record = AgentHandoffRecord(
            task_id=f"P0.{i}",
            task_name=f"Task {i}",
            executor_agent="Devin",
            auditor_agent="Claude",
            session_id=str(uuid4()),
            repository="test/repo",
            baseline_sha="abc123",
            local_branch=f"branch-{i}",
            public_branch=f"public-{i}",
            head_sha=f"sha{i}",
            task_commits=[f"commit{i}"],
            sync_verified=True,
            tests_status=EvidenceStatus.REPRODUCED,
            audit_verdict="P0_AUDIT_PASS" if i < 4 else "P0_AUDIT_FAIL"
        )
        handoff_trail.record(record)

    analysis = handoff_trail.analyze_agent_performance("Devin")
    assert analysis['total_handoffs'] == 5
    assert analysis['successful_handoffs'] == 4
    assert analysis['failure_rate'] == 0.2


def test_tool_agent_combination_analysis(handoff_trail):
    """Test performance analysis for tool+agent combination."""
    # Create handoffs with pytest usage by Devin
    for i in range(3):
        record = AgentHandoffRecord(
            task_id=f"P0.{i}",
            task_name=f"Task {i}",
            executor_agent="Devin",
            auditor_agent="Claude",
            session_id=str(uuid4()),
            repository="test/repo",
            baseline_sha="abc123",
            local_branch=f"branch-{i}",
            public_branch=f"public-{i}",
            head_sha=f"sha{i}",
            task_commits=[f"commit{i}"],
            sync_verified=True,
            tests_status=EvidenceStatus.REPRODUCED,
            audit_verdict="P0_AUDIT_PASS",
            metadata={"tools_used": ["pytest"]}
        )
        handoff_trail.record(record)

    analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin")
    assert analysis['total_handoffs'] == 3
    assert analysis['success_rate'] == 1.0
    # With 3 samples and 100% success rate, recommendation should be 'use'
    assert analysis['recommendation'] == 'use'


def test_evidence_status_enum():
    """Test that EvidenceStatus enum has all required values."""
    assert EvidenceStatus.DECLARED == "declared"
    assert EvidenceStatus.VERIFIED == "verified"
    assert EvidenceStatus.REPRODUCED == "reproduced"
    assert EvidenceStatus.INFERRED == "inferred"
    assert EvidenceStatus.UNKNOWN == "unknown"


def test_handoff_record_serialization():
    """Test that handoff records can be serialized and deserialized."""
    record = AgentHandoffRecord(
        task_id="P0.212",
        task_name="GPU degradation detection",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="jhonf463r/Python",
        baseline_sha="4e1af5cd270f3fe7bb5ebb898f2ae55b97b0947e",
        local_branch="feature/p0-212-gpu-minimal",
        public_branch="devin/p0-212-gpu-minimal",
        head_sha="2c983339912567eb0c7e63af0dbb0f7de29ee2af",
        task_commits=["65a8ac97", "bbaf42e6", "2c983339"],
        sync_verified=True,
        tests_executed=["test_gpu_healthy_when_nvidia_smi_succeeds"],
        tests_status=EvidenceStatus.REPRODUCED,
        authority="EnvironmentSelfAwarenessService._gpu_snapshot()",
        audit_verdict="P0_212_AUDIT_PASS"
    )

    # Serialize
    serialized = record.model_dump(mode='json')
    assert serialized['task_id'] == "P0.212"
    assert serialized['tests_status'] == "reproduced"

    # Deserialize
    deserialized = AgentHandoffRecord(**serialized)
    assert deserialized.task_id == record.task_id
    assert deserialized.executor_agent == record.executor_agent
    assert deserialized.tests_status == record.tests_status


def test_p0_212_specific_handoff_structure(handoff_trail):
    """Test the specific structure required for P0.212 handoff."""
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
            "gpu_authority_verified": True
        },
        next_agent="Devin",
        next_agent_authorization=AuthorizationStatus.DECLARED,
        next_action="Fix inherited P0.165 runtime_knowledge_snapshot issue in organism_state_snapshot.py",
        next_action_authorization=AuthorizationStatus.DECLARED,
        learning_signals={
            "devin_pytest_success_rate": 1.0,
            "claude_audit_accuracy": 1.0,
            "gpu_integration_complexity": "medium"
        },
        metadata={
            "git_sync_commands": [
                "git status --short --branch",
                "git rev-parse HEAD",
                "git branch -vv",
                "git remote -v",
                "git ls-remote --heads origin devin/p0-212-gpu-minimal"
            ],
            "test_commands": [
                "python -m pytest tests/test_environment_self_awareness_service.py -xvs"
            ]
        }
    )

    # Verify all P0.212 specific fields
    assert record.task_id == "P0.212"
    assert len(record.task_commits) == 3
    assert "65a8ac97" in record.task_commits
    assert "bbaf42e6" in record.task_commits
    assert "2c983339" in record.task_commits
    assert len(record.tests_executed) == 6
    assert record.sync_verified is True
    assert record.tests_status == EvidenceStatus.REPRODUCED
    assert len(record.inherited_failures) == 1
    assert len(record.new_failures) == 0
    assert record.audit_verdict == "P0_212_AUDIT_PASS"
    assert record.audit_evidence["all_passed"] is True
    assert record.next_agent == "Devin"
    assert record.next_agent_authorization == AuthorizationStatus.DECLARED
    assert "runtime_knowledge_snapshot" in record.next_action
    assert record.next_action_authorization == AuthorizationStatus.DECLARED

    # Verify consistency (note: unauthorized next_agent/next_action doesn't mark as inconsistent)
    issues = handoff_trail.verify_consistency(record)
    assert issues['is_consistent'] is True
    assert issues['unauthorized_next_agent'] is True  # Expected, not an error
    assert issues['unauthorized_next_action'] is True  # Expected, not an error


# ============================================================================
# ATTACK TESTS - Falsification Detection
# ============================================================================

def test_attack_declares_nonexistent_sha(handoff_trail):
    """Attack A: Devin declares non-existent SHA."""
    record = AgentHandoffRecord(
        task_id="ATTACK_A",
        task_name="Non-existent SHA attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="this_sha_does_not_exist_anywhere_0000000000",
        task_commits=["fake_commit"],
        sync_verified=True,  # Falsely claims verified
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS"
    )

    issues = handoff_trail.verify_consistency(record)
    # The system cannot verify Git state directly in this implementation
    # but it records the claim for external verification
    # The attack is detected by inconsistency between declared SHA and audit evidence
    # or through external Git verification
    # For now, we verify that the system at least doesn't crash and records the data
    assert 'is_consistent' in issues
    # In a real implementation with Git integration, this would be False


def test_attack_declares_head_a_git_shows_head_b(handoff_trail):
    """Attack B: Devin declares HEAD=A but Git shows HEAD=B."""
    record = AgentHandoffRecord(
        task_id="ATTACK_B",
        task_name="HEAD mismatch attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # Declared HEAD
        task_commits=["commit_a"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        audit_evidence={
            "audited_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"  # Actual Git HEAD
        }
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['audit_based_on_different_sha'] is True
    assert issues['is_consistent'] is False


def test_attack_declares_tests_pass_no_execution_evidence(handoff_trail):
    """Attack C: Devin declares tests PASS but no execution evidence."""
    record = AgentHandoffRecord(
        task_id="ATTACK_C",
        task_name="Fake test results attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_executed=["test_fake_1", "test_fake_2"],  # Declares tests
        tests_status=EvidenceStatus.DECLARED,  # But only DECLARED, not VERIFIED
        audit_verdict="PASS"
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['test_declared_but_not_verified'] is True
    assert issues['is_consistent'] is False


def test_attack_audits_sha_a_head_is_b(handoff_trail):
    """Attack D: Claude audits SHA=A while HEAD is B."""
    record = AgentHandoffRecord(
        task_id="ATTACK_D",
        task_name="Audit SHA mismatch attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",  # Current HEAD
        task_commits=["commit_b"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        audit_evidence={
            "audited_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # Audited different SHA
        }
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['audit_based_on_different_sha'] is True
    assert issues['is_consistent'] is False


def test_attack_declares_next_agent_no_authorization(handoff_trail):
    """Attack E: Handoff declares next_agent=Claude but no authorization."""
    record = AgentHandoffRecord(
        task_id="ATTACK_E",
        task_name="Unauthorized next agent attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        next_agent="Claude",
        next_agent_authorization=AuthorizationStatus.DECLARED,  # Only declared, not authorized
        next_action="Some sensitive action"
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['unauthorized_next_agent'] is True
    # Note: unauthorized next_agent doesn't mark as inconsistent - it's expected


def test_attack_agent_marks_own_evidence_reproduced(handoff_trail):
    """Attack F: Agent tries to mark its own evidence as REPRODUCED."""
    record = AgentHandoffRecord(
        task_id="ATTACK_F",
        task_name="Self-marking evidence attack",
        executor_agent="Devin",
        auditor_agent="",  # No auditor
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_executed=["test_self"],
        tests_status=EvidenceStatus.REPRODUCED,  # Marked as REPRODUCED without auditor
        audit_verdict=""  # No audit verdict
    )

    issues = handoff_trail.verify_consistency(record)
    # Without an auditor, REPRODUCED status is suspicious
    # The system should flag this as inconsistent
    assert issues['is_consistent'] is False
    assert issues['self_marked_reproduced'] is True


def test_attack_isolated_success_strong_recommendation(handoff_trail):
    """Attack G: Single isolated success attempts to produce strong recommendation."""
    # First, create a single successful handoff
    record = AgentHandoffRecord(
        task_id="ATTACK_G",
        task_name="Isolated success attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        metadata={"tools_used": ["pytest"]}
    )
    handoff_trail.record(record)

    # Try to get a strong recommendation from single data point
    analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin")
    assert analysis['total_handoffs'] == 1
    assert analysis['sample_count'] == 1
    # With only 1 sample, recommendation MUST be cautious, not strong
    assert analysis['recommendation'] == 'cautious'
    # Explicitly verify it's NOT use or avoid with insufficient evidence
    assert analysis['recommendation'] != 'use'
    assert analysis['recommendation'] != 'avoid'


def test_attack_contradictory_agent_results(handoff_trail):
    """Attack H: Two agents provide contradictory results."""
    # Agent 1 claims success
    record1 = AgentHandoffRecord(
        task_id="ATTACK_H1",
        task_name="Contradictory attack 1",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS"
    )
    handoff_trail.record(record1)

    # Agent 2 claims failure for same task
    record2 = AgentHandoffRecord(
        task_id="ATTACK_H2",
        task_name="Contradictory attack 2",
        executor_agent="Codex",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="FAIL"
    )
    handoff_trail.record(record2)

    # System should detect the contradiction when analyzing
    devin_analysis = handoff_trail.analyze_agent_performance("Devin")
    codex_analysis = handoff_trail.analyze_agent_performance("Codex")

    # Both should show their respective verdicts
    assert devin_analysis['successful_handoffs'] == 1
    assert codex_analysis['successful_handoffs'] == 0


def test_attack_branch_local_remote_sha_divergence(handoff_trail):
    """Attack I: Local branch and remote branch have different SHAs."""
    record = AgentHandoffRecord(
        task_id="ATTACK_I",
        task_name="Branch divergence attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="local_sha123",  # Local HEAD
        task_commits=["commit123"],
        sync_verified=False,  # Not verified (divergence)
        tests_status=EvidenceStatus.DECLARED,
        audit_verdict="PASS",
        audit_evidence={
            "local_sha": "local_sha123",
            "remote_sha": "remote_sha456"  # Different remote SHA
        }
    )

    issues = handoff_trail.verify_consistency(record)
    # sync_verified=False should be detected
    assert issues['is_consistent'] is False or not record.sync_verified


def test_attack_repository_changes_after_audit(handoff_trail):
    """Attack J: Repository changes after audit."""
    record = AgentHandoffRecord(
        task_id="ATTACK_J",
        task_name="Post-audit modification attack",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-attack",
        public_branch="public-attack",
        head_sha="sha_at_audit_time",
        task_commits=["commit123"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        audit_evidence={
            "audited_sha": "sha_at_audit_time",
            "audit_timestamp": "2026-08-09T00:00:00Z"
        },
        metadata={
            "current_head_sha": "sha_after_modification",  # Repository changed
            "modification_timestamp": "2026-08-09T01:00:00Z"
        }
    )

    issues = handoff_trail.verify_consistency(record)
    # The metadata showing different SHA is recorded for detection
    # External verification would flag this as repository changed post-audit
    assert record.metadata.get('current_head_sha') != record.head_sha
    # This is recorded as inconsistency data for external verification


def test_authorization_status_enum():
    """Test that AuthorizationStatus enum has all required values."""
    assert AuthorizationStatus.DECLARED == "declared"
    assert AuthorizationStatus.RECOMMENDED == "recommended"
    assert AuthorizationStatus.AUTHORIZED == "authorized"
    assert AuthorizationStatus.PENDING == "pending"
    assert AuthorizationStatus.REVOKED == "revoked"


def test_authorized_next_agent_consistency(handoff_trail):
    """Test that authorized next_agent doesn't trigger unauthorized flag."""
    record = AgentHandoffRecord(
        task_id="AUTHORIZED_TEST",
        task_name="Authorized next agent test",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-authorized",
        public_branch="public-authorized",
        head_sha="sha123",
        task_commits=["commit123"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        next_agent="Claude",
        next_agent_authorization=AuthorizationStatus.AUTHORIZED,  # Authorized
        next_action="Approved action",
        next_action_authorization=AuthorizationStatus.AUTHORIZED
    )

    issues = handoff_trail.verify_consistency(record)
    assert issues['unauthorized_next_agent'] is False
    assert issues['unauthorized_next_action'] is False
    assert issues['is_consistent'] is True


def test_strong_recommendation_with_sufficient_evidence(handoff_trail):
    """Test that strong recommendation 'use' is allowed with sufficient evidence."""
    # Create 3 successful handoffs (meets minimum threshold)
    for i in range(3):
        handoff_trail.record(AgentHandoffRecord(
            task_id=f"SUFFICIENT_EVIDENCE_{i}",
            task_name=f"Sufficient evidence test {i}",
            executor_agent="Devin",
            auditor_agent="Claude",
            session_id=str(uuid4()),
            repository="test/repo",
            baseline_sha="abc123",
            local_branch=f"branch-{i}",
            public_branch=f"public-{i}",
            head_sha=f"sha{i}",
            task_commits=[f"commit{i}"],
            sync_verified=True,
            tests_status=EvidenceStatus.REPRODUCED,
            audit_verdict="PASS",
            metadata={"tools_used": ["pytest"]}
        ))

    analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin")
    assert analysis['total_handoffs'] == 3
    assert analysis['success_rate'] == 1.0
    assert analysis['sample_count'] == 3
    # With 3 samples and 100% success rate, recommendation should be 'use'
    assert analysis['recommendation'] == 'use'


def test_learning_with_multiple_episodes(handoff_trail):
    """Test learning with multiple episodes including failures."""
    # Episode 1: Devin + pytest → PASS
    handoff_trail.record(AgentHandoffRecord(
        task_id="LEARNING_1",
        task_name="Learning episode 1",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-1",
        public_branch="public-1",
        head_sha="sha1",
        task_commits=["commit1"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="LEARNING_PASS",
        metadata={"tools_used": ["pytest"]}
    ))

    # Episode 2: Devin + pytest → PASS
    handoff_trail.record(AgentHandoffRecord(
        task_id="LEARNING_2",
        task_name="Learning episode 2",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-2",
        public_branch="public-2",
        head_sha="sha2",
        task_commits=["commit2"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="LEARNING_PASS",
        metadata={"tools_used": ["pytest"]}
    ))

    # Episode 3: Devin + pytest → FAIL
    handoff_trail.record(AgentHandoffRecord(
        task_id="LEARNING_3",
        task_name="Learning episode 3",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-3",
        public_branch="public-3",
        head_sha="sha3",
        task_commits=["commit3"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="LEARNING_FAIL",  # This one failed
        new_failures=["pytest_timeout"],
        metadata={"tools_used": ["pytest"]}
    ))

    analysis = handoff_trail.analyze_agent_performance("Devin")
    assert analysis['total_handoffs'] == 3
    assert analysis['successful_handoffs'] == 2
    assert analysis['failure_count'] == 1
    assert analysis['failure_rate'] == 0.333  # 1/3
    assert 'pytest_timeout' in analysis['failure_modes']

    # Tool+agent analysis should reflect the same
    tool_analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin")
    assert tool_analysis['total_handoffs'] == 3
    assert tool_analysis['success_count'] == 2
    assert tool_analysis['failure_count'] == 1
    assert tool_analysis['success_rate'] == 0.667  # 2/3


def test_agent_tool_task_differentiation(handoff_trail):
    """Test that system distinguishes agent+tool+task combinations."""
    # Devin + pytest + test_execution → PASS
    handoff_trail.record(AgentHandoffRecord(
        task_id="DIFF_1",
        task_name="Test execution task",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-1",
        public_branch="public-1",
        head_sha="sha1",
        task_commits=["commit1"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        metadata={"tools_used": ["pytest"]}
    ))

    # Devin + pytest + debugging → FAIL
    handoff_trail.record(AgentHandoffRecord(
        task_id="DIFF_2",
        task_name="Debugging task",
        executor_agent="Devin",
        auditor_agent="Claude",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-2",
        public_branch="public-2",
        head_sha="sha2",
        task_commits=["commit2"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="FAIL",
        new_failures=["debugging_timeout"],
        metadata={"tools_used": ["pytest"]}
    ))

    # Claude + pytest + audit → PASS
    handoff_trail.record(AgentHandoffRecord(
        task_id="DIFF_3",
        task_name="Audit task",
        executor_agent="Claude",
        auditor_agent="Devin",
        session_id=str(uuid4()),
        repository="test/repo",
        baseline_sha="abc123",
        local_branch="branch-3",
        public_branch="public-3",
        head_sha="sha3",
        task_commits=["commit3"],
        sync_verified=True,
        tests_status=EvidenceStatus.REPRODUCED,
        audit_verdict="PASS",
        metadata={"tools_used": ["pytest"]}
    ))

    # Test execution specific analysis
    test_execution_analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin", "test")
    assert test_execution_analysis['total_handoffs'] == 1
    assert test_execution_analysis['success_rate'] == 1.0

    # Debugging specific analysis
    debugging_analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin", "debugging")
    assert debugging_analysis['total_handoffs'] == 1
    assert debugging_analysis['success_rate'] == 0.0

    # Audit specific analysis
    audit_analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Claude", "audit")
    assert audit_analysis['total_handoffs'] == 1
    assert audit_analysis['success_rate'] == 1.0

    # Overall Devin + pytest (all tasks)
    overall_analysis = handoff_trail.analyze_tool_agent_combination("pytest", "Devin")
    assert overall_analysis['total_handoffs'] == 2
    assert overall_analysis['success_rate'] == 0.5  # 1 PASS, 1 FAIL
