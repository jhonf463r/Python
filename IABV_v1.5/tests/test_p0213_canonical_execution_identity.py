"""P0.213 Tests for CanonicalExecutionIdentity.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for canonical execution identity creation and validation.
"""
import pytest
from iabv_v15.domain.models import CanonicalExecutionIdentity


class TestCanonicalExecutionIdentity:
    """Test CanonicalExecutionIdentity creation and validation."""

    def test_valid_identity(self):
        """Test A: valid identity with all fields."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        assert identity.validate() is True
        assert identity.get_run_id() == "test_run_id"
        assert identity.get_episode_id() == "test_episode_id"
        assert identity.get_session_id() == "test_session_id"

    def test_valid_identity_with_optional_fields(self):
        """Test B: valid identity with optional None fields."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id=None,
            session_id=None
        )
        
        assert identity.validate() is True
        assert identity.get_run_id() == "test_run_id"
        assert identity.get_episode_id() is None
        assert identity.get_session_id() is None

    def test_empty_run_id_invalid(self):
        """Test C: empty run_id is invalid."""
        identity = CanonicalExecutionIdentity(
            run_id="",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        assert identity.validate() is False

    def test_whitespace_run_id_invalid(self):
        """Test D: whitespace-only run_id is invalid."""
        identity = CanonicalExecutionIdentity(
            run_id="   ",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        assert identity.validate() is False

    def test_frozen_dataclass_prevents_modification(self):
        """Test E: frozen dataclass prevents modification."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            identity.run_id = "modified_run_id"

    def test_deterministic_derivation(self):
        """Test F: identity can be derived deterministically."""
        identity1 = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        identity2 = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        assert identity1.run_id == identity2.run_id
        assert identity1.episode_id == identity2.episode_id
        assert identity1.session_id == identity2.session_id
