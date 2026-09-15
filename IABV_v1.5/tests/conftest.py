"""Shared test fixtures — isolate persistent learning state between tests."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_intent_learning_layer(tmp_path, monkeypatch):
    """Give default intent services a distinct caller-owned data directory."""
    monkeypatch.setenv('IABV_DATA_DIR', str(tmp_path / 'intent_learning_data'))
    yield
