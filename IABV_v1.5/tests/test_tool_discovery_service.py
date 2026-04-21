from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ProposalValidationResult,
    ToolCard,
    ToolDiscoveryStatus,
    ToolLiveStatus,
    ToolType,
    WindowObservation,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.tool_discovery_service import ToolDiscoveryService
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer


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


class _RegistryStub:
    def __init__(self, cards: list[ToolCard]) -> None:
        self._cards = cards

    def list_cards(self) -> list[ToolCard]:
        return list(self._cards)

    def refresh_card(self, card: ToolCard) -> ToolCard:
        return card


def test_tool_discovery_service_detects_candidate_and_reconciles_promoted_signal() -> None:
    root = _workspace('tool_discovery_service')
    try:
        lab, repository, storage = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Resolver bridge lag tecnico',
            subject_key='wplay:bridge-lag',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=False,
            observed_summary='ChatGPT sigue aportando diagnostico parcial, pero sin cerrar el cambio.',
            precision=0.42,
            robustness=0.38,
            execution_ms=2200,
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
        registry = _RegistryStub(
            [
                ToolCard(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    tool_type=ToolType.CUSTOM,
                    description='Consulta tecnica guiada con Codex.',
                    adapter_key='external_assistant',
                    capabilities=['llm_query', 'consult_external', 'code_assistance'],
                    metadata={
                        'assistant_kind': 'codex',
                        'launch_mode': 'desktop_app',
                        'prompt_template_id': 'codex_consult_v1',
                    },
                )
            ]
        )
        world_model_service = SimpleNamespace(
            current_model=lambda: WorldModelSnapshot(
                active_windows=[WindowObservation(title='Codex', app_name='Codex', pid=10, focused=True)],
                focused_window=WindowObservation(title='Codex', app_name='Codex', pid=10, focused=True),
                tool_live_status=[
                    ToolLiveStatus(
                        tool_id='codex_installed',
                        assistant_kind='codex',
                        title='Codex instalado',
                        available=True,
                        status='abierto',
                    )
                ],
            )
        )
        decision_log = SimpleNamespace(entries=[])
        validation_stub = SimpleNamespace(current_decision_log=lambda refresh=False: decision_log)
        service = ToolDiscoveryService(
            storage=storage,
            tool_registry=registry,
            experiment_lab_repository=repository,
            world_model_service=world_model_service,
            autonomous_validation_cycle=validation_stub,
        )

        detected = service.current_status(refresh=True)
        assert isinstance(detected, ToolDiscoveryStatus)
        assert detected.signals
        signal = detected.signals[0]
        assert signal.assistant_kind == 'codex'
        assert signal.status == 'detected'

        decision_log = SimpleNamespace(
            entries=[
                ProposalValidationResult(
                    proposal_id='proposal-1',
                    proposal_key=signal.proposal_key,
                    domain=ExperimentDomain.CODE,
                    subject_key='wplay:bridge-lag',
                    proposal_kind='validate_discovery',
                    decision='promoted',
                    winner='proposed_tool',
                    reason='Codex gano la validacion discovery para este problema.',
                    current_route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
                    current_assistant_kind='chatgpt',
                    current_config_signature='chatgpt-browser',
                    candidate_route=EvaluationRoute.CODE_AGENT,
                    candidate_assistant_kind='codex',
                    candidate_config_signature=signal.config_signature,
                )
            ]
        )

        promoted = service.current_status(refresh=True)
        assert promoted.signals[0].status == 'promoted'
        assert promoted.metadata['promoted_signals'][0]['tool_id'] == 'codex_installed'
        assert Path(promoted.package_path).exists()
        assert Path(promoted.markdown_path).exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_discovery_service_infers_baseline_from_runs_without_recommendation() -> None:
    """R14-1: _recommendation_from_runs must access probe.metrics.total_score,
    not probe.score.total_score (ExperimentRun has no 'score' attribute)."""
    root = _workspace('tool_discovery_run_baseline')
    try:
        lab, repository, storage = _lab(root)
        lab.record_outcome(
            domain=ExperimentDomain.CODE,
            objective='Diagnosticar fallo de login',
            subject_key='app:login-fail',
            route=EvaluationRoute.LANGUAGE_UNDERSTANDING,
            candidate_label='chatgpt_web_assisted',
            success=False,
            observed_summary='Diagnostico parcial sin cierre.',
            precision=0.35,
            robustness=0.30,
            execution_ms=1500,
            metadata={
                'assistant_kind': 'chatgpt',
                'config_signature': 'chatgpt-browser',
            },
        )
        registry = _RegistryStub(
            [
                ToolCard(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    tool_type=ToolType.CUSTOM,
                    description='Consulta tecnica guiada con Codex.',
                    adapter_key='external_assistant',
                    capabilities=['llm_query', 'consult_external', 'code_assistance'],
                    metadata={
                        'assistant_kind': 'codex',
                        'launch_mode': 'desktop_app',
                        'prompt_template_id': 'codex_consult_v1',
                    },
                )
            ]
        )
        service = ToolDiscoveryService(
            storage=storage,
            tool_registry=registry,
            experiment_lab_repository=repository,
        )
        status = service.build_status(subject_key='app:login-fail')
        assert isinstance(status, ToolDiscoveryStatus)
        assert status.signals, 'Expected at least one discovery signal from run-inferred baseline'
        signal = status.signals[0]
        assert signal.assistant_kind == 'codex'
        assert signal.status == 'detected'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_discovery_service_available_cards_survives_single_card_refresh_failure() -> None:
    """R14-2: _available_cards must not discard already-collected cards when
    refresh_card raises for a later card.  Before the fix, the entire for-loop
    was wrapped in a single try/except that returned [] on any exception,
    losing all previously collected healthy cards."""
    root = _workspace('tool_discovery_refresh_failure')
    try:
        _lab_unused, repository, storage = _lab(root)

        good_card = ToolCard(
            tool_id='codex_installed',
            title='Codex instalado',
            tool_type=ToolType.CUSTOM,
            description='Consulta tecnica guiada con Codex.',
            adapter_key='external_assistant',
            capabilities=['llm_query', 'consult_external', 'code_assistance'],
            available=True,
            metadata={'assistant_kind': 'codex'},
        )
        bad_card = ToolCard(
            tool_id='broken_tool',
            title='Broken tool',
            tool_type=ToolType.CUSTOM,
            description='This tool explodes on refresh.',
            adapter_key='broken_adapter',
            available=True,
        )

        class _BrokenRefreshRegistry:
            def __init__(self, cards: list[ToolCard]) -> None:
                self._cards = cards

            def list_cards(self) -> list[ToolCard]:
                return list(self._cards)

            def refresh_card(self, card: ToolCard) -> ToolCard:
                if card.tool_id == 'broken_tool':
                    raise RuntimeError('adapter crashed during availability check')
                return card

        registry = _BrokenRefreshRegistry([good_card, bad_card])
        service = ToolDiscoveryService(
            storage=storage,
            tool_registry=registry,
            experiment_lab_repository=repository,
        )
        cards = service._available_cards()
        assert len(cards) == 1, (
            f'Expected 1 healthy card after broken refresh, got {len(cards)}. '
            'Before the fix, a single refresh failure discarded all cards.'
        )
        assert cards[0].tool_id == 'codex_installed'
    finally:
        shutil.rmtree(root, ignore_errors=True)
