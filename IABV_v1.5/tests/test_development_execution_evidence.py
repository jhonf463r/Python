"""
Tests for DevelopmentExecutionEvidence model.

Tests verify:
- Minimal model fields
- Complete evidence construction
- Base commit and result commit handling
- Changed files
- Timestamps and duration
- Execution status
- EvidenceRef integration
- DevelopmentTestResult reference
- JSON round-trip persistence
- Temporal invariants (completed >= started, duration >= 0)
- Empty commit rejection when explicitly supplied
- Real repository evidence
- Real test/result linkage
"""

import pytest
from datetime import datetime, timezone, timedelta
from iabv_v15.domain.models import (
    DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus,
    DevelopmentTestResult,
    DevelopmentTestStatus,
    EvidenceRef,
    EvidenceKind,
)


class TestDevelopmentExecutionEvidenceMinimal:
    """Test minimal model construction."""

    def test_minimal_model(self):
        """Evidence can be created with minimal required fields."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        assert evidence.repository == "https://github.com/example/repo"
        assert evidence.base_commit is None
        assert evidence.result_commit is None
        assert evidence.changed_files == []
        assert evidence.executor_id is None
        assert evidence.execution_status == DevelopmentExecutionStatus.PENDING
        assert evidence.test_result_id is None
        assert evidence.evidence_refs == []


class TestDevelopmentExecutionEvidenceComplete:
    """Test complete evidence construction."""

    def test_complete_evidence(self):
        """Evidence can be created with all fields populated."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            base_commit="abc123",
            result_commit="def456",
            changed_files=["src/main.py", "tests/test_main.py"],
            executor_id="agent-001",
            started_at_utc=started,
            completed_at_utc=completed,
            duration_seconds=300.0,
            execution_status=DevelopmentExecutionStatus.COMPLETED,
            test_result_id="test-result-123",
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id="test-result-123",
                )
            ],
            metadata={"framework": "pytest"},
        )
        
        assert evidence.repository == "https://github.com/example/repo"
        assert evidence.base_commit == "abc123"
        assert evidence.result_commit == "def456"
        assert evidence.changed_files == ["src/main.py", "tests/test_main.py"]
        assert evidence.executor_id == "agent-001"
        assert evidence.started_at_utc == started
        assert evidence.completed_at_utc == completed
        assert evidence.duration_seconds == 300.0
        assert evidence.execution_status == DevelopmentExecutionStatus.COMPLETED
        assert evidence.test_result_id == "test-result-123"
        assert len(evidence.evidence_refs) == 1
        assert evidence.metadata == {"framework": "pytest"}


class TestDevelopmentExecutionEvidenceCommits:
    """Test base_commit and result_commit handling."""

    def test_base_commit_only(self):
        """Evidence can have only base_commit."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            base_commit="abc123",
        )
        assert evidence.base_commit == "abc123"
        assert evidence.result_commit is None

    def test_result_commit_only(self):
        """Evidence can have only result_commit."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            result_commit="def456",
        )
        assert evidence.base_commit is None
        assert evidence.result_commit == "def456"

    def test_both_commits(self):
        """Evidence can have both commits."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            base_commit="abc123",
            result_commit="def456",
        )
        assert evidence.base_commit == "abc123"
        assert evidence.result_commit == "def456"

    def test_empty_base_commit_rejected(self):
        """Empty base_commit string is rejected when explicitly provided."""
        with pytest.raises(ValueError, match="base_commit cannot be empty"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                base_commit="",
            )

    def test_empty_result_commit_rejected(self):
        """Empty result_commit string is rejected when explicitly provided."""
        with pytest.raises(ValueError, match="result_commit cannot be empty"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                result_commit="",
            )

    def test_whitespace_base_commit_rejected(self):
        """Whitespace-only base_commit is rejected."""
        with pytest.raises(ValueError, match="base_commit cannot be empty or whitespace-only"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                base_commit="   ",
            )

    def test_tab_base_commit_rejected(self):
        """Tab-only base_commit is rejected."""
        with pytest.raises(ValueError, match="base_commit cannot be empty or whitespace-only"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                base_commit="\t",
            )

    def test_newline_base_commit_rejected(self):
        """Newline-only base_commit is rejected."""
        with pytest.raises(ValueError, match="base_commit cannot be empty or whitespace-only"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                base_commit="\n",
            )

    def test_whitespace_result_commit_rejected(self):
        """Whitespace-only result_commit is rejected."""
        with pytest.raises(ValueError, match="result_commit cannot be empty or whitespace-only"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                result_commit="   ",
            )

    def test_valid_commit_string(self):
        """Valid commit string is accepted."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            base_commit="abc123",
            result_commit="def456",
        )
        assert evidence.base_commit == "abc123"
        assert evidence.result_commit == "def456"


