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
# R8-1: "buscá en internet" debe rutear a browser.search sin site_hint
# ---------------------------------------------------------------------------


def test_intent_classifier_routes_busca_en_internet_to_browser_search() -> None:
    intent_key, _, domain = _classify_goal('busca en internet la ultima version de Python')
    assert intent_key == 'browser.search', f'expected browser.search, got {intent_key}'
    assert domain == 'browser'


def test_intent_classifier_routes_busca_en_la_web_to_browser_search() -> None:
    intent_key, _, _ = _classify_goal('busca en la web cuanto cuesta el hosting en AWS')
    assert intent_key == 'browser.search'


def test_intent_classifier_routes_busca_online_to_browser_search() -> None:
    intent_key, _, _ = _classify_goal('busca online las novedades de Python 3.13')
    assert intent_key == 'browser.search'


# ---------------------------------------------------------------------------
# R8-2: frases de resumen/síntesis deben rutear a research.local
# ---------------------------------------------------------------------------


def test_intent_classifier_routes_resumi_archivos_to_research_local() -> None:
    intent_key, role, _ = _classify_goal('resumi 30 archivos de documentacion en uno solo')
    assert intent_key == 'research.local', f'expected research.local, got {intent_key}'
    assert role == 'research'


def test_intent_classifier_routes_sintetiza_to_research_local() -> None:
    intent_key, _, _ = _classify_goal('sintetiza los hallazgos del ultimo sprint en un reporte')
    assert intent_key == 'research.local'


def test_intent_classifier_routes_consolida_to_research_local() -> None:
    intent_key, _, _ = _classify_goal('consolida toda la evidencia de las pruebas en un solo documento')
    assert intent_key == 'research.local'
