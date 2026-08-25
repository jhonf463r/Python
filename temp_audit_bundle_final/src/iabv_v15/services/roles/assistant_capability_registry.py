"""Registro declarativo de `AssistantCapabilityProfile` para PCS v1.

Es puramente descriptivo: no dispara acciones, no muta estado, no consulta
red. Los valores semilla están basados en conocimiento público y se marcan
con ``confidence=0.7`` y ``unresolved_fields=["measured_latency",
"measured_cost"]`` para que una sesión futura los afine midiendo en vivo.

El registro es mutable sólo por ``register``/``with_defaults``: los perfiles
devueltos vía ``get``/``get_or_default``/``all_profiles`` son copias
independientes (``model_copy``) para evitar que un consumidor mute al resto.
"""

from __future__ import annotations

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantFrameKind,
    AssistantStrength,
)

# Fallback usado cuando se pregunta por un ``assistant_kind`` desconocido.
# La decisión de "desconocido" se toma acá y no en cada consumidor para
# mantener el invariante: el registry SIEMPRE devuelve un perfil válido.
_UNKNOWN_ASSISTANT_KIND = "unknown"


def _seed_profiles() -> list[AssistantCapabilityProfile]:
    """Perfiles hardcoded basados en conocimiento público."""

    unresolved = ["measured_latency", "measured_cost"]
    evidence = ["public_docs_v1"]

    return [
        AssistantCapabilityProfile(
            assistant_kind="codex",
            display_name="Codex / ChatGPT para código",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.STRUCTURED_REASONING,
            ],
            native_tools=["shell", "file_edit", "apply_patch"],
            optimal_frame=AssistantFrameKind.DIFF_AND_TESTS,
            max_context_tokens=128_000,
            avg_latency_ms=4_000,
            cost_signal="medium",
            supports_function_calling=True,
            supports_vision=False,
            supports_browser=False,
            supports_shell=True,
            known_limitations=[
                "No siempre verifica estado del sistema antes de editar.",
                "Puede re-ejecutar pytest ignorando run_pytest del cuerpo.",
            ],
            evidence_refs=evidence,
            confidence=0.7,
            unresolved_fields=unresolved,
        ),
        AssistantCapabilityProfile(
            assistant_kind="chatgpt_web",
            display_name="ChatGPT (web, GPT-4/4o)",
            strengths=[
                AssistantStrength.STRUCTURED_REASONING,
                AssistantStrength.CREATIVE_WRITING,
                AssistantStrength.MULTIMODAL_VISION,
                AssistantStrength.RETRIEVAL_AUGMENTED,
            ],
            native_tools=["web_browsing", "file_upload", "vision"],
            optimal_frame=AssistantFrameKind.STRUCTURED_QA,
            max_context_tokens=128_000,
            avg_latency_ms=6_000,
            cost_signal="medium",
            supports_function_calling=True,
            supports_vision=True,
            supports_browser=True,
            supports_shell=False,
            known_limitations=[
                "Cuota diaria variable según plan.",
                "No tiene acceso al filesystem local del usuario.",
            ],
            evidence_refs=evidence,
            confidence=0.7,
            unresolved_fields=unresolved,
        ),
        AssistantCapabilityProfile(
            assistant_kind="claude_web",
            display_name="Claude (Anthropic, web)",
            strengths=[
                AssistantStrength.LONG_CONTEXT_SYNTHESIS,
                AssistantStrength.STRUCTURED_REASONING,
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.CREATIVE_WRITING,
            ],
            native_tools=["file_upload", "vision"],
            optimal_frame=AssistantFrameKind.LONG_NARRATIVE,
            max_context_tokens=200_000,
            avg_latency_ms=8_000,
            cost_signal="medium",
            supports_function_calling=True,
            supports_vision=True,
            supports_browser=False,
            supports_shell=False,
            known_limitations=[
                "Sin browsing nativo en la web pública.",
                "Sin filesystem local.",
            ],
            evidence_refs=evidence,
            confidence=0.7,
            unresolved_fields=unresolved,
        ),
        AssistantCapabilityProfile(
            assistant_kind="devin",
            display_name="Devin (Cognition)",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.STRUCTURED_REASONING,
                AssistantStrength.SHELL_EXECUTION,
                AssistantStrength.WEB_BROWSING,
            ],
            native_tools=["shell", "file_edit", "browser", "git", "git_pr"],
            optimal_frame=AssistantFrameKind.TASK_LIST_AND_PR,
            max_context_tokens=200_000,
            avg_latency_ms=15_000,
            cost_signal="high",
            supports_function_calling=True,
            supports_vision=True,
            supports_browser=True,
            supports_shell=True,
            known_limitations=[
                "Latencia alta por ser agente multi-paso.",
                "Consume cuota por sesión.",
            ],
            evidence_refs=evidence,
            confidence=0.7,
            unresolved_fields=unresolved,
        ),
        AssistantCapabilityProfile(
            assistant_kind="windsurf",
            display_name="Windsurf (Codeium IDE agent)",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.STRUCTURED_REASONING,
                AssistantStrength.SHELL_EXECUTION,
            ],
            native_tools=["shell", "file_edit", "apply_patch", "ide_context"],
            optimal_frame=AssistantFrameKind.DIFF_AND_TESTS,
            max_context_tokens=200_000,
            avg_latency_ms=5_000,
            cost_signal="medium",
            supports_function_calling=True,
            supports_vision=False,
            supports_browser=False,
            supports_shell=True,
            known_limitations=[
                "Opera dentro del IDE; el usuario debe tener Windsurf abierto.",
                "No expone browsing web nativo ni visión en el producto actual.",
                "Cuota depende del plan de Codeium.",
            ],
            evidence_refs=evidence,
            confidence=0.7,
            unresolved_fields=unresolved,
        ),
        AssistantCapabilityProfile(
            assistant_kind="ollama_local",
            display_name="Ollama local (llama3/mistral/qwen)",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.STRUCTURED_REASONING,
            ],
            native_tools=[],
            optimal_frame=AssistantFrameKind.STRUCTURED_QA,
            max_context_tokens=8_000,
            avg_latency_ms=2_500,
            cost_signal="free_local",
            supports_function_calling=False,
            supports_vision=False,
            supports_browser=False,
            supports_shell=False,
            known_limitations=[
                "Calidad variable según modelo instalado.",
                "Ventana de contexto corta; no apto para síntesis larga.",
            ],
            evidence_refs=evidence,
            confidence=0.7,
            unresolved_fields=unresolved,
        ),
    ]


