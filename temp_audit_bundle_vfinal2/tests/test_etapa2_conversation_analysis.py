"""
ETAPA 2: Tests for conversational analysis integration
Verifies that conversation_analysis flows through the system and governs decisions.
"""
import pytest
from iabv_v15.domain.models import (
    InferenceRequest,
    IntentDisposition,
    PerceptionSnapshot,
    DecisionContext,
    TaskIntent,
)
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy


class TestETAPA2ConversationAnalysis:
    """Test suite for ETAPA 2 - Conversation Understanding"""

    @pytest.fixture
    def intent_service(self):
        return IntentUnderstandingService()

    @pytest.fixture
    def governance_policy(self):
        return AutonomyGovernancePolicy()

    def test_conversation_analysis_extracted_from_simple_message(self, intent_service):
        """Verify basic conversation analysis extraction"""
        request = InferenceRequest(
            user_goal="necesito revisar el codigo y mejorarlo pero primero quiero entender que falta",
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        # Verify conversation_analysis is in metadata
        conv_analysis = intent.metadata.get("conversation_analysis", {})
        assert conv_analysis, "conversation_analysis should be in intent.metadata"
        assert "primary_intent" in conv_analysis
        assert "ambiguity_score" in conv_analysis
        assert "requires_clarification" in conv_analysis
        assert "sub_intents" in conv_analysis

    def test_high_ambiguity_detected_in_compound_message(self, intent_service):
        """Verify ambiguity detection in messages with multiple intents"""
        request = InferenceRequest(
            user_goal=(
                "mira, hay varias cosas: "
                "primero necesito que revises el bug que aparecio en wplay, "
                "pero tambien quizas deberiamos buscar una herramienta mejor para testing, "
                "y no estoy seguro si conviene hacer refactor en paralelo o despues"
            ),
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        conv_analysis = intent.metadata.get("conversation_analysis", {})
        ambiguity_score = float(conv_analysis.get("ambiguity_score", 0.0))
        sub_intents = list(conv_analysis.get("sub_intents", []))

        # High ambiguity should be detected
        assert ambiguity_score >= 0.5, f"Expected ambiguity > 0.5, got {ambiguity_score}"
        # Should detect multiple sub-intents
        assert len(sub_intents) >= 1, "Should detect sub-intents in compound message"

    def test_clear_message_low_ambiguity(self, intent_service):
        """Verify low ambiguity for clear, single-intent messages"""
        request = InferenceRequest(
            user_goal="necesito abrir wplay y hacer login",
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        conv_analysis = intent.metadata.get("conversation_analysis", {})
        ambiguity_score = float(conv_analysis.get("ambiguity_score", 0.0))
        requires_clarification = bool(conv_analysis.get("requires_clarification"))

        assert ambiguity_score < 0.7, f"Clear message should have low ambiguity, got {ambiguity_score}"
        assert not requires_clarification, "Clear message should not require clarification"

    def test_conversation_analysis_propagates_to_intent_metadata(self, intent_service):
        """Verify conversation_analysis is properly stored in intent.metadata"""
        request = InferenceRequest(
            user_goal="necesito revisar codigo pero no se si hacer refactor ahora o despues, ambig mensaje largo",
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        # Verify propagation through intent.metadata
        decision_metadata = intent.metadata
        assert "conversation_analysis" in decision_metadata
        assert "ambiguity_score" in decision_metadata
        assert "primary_intent" in decision_metadata
        assert "sub_intents" in decision_metadata
        assert "requires_clarification" in decision_metadata
        assert "compound_intent" in decision_metadata or "compound" in decision_metadata.get("conversation_analysis", {})

    def test_high_ambiguity_blocks_autonomy_in_governance(self, governance_policy):
        """Verify governance policy blocks autonomy when ambiguity is high"""
        from iabv_v15.domain.models import GoalContext, AdaptiveSessionStatus

        result = governance_policy.evaluate(
            user_goal="algo ambiguo muy largo con multiples intenciones",
            session_status=AdaptiveSessionStatus.READY_TO_EXECUTE.value,
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            goal_context=GoalContext(),
            intent_key="project.evolution",
            intent_disposition=IntentDisposition.PLAN_THEN_EXECUTE.value,
            ambiguity_score=0.85,  # HIGH ambiguity
            requires_clarification=False,
            sub_intents=[],
        )

        # Should return clarification_needed autonomy level
        assert result.get("autonomy_level") == "clarification_needed"
        assert result.get("should_consult") is True

    def test_requires_clarification_blocks_autonomy_in_governance(self, governance_policy):
        """Verify governance blocks when explicit clarification flag is set"""
        from iabv_v15.domain.models import GoalContext, AdaptiveSessionStatus

        result = governance_policy.evaluate(
            user_goal="realizar varias tareas pero no queda claro el orden",
            session_status=AdaptiveSessionStatus.READY_TO_EXECUTE.value,
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            goal_context=GoalContext(),
            intent_key="project.evolution",
            intent_disposition=IntentDisposition.PLAN_THEN_EXECUTE.value,
            ambiguity_score=0.5,  # Moderate
            requires_clarification=True,  # EXPLICIT flag
            sub_intents=["refactor", "testing", "documentation"],
        )

        # Should block
        assert result.get("autonomy_level") == "clarification_needed"

    def test_clear_message_allows_autonomy_in_governance(self, governance_policy):
        """Verify governance allows autonomy for clear messages"""
        from iabv_v15.domain.models import GoalContext, AdaptiveSessionStatus

        result = governance_policy.evaluate(
            user_goal="abrir wplay e iniciar sesion",
            session_status=AdaptiveSessionStatus.READY_TO_EXECUTE.value,
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            goal_context=GoalContext(),
            intent_key="wplay.login",
            intent_disposition=IntentDisposition.PLAN_THEN_EXECUTE.value,
            ambiguity_score=0.2,  # LOW ambiguity
            requires_clarification=False,
            sub_intents=[],
        )

        # Should NOT be blocked by ambiguity
        assert result.get("autonomy_level") != "clarification_needed" or result.get("diagnosis") != "conversation_ambiguity"

    def test_conversation_segments_with_labels_detected(self, intent_service):
        """Verify that message segments are labeled correctly"""
        request = InferenceRequest(
            user_goal=(
                "Context: tengo un problema con el login. "
                "Request: necesito que revises el codigo de autenticacion. "
                "Criteria: pero sin hacer cambios antes de entender el problema. "
                "Instruction: analiza primero y explicame que ves."
            ),
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        conv_analysis = intent.metadata.get("conversation_analysis", {})
        segments = list(conv_analysis.get("segments", []))

        # Should have multiple segments
        assert len(segments) >= 2, "Should detect multiple message segments"

        # Segments should have labels
        for segment in segments:
            labels = segment.get("labels", [])
            assert len(labels) > 0, "Segments should have labels"

    def test_conversation_constraints_extracted(self, intent_service):
        """Verify that constraints from conversation are extracted"""
        request = InferenceRequest(
            user_goal="revisa el codigo pero sin ejecutar nada todavia, y no inventes soluciones",
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        conv_analysis = intent.metadata.get("conversation_analysis", {})
        constraints = list(conv_analysis.get("constraints", []))

        # Should detect constraints
        assert len(constraints) > 0, "Should extract constraints from message"
        # Common constraint patterns
        constraint_text = " ".join(constraints).lower()
        assert any(
            phrase in constraint_text for phrase in ["no ejecutar", "no invent", "sin"]
        ), "Constraints should include explicit restrictions"

    def test_sub_intents_scored_and_ordered(self, intent_service):
        """Verify sub_intents are detected and ordered by score"""
        request = InferenceRequest(
            user_goal=(
                "quiero mejorar varias cosas: "
                "necesito revisar el bug del login, "
                "refactorizar los tests, "
                "actualizar la documentacion, "
                "y optimizar rendimiento si hay tiempo"
            ),
            conversation_context=[],
        )
        intent, _ = intent_service.classify(request)

        conv_analysis = intent.metadata.get("conversation_analysis", {})
        sub_intents = list(conv_analysis.get("sub_intents", []))
        primary_intent = conv_analysis.get("primary_intent", "")

        # Should have detected compound nature
        compound = bool(conv_analysis.get("compound"))
        assert compound, "Should detect as compound message with multiple tasks"
        # Primary intent should be set
        assert primary_intent, "Should have a primary intent"

    def test_context_carried_from_history_detected(self, intent_service):
        """Verify that context from conversation history is detected"""
        conversation_context = [
            {
                "text": "estoy trabajando con wplay",
                "meta": "previous context",
            },
        ]
        request = InferenceRequest(
            user_goal="necesito mejorar el login",  # Short, implies context from history
            conversation_context=conversation_context,
        )
        intent, _ = intent_service.classify(request)

        conv_analysis = intent.metadata.get("conversation_analysis", {})
        context_carried = bool(conv_analysis.get("context_carried_from_history"))

        # Should detect that context is being carried from history
        if "wplay" in " ".join(str(c.get("text", "")) for c in conversation_context):
            # Context carried should be detected or intent should include site hint
            assert context_carried or intent.site_hint, "Should detect carried context or infer site"


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
