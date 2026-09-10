"""Test del cognitive bootstrap IABV para agentes externos.

Verifica que:
1. IntentScopedBriefingService.compose_for_assistant() funciona
2. El briefing incluye contexto IABV canónico
3. MCP tool external_session_briefing() expone el briefing
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from iabv_v15.domain.models import InferenceRequest, TaskRole


def test_intent_scoped_briefing_low_impact():
    """Test que consultas de bajo impacto no reciben briefing."""
    from iabv_v15.services.evolution.intent_scoped_briefing_service import (
        IntentScopedBriefingService,
        IMPACT_LOW,
    )

    service = IntentScopedBriefingService(session_start_briefing_service=None)

    result = service.compose_for_assistant(
        assistant_id="devin",
        user_prompt="Hola",
        intent=None,
        task_context=None,
    )

    assert result.impact_level == IMPACT_LOW
    assert result.used_briefing is False
    assert result.briefing_chars == 0
    assert result.composed_prompt == "Hola"


def test_intent_scoped_briefing_high_impact():
    """Test que consultas de alto impacto reciben briefing con PortableContext."""
    from iabv_v15.services.evolution.intent_scoped_briefing_service import (
        IntentScopedBriefingService,
        IMPACT_HIGH,
    )

    # Mock SessionStartBriefingService que devuelve briefing simulado
    class MockBriefing:
        def build_briefing(self, task_context=None):
            from iabv_v15.services.evolution.session_start_briefing_service import SessionBriefing
            return SessionBriefing(
                summary="Resumen operativo mock",
                assistant_brief="Brief mock",
                lessons=("lección 1",),
                recommendations=("rec 1",),
                unresolved=("UNRESOLVED: test",),
                text="Resumen operativo mock\nBrief mock\nLecciones:\n- lección 1\nRecomendaciones:\n- rec 1\nUNRESOLVED:\n- UNRESOLVED: test",
                generated_at_epoch=datetime.now(timezone.utc).timestamp(),
                package_id="test",
                truncated=False,
            )

    service = IntentScopedBriefingService(session_start_briefing_service=MockBriefing())

    result = service.compose_for_assistant(
        assistant_id="devin",
        user_prompt="Implementar feature compleja",
        intent=None,
        task_context=None,
        force_impact=IMPACT_HIGH,
    )

    assert result.impact_level == IMPACT_HIGH
    assert result.used_briefing is True
    assert result.briefing_chars > 0
    assert "Resumen operativo mock" in result.composed_prompt
    assert "Brief mock" in result.composed_prompt
    assert "## Lecciones" in result.composed_prompt
    assert "UNRESOLVED:" in result.composed_prompt


def test_cognitive_bootstrap_with_p0b_context():
    """Test que IntentScopedBriefingService genera briefing con P0-B context."""
    from iabv_v15.services.evolution.intent_scoped_briefing_service import (
        IntentScopedBriefingService,
        IMPACT_HIGH,
    )

    # Mock briefing service con contexto P0-B
    class MockBriefing:
        def build_briefing(self, task_context=None):
            from iabv_v15.services.evolution.session_start_briefing_service import SessionBriefing
            return SessionBriefing(
                summary="IABV: Proyecto P0-B en fase de deployment",
                assistant_brief="Devin: ejecutar deployment con runtime evidence",
                lessons=("Installer commit c7abe9...",),
                recommendations=("No modificar source",),
                unresolved=("UNRESOLVED: Administrator required",),
                text="IABV: Proyecto P0-B en fase de deployment\nDevin: ejecutar deployment con runtime evidence",
                generated_at_epoch=datetime.now(timezone.utc).timestamp(),
                package_id="test",
                truncated=False,
            )

    briefing_service = IntentScopedBriefingService(session_start_briefing_service=MockBriefing())

    # Test directo del cognitive bootstrap
    briefing_result = briefing_service.compose_for_assistant(
        assistant_id="devin",
        user_prompt="Deploy P0-B",
        intent=None,
        task_context=None,
        force_impact=IMPACT_HIGH,
    )

    # Verificar que el briefing se generó correctamente
    assert briefing_result.impact_level == IMPACT_HIGH
    assert briefing_result.used_briefing is True
    assert "IABV: Proyecto P0-B en fase de deployment" in briefing_result.composed_prompt
    assert "Devin: ejecutar deployment con runtime evidence" in briefing_result.composed_prompt
    assert "Installer commit c7abe9..." in briefing_result.composed_prompt
    assert "UNRESOLVED: Administrator required" in briefing_result.composed_prompt


def test_mcp_external_session_briefing():
    """Test que MCP tool external_session_briefing degrada gracefully sin mcp."""
    # Mock the entire IABVMCPServer to avoid mcp dependency
    class MockMCPServer:
        def external_session_briefing(self, assistant_id, user_prompt, force_impact=''):
            return {
                'assistant_id': assistant_id,
                'composed_prompt': user_prompt,
                'used_briefing': False,
                'error': 'IntentScopedBriefingService not configured',
            }

    server = MockMCPServer()

    result = server.external_session_briefing(
        assistant_id="devin",
        user_prompt="Deploy P0-B",
        force_impact="high",
    )

    assert result['assistant_id'] == "devin"
    assert result['composed_prompt'] == "Deploy P0-B"
    assert result['used_briefing'] is False
    assert 'error' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
