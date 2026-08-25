"""Post Action Observer: P0.213 Phase 4

This module implements the observer pattern for post-action observation.

CRITICAL: The observer is passive. It does NOT make authorization decisions.
It receives the REAL ToolResult from execution and persists observations.

Phase 4 Status: IMPLEMENTED
"""

from __future__ import annotations

import datetime
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from iabv_v15.domain.models import ToolResult, ToolTask, ToolCard

if TYPE_CHECKING:
    from iabv_v15.services.tools.tool_memory import ToolMemory


@dataclass
class ActionObservation:
    """Observation of an action execution.
    
    Fields:
        run_id: Authority-issued run identifier
        execution_id: Authority-issued execution identifier
        lease_id: Capability identifier used for authorization
        action: Action executed
        target: Target of action
        success: Whether action succeeded
        result_id: ToolResult identifier
        observed_at: Timestamp when observation was created
        metadata: Additional observation metadata
    """
    run_id: str
    execution_id: str
    lease_id: str
    action: str
    target: str
    success: bool
    result_id: str
    observed_at: float
    metadata: dict[str, Any] | None = None


class PostActionObserver:
    """Observer for post-action results.
    
    This component:
    1. Receives the REAL ToolResult from execution
    2. Preserves action identity, target, run_id, execution_id
    3. Records success/failure
    4. Timestamps observation
    5. Persists observation to memory via ToolMemory
    
    The observer is passive - it does NOT execute actions or make authorization decisions.
    """
    
    def __init__(self, tool_memory: ToolMemory | None = None):
        """Initialize post action observer.
        
        Args:
            tool_memory: ToolMemory for persistence (optional, for testing)
        """
        self._observations: list[ActionObservation] = []
        self._tool_memory = tool_memory
    
    def observe_action_result(
        self,
        run_id: str,
        execution_id: str,
        lease_id: str,
        action: str,
        target: str,
        result: ToolResult
    ) -> ActionObservation:
        """Observe an action result.
        
        Args:
            run_id: Authority-issued run identifier
            execution_id: Authority-issued execution identifier
            lease_id: Capability identifier used for authorization
            action: Action executed
            target: Target of action
            result: ToolResult from execution
            
        Returns:
            ActionObservation with observation data
        """
        observation = ActionObservation(
            run_id=run_id,
            execution_id=execution_id,
            lease_id=lease_id,
            action=action,
            target=target,
            success=result.success,
            result_id=result.result_id,
            observed_at=time.time(),
            metadata={
                'output_text': result.output_text,
                'error_message': result.error_message,
                'execution_state': result.execution_state.state,
            }
        )
        
        self._observations.append(observation)
        
        # Persist to ToolMemory if available
        if self._tool_memory is not None:
            # Add observation metadata to result for causal binding
            result_with_observation = result.model_copy(update={
                'metadata': {
                    **(result.metadata or {}),
                    'observation_run_id': run_id,
                    'observation_execution_id': execution_id,
                    'observation_lease_id': lease_id,
                    'observation_action': action,
                    'observation_target': target,
                    'observation_observed_at': observation.observed_at,
                }
            })
            # F14: Fix persistence no-op - persist observation to ToolMemory
            self._tool_memory.repository.save_result(result_with_observation)
        
        return observation
    
    def observe(
        self,
        result: ToolResult,
        task: ToolTask,
        card: ToolCard
    ) -> ActionObservation:
        """Observe an action result using the new F14 signature.
        
        This method extracts authority context from ToolResult and ToolTask
        to create an observation with proper causality.
        
        F14: Only observe successful authorized actions.
        For authority-down or unauthorized actions, return a rejected observation.
        
        Args:
            result: ToolResult from execution (with authority fields)
            task: ToolTask that was executed (with authority fields)
            card: ToolCard that was used
            
        Returns:
            ActionObservation with observation data
        """
        # F14: Only observe successful authorized actions
        if not result.success:
            # Return a rejected observation for failed/authority-down actions
            return ActionObservation(
                run_id=task.run_id or "unknown",
                execution_id=result.execution_id or task.execution_id or "unknown",
                lease_id=result.lease_id or task.lease_id or "unknown",
                action=result.action or task.action or "unknown",
                target=result.target or task.target or "unknown",
                observation_type='rejected',
                observed_at=datetime.datetime.now(datetime.timezone.utc),
                observation_data={
                    'success': False,
                    'execution_state': result.execution_state.state,
                    'error_message': result.error_message,
                    'reason': 'action_failed_or_unauthorized',
                }
            )
        
        run_id = task.run_id or "unknown"
        execution_id = result.execution_id or task.execution_id or "unknown"
        lease_id = result.lease_id or task.lease_id or "unknown"
        action = result.action or task.action or "unknown"
        target = result.target or task.target or "unknown"
        
        return self.observe_action_result(
            run_id=run_id,
            execution_id=execution_id,
            lease_id=lease_id,
            action=action,
            target=target,
            result=result
        )
    
    def get_observations(self) -> list[ActionObservation]:
        """Get all observations.
        
        Returns:
            List of all observations
        """
        return self._observations
    
    def get_observations_for_execution(self, execution_id: str) -> list[ActionObservation]:
        """Get observations for a specific execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            List of observations for the execution
        """
        return [obs for obs in self._observations if obs.execution_id == execution_id]
