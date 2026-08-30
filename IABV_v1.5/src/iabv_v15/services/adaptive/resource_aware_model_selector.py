"""Resource-Aware Model Selector — select models based on goal, capability, and resources.

Implements:
- GOAL → CAPABILITY → PROVIDER → MODEL chain
- Local vs remote provider distinction
- Resource-aware filtering (RAM, VRAM, CPU, GPU)
- Model capability requirements
- Historical experience integration
- Detailed explanation of decisions and alternatives

Reuses existing AdaptiveModelSelector and extends with resource-aware filtering.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from iabv_v15.services.adaptive.resource_aware_controller import (
    OperationCost,
    ResourcePressure,
    ResourceState,
)

logger = logging.getLogger(__name__)


class Capability(str, Enum):
    """Model capability levels."""
    TRIVIAL = "trivial"
    BASIC = "basic"
    STANDARD = "standard"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ProviderKind(str, Enum):
    """Provider kind (local vs remote)."""
    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class ModelCapability:
    """Model capability declaration."""
    model_id: str
    model_name: str
    provider_kind: ProviderKind
    capability_level: Capability
    ram_requirement_mb: float = 0.0
    vram_requirement_mb: float = 0.0
    context_window_tokens: int = 0
    avg_latency_ms: float = 0.0
    quality_score: float = 0.0
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelSelectionCriteria:
    """Criteria for model selection."""
    goal: str = ""
    required_capability: Capability = Capability.STANDARD
    prompt_complexity: str = "medium"  # low, medium, high
    ram_available_mb: int = 0
    vram_available_mb: int = 0
    cpu_load: float = 0.0
    gpu_available: bool = False
    resource_pressure: ResourcePressure = ResourcePressure.LOW
    resource_state: ResourceState = ResourceState.SAFE
    offline_only: bool = False
    max_latency_ms: float = 10000.0
    historical_success_rate: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelSelectionDecision:
    """Model selection decision with explanation."""
    selected_model: ModelCapability | None = None
    alternative_models: list[ModelCapability] = field(default_factory=list)
    rejected_models: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    explanation: str = ""
    confidence: float = 0.0
    resource_safe: bool = False
    fallback_used: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_model": self.selected_model.model_name if self.selected_model else None,
            "alternative_models": [m.model_name for m in self.alternative_models],
            "rejected_models": self.rejected_models,
            "reason": self.reason,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "resource_safe": self.resource_safe,
            "fallback_used": self.fallback_used,
            "timestamp": self.timestamp,
        }


class ResourceAwareModelSelector:
    """Select models based on goal, capability, and resource state."""

    # Model RAM requirements (from ResourceMetacognitionService)
    _MODEL_RAM_REQUIREMENTS: dict[str, float] = {
        'gemma3:1b': 1.5 * 1024,  # 1.5GB
        'gemma3:4b': 3.5 * 1024,  # 3.5GB
        'qwen2.5-coder:7b': 5.0 * 1024,  # 5GB
        'llama3.1:8b': 6.0 * 1024,  # 6GB
        'qwen2.5-coder:14b': 10.0 * 1024,  # 10GB
        'deepseek-coder-v2:16b': 12.0 * 1024,  # 12GB
    }

    # Default model capabilities (can be extended from Ollama inventory)
    _DEFAULT_MODELS: list[ModelCapability] = [
        ModelCapability(
            model_id="gemma3:1b",
            model_name="gemma3:1b",
            provider_kind=ProviderKind.LOCAL,
            capability_level=Capability.BASIC,
            ram_requirement_mb=1.5 * 1024,
            vram_requirement_mb=0.5 * 1024,
            context_window_tokens=8192,
            avg_latency_ms=500.0,
            quality_score=0.6,
        ),
        ModelCapability(
            model_id="gemma3:4b",
            model_name="gemma3:4b",
            provider_kind=ProviderKind.LOCAL,
            capability_level=Capability.STANDARD,
            ram_requirement_mb=3.5 * 1024,
            vram_requirement_mb=1.0 * 1024,
            context_window_tokens=8192,
            avg_latency_ms=800.0,
            quality_score=0.7,
        ),
        ModelCapability(
            model_id="llama3.1:8b",
            model_name="llama3.1:8b",
            provider_kind=ProviderKind.LOCAL,
            capability_level=Capability.ADVANCED,
            ram_requirement_mb=6.0 * 1024,
            vram_requirement_mb=2.0 * 1024,
            context_window_tokens=16384,
            avg_latency_ms=1200.0,
            quality_score=0.8,
        ),
    ]

    def __init__(
        self,
        *,
        ollama_inventory: dict[str, Any] | None = None,
    ) -> None:
        self._models = self._build_model_list(ollama_inventory)
        logger.info(f"Model selector initialized with {len(self._models)} models")

    def _build_model_list(self, ollama_inventory: dict[str, Any] | None) -> list[ModelCapability]:
        """Build model list from Ollama inventory and defaults."""
        models = list(self._DEFAULT_MODELS)
        
        if ollama_inventory:
            local_models = ollama_inventory.get("local_models", [])
            for model_info in local_models:
                model_name = model_info.get("name", "")
                if model_name:
                    # Check if already in defaults
                    if not any(m.model_name == model_name for m in models):
                        # Estimate capability based on model name
                        if "1b" in model_name or "tiny" in model_name.lower():
                            capability = Capability.BASIC
                            ram_mb = 1.5 * 1024
                        elif "4b" in model_name or "small" in model_name.lower():
                            capability = Capability.STANDARD
                            ram_mb = 3.5 * 1024
                        elif "8b" in model_name or "medium" in model_name.lower():
                            capability = Capability.ADVANCED
                            ram_mb = 6.0 * 1024
                        else:
                            capability = Capability.EXPERT
                            ram_mb = 10.0 * 1024
                        
                        models.append(ModelCapability(
                            model_id=model_name,
                            model_name=model_name,
                            provider_kind=ProviderKind.LOCAL,
                            capability_level=capability,
                            ram_requirement_mb=ram_mb,
                            vram_requirement_mb=ram_mb * 0.3,
                            context_window_tokens=8192,
                            avg_latency_ms=1000.0,
                            quality_score=0.7,
                        ))
        
        return models

    def select_model(
        self,
        criteria: ModelSelectionCriteria,
    ) -> ModelSelectionDecision:
        """Select the best model based on criteria.
        
        Selection logic:
        1. Filter by provider kind (local vs remote)
        2. Filter by capability (must meet or exceed required)
        3. Filter by resource safety (RAM, VRAM)
        4. Filter by availability
        5. Score by quality, latency, historical success
        6. Return best model with explanation
        """
        decision = ModelSelectionDecision(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Step 1: Filter by provider kind
        if criteria.offline_only:
            candidates = [m for m in self._models if m.provider_kind == ProviderKind.LOCAL]
            decision.reason += "Offline-only: filtering to local providers. "
        else:
            candidates = list(self._models)
            decision.reason += "Including all providers. "
        
        # Step 2: Filter by capability
        candidates = self._filter_by_capability(candidates, criteria.required_capability)
        decision.reason += f"Capability filter ({criteria.required_capability.value}): {len(candidates)} candidates. "
        
        # Step 3: Filter by resource safety
        candidates, rejected = self._filter_by_resources(candidates, criteria)
        decision.rejected_models.extend(rejected)
        decision.reason += f"Resource filter: {len(candidates)} candidates, {len(rejected)} rejected. "
        
        # Step 4: Filter by availability
        candidates = [m for m in candidates if m.available]
        decision.reason += f"Availability filter: {len(candidates)} candidates. "
        
        # Step 5: Score and rank
        scored = self._score_models(candidates, criteria)
        scored.sort(key=lambda x: x[1], reverse=True)
        
        if scored:
            best_model, best_score = scored[0]
            decision.selected_model = best_model
            decision.confidence = best_score
            decision.resource_safe = True
            decision.alternative_models = [m for m, _ in scored[1:4]]  # Top 3 alternatives
            decision.explanation = self._build_explanation(best_model, criteria, scored)
        else:
            # Fallback: select least resource-intensive model
            fallback = self._select_fallback(criteria)
            if fallback:
                decision.selected_model = fallback
                decision.fallback_used = True
                decision.resource_safe = False
                decision.confidence = 0.3
                decision.explanation = f"No suitable model found; using fallback {fallback.model_name} despite resource constraints."
            else:
                decision.reason = "No suitable model available and no fallback option."
                decision.resource_safe = False
        
        return decision

    def _filter_by_capability(
        self,
        models: list[ModelCapability],
        required: Capability,
    ) -> list[ModelCapability]:
        """Filter models by capability level."""
        capability_order = [
            Capability.TRIVIAL,
            Capability.BASIC,
            Capability.STANDARD,
            Capability.ADVANCED,
            Capability.EXPERT,
        ]
        required_idx = capability_order.index(required)
        
        return [
            m for m in models
            if capability_order.index(m.capability_level) >= required_idx
        ]

    def _filter_by_resources(
        self,
        models: list[ModelCapability],
        criteria: ModelSelectionCriteria,
    ) -> tuple[list[ModelCapability], list[dict[str, Any]]]:
        """Filter models by resource safety."""
        candidates = []
        rejected = []
        
        for model in models:
            # Check RAM
            ram_safe = model.ram_requirement_mb <= criteria.ram_available_mb
            
            # Check VRAM if GPU available
            if criteria.gpu_available:
                vram_safe = model.vram_requirement_mb <= criteria.vram_available_mb
            else:
                vram_safe = True  # No GPU, VRAM not required
            
            # Check resource pressure
            if criteria.resource_pressure == ResourcePressure.CRITICAL:
                # Only allow very small models
                pressure_safe = model.ram_requirement_mb < 2 * 1024
            elif criteria.resource_pressure == ResourcePressure.HIGH:
                # Allow small to medium models
                pressure_safe = model.ram_requirement_mb < 4 * 1024
            else:
                pressure_safe = True
            
            if ram_safe and vram_safe and pressure_safe:
                candidates.append(model)
            else:
                rejected.append({
                    "model": model.model_name,
                    "ram_safe": ram_safe,
                    "vram_safe": vram_safe,
                    "pressure_safe": pressure_safe,
                    "reason": self._get_rejection_reason(ram_safe, vram_safe, pressure_safe),
                })
        
        return candidates, rejected

    def _get_rejection_reason(
        self,
        ram_safe: bool,
        vram_safe: bool,
        pressure_safe: bool,
    ) -> str:
        """Get rejection reason."""
        reasons = []
        if not ram_safe:
            reasons.append("insufficient RAM")
        if not vram_safe:
            reasons.append("insufficient VRAM")
        if not pressure_safe:
            reasons.append("resource pressure too high")
        return ", ".join(reasons) if reasons else "unknown"

    def _score_models(
        self,
        models: list[ModelCapability],
        criteria: ModelSelectionCriteria,
    ) -> list[tuple[ModelCapability, float]]:
        """Score models based on multiple factors."""
        scored = []
        
        for model in models:
            score = 0.0
            
            # Quality score (40%)
            score += model.quality_score * 0.4
            
            # Latency score (20%) - lower is better
            if model.avg_latency_ms > 0:
                latency_score = max(0, 1 - (model.avg_latency_ms / criteria.max_latency_ms))
                score += latency_score * 0.2
            
            # Historical success rate (20%)
            hist_rate = criteria.historical_success_rate.get(model.model_id, 0.5)
            score += hist_rate * 0.2
            
            # Capability match (10%) - prefer minimal sufficient capability
            capability_order = [
                Capability.TRIVIAL,
                Capability.BASIC,
                Capability.STANDARD,
                Capability.ADVANCED,
                Capability.EXPERT,
            ]
            required_idx = capability_order.index(criteria.required_capability)
            model_idx = capability_order.index(model.capability_level)
            capability_diff = model_idx - required_idx
            # Prefer exact match or slightly above
            if capability_diff == 0:
                capability_score = 1.0
            elif capability_diff == 1:
                capability_score = 0.8
            elif capability_diff > 1:
                capability_score = 0.5
            else:
                capability_score = 0.0
            score += capability_score * 0.1
            
            # Resource efficiency (10%) - prefer models that use fewer resources
            if criteria.ram_available_mb > 0:
                efficiency = 1 - (model.ram_requirement_mb / criteria.ram_available_mb)
                score += max(0, efficiency) * 0.1
            
            scored.append((model, score))
        
        return scored

    def _select_fallback(self, criteria: ModelSelectionCriteria) -> ModelCapability | None:
        """Select fallback model when no suitable model found."""
        # Select smallest available model
        available = [m for m in self._models if m.available]
        if not available:
            return None
        
        available.sort(key=lambda m: m.ram_requirement_mb)
        return available[0]

    def _build_explanation(
        self,
        selected: ModelCapability,
        criteria: ModelSelectionCriteria,
        scored: list[tuple[ModelCapability, float]],
    ) -> str:
        """Build detailed explanation of selection decision."""
        explanation = f"Selected {selected.model_name} ({selected.provider_kind.value}) "
        explanation += f"with capability {selected.capability_level.value}. "
        
        explanation += f"RAM requirement: {selected.ram_requirement_mb/1024:.1f}GB, "
        explanation += f"available: {criteria.ram_available_mb/1024:.1f}GB. "
        
        if criteria.resource_pressure != ResourcePressure.LOW:
            explanation += f"Resource pressure: {criteria.resource_pressure.value}. "
        
        if criteria.historical_success_rate.get(selected.model_id):
            explanation += f"Historical success rate: {criteria.historical_success_rate[selected.model_id]:.1%}. "
        
        if scored:
            explanation += f"Score: {scored[0][1]:.2f}. "
        
        if scored and len(scored) > 1:
            explanation += f"Considered alternatives: {[m.model_name for m, _ in scored[1:3]]}. "
        
        return explanation
