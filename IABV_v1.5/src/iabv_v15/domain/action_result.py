"""ActionResult model for autonomous cycle verification.

This module defines the ActionResult model which captures the complete
context and outcome of actions executed by the system, enabling
verification and learning from experience.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActionResultStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ExecutionStatus(str, Enum):
    EXECUTED = "executed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"


class ActionResult(BaseModel):
    """Result of an executed action in the autonomous cycle.
    
    This model captures the complete context and outcome of an action
    executed by the system, enabling verification and learning from experience.
    """
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_name: str = Field(description="Name of the action executed")
    action_type: str = Field(description="Type/category of action (e.g., 'gpu_correction', 'secret_provision')")
    
    # Context
    initial_context: dict[str, Any] = Field(default_factory=dict, description="System state before action")
    parameters_used: dict[str, Any] = Field(default_factory=dict, description="Parameters passed to the action")
    
    # Results
    expected_result: dict[str, Any] = Field(default_factory=dict, description="What the action was expected to achieve")
    observed_result: dict[str, Any] = Field(default_factory=dict, description="What actually happened")
    
    # Evaluation
    status: ActionResultStatus = Field(default=ActionResultStatus.UNKNOWN, description="Whether the action succeeded")
    execution_status: ExecutionStatus = Field(default=ExecutionStatus.EXECUTED, description="Whether the action was executed, skipped, blocked, or failed")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in the result (0.0-1.0)")
    worked: bool = Field(default=False, description="Whether the action executed correctly (technical execution)")
    improved_system: bool = Field(default=False, description="Whether operational metrics improved after action (operational impact)")
    
    # Metrics for impact measurement
    metrics_before: dict[str, Any] = Field(default_factory=dict, description="Operational metrics before action")
    metrics_after: dict[str, Any] = Field(default_factory=dict, description="Operational metrics after action")
    impact_observation_period_seconds: int = Field(default=0, description="Period of observation for impact measurement")
    
    # Experience decision explainability
    experience_decision_reason: str | None = Field(default=None, description="Reason for decision based on experience")
    experience_statistics_used: dict[str, Any] = Field(default_factory=dict, description="Statistics used for experience-based decision")
    
    # Metadata
    timestamp_utc: datetime = Field(default_factory=utc_now, description="When the action was executed")
    execution_duration_ms: int = Field(default=0, description="How long the action took to execute")
    error_message: str | None = Field(default=None, description="Error message if the action failed")
    
    # Verification
    verification_method: str | None = Field(default=None, description="How the result was verified")
    verification_timestamp_utc: datetime | None = Field(default=None, description="When verification occurred")
    
    # Post-action observation
    improvement_reason: str | None = Field(default=None, description="Reason for improvement or no improvement")

    @field_serializer('timestamp_utc', 'verification_timestamp_utc')
    def serialize_datetime(self, dt: datetime | None, _info) -> str | None:
        """Serialize datetime fields to ISO format."""
        return dt.isoformat() if dt is not None else None
