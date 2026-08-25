from __future__ import annotations

from iabv_v15.domain.models import InferenceRequest, TaskRole
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService


def test_intent_understanding_service_detects_explicit_chatgpt_consultation() -> None:
    service = IntentUnderstandingService()

    intent, hypotheses = service.classify(
        InferenceRequest(user_goal='Necesito una consulta externa con ChatGPT para revisar el objetivo activo.')
    )

    assert intent.intent_key == 'research.external_consultation'
    assert intent.detected_role == TaskRole.RESEARCH
    assert intent.disposition.value == 'plan_then_execute'
    assert any(item.intent_key == 'knowledge.query' for item in hypotheses)


def test_intent_understanding_service_keeps_meta_assistant_question_local() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='sabes consultar automaticamente a codex y chatgpt internamente ?')
    )

    assert intent.intent_key in {'general.assistance', 'knowledge.query'}
    assert intent.detected_role == TaskRole.KNOWLEDGE


def test_intent_understanding_service_detects_self_awareness_prompt() -> None:
    service = IntentUnderstandingService()

    intent, hypotheses = service.classify(
        InferenceRequest(user_goal='conoces tu entorno y tu arquitectura?')
    )

    assert intent.intent_key == 'system.self_awareness'
    assert intent.detected_role == TaskRole.KNOWLEDGE
    assert intent.disposition.value == 'answer_now'
    assert intent.metadata.get('self_awareness_prompt') is True
    assert any(item.intent_key == 'knowledge.query' for item in hypotheses)


def test_intent_understanding_service_detects_self_awareness_connectivity_prompt() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='con que ias te puedes conectar ahora?')
    )

    assert intent.intent_key == 'system.self_awareness'
    assert intent.metadata.get('self_awareness_prompt') is True


def test_intent_understanding_service_detects_evolution_status_prompt() -> None:
    service = IntentUnderstandingService()

    intent, hypotheses = service.classify(
        InferenceRequest(user_goal='que herramienta va ganando ahora y que esta en validacion?')
    )

    assert intent.intent_key == 'consulta_estado_evolutivo'
    assert intent.detected_role == TaskRole.KNOWLEDGE
    assert intent.disposition.value == 'answer_now'
    assert intent.metadata.get('evolution_status_prompt') is True
    assert any(item.intent_key == 'knowledge.query' for item in hypotheses)


def test_intent_understanding_service_detects_discovery_prompt() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='que herramienta nueva vale la pena probar y que se descubrio nuevo?')
    )

    assert intent.intent_key == 'consulta_estado_evolutivo'
    assert intent.metadata.get('evolution_status_prompt') is True


def test_intent_understanding_service_prioritizes_actionable_intent_over_pure_self_awareness_when_message_is_compound() -> None:
    service = IntentUnderstandingService()

    intent, hypotheses = service.classify(
        InferenceRequest(
            user_goal='Conoces tu entorno y, con eso claro, revisa por que el chat se desvia con mensajes largos sin ejecutar nada todavia.'
        )
    )

    analysis = dict(intent.metadata.get('conversation_analysis') or {})

    assert intent.intent_key == 'project.evolution'
    assert intent.detected_role == TaskRole.PROJECT_EVOLUTION
    assert analysis.get('primary_intent') == 'project.evolution'
    assert 'system.self_awareness' in list(analysis.get('sub_intents') or [])
    assert 'no ejecutar todavia' in list(analysis.get('constraints') or [])
    assert any(item.intent_key == 'system.self_awareness' for item in hypotheses)


def test_intent_understanding_service_extracts_segment_types_from_long_message() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(
            user_goal=(
                'Te doy contexto: el chat se desvia con mensajes largos. '
                'Necesito que revises la intencion principal y las subintenciones, con el criterio de no inventar nada; '
                'si hay ambiguedad, dilo claro. '
                'Mi duda es si esto amerita usar Codex despues.'
            )
        )
    )

    analysis = dict(intent.metadata.get('conversation_analysis') or {})
    labels = {
        label
        for segment in list(analysis.get('segments') or [])
        for label in list(dict(segment).get('labels') or [])
    }

    assert intent.intent_key == 'project.evolution'
    assert analysis.get('primary_intent') == 'project.evolution'
    assert {'context', 'request', 'criteria', 'doubt'}.issubset(labels)
    assert analysis.get('compound') is True


def test_intent_understanding_service_uses_conversation_history_for_site_continuity() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(
            user_goal='revisa por que sigue fallando el login y dime si conviene usar codex despues',
            conversation_context=[
                {'role': 'user', 'text': 'Necesito revisar el login de Wplay', 'meta': ''},
                {'role': 'assistant', 'text': 'Seguimos con Wplay y el problema del acceso.', 'meta': ''},
            ],
        )
    )

    analysis = dict(intent.metadata.get('conversation_analysis') or {})

    assert intent.site_hint == 'wplay'
    assert analysis.get('context_carried_from_history') is True
    assert analysis.get('primary_intent') in {'wplay.login', 'project.evolution'}


# ---------------------------------------------------------------------------
# H5 - Code generation prompts deben rutear a project.evolution, no al
# fallback ``general.assistance``.


def _classify_goal(goal: str) -> tuple[str, str, str]:
    service = IntentUnderstandingService()
    intent, _ = service.classify(InferenceRequest(user_goal=goal))
    return intent.intent_key, intent.detected_role.value, intent.domain_hint


def test_intent_classifier_routes_generate_patch_to_project_evolution() -> None:
    intent_key, role, domain = _classify_goal('Genera un parche pequeno con tests unitarios')
    assert intent_key == 'project.evolution', f'expected project.evolution, got {intent_key}'
    assert role == 'project_evolution'
    assert domain == 'project'


