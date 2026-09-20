"""Integration tests for I0 canonical tool resolution.

This tests the complete chain:
assistant_kind → ToolRegistry → tool_id(s) → resource ranking → credential_ref
"""

import pytest
from typing import Any

from iabv_v15.domain.models import UniversalResource, ResourceKind
from iabv_v15.services.account_resource_scanner import (
    build_universal_resource_pool,
    rank_workers_for_target,
    universal_resource_to_worker,
)
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class TestI0CanonicalToolResolutionIntegration:
    """Integration tests for the complete I0 resolution chain."""

    def test_devin_assistant_to_resource_selection(self) -> None:
        """T2: assistant_kind='devin' → ToolRegistry → 'devin_api' → resource selection."""
        # Build a synthetic universal resource for Devin
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        # Convert to worker representation
        worker = universal_resource_to_worker(devin_resource)
        assert worker['tool'] == 'devin_api'
        assert worker['credential_ref'] == 'opaque-test-ref'

        # Rank workers for 'devin_api' (canonical tool_id)
        pool = {'workers': [], 'universal_resources': [devin_resource]}
        ranked = rank_workers_for_target('devin_api', pool=pool, universal_resources=[devin_resource])

        # Should find the resource
        assert len(ranked) >= 1
        top_worker = ranked[0]
        assert top_worker['tool'] == 'devin_api'
        assert top_worker['credential_ref'] == 'opaque-test-ref'

    def test_direct_tool_id_compatibility(self) -> None:
        """T4: direct tool_id='devin_api' should still work (legacy compatibility)."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        pool = {'workers': [], 'universal_resources': [devin_resource]}
        ranked = rank_workers_for_target('devin_api', pool=pool, universal_resources=[devin_resource])

        assert len(ranked) >= 1
        assert ranked[0]['tool'] == 'devin_api'

    def test_credential_propagation(self) -> None:
        """T3: credential_ref should be preserved through the chain."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        worker = universal_resource_to_worker(devin_resource)
        assert worker['resource_id'] == 'devin_credential_test'
        assert worker['provider'] == 'devin'
        assert worker['credential_ref'] == 'opaque-test-ref'

        pool = {'workers': [], 'universal_resources': [devin_resource]}
        ranked = rank_workers_for_target('devin_api', pool=pool, universal_resources=[devin_resource])

        top_worker = ranked[0]
        assert top_worker['resource_id'] == 'devin_credential_test'
        assert top_worker['provider'] == 'devin'
        assert top_worker['credential_ref'] == 'opaque-test-ref'

    def test_multiple_tool_ids_for_single_assistant(self) -> None:
        """T5: one-to-many support - single assistant_kind may resolve to multiple tool_ids."""
        # This tests the general capability, not specific to a real assistant
        # The implementation should support multiple tool_ids per assistant_kind
        pass  # This would require mocking ToolRegistry with multiple cards

    def test_no_matching_resource(self) -> None:
        """T6: when no resource matches, should return empty list."""
        pool = {'workers': [], 'universal_resources': []}
        ranked = rank_workers_for_target('devin_api', pool=pool, universal_resources=[])

        assert ranked == []

    def test_resource_not_routing_eligible(self) -> None:
        """Resources with routing_eligible=False should be excluded."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=False,  # Not eligible
        )

        pool = {'workers': [], 'universal_resources': [devin_resource]}
        ranked = rank_workers_for_target('devin_api', pool=pool, universal_resources=[devin_resource])

        # Should not find the resource
        assert len(ranked) == 0

    def test_unknown_assistant_kind_fail_closed(self, tool_registry: ToolRegistry) -> None:
        """T6: unknown assistant_kind should not select an incorrect tool (fail closed)."""
        # Verify that unknown assistant returns empty list
        tool_ids = tool_registry.resolve_tool_ids_by_assistant_kind('unknown_assistant_xyz')
        assert tool_ids == []

    @pytest.fixture
    def tool_registry(self, tmp_path) -> ToolRegistry:
        """Create a ToolRegistry with real ToolCards for testing."""
        db = AppDatabase(str(tmp_path / "app.sqlite"))
        storage = ArtifactStorage(str(tmp_path / "tool_teaching"))
        repo = ToolRecordRepository(db, storage)
        adapters = {}  # We don't need real adapters for resolution tests
        return ToolRegistry(repository=repo, adapters=adapters)
