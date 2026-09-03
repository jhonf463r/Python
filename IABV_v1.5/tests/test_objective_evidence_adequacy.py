"""Focused tests for objective evidence extraction and adequacy wiring.

These tests verify that ADEQUATE is ONLY reachable when there is
independently observable evidence that the task's declared objective
was addressed.

DO NOT use execution success, model confidence, or LLM judgment
as proof of objective satisfaction.
"""

import pytest

from iabv_v15.services.adaptive.objective_evidence import extract_objective_evidence
from iabv_v15.services.lab.adequacy_computation import compute_adequacy, AdequacyClassification


class TestObjectiveEvidenceExtraction:
    """Test conservative objective evidence extraction logic."""

    def test_matching_expected_outcome_returns_true_observed(self):
        """Scenario A: expected_outcome + matching observed result."""
        expected = "file created"
        observed = "file created successfully"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is True
        assert objective_addressed_is_observed is True

    def test_mismatching_expected_outcome_returns_false(self):
        """Scenario B: expected_outcome present but observed result does not match."""
        expected = "file created"
        observed = "error occurred during execution"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is False
        assert objective_addressed_is_observed is False

    def test_missing_expected_outcome_returns_false(self):
        """Scenario C: expected_outcome missing."""
        expected = ""
        observed = "file created successfully"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is False
        assert objective_addressed_is_observed is False

    def test_empty_expected_outcome_whitespace_only(self):
        """Scenario C: expected_outcome is whitespace only."""
        expected = "   "
        observed = "file created successfully"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is False
        assert objective_addressed_is_observed is False

    def test_missing_observed_summary_returns_false(self):
        """Scenario D: successful execution but no observed summary."""
        expected = "file created"
        observed = ""
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is False
        assert objective_addressed_is_observed is False

    def test_case_insensitive_containment(self):
        """Test that containment check is case-insensitive."""
        expected = "File Created"
        observed = "file created successfully"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is True
        assert objective_addressed_is_observed is True

    def test_whitespace_insensitive_containment(self):
        """Test that containment check is whitespace-insensitive."""
        expected = "  file created  "
        observed = "file created successfully"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is True
        assert objective_addressed_is_observed is True


class TestAdequacyWithObjectiveEvidence:
    """Test that adequacy computation respects objective evidence."""

    def test_adequate_reachable_with_evidence(self):
        """Scenario A: ADEQUATE can be reached when evidence is present."""
        classification, reason = compute_adequacy(
            expected_summary="file created",
            observed_summary="file created successfully",
            success=True,
            precision=0.9,
            robustness=0.8,
            user_progress=0.8,
            objective_addressed=True,
            objective_addressed_is_observed=True,
        )
        
        assert classification == AdequacyClassification.ADEQUATE
        assert "independently observed objective addressed" in reason

    def test_not_adequate_without_evidence(self):
        """Scenario B: NOT ADEQUATE when evidence does not match."""
        classification, reason = compute_adequacy(
            expected_summary="file created",
            observed_summary="error occurred",
            success=True,
            precision=0.9,
            robustness=0.8,
            user_progress=0.8,
            objective_addressed=False,
            objective_addressed_is_observed=False,
        )
        
        assert classification != AdequacyClassification.ADEQUATE

    def test_not_adequate_missing_expected(self):
        """Scenario C: NOT ADEQUATE when expected outcome is missing."""
        classification, reason = compute_adequacy(
            expected_summary="",
            observed_summary="file created successfully",
            success=True,
            precision=0.9,
            robustness=0.8,
            user_progress=0.8,
            objective_addressed=False,
            objective_addressed_is_observed=False,
        )
        
        assert classification == AdequacyClassification.INCONCLUSIVE
        assert "no expected objective" in reason

    def test_not_adequate_success_without_evidence(self):
        """Scenario D: NOT ADEQUATE when success=True but no objective evidence."""
        classification, reason = compute_adequacy(
            expected_summary="file created",
            observed_summary="operation completed",
            success=True,
            precision=0.9,
            robustness=0.8,
            user_progress=0.8,
            objective_addressed=False,
            objective_addressed_is_observed=False,
        )
        
        assert classification != AdequacyClassification.ADEQUATE

    def test_not_adequate_high_confidence_without_evidence(self):
        """Scenario E: NOT ADEQUATE when confidence is high but no objective evidence."""
        classification, reason = compute_adequacy(
            expected_summary="file created",
            observed_summary="operation completed",
            success=True,
            precision=0.95,  # High precision
            robustness=0.9,
            user_progress=0.9,
            objective_addressed=False,
            objective_addressed_is_observed=False,
        )
        
        assert classification != AdequacyClassification.ADEQUATE

    def test_caller_assertion_not_accepted(self):
        """Scenario: objective_addressed=True but not observed is rejected."""
        classification, reason = compute_adequacy(
            expected_summary="file created",
            observed_summary="file created successfully",
            success=True,
            precision=0.9,
            robustness=0.8,
            user_progress=0.8,
            objective_addressed=True,  # Caller assertion
            objective_addressed_is_observed=False,  # Not independently observed
        )
        
        assert classification == AdequacyClassification.INCONCLUSIVE
        assert "caller assertion" in reason

    def test_anti_bypass_success_does_not_imply_objective(self):
        """Anti-bypass test: success=True does NOT imply objective_addressed=True."""
        # This test explicitly proves that execution success is not accepted
        # as proof of objective satisfaction
        classification, reason = compute_adequacy(
            expected_summary="file created",
            observed_summary="operation completed",  # No evidence of file creation
            success=True,  # Execution succeeded
            precision=0.9,
            robustness=0.8,
            user_progress=0.8,
            objective_addressed=False,  # Must remain False
            objective_addressed_is_observed=False,  # Must remain False
        )
        
        assert classification != AdequacyClassification.ADEQUATE


class TestConservativeSemantics:
    """Test that the implementation maintains conservative semantics."""

    def test_no_false_positive_from_partial_match(self):
        """Partial matches should not produce false positives."""
        expected = "delete specific file"
        observed = "file created"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is False
        assert objective_addressed_is_observed is False

    def test_no_false_positive_from_generic_success(self):
        """Generic success messages should not produce false positives."""
        expected = "delete specific file"
        observed = "operation completed successfully"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        assert objective_addressed is False
        assert objective_addressed_is_observed is False

    def test_exact_match_required(self):
        """Exact textual containment is required for evidence."""
        expected = "file deleted"
        observed = "file removed"
        
        objective_addressed, objective_addressed_is_observed = extract_objective_evidence(
            expected_summary=expected,
            observed_summary=observed,
        )
        
        # "file deleted" is not in "file removed"
        assert objective_addressed is False
        assert objective_addressed_is_observed is False
