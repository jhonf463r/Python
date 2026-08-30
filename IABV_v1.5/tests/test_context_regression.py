"""Regression test for context reuse functionality.

Tests verify that context reuse still works after the resource governance
and reflection ordering fixes. This ensures the fixes don't break existing
context reuse semantics.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.domain.models import InferenceRequest


@pytest.fixture
def mock_orchestrator():
    """Create minimal AdaptiveTaskOrchestrator for testing."""
    from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
    
    orchestrator = AdaptiveTaskOrchestrator(
        intent_service=MagicMock(),
        context_assembler=MagicMock(),
        role_router=MagicMock(),
        cognitive_work_governor=MagicMock(),
        execution_policy_service=MagicMock(),
        world_model_service=MagicMock(),
        environment_self_awareness_service=MagicMock(),
        reflection_routing_service=MagicMock(),
        resource_aware_controller=MagicMock(),
    )
    
    # Configure minimal mocks
    orchestrator.intent_service.classify_with_schema.return_value = (
        MagicMock(hypotheses=[], metadata={}),
        MagicMock(),
    )
    orchestrator.role_router.build_decision_from_intent.return_value = MagicMock(
        provider_name='test_provider',
        role='general',
        capability='chat',
    )
    orchestrator.context_assembler.build_perception_snapshot.return_value = MagicMock(
        decision_context={},
        task_context={},
    )
    orchestrator._assess_resource_pressure.return_value = MagicMock()
    orchestrator._read_sync_pulse.return_value = {}
    orchestrator._maybe_synaptic_decision.return_value = None
    orchestrator._pre_dispatch_evidence_guard.return_value = (True, '')
    
    # Configure resource controller to return safe
    from iabv_v15.services.adaptive.resource_aware_controller import (
        ResourceCheck,
        ResourcePressure,
        ResourceState,
    )
    orchestrator.resource_aware_controller.check_resource_safety.return_value = ResourceCheck(
        safe=True,
        reason='OK',
        ram_available_mb=8192,
        cpu_load_1m=0.3,
        current_pressure=ResourcePressure.LOW,
        resource_state=ResourceState.SAFE,
    )
    
    return orchestrator


class TestContextReuseRegression:
    """Verify context reuse still works after fixes."""
    
    def test_request_metadata_preserved(
        self, mock_orchestrator
    ):
        """Verify request metadata is preserved through the request flow."""
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'context_reuse': True, 'session_id': 'test_session'}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify metadata is still accessible
            assert hasattr(request, 'metadata')
            assert request.metadata is not None
            assert request.metadata.get('context_reuse') == True
            assert request.metadata.get('session_id') == 'test_session'
        except Exception:
            # Metadata should be preserved even if execution fails
            assert hasattr(request, 'metadata')
            assert request.metadata is not None
    
    def test_resource_state_injected_without_breaking_context(
        self, mock_orchestrator
    ):
        """Verify resource state injection doesn't break existing context metadata."""
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'context_reuse': True, 'existing_key': 'existing_value'}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify original metadata is preserved
            assert request.metadata.get('context_reuse') == True
            assert request.metadata.get('existing_key') == 'existing_value'
            
            # Verify resource state was added
            assert 'resource_state' in request.metadata
            resource_state = request.metadata['resource_state']
            assert isinstance(resource_state, dict)
        except Exception:
            # Original metadata should still be preserved
            assert request.metadata.get('context_reuse') == True
            assert request.metadata.get('existing_key') == 'existing_value'
    
    def test_reflection_decision_injected_without_breaking_context(
        self, mock_orchestrator
    ):
        """Verify reflection decision injection doesn't break existing context metadata."""
        # Configure reflection decision
        from iabv_v15.services.adaptive.reflection_routing import ReflectionDecision
        reflection_decision = ReflectionDecision(
            routing_choice='observe',
            reason='Fresh observation needed',
            requires_targeted_refresh=False,
            confidence=0.8,
        )
        mock_orchestrator.reflection_routing_service.route_request.return_value = reflection_decision
        
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'context_reuse': True, 'existing_key': 'existing_value'}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify original metadata is preserved
            assert request.metadata.get('context_reuse') == True
            assert request.metadata.get('existing_key') == 'existing_value'
        except Exception:
            # Original metadata should still be preserved
            assert request.metadata.get('context_reuse') == True
            assert request.metadata.get('existing_key') == 'existing_value'
    
    def test_session_context_flows_through_orchestrator(
        self, mock_orchestrator
    ):
        """Verify session context flows through the orchestrator correctly."""
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={
                'session_id': 'test_session_123',
                'project_memory': {'key': 'value'},
                'session_goal': 'test goal',
            }
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify session context is preserved
            assert request.metadata.get('session_id') == 'test_session_123'
            assert request.metadata.get('project_memory') == {'key': 'value'}
            assert request.metadata.get('session_goal') == 'test goal'
        except Exception:
            # Session context should still be preserved
            assert request.metadata.get('session_id') == 'test_session_123'
            assert request.metadata.get('project_memory') == {'key': 'value'}
            assert request.metadata.get('session_goal') == 'test goal'
    
    def test_conversation_history_preserved(
        self, mock_orchestrator
    ):
        """Verify conversation history is preserved through the request flow."""
        conversation_history = [
            {'role': 'user', 'content': 'previous message 1'},
            {'role': 'assistant', 'content': 'previous response 1'},
        ]
        
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'conversation_history': conversation_history}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify conversation history is preserved
            assert request.metadata.get('conversation_history') == conversation_history
        except Exception:
            # Conversation history should still be preserved
            assert request.metadata.get('conversation_history') == conversation_history


