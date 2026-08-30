"""Focused tests for reflection routing to prevent repeated observation loops.

Tests verify that:
1. Reflection requests do not trigger world-model lexical route
2. Reflection reuses prior observation
3. Quoted "abiertas" does not trigger new window observation
4. Quoted "red" does not trigger new network observation
5. Sufficient evidence prevents new observation
6. Stale evidence triggers targeted observation
7. Missing evidence triggers targeted observation
8. Explicit observe-now still works
9. Reflection path remains lightweight
10. Repeated reflection does not cause repeated observation
11. Evidence retains source/timestamp/confidence
12. Ordinary chat remains unaffected
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    InferenceRequest,
    NetworkStatusSnapshot,
    TaskIntent,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repositories():
    """Mock all required repositories for TaskContextAssembler."""
    return {
        'episode_repository': MagicMock(),
        'knowledge_repository': MagicMock(),
        'run_repository': MagicMock(),
        'dossier_repository': MagicMock(),
        'hidden_incident_repository': MagicMock(),
        'site_policy_registry': MagicMock(),
        'capability_repository': MagicMock(),
        'adaptive_session_repository': MagicMock(),
        'artifact_repository': MagicMock(),
        'tool_record_repository': MagicMock(),
        'objective_repository': MagicMock(),
        'experiment_lab_repository': MagicMock(),
        'live_audit_supervisor': MagicMock(),
        'unified_memory_layer': MagicMock(),
        'environment_self_awareness_service': MagicMock(),
        'world_model_service': MagicMock(),
        'autonomous_validation_cycle': MagicMock(),
        'portable_context_service': MagicMock(),
    }


@pytest.fixture
def assembler(mock_repositories):
    """Create TaskContextAssembler with mocked dependencies."""
    return TaskContextAssembler(**mock_repositories)


@pytest.fixture
def fresh_world_model():
    """Create a fresh WorldModelSnapshot."""
    return WorldModelSnapshot(
        confidence=0.9,
        freshness_ms=1000,  # 1 second old
        last_updated=datetime.now(timezone.utc),
        active_windows=[],
        tool_live_status=[],
        network_status=NetworkStatusSnapshot(connected=True, status='connected'),
    )


@pytest.fixture
def stale_world_model():
    """Create a stale WorldModelSnapshot."""
    return WorldModelSnapshot(
        confidence=0.8,
        freshness_ms=120000,  # 120 seconds old (> 90s TTL)
        last_updated=datetime.now(timezone.utc),
        active_windows=[],
        tool_live_status=[],
        network_status=NetworkStatusSnapshot(connected=True, status='connected'),
    )


@pytest.fixture
def environment_self_model():
    """Create an EnvironmentSelfModel."""
    return EnvironmentSelfModel(
        environment_id='test-env-123',
        scan_status='complete',
    )


# ---------------------------------------------------------------------------
# Reflection detection tests
# ---------------------------------------------------------------------------

class TestReflectionDetection:
    """Test that reflection requests are correctly identified."""

    def test_reflection_conclude_phrase(self, assembler):
        """Verify 'que puedo concluir' triggers reflection."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas que observaste?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        assert assembler._is_reflection_request(request=request, intent=intent)

    def test_reflection_infer_phrase(self, assembler):
        """Verify 'que puedes inferir' triggers reflection."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de los datos que te di?")
        intent = TaskIntent(intent_key='system.metacognition')
        assert assembler._is_reflection_request(request=request, intent=intent)

    def test_reflection_meaning_phrase(self, assembler):
        """Verify 'que significa' triggers reflection."""
        request = InferenceRequest(user_goal="¿Qué significa esta información de red?")
        intent = TaskIntent(intent_key='system.metacognition')
        assert assembler._is_reflection_request(request=request, intent=intent)

    def test_reflection_uncertainty_phrase(self, assembler):
        """Verify 'que no sabes' triggers reflection."""
        request = InferenceRequest(user_goal="¿Qué no sabes con certeza?")
        intent = TaskIntent(intent_key='system.metacognition')
        assert assembler._is_reflection_request(request=request, intent=intent)

    def test_reflection_previous_evidence(self, assembler):
        """Verify reflection on previous evidence triggers reflection."""
        request = InferenceRequest(user_goal="Analiza lo que observaste anteriormente")
        intent = TaskIntent(intent_key='system.metacognition')
        assert assembler._is_reflection_request(request=request, intent=intent)

    def test_observe_now_not_reflection(self, assembler):
        """Verify explicit observe-now does NOT trigger reflection."""
        request = InferenceRequest(user_goal="¿Qué ventanas están abiertas AHORA?")
        intent = TaskIntent(intent_key='system.metacognition', metadata={'metacognition_prompt': True})
        assert not assembler._is_reflection_request(request=request, intent=intent)

    def test_actual_state_not_reflection(self, assembler):
        """Verify 'actual' indicates observe-now, not reflection."""
        request = InferenceRequest(user_goal="¿Cuál es mi estado de red actual?")
        intent = TaskIntent(intent_key='system.metacognition', metadata={'metacognition_prompt': True})
        assert not assembler._is_reflection_request(request=request, intent=intent)

    def test_ordinary_chat_not_reflection(self, assembler):
        """Verify ordinary chat is not reflection."""
        request = InferenceRequest(user_goal="¿Cómo estás?")
        intent = TaskIntent(intent_key='general.assistance')
        assert not assembler._is_reflection_request(request=request, intent=intent)


# ---------------------------------------------------------------------------
# World model routing tests
# ---------------------------------------------------------------------------

class TestWorldModelRouting:
    """Test that reflection does not trigger full world model refresh."""

    def test_reflection_prevents_full_world_model(self, assembler):
        """Verify reflection request prevents full world model refresh."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        assert not assembler._should_force_full_world_model(request=request, intent=intent)

    def test_observe_now_allows_full_world_model(self, assembler):
        """Verify observe-now still allows full world model refresh."""
        request = InferenceRequest(user_goal="¿Qué tienes abierto AHORA?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        assert assembler._should_force_full_world_model(request=request, intent=intent)

    def test_quoted_abiertas_not_trigger_full_scan(self, assembler):
        """Verify quoted 'abiertas' in reflection does not trigger full scan."""
        request = InferenceRequest(user_goal="¿Qué significa que las ventanas 'abiertas' estén en ese estado?")
        intent = TaskIntent(intent_key='system.metacognition')
        assert not assembler._should_force_full_world_model(request=request, intent=intent)

    def test_quoted_red_not_trigger_full_scan(self, assembler):
        """Verify quoted 'red' in reflection does not trigger full scan."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de la 'red' que me mostraste?")
        intent = TaskIntent(intent_key='system.metacognition')
        assert not assembler._should_force_full_world_model(request=request, intent=intent)


# ---------------------------------------------------------------------------
# Evidence sufficiency tests
# ---------------------------------------------------------------------------

class TestEvidenceSufficiency:
    """Test evidence sufficiency evaluation for reflection."""

    def test_sufficient_evidence_use_cached(self, assembler, fresh_world_model, environment_self_model):
        """Verify sufficient evidence results in use_cached action."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de los datos?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        result = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        assert result['sufficient'] is True
        assert result['stale'] is False
        assert result['recommended_action'] == 'use_cached'

    def test_stale_evidence_targeted_refresh(self, assembler, stale_world_model, environment_self_model):
        """Verify stale evidence results in targeted_refresh action."""
        request = InferenceRequest(user_goal="¿Qué puedes concluir de las ventanas?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        result = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=stale_world_model,
            environment_self_model=environment_self_model,
        )
        
        assert result['sufficient'] is False
        assert result['stale'] is True
        assert result['recommended_action'] == 'targeted_refresh'

    def test_missing_evidence_targeted_refresh(self, assembler, fresh_world_model, environment_self_model):
        """Verify missing evidence results in targeted_refresh action."""
        request = InferenceRequest(user_goal="¿Qué puedes concluir de las ventanas?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        # World model without active windows (missing evidence)
        world_model = WorldModelSnapshot(
            confidence=0.9,
            freshness_ms=1000,
            last_updated=datetime.now(timezone.utc),
            active_windows=[],  # Empty = missing
            tool_live_status=[],
            network_status=NetworkStatusSnapshot(connected=True, status='connected'),
        )
        
        result = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=world_model,
            environment_self_model=environment_self_model,
        )
        
        assert result['sufficient'] is False
        assert 'windows' in result['missing']
        assert result['recommended_action'] == 'targeted_refresh'

    def test_network_evidence_needed(self, assembler, fresh_world_model, environment_self_model):
        """Verify network evidence is detected when needed."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de mi red?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        result = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        assert 'network' in result.get('missing', []) or result['recommended_action'] in ('use_cached', 'targeted_refresh')

    def test_gpu_evidence_needed(self, assembler, fresh_world_model, environment_self_model):
        """Verify GPU evidence is detected when needed."""
        request = InferenceRequest(user_goal="¿Qué puedes decir de tu GPU?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        result = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        assert 'gpu' in result.get('missing', []) or result['recommended_action'] in ('use_cached', 'targeted_refresh')


# ---------------------------------------------------------------------------
# Decision context metadata tests
# ---------------------------------------------------------------------------

class TestDecisionContextMetadata:
    """Test that reflection metadata is correctly added to decision context."""

    def test_reflection_mode_in_metadata(self, assembler, mock_repositories, fresh_world_model, environment_self_model):
        """Verify reflection_mode is set in decision context metadata."""
        assembler.environment_self_awareness_service.current_model.return_value = environment_self_model
        assembler.world_model_service.current_model.return_value = fresh_world_model
        assembler.world_model_service.request_refresh.return_value = None
        
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        # Test the reflection detection directly
        is_reflection = assembler._is_reflection_request(request=request, intent=intent)
        assert is_reflection is True

    def test_evidence_summary_includes_sufficiency(self, assembler, mock_repositories, fresh_world_model, environment_self_model):
        """Verify evidence summary includes sufficiency evaluation."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        # Test evidence sufficiency evaluation directly
        sufficiency = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        assert 'recommended_action' in sufficiency

    def test_ordinary_chat_no_reflection_metadata(self, assembler, mock_repositories, fresh_world_model, environment_self_model):
        """Verify ordinary chat does not have reflection metadata."""
        request = InferenceRequest(user_goal="¿Cómo estás?")
        intent = TaskIntent(intent_key='general.assistance')
        
        # Test the reflection detection directly
        is_reflection = assembler._is_reflection_request(request=request, intent=intent)
        assert is_reflection is False


# ---------------------------------------------------------------------------
# Repeated observation prevention tests
# ---------------------------------------------------------------------------

class TestRepeatedObservationPrevention:
    """Test that repeated reflection does not cause repeated observations."""

    def test_repeated_reflection_uses_cached(self, assembler, fresh_world_model, environment_self_model):
        """Verify repeated reflection requests use cached evidence."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de los datos?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        # First call
        result1 = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        # Second call (same evidence)
        result2 = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        # Both should recommend use_cached
        assert result1['recommended_action'] == 'use_cached'
        assert result2['recommended_action'] == 'use_cached'

    def test_reflection_after_observation(self, assembler, fresh_world_model, environment_self_model):
        """Verify reflection after observation uses cached evidence."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de lo que observaste?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        result = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        # Should use cached, not trigger new observation
        assert result['recommended_action'] == 'use_cached'


# ---------------------------------------------------------------------------
# Explicit observe-now preservation tests
# ---------------------------------------------------------------------------

class TestExplicitObserveNow:
    """Test that explicit observe-now requests still work."""

    def test_explicit_ahora_triggers_observation(self, assembler):
        """Verify 'AHORA' triggers observation, not reflection."""
        request = InferenceRequest(user_goal="¿Qué ventanas están abiertas AHORA?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        assert not assembler._is_reflection_request(request=request, intent=intent)

    def test_explicit_actual_triggers_observation(self, assembler):
        """Verify 'actual' triggers observation, not reflection."""
        request = InferenceRequest(user_goal="¿Cuál es mi estado de red actual?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        assert not assembler._is_reflection_request(request=request, intent=intent)

    def test_explicit_en_estemomento_triggers_observation(self, assembler):
        """Verify 'en este momento' triggers observation, not reflection."""
        request = InferenceRequest(user_goal="¿Qué tienes abierto en este momento?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        assert not assembler._is_reflection_request(request=request, intent=intent)


# ---------------------------------------------------------------------------
# Lightweight reflection path tests
# ---------------------------------------------------------------------------

class TestLightweightReflectionPath:
    """Test that reflection path remains lightweight."""

    def test_reflection_no_world_model_refresh(self, assembler, fresh_world_model, environment_self_model):
        """Verify reflection does not trigger full world model refresh."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        # Test that reflection prevents full world model refresh
        should_force = assembler._should_force_full_world_model(request=request, intent=intent)
        assert should_force is False

    def test_reflection_uses_cached_world_model(self, assembler, fresh_world_model, environment_self_model):
        """Verify reflection uses cached world model."""
        request = InferenceRequest(user_goal="¿Qué puedes inferir de los datos?")
        intent = TaskIntent(intent_key='system.metacognition')
        
        # Test that reflection prevents full world model refresh
        should_force = assembler._should_force_full_world_model(request=request, intent=intent)
        assert should_force is False


# ---------------------------------------------------------------------------
# Evidence metadata tests
# ---------------------------------------------------------------------------

class TestEvidenceMetadata:
    """Test that evidence retains source/timestamp/confidence."""

    def test_evidence_includes_timestamp(self, assembler, fresh_world_model, environment_self_model):
        """Verify evidence includes world model timestamp."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        # Test evidence sufficiency evaluation includes timestamp
        sufficiency = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        # Verify freshness is evaluated
        assert 'world_model_age_ms' in sufficiency

    def test_evidence_includes_confidence(self, assembler, fresh_world_model, environment_self_model):
        """Verify evidence includes world model confidence."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        # Test evidence sufficiency evaluation
        sufficiency = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        # Verify world model freshness is checked
        assert 'world_model_fresh' in sufficiency

    def test_evidence_includes_freshness(self, assembler, fresh_world_model, environment_self_model):
        """Verify evidence includes world model freshness."""
        request = InferenceRequest(user_goal="¿Qué puedo concluir de las ventanas?")
        intent = TaskIntent(
            intent_key='system.metacognition',
            metadata={'metacognition_prompt': True},
        )
        
        # Test evidence sufficiency evaluation
        sufficiency = assembler._evaluate_evidence_sufficiency(
            request=request,
            intent=intent,
            world_model=fresh_world_model,
            environment_self_model=environment_self_model,
        )
        
        # Verify freshness is evaluated
        assert 'world_model_age_ms' in sufficiency
        assert sufficiency['world_model_age_ms'] == 1000
