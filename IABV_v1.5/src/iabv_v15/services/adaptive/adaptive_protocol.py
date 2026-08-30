"""Adaptive Operating Protocol — derive operating rules from measured experience.

Implements:
- OLD_RULE, OBSERVATION, ACTUAL_RESULT, NEW_RULE, CONFIDENCE cycle
- Rule learning from execution outcomes
- Confidence-based rule application
- Historical success alone does not authorize action
- Integration with ExperienceStorageService

The protocol learns from experience but remains conservative:
- Rules require multiple confirming observations
- Low confidence rules are not applied automatically
- Historical success is advisory, not authoritative
- Hard security/governance constraints are never modified
"""
from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveRule:
    """An adaptive operating rule learned from experience."""
    rule_id: str = ""
    rule_key: str = ""
    rule_value: str = ""
    confidence: float = 0.0
    observation_count: int = 0
    success_count: int = 0
    last_observation: str = ""
    last_result: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_key": self.rule_key,
            "rule_value": self.rule_value,
            "confidence": self.confidence,
            "observation_count": self.observation_count,
            "success_count": self.success_count,
            "last_observation": self.last_observation,
            "last_result": self.last_result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class ProtocolRecommendation:
    """Recommendation from the adaptive protocol."""
    rule_key: str = ""
    old_rule: str = ""
    new_rule: str = ""
    confidence: float = 0.0
    apply: bool = False
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    timestamp: str = ""


