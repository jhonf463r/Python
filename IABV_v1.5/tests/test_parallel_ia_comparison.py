"""Tests para PR I — cotejo paralelo de IAs externas.

Los tests se enfocan en la logica nueva del ``AdaptiveTaskOrchestrator``
(``_parallel_ia_comparison`` + gating via ``AutonomyGovernancePolicy``) sin
levantar todo el wiring del orquestador. Se crean ``stubs`` minimos que
simulan los colaboradores que el metodo necesita: ``synaptic_decision`` con
candidatos rankeados y ``autonomous_evolution_service`` con
``plan_or_execute``.

Regla operativa (AGENTS.md):
- primero tests focalizados del slice (este archivo)
- despues una regresion razonable sobre ``tests/``
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from iabv_v15.domain.models import (
    ExperimentRun,
    InferenceRequest,
    SynapticRoutingDecision,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


class _StubRoleRouter:
    """Minimal stub that exposes ``worker_health_gate`` for parallel comparison."""

    def worker_health_gate(self, *, target_assistant: str, **_: Any) -> dict[str, Any]:
        return {}


def _make_orchestrator(
    *,
    autonomous_evolution_service: Any,
    autonomy_governance_policy: AutonomyGovernancePolicy | None = None,
    experiment_lab: Any | None = None,
) -> AdaptiveTaskOrchestrator:
    """Instancia un orquestador `esqueleto` solo para probar la logica nueva.

    El metodo bajo prueba (``_parallel_ia_comparison``) solo usa
    ``self.autonomous_evolution_service``, ``self.autonomy_governance_policy``
    y ``self.experiment_lab``. Los demas atributos se dejan en ``None`` porque
    no se tocan en estos tests.
    """
    orchestrator = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
    orchestrator.role_router = _StubRoleRouter()
    orchestrator.adaptive_session_repository = None
    orchestrator.intent_service = None
    orchestrator.context_assembler = None
    orchestrator.capability_service = None
    orchestrator.strategy_pack_registry = None
    orchestrator.planner_service = None
    orchestrator.approval_gate_service = None
    orchestrator.execution_playbook_service = None
    orchestrator.task_outcome_recorder = None
    orchestrator.autonomous_evolution_service = autonomous_evolution_service
    orchestrator.unified_memory_layer = None
    orchestrator.goal_engine = None
    orchestrator.autonomy_governance_policy = autonomy_governance_policy
    orchestrator.synaptic_router = None
    orchestrator.experiment_lab = experiment_lab
    orchestrator.control_master_service = None
    orchestrator.control_master_digest_builder = None
    return orchestrator


def _make_request(user_goal: str = 'comparar IAs') -> InferenceRequest:
    return InferenceRequest(user_goal=user_goal, goal_parameters={})


def _make_synaptic_decision_two_candidates() -> SynapticRoutingDecision:
    """``SynapticRoutingDecision`` con selected + alternative (2 candidatos)."""
    return SynapticRoutingDecision(
        selected_assistant_kind='chatgpt',
        alternatives=[{'assistant_kind': 'codex', 'score': 0.71}],
        fit_score=0.8,
        weight_score=0.7,
        availability_score=1.0,
        total_score=0.82,
        routing_enabled=True,
        reason='ok',
    )


def _make_synaptic_decision_single_candidate() -> SynapticRoutingDecision:
    return SynapticRoutingDecision(
        selected_assistant_kind='chatgpt',
        alternatives=[],
        fit_score=0.8,
        weight_score=0.7,
        availability_score=1.0,
        total_score=0.82,
        routing_enabled=True,
        reason='ok',
    )


class _RecordingEvolutionService:
    """Fake ``AutonomousEvolutionService`` que registra llamadas."""

    def __init__(self, *, results_by_kind: dict[str, dict[str, Any]] | None = None, delay_s: float = 0.0) -> None:
        self._results_by_kind = dict(results_by_kind or {})
        self._delay_s = float(delay_s)
        self.calls: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def plan_or_execute(
        self,
        *,
        adaptive_payload: dict[str, Any],
        user_goal: str,
        source: str,
        decision_context: Any | None = None,
    ) -> dict[str, Any]:
        kind = str((adaptive_payload.get('metadata') or {}).get('assistant_kind') or '').lower()
        if self._delay_s > 0:
            time.sleep(self._delay_s)
        with self._lock:
            self.calls.append({
                'assistant_kind': kind,
                'user_goal': user_goal,
                'source': source,
            })
        default = {
            'status': 'prepared',
            'assistant_kind': kind,
            'response_validation': {'confidence': 0.7},
        }
        return dict(self._results_by_kind.get(kind, default))


class _PerKindDelayEvolutionService(_RecordingEvolutionService):
    """Variante donde cada ``assistant_kind`` tiene su propio delay."""

    def __init__(self, *, delays_by_kind: dict[str, float], results_by_kind: dict[str, dict[str, Any]] | None = None) -> None:
        super().__init__(results_by_kind=results_by_kind)
        self._delays_by_kind = dict(delays_by_kind)

    def plan_or_execute(
        self,
        *,
        adaptive_payload: dict[str, Any],
        user_goal: str,
        source: str,
        decision_context: Any | None = None,
    ) -> dict[str, Any]:
        kind = str((adaptive_payload.get('metadata') or {}).get('assistant_kind') or '').lower()
        delay = self._delays_by_kind.get(kind, 0.0)
        if delay:
            time.sleep(delay)
        with self._lock:
            self.calls.append({'assistant_kind': kind, 'user_goal': user_goal, 'source': source})
        default = {
            'status': 'prepared',
            'assistant_kind': kind,
            'response_validation': {'confidence': 0.7},
        }
        return dict(self._results_by_kind.get(kind, default))


class _InMemoryExperimentLab:
    """Fake ``ExperimentLab`` expuesto al orquestador solo para registro."""

    class _Repo:
        def __init__(self) -> None:
            self.runs: list[ExperimentRun] = []

        def save_run(self, run: ExperimentRun) -> ExperimentRun:
            self.runs.append(run)
            return run

    def __init__(self, *, with_register_comparison: bool = False) -> None:
        self.repository = _InMemoryExperimentLab._Repo()
        self.registered_comparisons: list[dict[str, Any]] = []
        self._with_register_comparison = bool(with_register_comparison)

    # Atributo opcional: si ``with_register_comparison=True`` el metodo se
    # expone; si no, el orquestador debe caer al camino ``save_run``.
    if True:
        def register_comparison(self, **kwargs: Any) -> None:
            if not self._with_register_comparison:
                raise AttributeError('register_comparison not exposed in this fake')
            self.registered_comparisons.append(dict(kwargs))


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


def test_governance_flag_defaults_to_true() -> None:
    policy = AutonomyGovernancePolicy()
    allowed, reason = policy.allow_parallel_ia_comparison()
    assert allowed is True
    assert reason is None


def test_governance_flag_can_be_disabled() -> None:
    policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)
    allowed, reason = policy.allow_parallel_ia_comparison()
    assert allowed is False
    assert reason  # razon no vacia


def test_two_candidates_both_consulted_when_governance_allows() -> None:
    service = _RecordingEvolutionService()
    orchestrator = _make_orchestrator(autonomous_evolution_service=service)
    synaptic = _make_synaptic_decision_two_candidates()

    result = orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)

    assert result is not None
    assert result['status'] == 'compared'
    kinds_called = sorted(call['assistant_kind'] for call in service.calls)
    assert kinds_called == ['chatgpt', 'codex']
    # Ambos resultados aparecen en el payload
    assert sorted(r['assistant_kind'] for r in result['results']) == ['chatgpt', 'codex']
    assert 'best' in result and result['best'].get('assistant_kind') in {'chatgpt', 'codex'}
    # Todos consultados con source explicito para trazabilidad
    assert all(call['source'] == 'parallel_ia_comparison' for call in service.calls)


def test_single_candidate_skips_parallel_execution() -> None:
    service = _RecordingEvolutionService()
    orchestrator = _make_orchestrator(autonomous_evolution_service=service)
    synaptic = _make_synaptic_decision_single_candidate()

    # El orquestador solo construye candidatos desde selected + alternatives;
    # con un unico selected el ranked list tiene longitud 1 y debe evitar el pool.
    assert len(orchestrator._ranked_candidates_from_synaptic(synaptic)) == 1
    result = orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)

    assert result is None
    assert service.calls == []


def test_governance_block_signals_block_via_gate() -> None:
    """Con governance en bloqueo, el gate devuelve allowed=False; el caller
    (``handle_request``) responde cayendo a ruta IA unica. Aqui verificamos
    solo el gate expuesto por el orquestador."""
    policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)
    service = _RecordingEvolutionService()
    orchestrator = _make_orchestrator(
        autonomous_evolution_service=service,
        autonomy_governance_policy=policy,
    )

    allowed, reason = orchestrator._parallel_comparison_allowed()
    assert allowed is False
    assert reason  # no vacio

    # Cuando se consulta el gate se espera que el caller NO invoque el pool,
    # simulamos ese caminar para asegurar cero llamadas a plan_or_execute.
    synaptic = _make_synaptic_decision_two_candidates()
    if allowed:  # pragma: no cover - defensa en caso de regresion
        orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)
    assert service.calls == []


def test_timeout_handling_slow_vs_fast_ia() -> None:
    """Una IA lenta + una rapida: el cotejo resuelve con al menos la rapida.

    Usamos un timeout dominantemente corto sobre el pool para forzar el
    escenario sin esperar 30s en test. Monkeypatchamos el constante del
    orquestador solo para este caso.
    """
    service = _PerKindDelayEvolutionService(
        delays_by_kind={'chatgpt': 0.01, 'codex': 5.0},
    )
    orchestrator = _make_orchestrator(autonomous_evolution_service=service)
    synaptic = _make_synaptic_decision_two_candidates()

    # Timeout agresivo solo para la prueba: la IA lenta NO completa a tiempo,
    # la rapida si. Esperamos que el cotejo devuelva el resultado parcial sin
    # romper.
    original_timeout = AdaptiveTaskOrchestrator._PARALLEL_IA_COMPARISON_TIMEOUT_S
    AdaptiveTaskOrchestrator._PARALLEL_IA_COMPARISON_TIMEOUT_S = 0.3
    try:
        result = orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)
    finally:
        AdaptiveTaskOrchestrator._PARALLEL_IA_COMPARISON_TIMEOUT_S = original_timeout

    assert result is not None
    # La IA rapida debe haber devuelto un resultado.
    returned_kinds = [r['assistant_kind'] for r in result.get('results', [])]
    assert 'chatgpt' in returned_kinds
    # La IA lenta puede haber completado antes de ser consultada, aparecer en
    # timed_out, o registrarse como fallo; el cotejo nunca debe propagar la
    # excepcion hacia afuera.
    assert result['status'] in {'compared', 'no_results'}


def test_experiment_lab_save_run_is_called_when_no_register_comparison() -> None:
    service = _RecordingEvolutionService()
    lab = _InMemoryExperimentLab(with_register_comparison=False)
    orchestrator = _make_orchestrator(
        autonomous_evolution_service=service,
        experiment_lab=lab,
    )
    synaptic = _make_synaptic_decision_two_candidates()

    result = orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)

    assert result is not None and result['status'] == 'compared'
    # Se guarda un ExperimentRun por candidato via repository.save_run.
    saved_kinds = sorted(run.assistant_kind for run in lab.repository.runs)
    assert saved_kinds == ['chatgpt', 'codex']


def test_experiment_lab_register_comparison_is_preferred_when_available() -> None:
    service = _RecordingEvolutionService()
    lab = _InMemoryExperimentLab(with_register_comparison=True)
    orchestrator = _make_orchestrator(
        autonomous_evolution_service=service,
        experiment_lab=lab,
    )
    synaptic = _make_synaptic_decision_two_candidates()

    result = orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)

    assert result is not None and result['status'] == 'compared'
    assert len(lab.registered_comparisons) == 1
    # Si se uso register_comparison no se debe haber caido al save_run.
    assert lab.repository.runs == []


def test_no_autonomous_evolution_service_returns_none() -> None:
    orchestrator = _make_orchestrator(autonomous_evolution_service=None)
    synaptic = _make_synaptic_decision_two_candidates()
    assert orchestrator._parallel_ia_comparison(None, _make_request(), synaptic) is None


def test_best_result_picks_higher_confidence() -> None:
    service = _RecordingEvolutionService(
        results_by_kind={
            'chatgpt': {
                'status': 'prepared',
                'assistant_kind': 'chatgpt',
                'response_validation': {'confidence': 0.55},
            },
            'codex': {
                'status': 'prepared',
                'assistant_kind': 'codex',
                'response_validation': {'confidence': 0.91},
            },
        }
    )
    orchestrator = _make_orchestrator(autonomous_evolution_service=service)
    synaptic = _make_synaptic_decision_two_candidates()

    result = orchestrator._parallel_ia_comparison(None, _make_request(), synaptic)
    assert result is not None
    assert result['best']['assistant_kind'] == 'codex'


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(pytest.main([__file__, '-v']))