def test_intent_classifier_routes_unit_tests_request_to_project_evolution() -> None:
    intent_key, _, _ = _classify_goal('Agrega pruebas unitarias al servicio')
    assert intent_key == 'project.evolution'


def test_intent_classifier_routes_write_function_to_project_evolution() -> None:
    intent_key, _, _ = _classify_goal('Escribe una funcion que normalice los scopes')
    assert intent_key == 'project.evolution'


def test_intent_classifier_routes_refactor_to_project_evolution() -> None:
    intent_key, _, _ = _classify_goal('Refactoriza el modulo de sesiones adaptativas')
    assert intent_key == 'project.evolution'


def test_intent_classifier_routes_implement_method_to_project_evolution() -> None:
    intent_key, _, _ = _classify_goal('Implementa un metodo para serializar el snapshot')
    assert intent_key == 'project.evolution'


def test_intent_classifier_flags_code_generation_prompt_metadata() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='Genera un parche pequeno con tests unitarios para el normalizador')
    )

    assert intent.intent_key == 'project.evolution'
    assert intent.metadata.get('code_generation_prompt') is True
    assert any(
        'generacion o modificacion de codigo' in reason
        for reason in intent.reasoning
    ), intent.reasoning


def test_intent_classifier_does_not_flag_code_generation_on_plain_question() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='hola que sabes hacer')
    )

    # Saludo conversacional: no debe levantar la flag ni enrutar a project.
    assert intent.intent_key != 'project.evolution'
    assert intent.metadata.get('code_generation_prompt') is None


# ---------------------------------------------------------------------------
# R21 - devin/windsurf deben rutear igual que chatgpt/claude/codex/ollama
# cuando el usuario los menciona explicitamente como asistente externo.


def test_intent_understanding_service_detects_explicit_devin_consultation() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='consulta con Devin la revision del parche actual.')
    )

    assert intent.intent_key == 'research.external_consultation'
    assert intent.detected_role == TaskRole.RESEARCH
    assert intent.metadata.get('explicit_external_consultation') is True
    assert 'Devin' in intent.title


def test_intent_understanding_service_detects_explicit_windsurf_consultation() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='apoyate en Windsurf para terminar el refactor del adapter.')
    )

    assert intent.intent_key == 'research.external_consultation'
    assert intent.detected_role == TaskRole.RESEARCH
    assert intent.metadata.get('explicit_external_consultation') is True
    assert 'Windsurf' in intent.title


def test_intent_understanding_service_flags_meta_assistant_prompt_for_devin_windsurf() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='sabes consultar automaticamente a devin y a windsurf?')
    )

    # No es una consulta dirigida, es pregunta meta sobre capacidades -> local.
    assert intent.intent_key in {'general.assistance', 'knowledge.query', 'system.self_awareness'}
    assert intent.metadata.get('meta_assistant_prompt') is True


# ---------------------------------------------------------------------------
# Audit fix: internal-topic messages must NOT inherit site_hint from
# conversation history.  E.g. asking about missing secrets after a Wplay
# conversation should NOT carry site_hint='wplay'.


def test_internal_topic_does_not_inherit_site_hint_from_wplay_history() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(
            user_goal='secretos que me pide como faltantes',
            conversation_context=[
                {'role': 'user', 'text': 'Abre Wplay y entra al casino', 'meta': ''},
                {'role': 'assistant', 'text': 'Preparo la sesion de Wplay.', 'meta': ''},
            ],
        )
    )

    # Must NOT route to any wplay intent — this is an internal question.
    assert 'wplay' not in intent.intent_key
    assert intent.intent_key in {
        'system.metacognition',
        'system.self_awareness',
        'general.assistance',
        'knowledge.query',
    }


def test_internal_topic_token_config_does_not_inherit_site_hint() -> None:
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(
            user_goal='por que no encuentra los tokens que tengo configurados',
            conversation_context=[
                {'role': 'user', 'text': 'Abre Wplay', 'meta': ''},
            ],
        )
    )

    assert 'wplay' not in intent.intent_key


def test_wplay_explicit_mention_still_routes_to_wplay() -> None:
    """Explicit mention of Wplay in the current message must still work."""
    service = IntentUnderstandingService()

    intent, _ = service.classify(
        InferenceRequest(user_goal='abre wplay y entra al casino')
    )

    # Either site_hint is set OR the intent routes to a wplay flow.
    # The IntentLearningLayer may shortcut the classification; what
    # matters is the intent routes correctly to Wplay.
    assert intent.site_hint == 'wplay' or 'wplay' in intent.intent_key


def test_intent_learning_layer_records_failure_and_decays() -> None:
    """record_failure should reduce confirmations and confidence."""
    import threading
    from iabv_v15.services.adaptive.intent_understanding_service import IntentLearningLayer

    # Isolated instance with no file persistence.
    layer = IntentLearningLayer.__new__(IntentLearningLayer)
    layer._lock = threading.Lock()
    layer._patterns = {}

    layer.record('test pattern decay', 'general.assistance', confidence=0.8)
    layer.record('test pattern decay', 'general.assistance', confidence=0.8)
    layer.record('test pattern decay', 'general.assistance', confidence=0.8)

    layer.record_failure('test pattern decay', 'general.assistance')

    record = layer._patterns.get('test pattern decay')
    assert record is not None
    assert record['confirmations'] == 2  # was 3, decayed to 2
    assert record['confidence'] < 0.8   # 0.8 * 0.7 = 0.56