class AssistantCapabilityRegistry:
    """Catálogo de perfiles indexado por ``assistant_kind``.

    Invariantes:
      - ``get_or_default`` nunca devuelve ``None``: ante un kind desconocido,
        devuelve un perfil vacío con ``assistant_kind='unknown'`` y
        ``confidence=0.0``.
      - ``all_profiles`` devuelve copias; mutarlas no afecta el registro.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, AssistantCapabilityProfile] = {}

    @classmethod
    def with_defaults(cls) -> "AssistantCapabilityRegistry":
        registry = cls()
        for profile in _seed_profiles():
            registry.register(profile)
        return registry

    def register(self, profile: AssistantCapabilityProfile) -> None:
        kind = (profile.assistant_kind or "").strip()
        if not kind:
            raise ValueError("AssistantCapabilityProfile requires a non-empty assistant_kind")
        self._profiles[kind] = profile

    def get(self, assistant_kind: str) -> AssistantCapabilityProfile | None:
        key = (assistant_kind or "").strip()
        profile = self._profiles.get(key)
        if profile is None:
            return None
        return profile.model_copy(deep=True)

    def get_or_default(self, assistant_kind: str) -> AssistantCapabilityProfile:
        profile = self.get(assistant_kind)
        if profile is not None:
            return profile
        return AssistantCapabilityProfile(
            assistant_kind=_UNKNOWN_ASSISTANT_KIND,
            display_name=(assistant_kind or "").strip() or _UNKNOWN_ASSISTANT_KIND,
            confidence=0.0,
            unresolved_fields=["measured_latency", "measured_cost", "strengths"],
            metadata={"requested_assistant_kind": (assistant_kind or "").strip()},
        )

    def known_kinds(self) -> list[str]:
        return sorted(self._profiles.keys())

    def all_profiles(self) -> list[AssistantCapabilityProfile]:
        return [p.model_copy(deep=True) for p in self._profiles.values()]
