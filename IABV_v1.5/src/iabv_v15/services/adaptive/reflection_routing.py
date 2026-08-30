"""Reflection Routing — distinguish REFLECT from OBSERVE_NOW with evidence reuse.

Implements:
- REFLECT_ON_EXISTING_EVIDENCE vs OBSERVE_NOW routing
- Evidence freshness and sufficiency checks (90s TTL for world model)
- Structured evidence metadata (observation ID, source, timestamp, confidence, evidence tag)
- Evidence sufficiency states: sufficient, stale, missing, insufficient
- Prevent quoted words from triggering new observations
- Preserve explicit observe-now keywords (AHORA, actual, en este momento)
- Prevent full world model scans on reflection
- Resource safety before targeted refresh

Reuses existing WorldModelSnapshot and EnvironmentSelfModel.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ReflectionRoute(str, Enum):
    """Reflection routing decision."""
    REFLECT_ON_EXISTING_EVIDENCE = "reflect_on_existing_evidence"
    OBSERVE_NOW = "observe_now"
    DEFERRED = "deferred"


class EvidenceState(str, Enum):
    """Evidence state."""
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"


class EvidenceSufficiency(str, Enum):
    """Evidence sufficiency state."""
    SUFFICIENT = "sufficient"
    STALE = "stale"
    MISSING = "missing"
    INSUFFICIENT = "insufficient"


@dataclass
class EvidenceMetadata:
    """Structured evidence metadata."""
    observation_id: str = ""
    source: str = ""
    timestamp: str = ""
    confidence: float = 0.0
    evidence_tag: str = ""
    state: EvidenceState = EvidenceState.UNRESOLVED
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "evidence_tag": self.evidence_tag,
            "state": self.state.value,
            "metadata": self.metadata,
        }


@dataclass
class ReflectionDecision:
    """Reflection routing decision."""
    route: ReflectionRoute = ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
    reason: str = ""
    evidence_sufficiency: EvidenceSufficiency = EvidenceSufficiency.INSUFFICIENT
    evidence_metadata: EvidenceMetadata = field(default_factory=EvidenceMetadata)
    requires_targeted_refresh: bool = False
    resource_safe: bool = True
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.value,
            "reason": self.reason,
            "evidence_sufficiency": self.evidence_sufficiency.value,
            "evidence_metadata": self.evidence_metadata.to_dict(),
            "requires_targeted_refresh": self.requires_targeted_refresh,
            "resource_safe": self.resource_safe,
            "timestamp": self.timestamp,
        }


class ReflectionRoutingService:
    """Route reflection requests to reuse evidence or trigger observations."""

    # Reflection TTL for world model freshness (90 seconds)
    _REFLECTION_TTL_SECONDS = 90.0

    # Explicit observe-now keywords (Spanish)
    _OBSERVE_NOW_KEYWORDS = ["ahora", "actual", "en este momento", "right now", "currently"]

    # Quoted words that should NOT trigger observation
    _IGNORED_QUOTED_TERMS = ["abiertas", "red", "conexión", "internet", "gpu", "ollama"]

    def __init__(
        self,
        *,
        world_model_service: Any = None,
        resource_controller: Any = None,
    ) -> None:
        self.world_model_service = world_model_service
        self.resource_controller = resource_controller

    def route_request(
        self,
        request_text: str,
        world_model: Any = None,
        environment_model: Any = None,
    ) -> ReflectionDecision:
        """Route a request to REFLECT or OBSERVE_NOW.
        
        Logic:
        1. Check for explicit observe-now keywords → OBSERVE_NOW
        2. Check if reflection request → REFLECT_ON_EXISTING_EVIDENCE
        3. Evaluate evidence freshness and sufficiency
        4. Check quoted terms (should not trigger observation)
        5. Check resource safety before targeted refresh
        """
        decision = ReflectionDecision(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Step 1: Check for explicit observe-now keywords
        if self._has_observe_now_keyword(request_text):
            decision.route = ReflectionRoute.OBSERVE_NOW
            decision.reason = "Explicit observe-now keyword detected"
            decision.evidence_sufficiency = EvidenceSufficiency.MISSING  # Force observation
            return decision

        # Step 2: Check if reflection request
        if not self._is_reflection_request(request_text):
            decision.route = ReflectionRoute.OBSERVE_NOW
            decision.reason = "Not a reflection request"
            decision.evidence_sufficiency = EvidenceSufficiency.MISSING
            return decision

        # Step 3: Evaluate evidence freshness and sufficiency
        sufficiency, metadata = self._evaluate_evidence_sufficiency(
            request_text,
            world_model,
            environment_model,
        )
        decision.evidence_sufficiency = sufficiency
        decision.evidence_metadata = metadata

        # Step 4: Check quoted terms
        quoted_terms = self._extract_quoted_terms(request_text)
        if quoted_terms and self._should_ignore_quoted_terms(quoted_terms):
            decision.route = ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
            decision.reason = f"Quoted terms ignored: {quoted_terms}"
            decision.requires_targeted_refresh = False
            return decision

        # Step 5: Determine route based on sufficiency
        if sufficiency == EvidenceSufficiency.SUFFICIENT:
            decision.route = ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
            decision.reason = "Evidence is sufficient and fresh"
            decision.requires_targeted_refresh = False
        elif sufficiency == EvidenceSufficiency.STALE:
            decision.route = ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
            decision.reason = "Evidence is stale, will trigger targeted refresh"
            decision.requires_targeted_refresh = True
        elif sufficiency == EvidenceSufficiency.MISSING:
            decision.route = ReflectionRoute.OBSERVE_NOW
            decision.reason = "Evidence is missing, observation required"
            decision.requires_targeted_refresh = False
        else:  # INSUFFICIENT
            decision.route = ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
            decision.reason = "Evidence is insufficient, will trigger targeted refresh"
            decision.requires_targeted_refresh = True

        # Step 6: Check resource safety if targeted refresh needed
        if decision.requires_targeted_refresh and self.resource_controller:
            from iabv_v15.services.adaptive.resource_aware_controller import OperationCost
            resource_check = self.resource_controller.check_resource_safety(
                operation_cost=OperationCost.CHEAP,
            )
            decision.resource_safe = resource_check.safe
            if not resource_check.safe:
                decision.route = ReflectionRoute.DEFERRED
                decision.reason = f"Resource safety check failed: {resource_check.reason}"
                decision.requires_targeted_refresh = False

        return decision

    def _has_observe_now_keyword(self, text: str) -> bool:
        """Check if text contains explicit observe-now keywords."""
        text_lower = text.lower()
        for keyword in self._OBSERVE_NOW_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    def _is_reflection_request(self, text: str) -> bool:
        """Check if text is a reflection request."""
        reflection_keywords = ["reflexión", "reflexionar", "pensar", "evaluar", "analizar", "considerar"]
        text_lower = text.lower()
        for kw in reflection_keywords:
            if kw in text_lower:
                return True
        return False

    def _evaluate_evidence_sufficiency(
        self,
        request_text: str,
        world_model: Any = None,
        environment_model: Any = None,
    ) -> tuple[EvidenceSufficiency, EvidenceMetadata]:
        """Evaluate evidence freshness and sufficiency."""
        metadata = EvidenceMetadata(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Check world model freshness
        if world_model:
            freshness_ms = getattr(world_model, "freshness_ms", 0)
            last_updated = getattr(world_model, "last_updated", None)
            confidence = getattr(world_model, "confidence", 0.0)

            metadata.source = "world_model"
            metadata.confidence = confidence
            metadata.state = EvidenceState.OBSERVED if confidence > 0.5 else EvidenceState.INFERRED

            if last_updated:
                metadata.timestamp = last_updated.isoformat() if hasattr(last_updated, 'isoformat') else str(last_updated)
                # Check freshness
                age_seconds = (datetime.now(timezone.utc) - last_updated).total_seconds()
                if age_seconds <= self._REFLECTION_TTL_SECONDS:
                    if confidence > 0.7:
                        return EvidenceSufficiency.SUFFICIENT, metadata
                    else:
                        return EvidenceSufficiency.INSUFFICIENT, metadata
                else:
                    return EvidenceSufficiency.STALE, metadata
            else:
                return EvidenceSufficiency.MISSING, metadata
        else:
            return EvidenceSufficiency.MISSING, metadata

    def _extract_quoted_terms(self, text: str) -> list[str]:
        """Extract quoted terms from text."""
        # Match quoted strings (both single and double quotes)
        pattern = r'["\']([^"\']+)["\']'
        matches = re.findall(pattern, text)
        return matches

    def _should_ignore_quoted_terms(self, terms: list[str]) -> bool:
        """Check if quoted terms should be ignored (not trigger observation)."""
        for term in terms:
            term_lower = term.lower()
            for ignored in self._IGNORED_QUOTED_TERMS:
                if ignored in term_lower:
                    return True
        return False
