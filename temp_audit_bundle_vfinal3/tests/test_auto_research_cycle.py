"""PR J: pruebas del auto-inicio de investigacion desde backlog.

Cubre el contrato minimo esperado de ``AutonomousValidationCycleService``:
- cuando hay items accionables y la bandera ``IABV_AUTO_RESEARCH_ENABLED``
  esta habilitada, el ciclo inicia un sandbox experiment por tick
- cuando la bandera esta deshabilitada, el ciclo no toca el backlog
- cuando las herramientas requeridas no estan disponibles, el item se omite
- el ciclo respeta ``_AUTO_RESEARCH_MAX_PER_TICK`` (maximo 1 por tick)

El sandbox real no se invoca: usamos un stub que registra las llamadas y
devuelve un ``SandboxExperiment`` coherente con la recomendacion recibida.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    EvaluationRoute,
    ExperimentDomain,
    SandboxExperiment,
    SandboxExperimentVerdict,
    ToolCard,
    ToolType,
    WorldModelSnapshot,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.self_teach.autonomous_validation_cycle import (
    AutonomousValidationCycleService,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _lab(root: Path):
    storage = ArtifactStorage(str(root / 'evolution'))
    repository = ExperimentLabRepository(AppDatabase(str(root / 'app.sqlite')), storage)
    lab = ExperimentLab(
        repository=repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=AdaptiveWeightLayer()),
    )
    return lab, repository, storage


class _StaticService:
    def __init__(self, model) -> None:
        self._model = model

    def current_model(self):
        return self._model


class _RecordingSandbox:
    """Devuelve un experimento coherente con la recomendacion recibida.

    El ciclo real delega en ``SandboxExperimentService`` para correr la
    validacion contra el estado operativo; aqui solo hace falta un objeto
    que cumpla el contrato ``validate_recommendation`` y registre las
    llamadas para que los tests puedan verificar cuantas iniciativas se
    dispararon y sobre que subject_key.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def validate_recommendation(self, recommendation, *, world_model, environment_model=None, reason='manual'):
        self.calls.append(
            {
                'subject_key': recommendation.subject_key,
                'assistant_kind': recommendation.recommended_assistant_kind,
                'config_signature': recommendation.recommended_config_signature,
                'reason': reason,
                'metadata': dict(recommendation.metadata or {}),
            }
        )
        return SandboxExperiment(
            subject_key=recommendation.subject_key,
            sandbox_subject_key=f'sandbox:{recommendation.subject_key}',
            domain=recommendation.domain,
            candidate_route=recommendation.recommended_route,
            candidate_assistant_kind=recommendation.recommended_assistant_kind,
            candidate_config_signature=recommendation.recommended_config_signature,
            promote_to_primary=False,
            verdict=SandboxExperimentVerdict.DOUBTFUL,
            summary=f'Auto-research iniciado para {recommendation.subject_key}.',
            metadata={'reason': reason, **(recommendation.metadata or {})},
        )


class _StubToolRegistry:
    """Registro minimo que expone ``list_cards()`` con tarjetas ``available``."""

    def __init__(self, *, available_tools: list[str]) -> None:
        self._cards = [
            ToolCard(
                tool_id=name,
                title=name,
                tool_type=ToolType.CUSTOM,
                adapter_key=name,
                available=True,
                capabilities=[name],
            )
            for name in available_tools
        ]

    def list_cards(self) -> list[ToolCard]:
        return list(self._cards)


def _write_backlog(data_root: Path, *, session: str, entries: list[dict]) -> Path:
    backlog_dir = data_root / 'chat_research_backlog'
    backlog_dir.mkdir(parents=True, exist_ok=True)
    path = backlog_dir / f'{session}.jsonl'
    with path.open('w', encoding='utf-8') as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return path


def _capability_entry(
    *,
    kind: str = 'hardware_gpu',
    matched: str = 'GPU',
    session: str = 'sess_a',
    status: str = 'open',
    detected_at: str = '2025-04-22T10:00:00+00:00',
) -> dict:
    return {
        'schema_version': 1,
        'session_id': session,
        'detected_at_utc': detected_at,
        'kind': kind,
        'label': f'Capability {kind}',
        'matched_text': matched,
        'research_hint': f'Probar {kind} localmente y medir performance.',
        'raw_message': f'Tengo {matched} disponible.',
        'status': status,
    }


