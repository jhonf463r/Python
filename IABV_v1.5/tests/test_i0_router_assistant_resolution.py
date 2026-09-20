"""Router-level tests for I0 canonical tool resolution.

These tests exercise the complete chain through LocalRoleRouter.worker_health_gate():
assistant_kind → ToolRegistry → tool_id(s) → resource ranking → credential_ref
"""

import pytest
from typing import Any

from iabv_v15.domain.models import UniversalResource, ResourceKind, ToolCard, ToolType
from iabv_v15.services.account_resource_scanner import (
    build_universal_resource_pool,
    rank_workers_for_target,
    universal_resource_to_worker,
)
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage


class TestI0RouterAssistantResolution:
    """Router-level tests for the complete I0 resolution chain."""

    @pytest.fixture
    def mock_scanner(self):
        """Create a mock scanner that can be configured to return a specific pool."""
        pool = {'workers': [], 'universal_resources': [], 'available_count': 0}

        def scanner():
            return pool

        def set_pool(resources_and_count):
            pool['universal_resources'] = resources_and_count.get('universal_resources', [])
            pool['available_count'] = resources_and_count.get('available_count', 0)
            # Convert universal resources to workers
            from iabv_v15.services.account_resource_scanner import universal_resource_to_worker
            pool['workers'] = [
                universal_resource_to_worker(r)
                for r in pool['universal_resources']
            ]

        scanner.set_pool = set_pool
        return scanner

    @pytest.fixture
    def tool_registry(self, tmp_path) -> ToolRegistry:
        """Create a ToolRegistry with real ToolCards for testing."""
        db = AppDatabase(str(tmp_path / "app.sqlite"))
        storage = ArtifactStorage(str(tmp_path / "tool_teaching"))
        repo = ToolRecordRepository(db, storage)
        adapters = {}
        registry = ToolRegistry(repository=repo, adapters=adapters)

        # Seed with a Devin ToolCard for testing
        devin_card = ToolCard(
            tool_id='devin_api',
            tool_type=ToolType.CUSTOM,
            title='Devin API',
            description='Devin API tool',
            adapter_key='devin_api',
            metadata={'assistant_kind': 'devin'},
        )
        repo.save_card(devin_card)

        return registry

    @pytest.fixture
    def router(self, tool_registry, mock_scanner, tmp_path) -> LocalRoleRouter:
        """Create a LocalRoleRouter with ToolRegistry injected."""
        # Create minimal mock dependencies
        class MockRunRepository:
            pass

        class MockArtifactRepository:
            pass

        router = LocalRoleRouter(
            workspace_root=str(tmp_path),
            general_provider=None,
            visual_provider=None,
            optional_provider=None,
            embedding_service=None,
            sql_service=None,
            analytics_service=None,
            customer_support_service=None,
            engineering_review_service=None,
            teaching_gap_analyzer=None,
            episode_repository=None,
            knowledge_repository=None,
            run_repository=MockRunRepository(),
            artifact_repository=MockArtifactRepository(),
            tool_teach_service=None,
            tool_registry=tool_registry,
            account_resource_scanner=mock_scanner,
            account_approval_ledger=None,
        )
        return router

    def test_t1_router_assistant_resolution(self, router: LocalRoleRouter, mock_scanner) -> None:
        """T1: router.worker_health_gate('devin') resolves through ToolRegistry."""
        # Create a synthetic pool with a devin_api resource
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [devin_resource],
            'available_count': 1,
        })

        # Call worker_health_gate with assistant_kind='devin'
        result = router.worker_health_gate(target_assistant='devin')

        # Should successfully resolve and rank the devin_api resource
        assert result['usable'] is True
        assert 'top_worker' in result
        top_worker = result['top_worker']
        assert top_worker['tool'] == 'devin_api'
        assert top_worker['credential_ref'] == 'opaque-test-ref'

    def test_t2_credential_propagation_through_router(self, router: LocalRoleRouter, mock_scanner) -> None:
        """T2: credential_ref survives through the router-level flow."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [devin_resource],
            'available_count': 1,
        })

        result = router.worker_health_gate(target_assistant='devin')

        assert result['usable'] is True
        top_worker = result['top_worker']
        assert top_worker['resource_id'] == 'devin_credential_test'
        assert top_worker['provider'] == 'devin'
        assert top_worker['credential_ref'] == 'opaque-test-ref'

    def test_t3_direct_tool_id_compatibility(self, router: LocalRoleRouter, mock_scanner) -> None:
        """T3: direct tool_id='devin_api' works through router."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [devin_resource],
            'available_count': 1,
        })

        result = router.worker_health_gate(target_assistant='devin_api')

        assert result['usable'] is True
        assert result['top_worker']['tool'] == 'devin_api'

    def test_t4_no_target_regression(self, router: LocalRoleRouter, mock_scanner) -> None:
        """T4: no-target (empty string) ranks all eligible workers."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [devin_resource],
            'available_count': 1,
        })

        result = router.worker_health_gate(target_assistant='')

        # Should rank all workers when no target is specified
        assert result['usable'] is True
        assert 'top_worker' in result

    def test_t5_unknown_assistant_fail_closed(self, router: LocalRoleRouter, mock_scanner) -> None:
        """T5: unknown assistant_kind does not select unrelated worker."""
        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [devin_resource],
            'available_count': 1,
        })

        result = router.worker_health_gate(target_assistant='unknown_assistant_xyz')

        # Should not select an unrelated worker (fail closed)
        assert result['usable'] is False
        assert 'No hay worker usable para unknown_assistant_xyz' in result['reason']

    def test_t6_resolver_error_fail_closed(self, router: LocalRoleRouter, mock_scanner) -> None:
        """T6: ToolRegistry resolution error does not select unrelated worker."""
        # Temporarily break the resolver to simulate an error
        original_resolve = router.tool_registry.resolve_tool_ids_by_assistant_kind

        def broken_resolve(assistant_kind: str) -> list[str]:
            raise RuntimeError("Simulated resolver error")

        router.tool_registry.resolve_tool_ids_by_assistant_kind = broken_resolve

        devin_resource = UniversalResource(
            resource_id='devin_credential_test',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-test-ref',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [devin_resource],
            'available_count': 1,
        })

        result = router.worker_health_gate(target_assistant='devin')

        # Should fail closed on resolver error
        assert result['usable'] is False

        # Restore original resolver
        router.tool_registry.resolve_tool_ids_by_assistant_kind = original_resolve

    def test_t7_one_to_many_router_behavior(self, tool_registry: ToolRegistry, mock_scanner, tmp_path) -> None:
        """T7: router handles one-to-many assistant_kind → tool_id mappings."""
        # Add multiple ToolCards for the same assistant_kind
        devin_card1 = ToolCard(
            tool_id='devin_api',
            tool_type=ToolType.CUSTOM,
            title='Devin API',
            description='Devin API tool',
            adapter_key='devin_api',
            metadata={'assistant_kind': 'devin'},
        )
        devin_card2 = ToolCard(
            tool_id='devin_api_v2',
            tool_type=ToolType.CUSTOM,
            title='Devin API V2',
            description='Devin API V2 tool',
            adapter_key='devin_api_v2',
            metadata={'assistant_kind': 'devin'},
        )
        tool_registry.repository.save_card(devin_card1)
        tool_registry.repository.save_card(devin_card2)

        # Create router with updated registry
        class MockRunRepository:
            pass

        class MockArtifactRepository:
            pass

        router = LocalRoleRouter(
            workspace_root=str(tmp_path),
            general_provider=None,
            visual_provider=None,
            optional_provider=None,
            embedding_service=None,
            sql_service=None,
            analytics_service=None,
            customer_support_service=None,
            engineering_review_service=None,
            teaching_gap_analyzer=None,
            episode_repository=None,
            knowledge_repository=None,
            run_repository=MockRunRepository(),
            artifact_repository=MockArtifactRepository(),
            tool_teach_service=None,
            tool_registry=tool_registry,
            account_resource_scanner=mock_scanner,
            account_approval_ledger=None,
        )

        # Create resources for both tool_ids
        resource1 = UniversalResource(
            resource_id='devin_v1',
            provider='devin',
            tool_id='devin_api',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-ref-v1',
            routing_eligible=True,
        )
        resource2 = UniversalResource(
            resource_id='devin_v2',
            provider='devin',
            tool_id='devin_api_v2',
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref='opaque-ref-v2',
            routing_eligible=True,
        )

        mock_scanner.set_pool({
            'workers': [],
            'universal_resources': [resource1, resource2],
            'available_count': 2,
        })

        result = router.worker_health_gate(target_assistant='devin')

        # Should rank candidates across both resolved tool_ids
        assert result['usable'] is True
        assert 'top_worker' in result
        # The top worker should be one of the two resources
        assert result['top_worker']['tool'] in ['devin_api', 'devin_api_v2']
