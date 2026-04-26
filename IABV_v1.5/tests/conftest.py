"""Global test fixtures for IABV v1.5 test suite."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_intent_learning_layer():
    """Reset the global IntentLearningLayer singleton before each test.

    The learning layer is a module-level singleton that persists across
    tests. Without this reset, patterns recorded by one test (e.g. via
    _seed_wplay_teaching → orchestrator.handle_request) pollute the
    classification of subsequent tests, causing spurious failures.
    """
    from iabv_v15.services.adaptive.intent_understanding_service import (
        _intent_learning_layer,
    )
    _intent_learning_layer.clear()
    yield
    _intent_learning_layer.clear()
