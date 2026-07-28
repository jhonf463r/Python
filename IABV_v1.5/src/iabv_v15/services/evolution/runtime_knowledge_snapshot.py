"""
Runtime Knowledge Layer - Minimal Snapshot Export (P0.158)

Read-only snapshot of runtime organism state for observability.
This is a pure export layer - no decision authority, no memory, no orchestration.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


def export_runtime_knowledge_snapshot(workspace_root: str | Path) -> dict[str, Any]:
    """Export a minimal read-only snapshot of runtime organism state.

    This function aggregates existing runtime data without introducing
    new authority or memory. It's purely for observability.

    Args:
        workspace_root: Path to the IABV workspace root

    Returns:
        Compact snapshot dictionary with:
        - timestamp
        - runtime_organ_state (if available)
        - portable_context_summary (if available)
        - evidence_sources
    """
    workspace = Path(workspace_root)
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "runtime_organ_state": _load_runtime_organ_state(workspace),
        "portable_context_summary": _load_portable_context_summary(workspace),
        "evidence_sources": [],
    }

    # Track which sources were successfully read
    if snapshot["runtime_organ_state"].get("status") == "ok":
        snapshot["evidence_sources"].append("runtime_organs/latest.json")
    if snapshot["portable_context_summary"].get("status") == "ok":
        snapshot["evidence_sources"].append("portable_context")

    return snapshot


def _load_runtime_organ_state(workspace: Path) -> dict[str, Any]:
    """Load runtime organ state from existing JSON file if available.

    This is read-only - does not modify any state.
    """
    path = workspace / "data" / "evolution" / "runtime_organs" / "latest.json"
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "organ_count": len(data.get("organs", [])),
                "data": data,
                "source_path": str(path),
                "exists": True,
                "updated_at": path.stat().st_mtime,
            }
        return {
            "status": "unavailable",
            "organ_count": 0,
            "source_path": str(path),
            "exists": False,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "organ_count": 0,
            "source_path": str(path),
            "exists": path.exists(),
        }


def _load_portable_context_summary(workspace: Path) -> dict[str, Any]:
    """Load portable context summary if available.

    This is read-only - does not modify any state.
    Reads portable_context/latest.json first, then falls back to agent_session_gate/history.
    """
    # Primary source: portable_context/latest.json
    primary_path = workspace / "data" / "evolution" / "portable_context" / "latest.json"
    try:
        if primary_path.exists():
            data = json.loads(primary_path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "source": "portable_context/latest.json",
                "data": data,
                "source_path": str(primary_path),
                "exists": True,
                "updated_at": primary_path.stat().st_mtime,
            }
    except Exception as e:
        # If primary fails, try fallback
        pass

    # Fallback: agent_session_gate/history
    history_dir = workspace / "data" / "evolution" / "agent_session_gate" / "history"
    try:
        if history_dir.exists():
            history_files = list(history_dir.glob("*.json"))
            if history_files:
                latest = max(history_files, key=lambda p: p.stat().st_mtime)
                data = json.loads(latest.read_text(encoding="utf-8"))
                return {
                    "status": "ok",
                    "source": "agent_session_gate/history (fallback)",
                    "history_files": len(history_files),
                    "latest_file": latest.name,
                    "data": data,
                    "source_path": str(latest),
                    "exists": True,
                    "updated_at": latest.stat().st_mtime,
                }
        return {
            "status": "unavailable",
            "source_path": str(primary_path),
            "exists": False,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source_path": str(primary_path),
            "exists": primary_path.exists(),
        }


def export_compact_runtime_dossier(workspace_root: str | Path) -> dict[str, Any]:
    """Export a compact dossier for quick runtime health check.

    This is a minimal subset of the full snapshot focused on:
    - Organ count and health
    - Active heavy organs
    - Recent activity indicators

    Returns:
        Compact dossier with key health indicators
    """
    snapshot = export_runtime_knowledge_snapshot(workspace_root)
    organs = snapshot["runtime_organ_state"].get("data", {}).get("organs", [])

    dossier = {
        "timestamp": snapshot["timestamp"],
        "total_organs": len(organs),
        "active_organs": len([o for o in organs if o.get("mode") == "active"]),
        "heavy_active_organs": len([o for o in organs if o.get("cost_class") == "heavy" and o.get("mode") == "active"]),
        "organs_with_recent_work": len([o for o in organs if o.get("last_started_at", 0) > 0]),
        "degraded_organs": len([o for o in organs if o.get("fitness_score", 1.0) < 0.4]),
        "evidence_sources": snapshot["evidence_sources"],
    }

    return dossier