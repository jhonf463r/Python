from __future__ import annotations

from iabv_v15.domain.models import CapabilityReadiness, CapabilityStatus, IssueSeverity, StrategyCandidate, StrategyPack, TaskContext, TaskIntent
from iabv_v15.services.adaptive.adaptive_planner_service import AdaptivePlannerService


def test_adaptive_planner_service_uses_patterns_and_experiment_route_phase_by_phase() -> None:
    planner = AdaptivePlannerService()
    playbook = planner.build_playbook(
        intent=TaskIntent(title='Abrir Wplay e iniciar sesion', intent_key='wplay.login', site_hint='wplay'),
        context=TaskContext(
            site_id='wplay',
            site_display_name='Wplay',
            interaction_patterns=[
                {
                    'pattern_id': 'pattern-ui-1',
                    'title': 'Login Wplay confirmado',
                    'channel': 'ui',
                    'site_id': 'wplay',
                    'success_count': 4,
                    'failure_count': 0,
                    'reusable': True,
                }
            ],
            experiment_insights=[
                {
                    'domain': 'language',
                    'recommended_route': 'ui',
                    'score': 0.91,
                    'confidence': 0.88,
                }
            ],
        ),
        pack=StrategyPack(pack_id='wplay.login', title='Wplay login', domain_kind='browser', risk_level=IssueSeverity.MEDIUM),
        capabilities=[
            CapabilityReadiness(
                capability_id='wplay.login',
                title='Login Wplay',
                status=CapabilityStatus.PARTIAL,
                suggested_next_step='Reforzar evidencia visual y ejecutar la ruta guiada.',
            )
        ],
        strategy_candidates=[
            StrategyCandidate(
                pack_id='wplay.login',
                title='Login guiado UI',
                rationale='La ruta visual ya fue observada y el laboratorio favorece UI.',
                algorithm_id='guided_ui',
                readiness_status=CapabilityStatus.PARTIAL,
                risk_level=IssueSeverity.MEDIUM,
                metadata={
                    'recommended_route': 'ui',
                    'recommended_tool_id': 'playwright_browser',
                    'recommended_execution_scope': 'guided_browser',
                    'experiment_alignment_score': 0.93,
                },
            )
        ],
    )

    assert playbook.metadata['preferred_route'] == 'ui'
    assert playbook.metadata['matching_pattern_count'] == 1
    assert 'Patrones reutilizables detectados' in playbook.summary
    propose = next(step for step in playbook.steps if step.phase_key == 'propose_strategy')
    execute = next(step for step in playbook.steps if step.phase_key == 'execute')
    verify = next(step for step in playbook.steps if step.phase_key == 'verify')
    record = next(step for step in playbook.steps if step.phase_key == 'record_outcome')
    assert propose.metadata['preferred_route'] == 'ui'
    assert propose.metadata['matching_pattern_count'] == 1
    assert 'Ruta sugerida: ui' in propose.detail
    assert execute.metadata['recommended_tool_id'] == 'playwright_browser'
    assert 'Herramienta sugerida: playwright_browser.' in execute.detail
    assert 'Comparar contra 1 patrones universales' in verify.detail
    assert 'Actualizar el episodio o patron universal relacionado' in record.detail