class AdaptiveProtocolService:
    """Manage adaptive operating rules derived from experience."""

    # Confidence thresholds
    _MIN_CONFIDENCE_TO_APPLY = 0.7
    _MIN_OBSERVATIONS = 3
    _SUCCESS_RATE_THRESHOLD = 0.8

    def __init__(
        self,
        *,
        evolution_dir: str,
        experience_storage: Any = None,
    ) -> None:
        self.evolution_dir = Path(evolution_dir).resolve()
        self.state_dir = self.evolution_dir / "adaptive_protocol"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.experience_storage = experience_storage
        self._rules_file = self.state_dir / "rules.json"
        self._lock = threading.RLock()
        self._rules: dict[str, AdaptiveRule] = {}
        
        self._load_rules()

    def learn_from_outcome(
        self,
        old_rule: str,
        observation: str,
        actual_result: str,
        new_rule: str,
        rule_key: str,
    ) -> AdaptiveRule:
        """Learn from an execution outcome and update adaptive rule.
        
        Learning cycle:
        1. OLD_RULE: The rule that was applied
        2. OBSERVATION: What was observed during execution
        3. ACTUAL_RESULT: The actual outcome
        4. NEW_RULE: The proposed new rule based on the result
        5. CONFIDENCE: Updated based on success/failure pattern
        """
        with self._lock:
            # Get or create rule
            if rule_key not in self._rules:
                rule = AdaptiveRule(
                    rule_id=f"rule_{rule_key}",
                    rule_key=rule_key,
                    rule_value=old_rule,
                    confidence=0.0,
                    observation_count=0,
                    success_count=0,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                self._rules[rule_key] = rule
            else:
                rule = self._rules[rule_key]
            
            # Update observation
            rule.observation_count += 1
            rule.last_observation = observation
            rule.last_result = actual_result
            
            # Determine if this observation supports the new rule
            supports_new_rule = self._supports_new_rule(observation, actual_result, new_rule)
            
            if supports_new_rule:
                rule.success_count += 1
                rule.rule_value = new_rule
            
            # Update confidence based on success rate and observation count
            if rule.observation_count >= self._MIN_OBSERVATIONS:
                success_rate = rule.success_count / rule.observation_count
                # Confidence grows with both success rate and observation count
                base_confidence = success_rate
                observation_bonus = min(0.2, (rule.observation_count - self._MIN_OBSERVATIONS) * 0.05)
                rule.confidence = min(1.0, base_confidence + observation_bonus)
            else:
                rule.confidence = 0.0
            
            rule.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Persist
            self._persist_rules()
            
            # Record to experience storage
            if self.experience_storage:
                try:
                    self.experience_storage.record_adaptive_rule_update(
                        old_rule=old_rule,
                        observation=observation,
                        actual_result=actual_result,
                        new_rule=new_rule,
                        confidence=rule.confidence,
                    )
                except Exception as e:
                    logger.warning(f"Failed to record rule update to experience storage: {e}")
            
            logger.info(f"Learned from outcome: rule_key={rule_key}, confidence={rule.confidence:.2f}, "
                       f"observations={rule.observation_count}, success_rate={rule.success_count/rule.observation_count if rule.observation_count > 0 else 0:.2f}")
            
            return rule

    def _supports_new_rule(
        self,
        observation: str,
        actual_result: str,
        new_rule: str,
    ) -> bool:
        """Determine if the observation supports the new rule."""
        # Simple heuristic: if actual_result indicates success, it supports the rule
        success_indicators = ["success", "completed", "finished", "done", "ok"]
        failure_indicators = ["error", "failed", "timeout", "crash", "exception"]
        
        result_lower = actual_result.lower()
        
        if any(ind in result_lower for ind in failure_indicators):
            return False
        
        if any(ind in result_lower for ind in success_indicators):
            return True
        
        # Default: neutral observation doesn't support or reject
        return False

    def get_recommendation(self, rule_key: str) -> ProtocolRecommendation:
        """Get a recommendation for a rule based on learned experience.
        
        Returns:
        - apply=True if confidence is high enough and rule should be applied
        - apply=False if confidence is low or rule should not be applied
        - Historical success alone does NOT authorize action
        """
        with self._lock:
            rule = self._rules.get(rule_key)
            
            if not rule:
                return ProtocolRecommendation(
                    rule_key=rule_key,
                    old_rule="",
                    new_rule="",
                    confidence=0.0,
                    apply=False,
                    reason="No learned rule for this key",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            
            # Check if rule meets confidence threshold
            if rule.confidence < self._MIN_CONFIDENCE_TO_APPLY:
                return ProtocolRecommendation(
                    rule_key=rule_key,
                    old_rule="",
                    new_rule=rule.rule_value,
                    confidence=rule.confidence,
                    apply=False,
                    reason=f"Confidence too low ({rule.confidence:.2f} < {self._MIN_CONFIDENCE_TO_APPLY})",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            
            # Check if we have enough observations
            if rule.observation_count < self._MIN_OBSERVATIONS:
                return ProtocolRecommendation(
                    rule_key=rule_key,
                    old_rule="",
                    new_rule=rule.rule_value,
                    confidence=rule.confidence,
                    apply=False,
                    reason=f"Insufficient observations ({rule.observation_count} < {self._MIN_OBSERVATIONS})",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            
            # Check success rate
            if rule.observation_count > 0:
                success_rate = rule.success_count / rule.observation_count
                if success_rate < self._SUCCESS_RATE_THRESHOLD:
                    return ProtocolRecommendation(
                        rule_key=rule_key,
                        old_rule="",
                        new_rule=rule.rule_value,
                        confidence=rule.confidence,
                        apply=False,
                        reason=f"Success rate too low ({success_rate:.2f} < {self._SUCCESS_RATE_THRESHOLD})",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
            
            # Rule meets all criteria
            return ProtocolRecommendation(
                rule_key=rule_key,
                old_rule="",
                new_rule=rule.rule_value,
                confidence=rule.confidence,
                apply=True,
                reason=f"Rule meets confidence threshold ({rule.confidence:.2f}) with {rule.observation_count} observations",
                evidence=[f"Success rate: {rule.success_count/rule.observation_count:.2f}"],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def get_all_rules(self) -> dict[str, AdaptiveRule]:
        """Get all learned rules."""
        with self._lock:
            return dict(self._rules)

    def _load_rules(self) -> None:
        """Load rules from disk."""
        if not self._rules_file.exists():
            return
        
        try:
            with open(self._rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for rule_key, rule_data in data.items():
                self._rules[rule_key] = AdaptiveRule(
                    rule_id=rule_data.get("rule_id", ""),
                    rule_key=rule_data.get(" rule_key", ""),
                    rule_value=rule_data.get("rule_value", ""),
                    confidence=rule_data.get("confidence", 0.0),
                    observation_count=rule_data.get("observation_count", 0),
                    success_count=rule_data.get("success_count", 0),
                    last_observation=rule_data.get("last_observation", ""),
                    last_result=rule_data.get("last_result", ""),
                    created_at=rule_data.get("created_at", ""),
                    updated_at=rule_data.get("updated_at", ""),
                    metadata=rule_data.get("metadata", {}),
                )
            
            logger.info(f"Loaded {len(self._rules)} adaptive rules")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")

    def _persist_rules(self) -> None:
        """Persist rules to disk."""
        try:
            data = {k: v.to_dict() for k, v in self._rules.items()}
            with open(self._rules_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist rules: {e}")

    def reset_rule(self, rule_key: str) -> None:
        """Reset a rule to initial state (for testing or correction)."""
        with self._lock:
            if rule_key in self._rules:
                rule = self._rules[rule_key]
                rule.confidence = 0.0
                rule.observation_count = 0
                rule.success_count = 0
                rule.updated_at = datetime.now(timezone.utc).isoformat()
                self._persist_rules()
                logger.info(f"Reset rule: {rule_key}")
