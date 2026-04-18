from __future__ import annotations

from iabv_v15.domain.models import InferenceRequest, ScenarioDefinition, ScenarioMode, TaskIntent


class ScenarioRegistry:
    def resolve_for_request(self, request: InferenceRequest, intent: TaskIntent) -> ScenarioDefinition:
        site_id = intent.site_hint or request.site_hint
        if intent.intent_key == 'wplay.login':
            return ScenarioDefinition(
                scenario_id='wplay.login',
                title='Abrir Wplay e iniciar sesion',
                summary='Diagnostica si la app ya entiende, ensena y puede preparar el login de Wplay de forma coherente.',
                site_id='wplay',
                intent_keys=['wplay.login'],
                mode=ScenarioMode.LIVE_GUIDED,
                approval_required=True,
                expected_signals=['intent:wplay.login', 'pack:wplay.login', 'capability:wplay.login', 'capability:wplay.session.restore'],
                failure_signals=['incident:session_restore_weak', 'incident:bridge_lag', 'incident:navigation_stall'],
                metadata={'sensitive': True},
            )
        if intent.intent_key == 'wplay.core':
            return ScenarioDefinition(
                scenario_id='wplay.open',
                title='Abrir Wplay',
                summary='Comprueba si la app puede preparar la apertura del sitio y la sesion con guardrails.',
                site_id='wplay',
                intent_keys=['wplay.core'],
                mode=ScenarioMode.LIVE_GUIDED,
                approval_required=True,
                expected_signals=['intent:wplay.core', 'pack:wplay.core', 'capability:wplay.session.restore'],
                failure_signals=['incident:navigation_stall', 'incident:session_restore_weak'],
                metadata={'sensitive': True},
            )
        if intent.intent_key == 'wplay.casino':
            return ScenarioDefinition(
                scenario_id='wplay.casino',
                title='Ir a casino en Wplay',
                summary='Valida login, navegacion a casino y el estado del pack sensible antes de cualquier accion critica.',
                site_id='wplay',
                intent_keys=['wplay.casino'],
                mode=ScenarioMode.LIVE_GUIDED,
                approval_required=True,
                expected_signals=['intent:wplay.casino', 'pack:wplay.casino', 'capability:wplay.navigate.casino'],
                failure_signals=['incident:navigation_stall', 'incident:critical_object_missing'],
                metadata={'sensitive': True, 'monetary': True},
            )
        if intent.intent_key == 'browser.search' and site_id == 'google':
            return ScenarioDefinition(
                scenario_id='browser.search.google',
                title='Buscar en Google',
                summary='Comprueba una tarea web simple para separar fallos generales de navegador de fallos del dominio Wplay.',
                site_id='google',
                intent_keys=['browser.search'],
                mode=ScenarioMode.SIMULATE,
                approval_required=False,
                expected_signals=['intent:browser.search', 'pack:browser.generic', 'capability:browser.search.google'],
                failure_signals=['incident:navigation_stall', 'incident:bridge_lag'],
            )
        return ScenarioDefinition(
            scenario_id=intent.intent_key or 'general.assistance',
            title=intent.title or request.user_goal,
            summary='Escenario generico para diagnostico adaptativo.',
            site_id=site_id,
            intent_keys=[intent.intent_key],
            mode=ScenarioMode.REPLAY_ONLY,
            approval_required=False,
            expected_signals=[f'intent:{intent.intent_key}', f'pack:{intent.intent_key}'],
            failure_signals=[],
        )
