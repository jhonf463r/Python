"""Tests del `SynapticRouter` (PCS v1 — Pieza 4)."""

from __future__ import annotations

from typing import Callable

import pytest

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantFrameKind,
    AssistantStrength,
    NetworkStatusSnapshot,
    SynapticRoutingDecision,
    ToolLiveStatus,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.roles.assistant_capability_registry import (
    AssistantCapabilityRegistry,
)
from iabv_v15.services.roles.synaptic_router import (
    SynapticRouter,
    _FEATURE_FLAG_ENV,
)


def _registry_with_profiles() -> AssistantCapabilityRegistry:
    """Registry determinístico con 3 perfiles que los tests pueden anclar."""

    registry = AssistantCapabilityRegistry()
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="codex",
            display_name="Codex",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.STRUCTURED_REASONING,
            ],
            optimal_frame=AssistantFrameKind.DIFF_AND_TESTS,
            confidence=0.9,
        )
    )
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="claude_web",
            display_name="Claude",
            strengths=[
                AssistantStrength.LONG_CONTEXT_SYNTHESIS,
                AssistantStrength.STRUCTURED_REASONING,
            ],
            optimal_frame=AssistantFrameKind.LONG_NARRATIVE,
            confidence=0.85,
        )
    )
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="chatgpt_web",
            display_name="ChatGPT",
            strengths=[
                AssistantStrength.STRUCTURED_REASONING,
                AssistantStrength.MULTIMODAL_VISION,
            ],
            optimal_frame=AssistantFrameKind.STRUCTURED_QA,
            confidence=0.8,
        )
    )
    return registry


def _empty_world_model() -> WorldModelSnapshot:
    return WorldModelSnapshot(
        network_status=NetworkStatusSnapshot(connected=True, status="ok"),
    )


def _router_with(
    *,
    world_model_provider: Callable[[], WorldModelSnapshot | None] | None = None,
    registry: AssistantCapabilityRegistry | None = None,
) -> SynapticRouter:
    return SynapticRouter(
        capability_registry=registry or _registry_with_profiles(),
        adaptive_weight_layer=AdaptiveWeightLayer(),
        world_model_provider=world_model_provider or _empty_world_model,
    )


def test_feature_flag_off_preserves_previous_behaviour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_FEATURE_FLAG_ENV, raising=False)
    router = _router_with()
    decision = router.decide(task_kind="code_generation")

    assert isinstance(decision, SynapticRoutingDecision)
    assert decision.routing_enabled is False
    assert decision.selected_assistant_kind == ""
    assert decision.metadata["routing_enabled"] is False
    # Los scores del ganador quedan en 0 cuando el flag está off, pero
    # las alternativas sí traen el ranking calculado como evidencia.
    assert decision.total_score == 0.0
    assert decision.alternatives, "alternatives deben traer el ranking aunque el flag esté off"
    for alt in decision.alternatives:
        assert set(alt.keys()) == {"assistant_kind", "score"}


def test_feature_flag_on_selects_highest_total_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")
    router = _router_with()
    decision = router.decide(task_kind="code_generation")

    assert decision.routing_enabled is True
    # Sólo `codex` tiene `CODE_GENERATION` → fit=1.0 * 0.5 = 0.5.
    # El resto tiene fit=0.0. availability=0.3 para todos (WM sin tools)
    # y weight=0.0 (no hay historial).
    assert decision.selected_assistant_kind == "codex"
    assert decision.fit_score == pytest.approx(1.0)
    assert decision.weight_score == pytest.approx(0.0)
    assert decision.availability_score == pytest.approx(0.3)
    expected_total = round(1.0 * 0.5 + 0.0 * 0.3 + 0.3 * 0.2, 4)
    assert decision.total_score == pytest.approx(expected_total)


def test_fit_score_counts_matching_strengths_fraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """task_kind genérico ``'code'`` mapea a >1 strengths vía substring."""

    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")
    router = _router_with()
    decision = router.decide(task_kind="code")

    # "code" → {CODE_GENERATION, CODE_REVIEW} (substring match).
    # codex cubre ambos → fit=1.0. claude_web cubre CODE_REVIEW no,
    # sólo STRUCTURED_REASONING y LONG_CONTEXT_SYNTHESIS → fit=0.0.
    assert decision.selected_assistant_kind == "codex"
    assert decision.fit_score == pytest.approx(1.0)
    # Los ranking contiene los 3 candidatos: ganador + 2 alternativas.
    assert len(decision.alternatives) == 2