class TestDevelopmentExecutionEvidenceChangedFiles:
    """Test changed_files handling."""

    def test_changed_files_list(self):
        """Changed files can be listed."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            changed_files=["src/main.py", "tests/test_main.py", "README.md"],
        )
        assert evidence.changed_files == ["src/main.py", "tests/test_main.py", "README.md"]

    def test_changed_files_empty(self):
        """Changed files can be empty list."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            changed_files=[],
        )
        assert evidence.changed_files == []


class TestDevelopmentExecutionEvidenceTimestamps:
    """Test timestamp and duration handling."""

    def test_both_timestamps_none(self):
        """Both timestamps can be None (no execution started yet)."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=None,
            completed_at_utc=None,
        )
        assert evidence.started_at_utc is None
        assert evidence.completed_at_utc is None

    def test_started_at_only(self):
        """Evidence can have only started_at_utc."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=started,
        )
        assert evidence.started_at_utc == started
        assert evidence.completed_at_utc is None

    def test_completed_at_only(self):
        """Evidence can have only completed_at_utc (historical evidence) with COMPLETED status."""
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=None,
            completed_at_utc=completed,
            execution_status=DevelopmentExecutionStatus.COMPLETED,
        )
        assert evidence.started_at_utc is None
        assert evidence.completed_at_utc == completed

    def test_both_timestamps_equal(self):
        """Both timestamps can be equal (instant execution)."""
        now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=now,
            completed_at_utc=now,
            execution_status=DevelopmentExecutionStatus.COMPLETED,
        )
        assert evidence.started_at_utc == now
        assert evidence.completed_at_utc == now

    def test_completed_after_started(self):
        """completed_at_utc can be after started_at_utc."""
        started = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            started_at_utc=started,
            completed_at_utc=completed,
            execution_status=DevelopmentExecutionStatus.COMPLETED,
        )
        assert evidence.completed_at_utc > evidence.started_at_utc

    def test_completed_before_started_rejected(self):
        """completed_at_utc < started_at_utc is rejected."""
        started = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="completed_at_utc must be >= started_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                started_at_utc=started,
                completed_at_utc=completed,
                execution_status=DevelopmentExecutionStatus.COMPLETED,
            )

    def test_duration_seconds(self):
        """Duration can be specified."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            duration_seconds=123.45,
        )
        assert evidence.duration_seconds == 123.45


class TestDevelopmentExecutionEvidenceStatus:
    """Test execution_status handling."""

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
        """Evidence can have COMPLETED status with completed_at_utc."""
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            execution_status=DevelopmentExecutionStatus.COMPLETED,
            completed_at_utc=completed,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.COMPLETED

    def test_failed_status(self):
        """Evidence can have FAILED status with completed_at_utc."""
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            execution_status=DevelopmentExecutionStatus.FAILED,
            completed_at_utc=completed,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.FAILED

    def test_cancelled_status(self):
        """Evidence can have CANCELLED status with completed_at_utc."""
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            execution_status=DevelopmentExecutionStatus.CANCELLED,
            completed_at_utc=completed,
        )
        assert evidence.execution_status == DevelopmentExecutionStatus.CANCELLED

    def test_completed_status_requires_completed_at(self):
        """COMPLETED status requires completed_at_utc."""
        with pytest.raises(ValueError, match="COMPLETED requires completed_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                execution_status=DevelopmentExecutionStatus.COMPLETED,
                completed_at_utc=None,
            )

    def test_failed_status_requires_completed_at(self):
        """FAILED status requires completed_at_utc."""
        with pytest.raises(ValueError, match="FAILED requires completed_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                execution_status=DevelopmentExecutionStatus.FAILED,
                completed_at_utc=None,
            )

    def test_cancelled_status_requires_completed_at(self):
        """CANCELLED status requires completed_at_utc."""
        with pytest.raises(ValueError, match="CANCELLED requires completed_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                execution_status=DevelopmentExecutionStatus.CANCELLED,
                completed_at_utc=None,
            )

    def test_pending_status_should_not_have_completed_at(self):
        """PENDING status should not have completed_at_utc."""
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="PENDING should not have completed_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                execution_status=DevelopmentExecutionStatus.PENDING,
                completed_at_utc=completed,
            )

    def test_running_status_should_not_have_completed_at(self):
        """RUNNING status should not have completed_at_utc."""
        completed = datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="RUNNING should not have completed_at_utc"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                execution_status=DevelopmentExecutionStatus.RUNNING,
                completed_at_utc=completed,
            )


class TestDevelopmentExecutionEvidenceEvidenceRef:
    """Test EvidenceRef integration."""

    def test_evidence_refs_list(self):
        """Evidence can have multiple EvidenceRef entries (non-DEVELOPMENT_TEST kind)."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.LOG,
                    label="Execution log",
                    ref_id="log-456",
                ),
                EvidenceRef(
                    kind=EvidenceKind.ARTIFACT,
                    label="Build artifact",
                    ref_id="artifact-789",
                ),
            ],
        )
        assert len(evidence.evidence_refs) == 2
        assert evidence.evidence_refs[0].kind == EvidenceKind.LOG
        assert evidence.evidence_refs[1].kind == EvidenceKind.ARTIFACT

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
        """Evidence can reference a DevelopmentTestResult by ID with matching EvidenceRef."""
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


