"""Shared test fixtures — isolate singleton state between test modules."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_intent_learning_layer():
    """Reset the IntentLearningLayer singleton before each test.

    The singleton persists across tests and earlier classify() calls
    record learned patterns that contaminate later tests.  We clear
    all in-memory patterns before each test and restore the original
    snapshot after so each test sees only the patterns loaded from
    disk at import time.
    """
    from iabv_v15.services.adaptive.intent_understanding_service import (
        _intent_learning_layer,
    )
    snapshot = dict(_intent_learning_layer._patterns)
    _intent_learning_layer.clear()
    yield
    _intent_learning_layer._patterns = snapshot