def test_availability_score_derives_from_world_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")

    def _wm_with_status() -> WorldModelSnapshot:
        return WorldModelSnapshot(
            tool_live_status=[
                ToolLiveStatus(
                    tool_id="codex",
                    assistant_kind="codex",
                    available=False,
                    status="no_disponible",
                ),
                ToolLiveStatus(
                    tool_id="claude_web",
                    assistant_kind="claude_web",
                    available=True,
                    status="ok",
                ),
            ]
        )

    router = _router_with(world_model_provider=_wm_with_status)
    decision = router.decide(task_kind="structured_reasoning")

    # task_kind="structured_reasoning" → todos tienen fit=1.0
    # (los 3 perfiles incluyen STRUCTURED_REASONING).
    # codex: availability=0.0 → total=0.5+0+0.0=0.5
    # claude_web: availability=1.0 → total=0.5+0+0.2=0.7
    # chatgpt_web: availability=0.3 (no aparece en WM) → total=0.5+0+0.06=0.56
    assert decision.selected_assistant_kind == "claude_web"
    assert decision.availability_score == pytest.approx(1.0)
    alt_scores = {alt["assistant_kind"]: alt["score"] for alt in decision.alternatives}
    assert alt_scores["chatgpt_web"] > alt_scores["codex"]


def test_alternatives_are_sorted_descending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")
    router = _router_with()
    decision = router.decide(task_kind="structured_reasoning")

    # Los 3 perfiles comparten STRUCTURED_REASONING → fit=1.0 para todos.
    # Con availability=0.3 y weight=0.0 para todos, los totales empatan y
    # el orden de desempate es alfabético ascendente.
    scores = [alt["score"] for alt in decision.alternatives]
    assert scores == sorted(scores, reverse=True)
    kinds_in_order = [decision.selected_assistant_kind] + [
        alt["assistant_kind"] for alt in decision.alternatives
    ]
    # Como todos empatan, el orden alfabético estable nos da el ganador
    # alfabéticamente menor primero.
    assert kinds_in_order == sorted(kinds_in_order)


def test_unknown_candidate_uses_registry_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")
    router = _router_with()
    decision = router.decide(
        task_kind="code_generation",
        candidate_assistant_kinds=["codex", "made_up_assistant"],
    )

    # codex: fit=1.0 → total=0.56. made_up_assistant: fit=0 → total=0.06.
    assert decision.selected_assistant_kind == "codex"
    assert len(decision.alternatives) == 1
    assert decision.alternatives[0]["assistant_kind"] == "made_up_assistant"
    # El ganador sí es un kind conocido del registry.
    assert decision.metadata["winner_profile_known"] is True


def test_decision_serialises_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")
    router = _router_with()
    decision = router.decide(task_kind="code_generation")

    dumped = decision.model_dump(mode="json")
    hydrated = SynapticRoutingDecision.model_validate(dumped)

    assert hydrated == decision
    assert hydrated.routing_enabled is True
    assert hydrated.selected_assistant_kind == decision.selected_assistant_kind
    assert hydrated.alternatives == decision.alternatives


def test_unknown_task_kind_marks_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_FEATURE_FLAG_ENV, "true")
    router = _router_with()
    decision = router.decide(task_kind="xx_totally_unknown_kind_xx")

    assert "task_kind_unknown" in decision.unresolved_fields
    # Sin relevant strengths el fit de todos los candidatos es 0.0;
    # el ganador sale sólo por availability (0.3) y weight (0.0).
    assert decision.fit_score == pytest.approx(0.0)
    assert decision.total_score == pytest.approx(round(0.3 * 0.2, 4))


def test_flag_variants_are_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = _router_with()
    for raw in ("True", "TRUE", "true"):
        monkeypatch.setenv(_FEATURE_FLAG_ENV, raw)
        assert router.decide(task_kind="code_generation").routing_enabled is True
    for raw in ("false", "0", "off", ""):
        monkeypatch.setenv(_FEATURE_FLAG_ENV, raw)
        assert router.decide(task_kind="code_generation").routing_enabled is False
