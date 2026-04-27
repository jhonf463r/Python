"""`SynapticRouter` (PCS v1 — Pieza 4).

Adaptador puramente descriptivo: para un `task_kind` dado y una lista de
candidatos (o todos los kinds conocidos por el registry), calcula un
``fit_score`` (cuán bien se alinea el perfil de capacidades con el tipo
de tarea), un ``weight_score`` (historial adaptativo) y un
``availability_score`` (lectura del world_model vivo), y devuelve una
`SynapticRoutingDecision` con el ganador ordenado por puntaje total.

Contratos que respeta:
  * **No ejecuta la ruta** ni toca red/filesystem. `LocalRoleRouter`
    sigue siendo el decisor operativo; este router es un adaptador
    PCS que puede consumir otra capa (tool MCP, UI, etc.).
  * **Feature flag explícito**: con ``SYNAPTIC_ROUTING`` distinto de
    ``"true"`` devuelve una decisión con ``routing_enabled=False`` y
    ``selected_assistant_kind=''`` — el comportamiento previo del
    sistema queda idéntico por default.
  * **Fail-observable** ante kinds desconocidos: el registry devuelve
    un perfil placeholder (`assistant_kind='unknown'`, strengths=[])
    con ``confidence=0.0``; el router traspasa eso como evidencia.
  * No usa ``getattr``/``setattr`` para esquivar tipado: el branching
    por dependencias ausentes es explícito contra ``None``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantStrength,
    ExperimentRun,
    SynapticRoutingDecision,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.roles.assistant_capability_registry import (
    AssistantCapabilityRegistry,
)

if TYPE_CHECKING:
    from iabv_v15.infra.persistence.experiment_lab_repository import (
        ExperimentLabRepository,
    )

# Pesos del score total (0.5 / 0.3 / 0.2 según spec PCS v1). Expuestos
# como constantes en vez de números mágicos para que los tests puedan
# validar la fórmula sin duplicarla.
_FIT_WEIGHT = 0.5
_WEIGHT_WEIGHT = 0.3
_AVAILABILITY_WEIGHT = 0.2

# Availability defaults según tool_live_status del WorldModel vivo.
_AVAILABILITY_WHEN_AVAILABLE = 1.0
_AVAILABILITY_WHEN_UNKNOWN = 0.3
_AVAILABILITY_WHEN_UNAVAILABLE = 0.0

_FEATURE_FLAG_ENV = "SYNAPTIC_ROUTING"
# Alias explícito con prefijo IABV_ para coherencia con el resto de flags del
# repo (``IABV_AUTONOMOUS_EVOLUTION``, ``IABV_AUTONOMOUS_EXTERNAL_LAUNCH``…).
# Si cualquiera de los dos está en "true" el flag se considera ON.
_FEATURE_FLAG_ENV_ALIAS = "IABV_SYNAPTIC_ROUTING_ENABLED"

_TRUTHY_FLAG_VALUES = {"1", "true", "yes", "on", "si"}


def _feature_flag_enabled() -> bool:
    """Lectura en caliente del flag; así los tests lo pueden togglear.

    Soporta dos nombres de env:
      * ``SYNAPTIC_ROUTING`` (nombre histórico),
      * ``IABV_SYNAPTIC_ROUTING_ENABLED`` (alias con prefijo coherente).
    Ambos aceptan ``"1"``/``"true"``/``"yes"``/``"on"``/``"si"`` (case-insensitive).
    Si ambos están definidos, cualquiera encendido → ``True``.
    """

    for name in (_FEATURE_FLAG_ENV, _FEATURE_FLAG_ENV_ALIAS):
        raw = os.environ.get(name)
        if raw is None:
            continue
        if raw.strip().lower() in _TRUTHY_FLAG_VALUES:
            return True
    return False


def _normalize_kind(value: str) -> str:
    return (value or "").strip().lower()


# ---------------------------------------------------------------------------
# Provider-hint extraction — when the user_goal explicitly mentions a
# provider ("consulta con gemini", "preguntale a claude", etc.) we give
# that candidate a bonus so the router respects the user's preference.
# ---------------------------------------------------------------------------
_PROVIDER_KEYWORDS: dict[str, list[str]] = {
    "gemini": ["gemini", "google ai", "aistudio"],
    "groq": ["groq"],
    "ollama_local": ["ollama", "local", "llama"],
    "chatgpt_web": ["chatgpt", "openai", "gpt-4", "gpt4"],
    "claude_web": ["claude", "anthropic"],
    "codex": ["codex"],
    "devin": ["devin"],
    "windsurf": ["windsurf"],
}

_PROVIDER_HINT_BONUS = 0.35


def _extract_provider_hint(user_goal: str) -> str | None:
    """Return the assistant_kind the user explicitly mentioned, or None."""
    if not user_goal:
        return None
    lower = user_goal.lower()
    for kind, keywords in _PROVIDER_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return kind
    return None


# H8 — Alias para variantes comunes de ``task_kind``.
# El router ya matcheaba por substring (``code`` → ``code_generation`` +
# ``code_review``), pero quedaban huecos donde el nombre usado en PCS v1 / UI
# no comparte raíz con el strength. Este mapa los resuelve antes del match
# por substring para evitar ``task_kind_unknown`` en requests razonables.
# Los valores deben coincidir con ``AssistantStrength.value``; si no, el
# match por substring toma el relevo como antes.
_TASK_KIND_ALIASES: dict[str, str] = {
    # Frame ``structured_qa`` se confunde con task_kind en el bridge MCP.
    "structured_qa": "structured_reasoning",
    "question_answering": "structured_reasoning",
    "qa": "structured_reasoning",
    "reasoning": "structured_reasoning",
    # RAG / retrieval-augmented generation.
    "rag": "retrieval_augmented",
    "retrieval": "retrieval_augmented",
    # Long-context / summarization.
    "summarization": "long_context_synthesis",
    "summarize": "long_context_synthesis",
    "long_context": "long_context_synthesis",
    # Visión / multimodal.
    "vision": "multimodal_vision",
    "image_understanding": "multimodal_vision",
    "multimodal": "multimodal_vision",
    # Matemáticas.
    "math": "mathematical_reasoning",
    "maths": "mathematical_reasoning",
    # Shell / ejecución.
    "shell": "shell_execution",
    "bash": "shell_execution",
    "execute_command": "shell_execution",
    # Web browsing.
    "web": "web_browsing",
    "browse": "web_browsing",
    "browsing": "web_browsing",
    # Código (más específico que el match por substring).
    "coding": "code_generation",
    "programming": "code_generation",
    # Escritura creativa.
    "writing": "creative_writing",
    "creative": "creative_writing",
}


def _resolve_task_kind_alias(key: str) -> str:
    """Traduce ``key`` a un ``AssistantStrength.value`` canónico si aplica."""
    return _TASK_KIND_ALIASES.get(key, key)


def _relevant_strengths(task_kind: str) -> set[AssistantStrength]:
    """Conjunto de strengths que ``task_kind`` considera relevantes.

    1. si coincide con el ``value`` de un `AssistantStrength` → devuelve
       ese único strength;
    2. si no, fallback por substring: cualquier strength cuyo ``value``
       contenga ``task_kind`` o viceversa (cubre variantes tipo
       ``"code"`` → ``code_generation`` + ``code_review``).
    3. si queda vacío (task_kind no mapea a nada) → set vacío y el
       router devuelve fit_score=0.0 con ``unresolved_fields`` marcando
       que el task_kind es desconocido.

    Antes de (1) se aplica ``_resolve_task_kind_alias`` para normalizar
    variantes comunes (p. ej. ``structured_qa`` → ``structured_reasoning``).
    """

    key = _normalize_kind(task_kind)
    if not key:
        return set()
    key = _resolve_task_kind_alias(key)
    for strength in AssistantStrength:
        if strength.value == key:
            return {strength}
    matching: set[AssistantStrength] = set()
    for strength in AssistantStrength:
        if key in strength.value or strength.value in key:
            matching.add(strength)
    return matching


def _fit_score(
    profile: AssistantCapabilityProfile,
    relevant: set[AssistantStrength],
) -> float:
    if not relevant:
        return 0.0
    profile_strengths = set(profile.strengths)
    overlap = profile_strengths & relevant
    return round(len(overlap) / max(1, len(relevant)), 4)


def _availability_score(
    assistant_kind: str, world_model: WorldModelSnapshot | None
) -> float:
    """Derivado de `WorldModelSnapshot.tool_live_status`.

    * ``1.0`` si hay algún `ToolLiveStatus` con ese kind y ``available=True``.
    * ``0.0`` si hay algún `ToolLiveStatus` con ese kind y ``available=False``.
    * ``0.3`` si no hay entrada para ese kind (desconocido en vivo).
    * ``0.3`` si ``world_model`` es ``None`` (WM no wireado).
    """

    if world_model is None:
        return _AVAILABILITY_WHEN_UNKNOWN
    key = _normalize_kind(assistant_kind)
    if not key:
        return _AVAILABILITY_WHEN_UNKNOWN
    matches = [
        status
        for status in (world_model.tool_live_status or [])
        if _normalize_kind(status.assistant_kind) == key
    ]
    if not matches:
        return _AVAILABILITY_WHEN_UNKNOWN
    if any(bool(status.available) for status in matches):
        return _AVAILABILITY_WHEN_AVAILABLE
    return _AVAILABILITY_WHEN_UNAVAILABLE


def _weight_score(
    assistant_kind: str, weights: dict[tuple[object, str, str], dict[str, Any]]
) -> float:
    """Extrae ``adaptive_weight`` para ese kind si el layer devolvió algo.

    El layer indexa por ``(route, assistant_kind, config_signature)``; no
    tenemos route concreto acá, así que busca el primer match por
    ``assistant_kind`` normalizado. Si no hay historial, devuelve 0.0
    (tolerancia explícita pedida por el spec PCS v1).
    """

    key = _normalize_kind(assistant_kind)
    if not key or not weights:
        return 0.0
    for (_route, candidate_kind, _signature), profile in weights.items():
        if _normalize_kind(str(candidate_kind)) == key:
            weight = profile.get("adaptive_weight")
            try:
                return round(float(weight or 0.0), 4)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


class SynapticRouter:
    """Routing sináptico PCS v1. Ver docstring de módulo.

    Parameters
    ----------
    capability_registry:
        Fuente de ``AssistantCapabilityProfile``. Nunca devuelve ``None``
        (placeholder ``'unknown'`` para kinds desconocidos).
    adaptive_weight_layer:
        Capa adaptativa ya wireada; el router la consulta vía ``suggest``.
    world_model_provider:
        Callable que devuelve el `WorldModelSnapshot` vivo actual o
        ``None`` si el WM no está wireado.
    """

    def __init__(
        self,
        *,
        capability_registry: AssistantCapabilityRegistry,
        adaptive_weight_layer: AdaptiveWeightLayer,
        world_model_provider: Callable[[], WorldModelSnapshot | None],
        experiment_lab_repository: ExperimentLabRepository | None = None,
        enabled_override: bool | None = None,
    ) -> None:
        self._registry = capability_registry
        self._weight_layer = adaptive_weight_layer
        self._world_model_provider = world_model_provider
        self._experiment_lab_repository = experiment_lab_repository
        # ``enabled_override`` viene de configuración persistente (``AppConfig``)
        # y tiene precedencia sobre el env var salvo que esté en ``None`` (no
        # configurado). Esto permite al usuario encender el router desde
        # ``config`` sin exportar variables de entorno cada sesión, pero sigue
        # dejando al env var como escape hatch en pruebas / sesiones efímeras.
        self._enabled_override = enabled_override

    def _routing_enabled(self) -> bool:
        if self._enabled_override is not None:
            return bool(self._enabled_override)
        return _feature_flag_enabled()

    def decide(
        self,
        *,
        task_kind: str,
        candidate_assistant_kinds: list[str] | None = None,
        user_goal: str = "",
    ) -> SynapticRoutingDecision:
        task_kind_clean = (task_kind or "").strip()
        routing_enabled = self._routing_enabled()

        candidates = self._resolve_candidates(candidate_assistant_kinds)
        profiles = [
            (kind, self._registry.get_or_default(kind)) for kind in candidates
        ]

        relevant = _relevant_strengths(task_kind_clean)
        world_model = self._safe_world_model()
        weights = self._safe_weights()

        provider_hint = _extract_provider_hint(user_goal)

        scored: list[dict[str, Any]] = []
        for kind, profile in profiles:
            fit = _fit_score(profile, relevant)
            weight = _weight_score(kind, weights)
            availability = _availability_score(kind, world_model)
            hint_bonus = _PROVIDER_HINT_BONUS if (provider_hint and _normalize_kind(kind) == _normalize_kind(provider_hint)) else 0.0
            total = round(
                fit * _FIT_WEIGHT
                + weight * _WEIGHT_WEIGHT
                + availability * _AVAILABILITY_WEIGHT
                + hint_bonus,
                4,
            )
            scored.append(
                {
                    "assistant_kind": kind,
                    "fit_score": fit,
                    "weight_score": weight,
                    "availability_score": availability,
                    "hint_bonus": hint_bonus,
                    "total_score": total,
                    "profile_confidence": profile.confidence,
                    "profile_known": profile.assistant_kind != "unknown",
                }
            )

        scored.sort(
            key=lambda row: (row["total_score"], row["assistant_kind"]),
            reverse=True,
        )
        # Desempate alfabético ascendente dentro del mismo score:
        # re-ordenamos estable por (score DESC, kind ASC).
        scored.sort(
            key=lambda row: (-float(row["total_score"]), row["assistant_kind"]),
        )

        unresolved: list[str] = []
        if not relevant:
            unresolved.append("task_kind_unknown")
        if world_model is None:
            unresolved.append("world_model_unavailable")
        if not weights:
            unresolved.append("adaptive_history_empty")

        evidence_refs = ["synaptic_router_pcs_v1"]

        if not routing_enabled:
            # Feature flag off: devolvemos evidencia de los scores pero
            # NO seleccionamos nada para preservar el comportamiento
            # previo del sistema (LocalRoleRouter sigue decidiendo).
            return SynapticRoutingDecision(
                selected_assistant_kind="",
                alternatives=[
                    {
                        "assistant_kind": row["assistant_kind"],
                        "score": float(row["total_score"]),
                    }
                    for row in scored
                ],
                fit_score=0.0,
                weight_score=0.0,
                availability_score=0.0,
                total_score=0.0,
                routing_enabled=False,
                reason=(
                    "SYNAPTIC_ROUTING feature flag off; preserving previous "
                    "behaviour (LocalRoleRouter continues to decide)."
                ),
                evidence_refs=evidence_refs,
                unresolved_fields=unresolved,
                metadata={
                    "routing_enabled": False,
                    "task_kind": task_kind_clean,
                    "candidate_count": len(scored),
                },
            )

        if not scored:
            return SynapticRoutingDecision(
                selected_assistant_kind="",
                routing_enabled=True,
                reason="No candidate assistant kinds available in registry.",
                evidence_refs=evidence_refs,
                unresolved_fields=[*unresolved, "no_candidates"],
                metadata={
                    "routing_enabled": True,
                    "task_kind": task_kind_clean,
                    "candidate_count": 0,
                },
            )

        winner = scored[0]
        alternatives = [
            {
                "assistant_kind": row["assistant_kind"],
                "score": float(row["total_score"]),
            }
            for row in scored[1:]
        ]
        hint_part = f", hint_bonus={winner.get('hint_bonus', 0):.2f}" if winner.get('hint_bonus') else ""
        reason = (
            f"Selected '{winner['assistant_kind']}' for task_kind="
            f"'{task_kind_clean}' with total_score={winner['total_score']:.4f} "
            f"(fit={winner['fit_score']:.2f}, "
            f"weight={winner['weight_score']:.2f}, "
            f"availability={winner['availability_score']:.2f}"
            f"{hint_part})."
        )
        if provider_hint:
            evidence_refs.append(f"provider_hint:{provider_hint}")

        meta: dict[str, Any] = {
            "routing_enabled": True,
            "task_kind": task_kind_clean,
            "candidate_count": len(scored),
            "scoring_weights": {
                "fit": _FIT_WEIGHT,
                "weight": _WEIGHT_WEIGHT,
                "availability": _AVAILABILITY_WEIGHT,
            },
            "winner_profile_known": bool(winner["profile_known"]),
        }
        if provider_hint:
            meta["provider_hint"] = provider_hint
            meta["provider_hint_bonus"] = _PROVIDER_HINT_BONUS

        return SynapticRoutingDecision(
            selected_assistant_kind=str(winner["assistant_kind"]),
            alternatives=alternatives,
            fit_score=float(winner["fit_score"]),
            weight_score=float(winner["weight_score"]),
            availability_score=float(winner["availability_score"]),
            total_score=float(winner["total_score"]),
            routing_enabled=True,
            reason=reason,
            evidence_refs=evidence_refs,
            unresolved_fields=unresolved,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Helpers privados

    def _resolve_candidates(
        self, candidate_assistant_kinds: list[str] | None
    ) -> list[str]:
        if candidate_assistant_kinds is None:
            return list(self._registry.known_kinds())
        deduped: list[str] = []
        seen: set[str] = set()
        for raw in candidate_assistant_kinds:
            normalized = _normalize_kind(raw)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _safe_world_model(self) -> WorldModelSnapshot | None:
        try:
            return self._world_model_provider()
        except Exception:  # pragma: no cover - defensive
            return None

    def _safe_weights(self) -> dict[tuple[object, str, str], dict[str, Any]]:
        try:
            grouped = self._load_grouped_runs()
            return self._weight_layer.suggest(grouped_runs=grouped)
        except Exception:  # pragma: no cover - defensive
            return {}

    def _load_grouped_runs(
        self, *, limit_per_query: int = 50,
    ) -> dict[tuple[object, str, str], list[ExperimentRun]]:
        repo = self._experiment_lab_repository
        if repo is None:
            return {}
        try:
            runs = repo.list_runs(limit=limit_per_query)
        except Exception:
            return {}
        grouped: dict[tuple[object, str, str], list[ExperimentRun]] = {}
        for run in runs:
            key = (run.route, str(run.assistant_kind or '').strip().lower(), str(run.config_signature or '').strip())
            grouped.setdefault(key, []).append(run)
        return grouped