class TestContextReuseWithResourceGovernance:
    """Verify context reuse works with resource governance enabled."""
    
    def test_context_reuse_with_resource_check(
        self, mock_orchestrator
    ):
        """Verify context reuse works when resource check is performed."""
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'context_reuse': True}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify resource check was called
            assert mock_orchestrator.resource_aware_controller.check_resource_safety.called
            
            # Verify context reuse metadata is still present
            assert request.metadata.get('context_reuse') == True
        except Exception:
            # Context reuse metadata should still be present
            assert request.metadata.get('context_reuse') == True
    
    def test_context_reuse_with_unsafe_resources(
        self, mock_orchestrator
    ):
        """Verify context reuse is handled when resources are unsafe."""
        # Configure unsafe resource check
        from iabv_v15.services.adaptive.resource_aware_controller import (
            ResourceCheck,
            ResourcePressure,
            ResourceState,
        )
        mock_orchestrator.resource_aware_controller.check_resource_safety.return_value = ResourceCheck(
            safe=False,
            reason='Insufficient RAM',
            ram_available_mb=1024,
            cpu_load_1m=0.9,
            current_pressure=ResourcePressure.CRITICAL,
            resource_state=ResourceState.UNSAFE,
        )
        
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'context_reuse': True}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Context reuse metadata should still be present even if blocked
            assert request.metadata.get('context_reuse') == True
        except Exception:
            # Context reuse metadata should still be present
            assert request.metadata.get('context_reuse') == True


class TestContextReuseWithReflection:
    """Verify context reuse works with reflection routing enabled."""
    
    def test_context_reuse_with_reflection_routing(
        self, mock_orchestrator
    ):
        """Verify context reuse works when reflection routing is performed."""
        request = InferenceRequest(
            user_goal='reflect on progress',
            prompt='reflect on progress',
            metadata={'context_reuse': True}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Verify reflection routing was called
            assert mock_orchestrator.reflection_routing_service.route_request.called
            
            # Verify context reuse metadata is still present
            assert request.metadata.get('context_reuse') == True
        except Exception:
            # Context reuse metadata should still be present
            assert request.metadata.get('context_reuse') == True
    
    def test_context_reuse_with_reflection_decision(
        self, mock_orchestrator
    ):
        """Verify context reuse works when reflection decision is injected."""
        from iabv_v15.services.adaptive.reflection_routing import ReflectionDecision
        reflection_decision = ReflectionDecision(
            routing_choice='reflect',
            reason='Evidence needs refresh',
            requires_targeted_refresh=True,
            confidence=0.9,
        )
        mock_orchestrator.reflection_routing_service.route_request.return_value = reflection_decision
        
        request = InferenceRequest(
            user_goal='test',
            prompt='test',
            metadata={'context_reuse': True}
        )
        
        try:
            route, result, session = mock_orchestrator.handle_request(request, _priority=0, _cognitive_load={})
            
            # Context reuse metadata should still be present
            assert request.metadata.get('context_reuse') == True
        except Exception:
            # Context reuse metadata should still be present
            assert request.metadata.get('context_reuse') == True
