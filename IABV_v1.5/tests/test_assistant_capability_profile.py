"""Tests del contrato `AssistantCapabilityProfile` y del registry PCS v1."""

from __future__ import annotations

import pytest

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantFrameKind,
    AssistantStrength,
)
from iabv_v15.services.roles.assistant_capability_registry import (
    AssistantCapabilityRegistry,
)


def test_profile_default_values_are_safe() -> None:
    profile = AssistantCapabilityProfile(assistant_kind="custom")
    assert profile.assistant_kind == "custom"
    assert profile.display_name == ""
    assert profile.strengths == []
    assert profile.native_tools == []
    assert profile.optimal_frame == AssistantFrameKind.STRUCTURED_QA
    assert profile.max_context_tokens == 0
    assert profile.cost_signal == "unknown"
    assert profile.confidence == 0.0
    assert profile.unresolved_fields == []
    assert profile.metadata == {}


def test_profile_serialization_round_trip() -> None:
    profile = AssistantCapabilityProfile(
        assistant_kind="claude_web",
        display_name="Claude",
        strengths=[AssistantStrength.LONG_CONTEXT_SYNTHESIS],
        optimal_frame=AssistantFrameKind.LONG_NARRATIVE,
        max_context_tokens=200_000,
        supports_vision=True,
        confidence=0.7,
        unresolved_fields=["measured_latency"],
    )
    raw = profile.model_dump(mode="json")
    rebuilt = AssistantCapabilityProfile.model_validate(raw)
    assert rebuilt == profile
    assert raw["strengths"] == ["long_context_synthesis"]
    assert raw["optimal_frame"] == "long_narrative"


def test_registry_with_defaults_seeds_known_kinds() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    known = set(registry.known_kinds())
    assert known == {"codex", "chatgpt_web", "claude_web", "devin", "ollama_local"}

    codex = registry.get("codex")
    assert codex is not None
    assert codex.optimal_frame == AssistantFrameKind.DIFF_AND_TESTS
    assert AssistantStrength.CODE_GENERATION in codex.strengths
    assert codex.confidence == 0.7
    assert "measured_latency" in codex.unresolved_fields

    claude = registry.get("claude_web")
    assert claude is not None
    assert claude.optimal_frame == AssistantFrameKind.LONG_NARRATIVE
    assert claude.max_context_tokens >= 200_000

    devin = registry.get("devin")
    assert devin is not None
    assert devin.optimal_frame == AssistantFrameKind.TASK_LIST_AND_PR
    assert devin.supports_shell is True

    ollama = registry.get("ollama_local")
    assert ollama is not None
    assert ollama.cost_signal == "free_local"
    assert ollama.supports_function_calling is False


def test_registry_get_returns_none_for_unknown() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    assert registry.get("nonexistent_kind") is None


def test_registry_get_or_default_returns_placeholder_for_unknown() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    fallback = registry.get_or_default("gpt_5_future")
    assert fallback.assistant_kind == "unknown"
    assert fallback.confidence == 0.0
    assert fallback.metadata.get("requested_assistant_kind") == "gpt_5_future"


def test_registry_returned_profiles_are_independent_copies() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    first = registry.get("codex")
    second = registry.get("codex")
    assert first is not None and second is not None
    assert first is not second
    first.strengths.append(AssistantStrength.CREATIVE_WRITING)
    # la mutación del consumidor no contamina el registro
    fresh = registry.get("codex")
    assert fresh is not None
    assert AssistantStrength.CREATIVE_WRITING not in fresh.strengths


def test_registry_all_profiles_returns_copies() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    profiles = registry.all_profiles()
    assert len(profiles) == 5
    profiles[0].display_name = "mutated"
    # no afecta al registro original
    reloaded = registry.all_profiles()
    assert all(p.display_name != "mutated" for p in reloaded)


def test_registry_register_rejects_empty_kind() -> None:
    registry = AssistantCapabilityRegistry()
    with pytest.raises(ValueError):
        registry.register(AssistantCapabilityProfile(assistant_kind="   "))


def test_registry_register_overrides_existing() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    override = AssistantCapabilityProfile(
        assistant_kind="codex",
        display_name="Codex override",
        confidence=0.9,
    )
    registry.register(override)
    assert registry.get("codex") == override
