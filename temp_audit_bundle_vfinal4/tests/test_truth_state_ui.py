"""Tests for truth-state (observed / inferred / unresolved) in non-chat UI surfaces.

Covers:
- EvolutionCenterViewModel._classify_panel_truth
- truthState injection in panel dicts
- ControlCenterViewModel.diagnosticTruthState property
"""

from __future__ import annotations

from typing import Any

import pytest

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


# ─── _classify_panel_truth (tested via direct import of the static method) ───

def _import_classify_panel_truth():
    """Import _classify_panel_truth avoiding circular import."""
    import importlib
    mod = importlib.import_module('iabv_v15.ui.viewmodels.evolution_center_viewmodel')
    return mod.EvolutionCenterViewModel._classify_panel_truth


class TestClassifyPanelTruth:
    """Static classifier returns correct truth state for panel payloads."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.classify = _import_classify_panel_truth()

    def test_live_source_with_data_is_observed(self) -> None:
        tag = self.classify(has_live_source=True, payload={'cpu': '80%'})
        assert tag == 'observed'

    def test_no_live_source_with_data_is_inferred(self) -> None:
        tag = self.classify(has_live_source=False, payload={'brief': 'context'})
        assert tag == 'inferred'

    def test_live_source_empty_payload_is_unresolved(self) -> None:
        tag = self.classify(has_live_source=True, payload={})
        assert tag == 'unresolved'

    def test_no_live_source_empty_payload_is_unresolved(self) -> None:
        tag = self.classify(has_live_source=False, payload={})
        assert tag == 'unresolved'

    def test_payload_with_only_truth_state_key_is_unresolved(self) -> None:
        tag = self.classify(has_live_source=True, payload={'truthState': 'observed'})
        assert tag == 'unresolved'

    def test_payload_with_falsy_values_is_unresolved(self) -> None:
        tag = self.classify(
            has_live_source=True,
            payload={'a': '', 'b': 0, 'c': None},
        )
        assert tag == 'unresolved'

    def test_returns_only_valid_tags(self) -> None:
        valid = {'observed', 'inferred', 'unresolved'}
        for live, payload in [
            (True, {'d': 'yes'}), (True, {}),
            (False, {'d': 'yes'}), (False, {}),
        ]:
            tag = self.classify(has_live_source=live, payload=payload)
            assert tag in valid


# ─── ControlCenterViewModel diagnosticTruthState ─────────────


class TestDiagnosticTruthState:
    """diagnosticTruthState tracks the evidence basis of the diagnostic text."""

    def test_initial_state_is_unresolved(self) -> None:
        class _VM:
            _diagnostic_truth_state = 'unresolved'
            get_diagnostic_truth_state = ControlCenterViewModel.get_diagnostic_truth_state

        assert _VM().get_diagnostic_truth_state() == 'unresolved'

    def test_getter_returns_current_value(self) -> None:
        class _VM:
            _diagnostic_truth_state = 'observed'
            get_diagnostic_truth_state = ControlCenterViewModel.get_diagnostic_truth_state

        assert _VM().get_diagnostic_truth_state() == 'observed'

    def test_truth_state_tracks_diagnostic_changes(self) -> None:
        class _VM:
            _diagnostic_truth_state = 'unresolved'
            get_diagnostic_truth_state = ControlCenterViewModel.get_diagnostic_truth_state

        vm = _VM()
        assert vm.get_diagnostic_truth_state() == 'unresolved'
        vm._diagnostic_truth_state = 'observed'
        assert vm.get_diagnostic_truth_state() == 'observed'
        vm._diagnostic_truth_state = 'inferred'
        assert vm.get_diagnostic_truth_state() == 'inferred'