class TestDevelopmentExecutionEvidenceLinkageCoherence:
    """Test linkage coherence between test_result_id and DEVELOPMENT_TEST EvidenceRef."""

    def test_linkage_valid(self):
        """Valid linkage: test_result_id matches DEVELOPMENT_TEST EvidenceRef.ref_id."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id="test-123",
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id="test-123",
                )
            ],
        )
        assert evidence.test_result_id == "test-123"
        assert evidence.evidence_refs[0].ref_id == "test-123"

    def test_test_result_id_without_ref_rejected(self):
        """test_result_id present without DEVELOPMENT_TEST EvidenceRef is rejected."""
        with pytest.raises(ValueError, match="test_result_id is present but no DEVELOPMENT_TEST EvidenceRef found"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                test_result_id="test-123",
                evidence_refs=[],
            )

    def test_ref_without_test_result_id_rejected(self):
        """DEVELOPMENT_TEST EvidenceRef present without test_result_id is rejected."""
        with pytest.raises(ValueError, match="DEVELOPMENT_TEST EvidenceRef present but test_result_id is None"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                test_result_id=None,
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_TEST,
                        label="Test results",
                        ref_id="test-123",
                    )
                ],
            )

    def test_mismatched_ids_rejected(self):
        """test_result_id and EvidenceRef.ref_id must match."""
        with pytest.raises(ValueError, match="test_result_id.*does not match DEVELOPMENT_TEST EvidenceRef.ref_id"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                test_result_id="test-123",
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_TEST,
                        label="Test results",
                        ref_id="test-456",
                    )
                ],
            )

    def test_multiple_dev_test_refs_rejected(self):
        """Multiple DEVELOPMENT_TEST EvidenceRefs are rejected when test_result_id is present."""
        with pytest.raises(ValueError, match="Multiple DEVELOPMENT_TEST EvidenceRefs found"):
            DevelopmentExecutionEvidence(
                repository="https://github.com/example/repo",
                test_result_id="test-123",
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_TEST,
                        label="Test results 1",
                        ref_id="test-123",
                    ),
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_TEST,
                        label="Test results 2",
                        ref_id="test-123",
                    )
                ],
            )

    def test_no_linkage_valid(self):
        """No linkage is valid when both test_result_id and DEVELOPMENT_TEST refs are absent."""
        evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=None,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.LOG,
                    label="Execution log",
                    ref_id="log-456",
                )
            ],
        )
        assert evidence.test_result_id is None
        assert len(evidence.evidence_refs) == 1


class TestDevelopmentExecutionEvidencePersistence:
    """Test JSON round-trip persistence."""

    def test_json_round_trip(self):
        """JSON serialization and deserialization preserves all fields including EvidenceRef."""
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
                ),
                EvidenceRef(
                    kind=EvidenceKind.LOG,
                    label="Execution log",
                    ref_id="log-456",
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
        assert len(restored.evidence_refs) == 2
        assert restored.evidence_refs[0].kind == EvidenceKind.DEVELOPMENT_TEST
        assert restored.evidence_refs[0].ref_id == "test-123"
        assert restored.evidence_refs[0].label == "Test results"
        assert restored.evidence_refs[1].kind == EvidenceKind.LOG
        assert restored.evidence_refs[1].ref_id == "log-456"
        assert restored.metadata == original.metadata


class TestDevelopmentExecutionEvidenceInvariants:
    """Test invariant validation."""

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
