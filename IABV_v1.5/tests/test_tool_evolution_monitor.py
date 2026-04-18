from __future__ import annotations

import shutil
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ToolCard,
    ToolDiscoverySignal,
    ToolDiscoveryStatus,
    ToolType,
    ProposalValidationResult,
    ToolEvolutionDecisionLog,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.evolution.tool_evolution_monitor import ToolEvolutionMonitor
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _lab(root: Path) -> tuple[ExperimentLab, ExperimentLabRepository, ArtifactStorage]:
    storage = ArtifactStorage(str(root / 'evolution'))
    repository = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), storage)
    lab = ExperimentLab(
        repository=repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer()),
    )
    return lab, repository, storage


def test_tool_evolution_monitor_detects_degradation_and_proposes_local_first_candidate() -> None:
    root = _workspace('tool_evolution_monitor')
    try:
        lab, repository, storage = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=True,
            observed_summary='Diagnostico parcial con bloqueo de hilo.',
            precision=0.68,
            robustness=0.61,
            execution_ms=2200,
            metadata={
                'assistant_kind': 'chatgpt',
                'config_signature': 'chatgpt-browser',
                'used_fallback': True,
                'external_state_flags': ['wrong_thread'],
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=False,
            observed_summary='La consulta vuelve a atascarse por contexto externo.',
            precision=0.21,
            robustness=0.3,
            execution_ms=2600,
            metadata={
                'assistant_kind': 'chatgpt',
                'config_signature': 'chatgpt-browser',
                'used_fallback': True,
                'external_state_flags': ['wrong_thread'],
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_installed',
            success=True,
            observed_summary='Correccion precisa del bridge sin bloqueo.',
            precision=0.86,
            robustness=0.84,
            execution_ms=260,
            metadata={
                'assistant_kind': 'codex',
                'config_signature': 'codex-plan',
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='wplay:bridge-lag',
                recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                recommended_assistant_kind='chatgpt',
                recommended_config_signature='chatgpt-browser',
                score=0.41,
                confidence=0.52,
                rationale='Recomendacion previa aun no recalibrada frente a la degradacion reciente.',
                metadata={'comparison_scope_keys': ['wplay:bridge-lag']},
            )
        )

        monitor = ToolEvolutionMonitor(
            storage=storage,
            experiment_lab_repository=repository,
            adaptive_weight_layer=AdaptiveWeightLayer(),
        )

        status = monitor.current_status(refresh=True)
        summary = monitor.status_summary(status)

        assert status.performance
        assert any(item.assistant_kind == 'chatgpt' and item.degraded for item in status.performance)
        assert any(item.assistant_kind == 'codex' for item in status.performance)
        assert status.proposals
        assert status.proposals[0].proposal_kind in {'validate_replacement', 'validate_local_first', 'compare_again'}
        assert status.proposals[0].candidate_assistant_kind == 'codex'
        assert status.proposals[0].metadata['next_action'] == 'validate_in_sandbox'
        assert 'wplay:bridge-lag' in summary['degraded_subjects']
        assert Path(status.package_path).exists()
        assert Path(status.markdown_path).exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_evolution_monitor_reconciles_decided_proposals_from_decision_log() -> None:
    root = _workspace('tool_evolution_monitor_decision_log')
    try:
        lab, repository, storage = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=True,
            observed_summary='Diagnostico parcial con bloqueo de hilo.',
            precision=0.68,
            robustness=0.61,
            execution_ms=2200,
            metadata={
                'assistant_kind': 'chatgpt',
                'config_signature': 'chatgpt-browser',
                'used_fallback': True,
                'external_state_flags': ['wrong_thread'],
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=False,
            observed_summary='La consulta vuelve a atascarse por contexto externo.',
            precision=0.21,
            robustness=0.3,
            execution_ms=2600,
            metadata={
                'assistant_kind': 'chatgpt',
                'config_signature': 'chatgpt-browser',
                'used_fallback': True,
                'external_state_flags': ['wrong_thread'],
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.CODE_AGENT,
            candidate_label='codex_installed',
            success=True,
            observed_summary='Correccion precisa del bridge sin bloqueo.',
            precision=0.86,
            robustness=0.84,
            execution_ms=260,
            metadata={
                'assistant_kind': 'codex',
                'config_signature': 'codex-plan',
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='wplay:bridge-lag',
                recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                recommended_assistant_kind='chatgpt',
                recommended_config_signature='chatgpt-browser',
                score=0.41,
                confidence=0.52,
                rationale='Recomendacion previa aun no recalibrada frente a la degradacion reciente.',
                metadata={'comparison_scope_keys': ['wplay:bridge-lag']},
            )
        )
        decision_log = ToolEvolutionDecisionLog(
            entries=[
                ProposalValidationResult(
                    proposal_id='proposal-1',
                    proposal_key='wplay:bridge-lag|validate_replacement|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|codex-plan',
                    domain=ExperimentDomain.CODE,
                    subject_key='wplay:bridge-lag',
                    proposal_kind='validate_replacement',
                    decision='promoted',
                    winner='proposed_tool',
                    reason='Codex gano la validacion y reemplazo a la ruta degradada.',
                    current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                    current_assistant_kind='chatgpt',
                    current_config_signature='chatgpt-browser',
                    candidate_route=EvaluationRoute.CODE_AGENT,
                    candidate_assistant_kind='codex',
                    candidate_config_signature='codex-plan',
                )
            ]
        )
        validation_stub = SimpleNamespace(
            current_snapshot=lambda: SimpleNamespace(status='active', summary='Validando propuestas del monitor.', current_experiment=None),
            current_decision_log=lambda refresh=False: decision_log,
            decision_log_summary=lambda log=None: {
                'winning_by_problem': {'wplay:bridge-lag': 'codex'},
                'degraded_tools': ['chatgpt'],
                'in_validation': [],
                'last_decision': {
                    'subject_key': 'wplay:bridge-lag',
                    'proposal_key': 'wplay:bridge-lag|validate_replacement|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|codex-plan',
                    'decision': 'promoted',
                    'winner': 'proposed_tool',
                    'reason': 'Codex gano la validacion y reemplazo a la ruta degradada.',
                },
                'summary_by_tool': {'chatgpt': 'degradado', 'codex': 'ganando'},
                'summary_by_problem': {'wplay:bridge-lag': 'codex'},
                'unresolved_fields': [],
            },
        )

        monitor = ToolEvolutionMonitor(
            storage=storage,
            experiment_lab_repository=repository,
            adaptive_weight_layer=AdaptiveWeightLayer(),
            autonomous_validation_cycle=validation_stub,
        )

        status = monitor.current_status(refresh=True)
        summary = monitor.status_summary(status)

        assert status.proposals == []
        assert status.metadata['active_proposal_count'] == 0
        assert status.metadata['decided_proposal_count'] == 1
        assert summary['active_proposals'] == []
        assert summary['decided_proposals'][0]['status'] == 'promoted'
        assert summary['winning_by_problem']['wplay:bridge-lag'] == 'codex'
        assert '0 propuesta(s) activa(s), 1 ya decidida(s)' in status.summary
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_evolution_monitor_emits_validate_discovery_for_new_candidate() -> None:
    root = _workspace('tool_evolution_monitor_discovery')
    try:
        lab, repository, storage = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=False,
            observed_summary='La ruta actual explica, pero no cierra el cambio.',
            precision=0.39,
            robustness=0.34,
            execution_ms=2100,
            metadata={
                'assistant_kind': 'chatgpt',
                'config_signature': 'chatgpt-browser',
                'comparison_scope_key': 'wplay:bridge-lag',
            },
        )
        repository.save_recommendation(
            ExperimentRecommendation(
                domain=ExperimentDomain.CODE,
                subject_key='wplay:bridge-lag',
                recommended_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                recommended_assistant_kind='chatgpt',
                recommended_config_signature='chatgpt-browser',
                score=0.44,
                confidence=0.58,
                rationale='Linea base actual antes de probar candidatos nuevos.',
            )
        )
        discovery_status = ToolDiscoveryStatus(
            summary='Detecte Codex como candidato nuevo para este problema.',
            signals=[
                ToolDiscoverySignal(
                    proposal_key='wplay:bridge-lag|validate_discovery|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|desktop_app:codex_consult_v1:external_assistant',
                    domain=ExperimentDomain.CODE,
                    scope='wplay:bridge-lag',
                    title='Probar Codex para wplay:bridge-lag',
                    summary='Codex aparece disponible y vale la pena validarlo contra ChatGPT.',
                    tool_id='codex_installed',
                    tool_title='Codex instalado',
                    assistant_kind='codex',
                    route=EvaluationRoute.CODE_AGENT,
                    config_signature='desktop_app:codex_consult_v1:external_assistant',
                    status='detected',
                    confidence=0.81,
                    compatibility_score=0.92,
                    impact_score=0.78,
                    cost_score=0.66,
                    evidence_refs=['run-1'],
                    metadata={
                        'baseline_weighted_score': 0.44,
                        'estimated_candidate_score': 0.54,
                    },
                )
            ],
        )
        discovery_stub = SimpleNamespace(current_status=lambda refresh=False, subject_key=None: discovery_status)

        monitor = ToolEvolutionMonitor(
            storage=storage,
            experiment_lab_repository=repository,
            adaptive_weight_layer=AdaptiveWeightLayer(),
            tool_discovery_service=discovery_stub,
        )

        status = monitor.current_status(refresh=True)

        assert status.proposals
        discovery_proposal = next(item for item in status.proposals if item.proposal_kind == 'validate_discovery')
        assert discovery_proposal.candidate_assistant_kind == 'codex'
        assert discovery_proposal.metadata['discovery_signal_id']
        assert discovery_proposal.metadata['discovery_source'] == 'tool_registry'
    finally:
        shutil.rmtree(root, ignore_errors=True)
