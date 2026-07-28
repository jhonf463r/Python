"""ExperienceRepository for storing situation → action → result tuples.

This repository stores the experience of the autonomous system, enabling
it to learn from past actions and their outcomes. It is NOT a "learning"
system - it simply records what happened in a structured way.
"""

import json
from pathlib import Path
from typing import Any

from iabv_v15.domain.action_result import ActionResult, ExecutionStatus


class ExperienceRepository:
    """Repository for storing and retrieving action experiences.
    
    This repository persists ActionResults to disk, enabling the system
    to recall what actions were taken in what situations and what the
    outcomes were.
    """
    
    def __init__(self, *, workspace_root: str = ".") -> None:
        self.workspace_root = Path(workspace_root)
        self.experience_dir = self.workspace_root / "data" / "evolution" / "experience"
        self.experience_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_experience_file(self, action_type: str) -> Path:
        """Get the file path for a given action type."""
        return self.experience_dir / f"{action_type}.jsonl"
    
    def save(self, result: ActionResult) -> None:
        """Save an ActionResult to the repository.

        Args:
            result: The ActionResult to persist
        """
        file_path = self._get_experience_file(result.action_type)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")
    
    def get_by_action_type(
        self,
        action_type: str,
        limit: int = 100,
    ) -> list[ActionResult]:
        """Retrieve experiences for a specific action type.
        
        Args:
            action_type: The type of action to retrieve
            limit: Maximum number of experiences to return
            
        Returns:
            List of ActionResults, most recent first
        """
        file_path = self._get_experience_file(action_type)
        if not file_path.exists():
            return []
        
        experiences: list[ActionResult] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        experiences.append(ActionResult.model_validate_json(line))
                    except Exception:
                        continue
        
        # Sort by timestamp descending and limit
        experiences.sort(key=lambda x: x.timestamp_utc, reverse=True)
        return experiences[:limit]
    
    def get_successful_experiences(
        self,
        action_type: str,
        limit: int = 50,
    ) -> list[ActionResult]:
        """Retrieve only successful experiences for an action type.
        
        Args:
            action_type: The type of action to retrieve
            limit: Maximum number of experiences to return
            
        Returns:
            List of successful ActionResults, most recent first
        """
        all_experiences = self.get_by_action_type(action_type, limit=limit * 2)
        return [
            exp for exp in all_experiences
            if exp.status.value == "success" and exp.worked
        ][:limit]
    
    def get_by_context(
        self,
        action_type: str,
        context_key: str,
        context_value: Any,
        limit: int = 50,
    ) -> list[ActionResult]:
        """Retrieve experiences matching a specific context key-value pair.
        
        Args:
            action_type: The type of action to retrieve
            context_key: The key in initial_context to match
            context_value: The value to match
            limit: Maximum number of experiences to return
            
        Returns:
            List of matching ActionResults, most recent first
        """
        all_experiences = self.get_by_action_type(action_type, limit=limit * 2)
        return [
            exp for exp in all_experiences
            if exp.initial_context.get(context_key) == context_value
        ][:limit]
    
    def get_statistics(self, action_type: str) -> dict[str, Any]:
        """Get statistics about experiences for an action type.
        
        Args:
            action_type: The type of action to analyze
            
        Returns:
            Dictionary with statistics (total, successful, failed, worked rate)
            Note: worked_rate excludes SKIPPED actions from the denominator
        """
        experiences = self.get_by_action_type(action_type, limit=1000)
        if not experiences:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "executed": 0,
                "skipped": 0,
                "worked_rate": 0.0,
            }
        
        total = len(experiences)
        successful = sum(1 for exp in experiences if exp.status.value == "success")
        worked = sum(1 for exp in experiences if exp.worked)
        
        # Exclude SKIPPED from worked_rate denominator to avoid skewing
        executed = sum(1 for exp in experiences if exp.execution_status != ExecutionStatus.SKIPPED)
        
        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "executed": executed,
            "skipped": total - executed,
            "worked_rate": worked / executed if executed > 0 else 0.0,
        }
