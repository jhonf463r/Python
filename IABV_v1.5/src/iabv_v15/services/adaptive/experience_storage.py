"""Experience Storage — integrate with existing ToolMemory/ExperimentLab.

Records execution outcomes, resource costs, and decision patterns for adaptive learning.
Reuses existing ToolRecordRepository, ExperimentLabRepository, and DecisionAuditTrail.

Data recorded:
- Execution outcome (success/failure, duration, resource cost)
- Model selection decisions
- Resource state at decision time
- Adaptive rule updates (OLD_RULE, OBSERVATION, ACTUAL_RESULT, NEW_RULE, CONFIDENCE)
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionExperience:
    """Record of an execution experience."""
    experience_id: str = ""
    action: str = ""
    goal: str = ""
    model_used: str = ""
    provider_kind: str = ""
    resource_state: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    duration_ms: float = 0.0
    ram_delta_mb: float = 0.0
    error: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "action": self.action,
            "goal": self.goal,
            "model_used": self.model_used,
            "provider_kind": self.provider_kind,
            "resource_state": self.resource_state,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "ram_delta_mb": self.ram_delta_mb,
            "error": self.error,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ModelSelectionExperience:
    """Record of a model selection decision."""
    selection_id: str = ""
    goal: str = ""
    required_capability: str = ""
    criteria: dict[str, Any] = field(default_factory=dict)
    selected_model: str = ""
    alternatives: list[str] = field(default_factory=list)
    resource_state: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    resource_safe: bool = False
    fallback_used: bool = False
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "goal": self.goal,
            "required_capability": self.required_capability,
            "criteria": self.criteria,
            "selected_model": self.selected_model,
            "alternatives": self.alternatives,
            "resource_state": self.resource_state,
            "confidence": self.confidence,
            "resource_safe": self.resource_safe,
            "fallback_used": self.fallback_used,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AdaptiveRuleUpdate:
    """Record of an adaptive rule update."""
    rule_id: str = ""
    old_rule: str = ""
    observation: str = ""
    actual_result: str = ""
    new_rule: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = field(default_factory=list)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "old_rule": self.old_rule,
            "observation": self.observation,
            "actual_result": self.actual_result,
            "new_rule": self.new_rule,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ExperienceStorageService:
    """Store and retrieve experience data for adaptive learning.

    Integrates with existing repositories:
    - ToolRecordRepository: for tool execution records
    - ExperimentLabRepository: for experiment results
    - DecisionAuditTrail: for decision tracking
    """

    def __init__(
        self,
        *,
        evolution_dir: str,
        tool_record_repository: Any = None,
        experiment_lab_repository: Any = None,
        decision_audit_trail: Any = None,
    ) -> None:
        self.evolution_dir = Path(evolution_dir).resolve()
        self.state_dir = self.evolution_dir / "experience_storage"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.tool_record_repository = tool_record_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.decision_audit_trail = decision_audit_trail
        
        # Local storage for adaptive-specific data
        self._execution_log = self.state_dir / "execution_experience.jsonl"
        self._selection_log = self.state_dir / "selection_experience.jsonl"
        self._rule_log = self.state_dir / "adaptive_rules.jsonl"
        
        self._lock = threading.RLock()

    def record_execution(
        self,
        action: str,
        goal: str,
        model_used: str,
        provider_kind: str,
        resource_state: dict[str, Any],
        outcome: str,
        duration_ms: float,
        ram_delta_mb: float = 0.0,
        error: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionExperience:
        """Record an execution experience."""
        import uuid
        
        experience = ExecutionExperience(
            experience_id=str(uuid.uuid4()),
            action=action,
            goal=goal,
            model_used=model_used,
            provider_kind=provider_kind,
            resource_state=resource_state,
            outcome=outcome,
            duration_ms=duration_ms,
            ram_delta_mb=ram_delta_mb,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        
        # Persist to local log
        self._persist_execution(experience)
        
        # Also record to ToolRecordRepository if available
        if self.tool_record_repository:
            try:
                self._record_to_tool_repository(experience)
            except Exception as e:
                logger.warning(f"Failed to record to ToolRecordRepository: {e}")
        
        return experience

    def record_model_selection(
        self,
        goal: str,
        required_capability: str,
        criteria: dict[str, Any],
        selected_model: str,
        alternatives: list[str],
        resource_state: dict[str, Any],
        confidence: float,
        resource_safe: bool,
        fallback_used: bool,
        metadata: dict[str, Any] | None = None,
    ) -> ModelSelectionExperience:
        """Record a model selection decision."""
        import uuid
        
        selection = ModelSelectionExperience(
            selection_id=str(uuid.uuid4()),
            goal=goal,
            required_capability=required_capability,
            criteria=criteria,
            selected_model=selected_model,
            alternatives=alternatives,
            resource_state=resource_state,
            confidence=confidence,
            resource_safe=resource_safe,
            fallback_used=fallback_used,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        
        # Persist to local log
        self._persist_selection(selection)
        
        # Also record to DecisionAuditTrail if available
        if self.decision_audit_trail:
            try:
                self._record_to_decision_audit(selection)
            except Exception as e:
                logger.warning(f"Failed to record to DecisionAuditTrail: {e}")
        
        return selection

    def record_adaptive_rule_update(
        self,
        old_rule: str,
        observation: str,
        actual_result: str,
        new_rule: str,
        confidence: float,
        evidence_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdaptiveRuleUpdate:
        """Record an adaptive rule update."""
        import uuid
        
        rule_update = AdaptiveRuleUpdate(
            rule_id=str(uuid.uuid4()),
            old_rule=old_rule,
            observation=observation,
            actual_result=actual_result,
            new_rule=new_rule,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        
        # Persist to local log
        self._persist_rule_update(rule_update)
        
        return rule_update

    def _persist_execution(self, experience: ExecutionExperience) -> None:
        """Persist execution experience to local log."""
        with self._lock:
            try:
                with open(self._execution_log, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(experience.to_dict(), default=str) + '\n')
            except Exception as e:
                logger.error(f"Failed to persist execution experience: {e}")

    def _persist_selection(self, selection: ModelSelectionExperience) -> None:
        """Persist selection experience to local log."""
        with self._lock:
            try:
                with open(self._selection_log, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(selection.to_dict(), default=str) + '\n')
            except Exception as e:
                logger.error(f"Failed to persist selection experience: {e}")

    def _persist_rule_update(self, rule_update: AdaptiveRuleUpdate) -> None:
        """Persist rule update to local log."""
        with self._lock:
            try:
                with open(self._rule_log, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(rule_update.to_dict(), default=str) + '\n')
            except Exception as e:
                logger.error(f"Failed to persist rule update: {e}")

    def _record_to_tool_repository(self, experience: ExecutionExperience) -> None:
        """Record to ToolRecordRepository (integration point)."""
        # This is a placeholder for actual integration
        # The actual implementation would depend on the ToolRecordRepository API
        logger.debug(f"Recording to ToolRecordRepository: {experience.action}")

    def _record_to_decision_audit(self, selection: ModelSelectionExperience) -> None:
        """Record to DecisionAuditTrail (integration point)."""
        # This is a placeholder for actual integration
        # The actual implementation would depend on the DecisionAuditTrail API
        logger.debug(f"Recording to DecisionAuditTrail: {selection.selected_model}")

    def get_execution_history(
        self,
        action: str | None = None,
        model: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionExperience]:
        """Retrieve execution history, optionally filtered."""
        experiences = []
        
        if not self._execution_log.exists():
            return experiences
        
        with self._lock:
            try:
                with open(self._execution_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if action is not None and data.get("action") != action:
                                continue
                            if model is not None and data.get("model_used") != model:
                                continue
                            
                            exp = ExecutionExperience(
                                experience_id=data.get("experience_id", ""),
                                action=data.get("action", ""),
                                goal=data.get("goal", ""),
                                model_used=data.get("model_used", ""),
                                provider_kind=data.get("provider_kind", ""),
                                resource_state=data.get("resource_state", {}),
                                outcome=data.get("outcome", ""),
                                duration_ms=data.get("duration_ms", 0.0),
                                ram_delta_mb=data.get("ram_delta_mb", 0.0),
                                error=data.get("error", ""),
                                timestamp=data.get("timestamp", ""),
                                metadata=data.get("metadata", {}),
                            )
                            experiences.append(exp)
                            if len(experiences) >= limit:
                                break
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse execution experience: {e}")
            except Exception as e:
                logger.error(f"Failed to read execution log: {e}")
        
        experiences.sort(key=lambda e: e.timestamp, reverse=True)
        return experiences

    def get_model_success_rate(self, model: str) -> float:
        """Calculate success rate for a specific model."""
        history = self.get_execution_history(model=model, limit=1000)
        
        if not history:
            return 0.5  # Default neutral
        
        success_count = sum(1 for e in history if e.outcome == "success")
        return success_count / len(history)

    def get_selection_history(
        self,
        goal: str | None = None,
        model: str | None = None,
        limit: int = 100,
    ) -> list[ModelSelectionExperience]:
        """Retrieve selection history, optionally filtered."""
        selections = []
        
        if not self._selection_log.exists():
            return selections
        
        with self._lock:
            try:
                with open(self._selection_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if goal is not None and data.get("goal") != goal:
                                continue
                            if model is not None and data.get("selected_model") != model:
                                continue
                            
                            sel = ModelSelectionExperience(
                                selection_id=data.get("selection_id", ""),
                                goal=data.get("goal", ""),
                                required_capability=data.get("required_capability", ""),
                                criteria=data.get("criteria", {}),
                                selected_model=data.get("selected_model", ""),
                                alternatives=data.get("alternatives", []),
                                resource_state=data.get("resource_state", {}),
                                confidence=data.get("confidence", 0.0),
                                resource_safe=data.get("resource_safe", False),
                                fallback_used=data.get("fallback_used", False),
                                timestamp=data.get("timestamp", ""),
                                metadata=data.get("metadata", {}),
                            )
                            selections.append(sel)
                            if len(selections) >= limit:
                                break
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse selection experience: {e}")
            except Exception as e:
                logger.error(f"Failed to read selection log: {e}")
        
        selections.sort(key=lambda s: s.timestamp, reverse=True)
        return selections
