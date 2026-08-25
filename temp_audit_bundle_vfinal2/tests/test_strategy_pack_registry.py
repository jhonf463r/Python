from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import CapabilityReadiness, CapabilityStatus, TaskContext, TaskIntent, TaskRole
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_strategy_pack_registry_does_not_rewrite_identical_defaults(monkeypatch) -> None:
    root = _workspace('strategy_pack_registry')
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'evolution'))
    repository = StrategyPackRepository(db, storage)

    StrategyPackRegistry(repository)

    def fail_save(pack):
        raise AssertionError('No deberia reescribir packs identicos al arrancar otra vez.')

    monkeypatch.setattr(repository, 'save', fail_save)
    StrategyPackRegistry(repository)


def test_strategy_pack_registry_uses_experiment_insight_to_bias_browser_candidate_order() -> None:
    root = _workspace('strategy_pack_registry_lab_browser')
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'evolution'))
    repository = StrategyPackRepository(db, storage)
    registry = StrategyPackRegistry(repository)
    intent = TaskIntent(intent_key='browser.search', title='Busqueda web', detected_role=TaskRole.TRAINING)
    context = TaskContext(
        experiment_insights=[
            {
                'domain': 'language',
                'subject_key': 'general',
                'recommended_route': 'language_understanding',
                'score': 0.91,
                'confidence': 0.87,
                'rationale': 'La comprension local resuelve mejor este tipo de busquedas abiertas.',
            }
        ]
    )
    pack = registry.resolve_pack(intent, context)
    capabilities = [
        CapabilityReadiness(
            capability_id='browser.generic.navigation',
            title='Navegacion generica',
            status=CapabilityStatus.READY,
            score=0.9,
        )
    ]

    candidates = registry.build_candidates(pack=pack, intent=intent, context=context, capabilities=capabilities)

    assert candidates[0].algorithm_id == 'search_then_open'
    assert candidates[0].metadata['experiment_recommendation']['recommended_route'] == 'language_understanding'
    assert candidates[0].metadata['experiment_alignment_score'] > candidates[1].metadata['experiment_alignment_score']
    assert 'Laboratorio universal sugiere language_understanding' in candidates[0].rationale


def test_strategy_pack_registry_applies_lab_route_to_existing_tool_pack_without_replacing_it() -> None:
    root = _workspace('strategy_pack_registry_lab_tools')
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'evolution'))
    repository = StrategyPackRepository(db, storage)
    registry = StrategyPackRegistry(repository)
    intent = TaskIntent(intent_key='tools.local_workflow', title='Tool local-first', detected_role=TaskRole.TOOL_USE)
    context = TaskContext(
        experiment_insights=[
            {
                'domain': 'code',
                'subject_key': 'general',
                'recommended_route': 'code_agent',
                'score': 0.94,
                'confidence': 0.9,
                'rationale': 'El agente de codigo local es la via historicamente mas fuerte para esta tarea.',
            }
        ]
    )
    pack = registry.resolve_pack(intent, context)
    capabilities = [
        CapabilityReadiness(capability_id='tools.local.registry', title='Registro tools', status=CapabilityStatus.READY, score=0.9),
        CapabilityReadiness(capability_id='tools.local.execution', title='Ejecucion tools', status=CapabilityStatus.READY_WITH_APPROVAL, score=0.82),
    ]

    candidates = registry.build_candidates(pack=pack, intent=intent, context=context, capabilities=capabilities)
    parameter_map = {item.key: item for item in candidates[0].parameters}

    assert pack.pack_id == 'tools.local_first'
    assert parameter_map['tool_id'].default_value == 'aider_coder'
    assert parameter_map['tool_id'].value == 'aider_coder'
    assert parameter_map['execution_scope'].default_value == 'write'
    assert candidates[0].metadata['recommended_tool_id'] == 'aider_coder'
    assert candidates[0].metadata['recommended_execution_scope'] == 'write'
