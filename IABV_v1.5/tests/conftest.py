"""Test configuration for P0-B V4-r4 authority tests.

F14 V4-r4 FIX: Pytest fixtures for test-only backend.

This provides test-only components that can be used in unit tests while
keeping production code fail-closed on DPAPI unavailability.
"""

import pytest
from pathlib import Path

# Import from test_key_backend directly
import sys
sys.path.insert(0, str(Path(__file__).parent))

from test_key_backend import TestKeyStorage, TestTrustStore, TestAuditAuthorityProcess


@pytest.fixture
def test_authority_key_storage(tmp_path):
    """Provide test-only key storage for unit tests."""
    return TestKeyStorage(tmp_path / "authority_keys")


@pytest.fixture
def test_trust_store(tmp_path):
    """Provide test-only trust store for unit tests."""
    return TestTrustStore(tmp_path / "authority_protected")


@pytest.fixture
def test_authority_process(tmp_path, test_authority_key_storage):
    """Provide test-only authority process for unit tests."""
    return TestAuditAuthorityProcess(tmp_path, test_authority_key_storage)