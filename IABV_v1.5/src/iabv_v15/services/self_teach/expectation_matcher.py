from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, ScenarioDefinition


class ExpectationMatcher:
    def compare(self, scenario: ScenarioDefinition, session: AdaptiveSession) -> tuple[list[str], list[str]]:
        expected = list(scenario.expected_signals)
        observed = [f'intent:{session.intent.intent_key}', f'pack:{session.chosen_pack_id}']
        for capability in session.capability_readiness:
            observed.append(f'capability:{capability.capability_id}:{capability.status.value}')
        for incident in session.context.recent_incidents[:6]:
            kind = str(incident.get('incident_kind') or '')
            if kind:
                observed.append(f'incident:{kind}')
        execute_step = next((item for item in (session.playbook.steps if session.playbook else []) if item.phase_key == 'execute'), None)
        execution_state = session.metadata.get('execution_state') if isinstance(session.metadata, dict) else None
        if execute_step is not None:
            observed.append(f'execute:executable:{str(bool(execute_step.executable)).lower()}')
            observed.append(f'execute:simulation_only:{str(bool(execute_step.simulation_only)).lower()}')
        if isinstance(execution_state, dict):
            observed.append(f"execute:executor_available:{str(bool(execution_state.get('executor_available'))).lower()}")
            observed.append(f"execute:state:{str(execution_state.get('state') or 'unknown')}")
        return expected, observed
