"""
Tests for DevelopmentTestResult model.

Tests verify:
- All status types (PASSED, FAILED, ERROR, TIMEOUT, NOT_RUN)
- Invariants (coherent states, non-negative counts)
- JSON round-trip persistence
- Commit preservation
- Exit code handling
- stdout/stderr preservation
"""

import pytest
from datetime import datetime, timezone
from iabv_v15.domain.models import (
    DevelopmentTestResult,
    DevelopmentTestStatus,
)


class TestDevelopmentTestResultStatus:
    """Test all status types."""

    def test_passed_complete(self):
        """PASSED status with complete fields."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
            duration_seconds=5.2,
            stdout="All tests passed",
            stderr="",
            test_count=10,
            passed_count=10,
            failed_count=0,
            error_count=0,
            skipped_count=0,
            commit="abc123",
        )
        assert result.status == DevelopmentTestStatus.PASSED
        assert result.exit_code == 0
        assert result.test_count == 10
        assert result.passed_count == 10
        assert result.failed_count == 0

    def test_failed_complete(self):
        """FAILED status with failed tests."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.FAILED,
            command="pytest tests/",
            exit_code=1,
            duration_seconds=3.1,
            stdout="8 passed, 2 failed",
            stderr="AssertionError in test_foo",
            test_count=10,
            passed_count=8,
            failed_count=2,
            error_count=0,
            skipped_count=0,
            commit="abc123",
        )
        assert result.status == DevelopmentTestStatus.FAILED
        assert result.exit_code == 1
        assert result.failed_count == 2

    def test_error_status(self):
        """ERROR status for execution errors."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.ERROR,
            command="pytest tests/",
            exit_code=2,
            duration_seconds=0.5,
            stdout="",
            stderr="ImportError: module not found",
            test_count=None,
            passed_count=None,
            failed_count=None,
            error_count=None,
            skipped_count=None,
            commit="abc123",
        )
        assert result.status == DevelopmentTestStatus.ERROR
        assert result.exit_code == 2

    def test_timeout_status(self):
        """TIMEOUT status with no exit code."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.TIMEOUT,
            command="pytest tests/",
            exit_code=None,  # No exit code for timeout
            duration_seconds=60.0,
            stdout="",
            stderr="Timeout after 60s",
            test_count=None,
            passed_count=None,
            failed_count=None,
            error_count=None,
            skipped_count=None,
            commit="abc123",
        )
        assert result.status == DevelopmentTestStatus.TIMEOUT
        assert result.exit_code is None

    def test_not_run_status(self):
        """NOT_RUN status without execution."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.NOT_RUN,
            command="pytest tests/",
            exit_code=None,
            duration_seconds=None,
            stdout="",
            stderr="",
            test_count=None,
            passed_count=None,
            failed_count=None,
            error_count=None,
            skipped_count=None,
            commit=None,
        )
        assert result.status == DevelopmentTestStatus.NOT_RUN
        assert result.exit_code is None
        assert result.duration_seconds is None


class TestDevelopmentTestResultInvariants:
    """Test invariant validation."""

    def test_passed_with_failed_count_rejected(self):
        """PASSED status cannot have failed_count > 0."""
        with pytest.raises(ValueError, match="PASSED status cannot have failed_count > 0"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.PASSED,
                command="pytest tests/",
                exit_code=0,
                failed_count=1,  # Invalid
            )

    def test_negative_count_rejected(self):
        """Negative test counts are rejected."""
        with pytest.raises(ValueError, match="Test counts cannot be negative"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                test_count=-1,
            )

        with pytest.raises(ValueError, match="Test counts cannot be negative"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                passed_count=-1,
            )

        with pytest.raises(ValueError, match="Test counts cannot be negative"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                failed_count=-1,
            )

        with pytest.raises(ValueError, match="Test counts cannot be negative"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                error_count=-1,
            )

        with pytest.raises(ValueError, match="Test counts cannot be negative"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                skipped_count=-1,
            )

    def test_negative_duration_rejected(self):
        """Negative duration is rejected."""
        with pytest.raises(ValueError, match="duration_seconds cannot be negative"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.PASSED,
                command="pytest tests/",
                duration_seconds=-1.0,
            )

    def test_failed_with_failed_count_zero_rejected(self):
        """FAILED status with explicit failed_count=0 is contradictory."""
        with pytest.raises(ValueError, match="FAILED status with explicit failed_count=0 is contradictory"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                exit_code=1,
                failed_count=0,  # Invalid when explicitly provided
            )

    def test_failed_with_failed_count_none_valid(self):
        """FAILED status with failed_count=None is valid (counts unknown)."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.FAILED,
            command="pytest tests/",
            exit_code=1,
            failed_count=None,  # Valid when unknown
        )
        assert result.status == DevelopmentTestStatus.FAILED
        assert result.failed_count is None

    def test_failed_with_failed_count_positive_valid(self):
        """FAILED status with failed_count > 0 is valid."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.FAILED,
            command="pytest tests/",
            exit_code=1,
            failed_count=2,
        )
        assert result.status == DevelopmentTestStatus.FAILED
        assert result.failed_count == 2

    def test_count_sum_exact_valid(self):
        """Count sum equals test_count is valid when all counters present."""
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            test_count=10,
            passed_count=9,
            failed_count=0,
            error_count=0,
            skipped_count=1,
        )
        assert result.test_count == 10
        assert result.passed_count + result.failed_count + result.error_count + result.skipped_count == 10

    def test_count_sum_greater_than_total_rejected(self):
        """Count sum greater than test_count is rejected when all counters present."""
        with pytest.raises(ValueError, match="Count sum .* does not equal test_count"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                test_count=10,
                passed_count=8,
                failed_count=1,
                error_count=5,  # Sum would be 15 > 10
                skipped_count=1,
            )

    def test_count_sum_less_than_total_rejected(self):
        """Count sum less than test_count is rejected when all counters present."""
        with pytest.raises(ValueError, match="Count sum .* does not equal test_count"):
            DevelopmentTestResult(
                status=DevelopmentTestStatus.FAILED,
                command="pytest tests/",
                test_count=10,
                passed_count=5,
                failed_count=1,
                error_count=0,
                skipped_count=1,  # Sum would be 7 < 10
            )

    def test_count_sum_with_none_counters_valid(self):
        """Count sum is not enforced when any counter is None (partial information)."""
        # This should NOT raise an error even though sum != test_count
        result = DevelopmentTestResult(
            status=DevelopmentTestStatus.FAILED,
            command="pytest tests/",
            test_count=10,
            passed_count=8,
            failed_count=1,
            error_count=None,  # Missing, so sum not enforced
            skipped_count=1,
        )
        assert result.test_count == 10
        assert result.error_count is None


class TestDevelopmentTestResultPersistence:
    """Test JSON round-trip persistence."""

    def test_json_round_trip(self):
        """JSON serialization and deserialization preserves all fields."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
            duration_seconds=5.2,
            stdout="All tests passed",
            stderr="",
            test_count=10,
            passed_count=10,
            failed_count=0,
            error_count=0,
            skipped_count=0,
            commit="abc123def456",
        )

        # Serialize
        json_data = original.model_dump(mode='json')

        # Deserialize
        restored = DevelopmentTestResult(**json_data)

        # Verify all fields preserved
        assert restored.status == original.status
        assert restored.command == original.command
        assert restored.exit_code == original.exit_code
        assert restored.duration_seconds == original.duration_seconds
        assert restored.stdout == original.stdout
        assert restored.stderr == original.stderr
        assert restored.test_count == original.test_count
        assert restored.passed_count == original.passed_count
        assert restored.failed_count == original.failed_count
        assert restored.error_count == original.error_count
        assert restored.skipped_count == original.skipped_count
        assert restored.commit == original.commit

    def test_commit_preserved(self):
        """Commit SHA is preserved through round-trip."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            commit="4720985b44fb7fae26cb9df85a3fb9459ae15e5e",
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentTestResult(**json_data)

        assert restored.commit == "4720985b44fb7fae26cb9df85a3fb9459ae15e5e"

    def test_none_commit_preserved(self):
        """None commit is preserved through round-trip."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            commit=None,
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentTestResult(**json_data)

        assert restored.commit is None

    def test_exit_code_none_preserved(self):
        """None exit code is preserved for TIMEOUT/NOT_RUN."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.TIMEOUT,
            command="pytest tests/",
            exit_code=None,
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentTestResult(**json_data)

        assert restored.exit_code is None

    def test_stdout_stderr_preserved(self):
        """stdout and stderr are preserved through round-trip."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.FAILED,
            command="pytest tests/",
            stdout="8 passed, 2 failed",
            stderr="AssertionError in test_foo\nTraceback (most recent call last):\n  File \"test_foo.py\", line 10",
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentTestResult(**json_data)

        assert restored.stdout == original.stdout
        assert restored.stderr == original.stderr

    def test_executed_at_utc_preserved(self):
        """executed_at_utc is preserved through round-trip."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentTestResult(**json_data)

        assert restored.executed_at_utc == original.executed_at_utc

    def test_metadata_preserved(self):
        """metadata dictionary is preserved through round-trip."""
        original = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            metadata={"framework": "pytest", "version": "8.0.0", "environment": "ci"},
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentTestResult(**json_data)

        assert restored.metadata == original.metadata
        assert restored.metadata["framework"] == "pytest"
        assert restored.metadata["version"] == "8.0.0"


class TestDevelopmentTestResultEvidenceIntegration:
    """Test integration with evidence system."""

    def test_can_create_evidence_ref(self):
        """DevelopmentTestResult can be referenced as evidence."""
        from iabv_v15.domain.models import EvidenceRef, EvidenceKind

        test_result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            commit="abc123",
        )

        evidence = EvidenceRef(
            kind=EvidenceKind.DEVELOPMENT_TEST,
            label="Development test result",
            ref_id=test_result.test_result_id,
        )

        assert evidence.kind == EvidenceKind.DEVELOPMENT_TEST
        assert evidence.ref_id == test_result.test_result_id