def _build_cycle(
    root: Path,
    *,
    data_root: Path | None = None,
    tool_registry=None,
):
    lab, repository, storage = _lab(root)
    sandbox = _RecordingSandbox()
    cycle = AutonomousValidationCycleService(
        experiment_lab=lab,
        experiment_lab_repository=repository,
        sandbox_experiment_service=sandbox,
        world_model_service=_StaticService(WorldModelSnapshot()),
        environment_self_awareness_service=_StaticService(EnvironmentSelfModel(scan_status='ready')),
        storage=storage,
        auto_start=False,
        tool_registry=tool_registry,
        research_backlog_root=data_root,
    )
    return cycle, sandbox, repository


def test_auto_research_initiates_sandbox_when_enabled_and_item_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('IABV_AUTO_RESEARCH_ENABLED', '1')
    root = _workspace('auto_research_actionable')
    try:
        data_root = root / 'data'
        data_root.mkdir(parents=True, exist_ok=True)
        backlog_path = _write_backlog(
            data_root,
            session='sess_a',
            entries=[_capability_entry(kind='hardware_gpu', matched='GPU')],
        )
        cycle, sandbox, _repository = _build_cycle(root, data_root=data_root)

        cycle._safe_tick(reason='unit_test')

        assert len(sandbox.calls) == 1
        call = sandbox.calls[0]
        assert call['subject_key'].startswith('capability:hardware_gpu')
        assert call['assistant_kind'] == 'auto_research'
        assert call['metadata']['auto_research_source'] == 'capability_research'

        # El backlog debe haber quedado marcado como in_progress para no
        # reiniciar la misma investigacion en el siguiente tick.
        lines = [
            json.loads(line)
            for line in backlog_path.read_text(encoding='utf-8').splitlines()
            if line.strip()
        ]
        assert lines[0]['status'] == 'in_progress'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_research_is_noop_when_flag_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('IABV_AUTO_RESEARCH_ENABLED', '0')
    root = _workspace('auto_research_disabled')
    try:
        data_root = root / 'data'
        data_root.mkdir(parents=True, exist_ok=True)
        backlog_path = _write_backlog(
            data_root,
            session='sess_a',
            entries=[_capability_entry(kind='hardware_gpu', matched='GPU')],
        )
        cycle, sandbox, _repository = _build_cycle(root, data_root=data_root)

        scanned = cycle._scan_research_backlog()
        initiated = cycle._auto_research_pass(reason='unit_test')

        assert scanned == []
        assert initiated == []
        assert sandbox.calls == []
        original = backlog_path.read_text(encoding='utf-8').strip().splitlines()
        assert json.loads(original[0])['status'] == 'open'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_research_skips_items_without_required_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('IABV_AUTO_RESEARCH_ENABLED', '1')
    root = _workspace('auto_research_missing_tools')
    try:
        data_root = root / 'data'
        data_root.mkdir(parents=True, exist_ok=True)
        # ``local_model`` requiere ``ollama`` segun la tabla de mapeos del
        # ciclo. El registro provisto no expone esa herramienta, asi que el
        # item debe quedar descartado hasta que el usuario lo instale.
        _write_backlog(
            data_root,
            session='sess_b',
            entries=[
                _capability_entry(
                    kind='local_model',
                    matched='qwen3',
                    detected_at='2025-04-22T11:00:00+00:00',
                )
            ],
        )
        registry = _StubToolRegistry(available_tools=['python', 'git'])
        cycle, sandbox, _repository = _build_cycle(
            root, data_root=data_root, tool_registry=registry
        )

        actionable = cycle._scan_research_backlog()
        initiated = cycle._auto_research_pass(reason='unit_test')

        assert actionable == []
        assert initiated == []
        assert sandbox.calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_auto_research_respects_max_one_initiation_per_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('IABV_AUTO_RESEARCH_ENABLED', '1')
    root = _workspace('auto_research_max_per_tick')
    try:
        data_root = root / 'data'
        data_root.mkdir(parents=True, exist_ok=True)
        _write_backlog(
            data_root,
            session='sess_multi',
            entries=[
                _capability_entry(
                    kind='hardware_gpu',
                    matched='GPU',
                    detected_at='2025-04-22T12:00:00+00:00',
                ),
                _capability_entry(
                    kind='external_account',
                    matched='github',
                    detected_at='2025-04-22T12:05:00+00:00',
                ),
                _capability_entry(
                    kind='local_runtime',
                    matched='docker',
                    detected_at='2025-04-22T12:10:00+00:00',
                ),
            ],
        )
        cycle, sandbox, _repository = _build_cycle(root, data_root=data_root)

        actionable = cycle._scan_research_backlog()
        initiated = cycle._auto_research_pass(reason='unit_test')

        # El scan puede exponer hasta 3 items accionables, pero el tick
        # solo puede lanzar 1 para no saturar el sandbox.
        assert len(actionable) == 3
        assert len(initiated) == 1
        assert len(sandbox.calls) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
