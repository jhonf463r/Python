"""
Unit tests for DevelopmentExecutionEvidence domain model.

Tests cover:
- All execution status types (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- EvidenceRef integration
- DevelopmentTestResult reference linkage
- JSON round-trip persistence
- Invariant validation (temporal, duration, test_result_id coherence)
"""

import pytest
from datetime import datetime, timezone
from iabv_v15.domain.models import (
    DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus,
    DevelopmentTestResult,
    DevelopmentTestStatus,
    EvidenceRef,
    EvidenceKind,
)


class TestDevelopmentExecutionEvidenceStatus:
    """Test all execution status types."""

    def test_pending_status(self):
        """Evidence can have PENDING status."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            execution_status=DevelopmentExecutionStatus.PENDING,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.PENDING

    def test_running_status(self):
        """Evidence can have RUNNING status."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            execution_status=DevelopmentExecutionStatus.RUNNING,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.RUNNING

    def test_completed_status(self):
        """Evidence can have COMPLETED status."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=started,
            execution_status=DevelopmentExecutionStatus.COMPLETED,
            completed_at_utc=completed,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.COMPLETED

    def test_failed_status(self):
        """Evidence can have FAILED status."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=started,
            execution_status=DevelopmentExecutionStatus.FAILED,
            completed_at_utc=completed,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.FAILED

    def test_cancelled_status(self):
        """Evidence can have CANCELLED status."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=started,
            execution_status=DevelopmentExecutionStatus.CANCELLED,
            completed_at_utc=completed,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.CANCELLED


class TestDevelopmentExecutionEvidenceEvidenceRef:
    """Test EvidenceRef integration."""

    def test_evidence_refs_list(self):
        """Evidence can have multiple EvidenceRef entries."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id="test-123",
                ),
                EvidenceRef(
                    kind=EvidenceKind.LOG,
                    label="Execution log",
                    ref_id="log-456",
                ),
            ],
        )
        assert len(evidence.evidence_refs) == 2
        assert evidence.evidence_refs[0].kind == EvidenceKind.DEVELOPMENT_TEST
        assert evidence.evidence_refs[1].kind == EvidenceKind.LOG

    def test_evidence_refs_empty(self):
        """Evidence can have empty evidence_refs list."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            evidence_refs=[],
        )
        assert evidence.evidence_refs == []


class TestDevelopmentExecutionEvidenceTestResultReference:
    """Test DevelopmentTestResult reference."""

    def test_test_result_id(self):
        """Evidence can reference a DevelopmentTestResult by ID."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id="test-result-123",
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id="test-result-123",
                )
            ],
        )
        assert evidence.test_result_id == "test-result-123"

    def test_test_result_id_none(self):
        """test_result_id can be None."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=None,
        )
        assert evidence.test_result_id is None


class TestDevelopmentExecutionEvidencePersistence:
    """Test JSON round-trip persistence."""

    def test_json_round_trip(self):
        """JSON serialization and deserialization preserves all fields."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        
        original = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            base_commit="abc123",
            result_commit="def456",
            changed_files=["src/main.py"],
            executor_id="agent-001",
            started_at_utc=started,
            completed_at_utc=completed,
            duration_seconds=300.0,
            execution_status=DevelopmentExecutionStatus.COMPLETED,
            test_result_id="test-123",
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id="test-123",
                )
            ],
            metadata={"key": "value"},
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentExecutionEvidence(**json_data)

        assert restored.evidence_id == original.evidence_id
        assert restored.repository == original.repository
        assert restored.base_commit == original.base_commit
        assert restored.result_commit == original.result_commit
        assert restored.changed_files == original.changed_files
        assert restored.executor_id == original.executor_id
        assert restored.started_at_utc == original.started_at_utc
        assert restored.completed_at_utc == original.completed_at_utc
        assert restored.duration_seconds == original.duration_seconds
        assert restored.execution_status == original.execution_status
        assert restored.test_result_id == original.test_result_id
        assert restored.metadata == original.metadata


class TestDevelopmentExecutionEvidenceInvariants:
    """Test invariant validation."""

    def test_non_terminal_state_cannot_have_completed_at(self):
        """Non-terminal states must not have completed_at_utc."""
        completed = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="PENDING cannot have completed_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                execution_status=DevelopmentExecutionStatus.PENDING,
                completed_at_utc=completed,
            )

    def test_negative_duration_rejected(self):
        """Negative duration_seconds is rejected."""
        with pytest.raises(ValueError, match="duration_seconds cannot be negative"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                duration_seconds=-1.0,
            )

    def test_zero_duration_valid(self):
        """Zero duration_seconds is valid."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            duration_seconds=0.0,
        )
        assert evidence.duration_seconds == 0.0

    def test_test_result_id_requires_evidence_ref(self):
        """test_result_id requires corresponding DEVELOPMENT_TEST evidence_ref."""
        with pytest.raises(ValueError, match="test_result_id requires corresponding DEVELOPMENT_TEST evidence_ref"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                test_result_id="test-123",
                evidence_refs=[],
            )

    def test_empty_changed_file_rejected(self):
        """Empty string in changed_files is rejected."""
        with pytest.raises(ValueError, match="changed_files cannot contain empty or whitespace-only strings"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                changed_files=["", "src/main.py"],
            )

    def test_whitespace_changed_file_rejected(self):
        """Whitespace-only string in changed_files is rejected."""
        with pytest.raises(ValueError, match="changed_files cannot contain empty or whitespace-only strings"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                changed_files=["  ", "src/main.py"],
            )


class TestDevelopmentExecutionEvidenceTestResultLinkage:
    """Test verifiable linkage with DevelopmentTestResult."""

    def test_evidence_links_to_test_result(self):
        """DevelopmentExecutionEvidence can link to DevelopmentTestResult via test_result_id."""
        # Create a DevelopmentTestResult
        test_result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create evidence that references it
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result.test_result_id,
                )
            ],
        )
        
        # Verify the linkage
        assert evidence.test_result_id == test_result.test_result_id
        assert evidence.evidence_refs[0].ref_id == test_result.test_result_id
        assert evidence.evidence_refs[0].kind == EvidenceKind.DEVELOPMENT_TEST
