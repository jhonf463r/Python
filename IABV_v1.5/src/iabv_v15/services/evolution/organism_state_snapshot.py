"""
Organism State Snapshot - Unified Read-Only View (P0.165)

Single source of truth for organism state.
This is a read-only, unified snapshot that consolidates existing pieces
without creating new authority, memory, or orchestration.

The snapshot reuses existing services and models:
- RuntimeOrgans (via runtime_knowledge_snapshot)
- PortableContext (via runtime_knowledge_snapshot)
- Self Examination (via OperationalSelfExaminationService)
- World Model (via WorldModelService)
- Control Master (via ControlMasterService)
- Operational Learning (via ExperimentLab)

This is NOT a decision layer. It is purely for observability.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def export_organism_state_snapshot(
    workspace_root: str | Path,
    *,
    portable_context_service: Any = None,
    self_examination_service: Any = None,
    world_model_service: Any = None,
    control_master_service: Any = None,
    experiment_lab: Any = None,
    environment_self_awareness_service: Any = None,
) -> dict[str, Any]:
    """Export a unified read-only snapshot of the organism state.

    This function aggregates existing state from canonical services
    without introducing new authority or memory. It's purely for observability.

    Args:
        workspace_root: Path to the IABV workspace root
        portable_context_service: Optional PortableContextService instance
        self_examination_service: Optional OperationalSelfExaminationService instance
        world_model_service: Optional WorldModelService instance
        control_master_service: Optional ControlMasterService instance
        experiment_lab: Optional ExperimentLab instance
        environment_self_awareness_service: Optional EnvironmentSelfAwarenessService instance for fresh GPU data

    Returns:
        Unified snapshot dictionary with:
        - timestamp
        - workspace_root
        - runtime_knowledge (organs, portable context)
        - self_examination (findings, health)
        - world_model (environment, tools, network)
        - control_master (governance state)
        - operational_learning (experiments, recommendations)
        - gpu_health (GPU health status from environment self-awareness)
        - unresolved_fields (unresolved signals including GPU degradation)
        - evidence_sources (traceability)
    """
    workspace = Path(workspace_root)

    # Import runtime knowledge snapshot (P0.158)
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_runtime_knowledge_snapshot,
    )

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "runtime_knowledge": _load_runtime_knowledge(workspace),
        "self_examination": _load_self_examination(
            workspace, self_examination_service
        ),
        "world_model": _load_world_model(workspace, world_model_service),
        "control_master": _load_control_master(
            workspace, control_master_service
        ),
        "operational_learning": _load_operational_learning(
            workspace, experiment_lab
        ),
        "gpu_health": _load_gpu_health(workspace, environment_self_awareness_service),
        "unresolved_fields": _load_unresolved_fields(workspace, environment_self_awareness_service),
        "evidence_sources": [],
    }

    # Track which sources were successfully read
    _track_evidence_sources(snapshot)

    return snapshot


def _load_runtime_knowledge(workspace: Path) -> dict[str, Any]:
    """Load runtime knowledge (organs + portable context)."""
    from iabv_v15.services.evolution.runtime_knowledge_snapshot import (
        export_runtime_knowledge_snapshot,
    )

    try:
        return export_runtime_knowledge_snapshot(workspace)
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "runtime_organ_state": {"status": "unavailable"},
            "portable_context_summary": {"status": "unavailable"},
        }


def _load_self_examination(
    workspace: Path, service: Any = None
) -> dict[str, Any]:
    """Load self-examination findings and health."""
    if service is not None:
        try:
            snapshot = service.take_snapshot()
            return {
                "status": "ok",
                "findings_count": len(snapshot.findings),
                "findings": [
                    {
                        "severity": f.severity.value,
                        "category": f.category,
                        "summary": f.summary,
                    }
                    for f in snapshot.findings[:20]
                ],
                "health_indicators": snapshot.health_indicators,
                "source": "live_service",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "live_service",
            }

    # Fallback: read from file
    path = workspace / "data" / "evolution" / "self_examination" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "findings_count": len(data.get("findings", [])),
                "findings": data.get("findings", [])[:20],
                "health_indicators": data.get("health_indicators", {}),
                "source": "file_fallback",
                "source_path": str(path),
            }
        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source": "file_fallback",
            "source_path": str(path),
        }


def _load_world_model(workspace: Path, service: Any = None) -> dict[str, Any]:
    """Load world model snapshot (environment, tools, network)."""
    if service is not None:
        try:
            snapshot = service.take_snapshot()
            return {
                "status": "ok",
                "windows_count": len(snapshot.windows),
                "tools_count": len(snapshot.tools),
                "network_status": snapshot.network_status,
                "blockers_count": len(snapshot.blockers),
                "source": "live_service",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "live_service",
            }

    # Fallback: read from file
    path = workspace / "data" / "evolution" / "world_model" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "windows_count": len(data.get("windows", [])),
                "tools_count": len(data.get("tools", [])),
                "network_status": data.get("network_status", "unknown"),
                "blockers_count": len(data.get("blockers", [])),
                "source": "file_fallback",
                "source_path": str(path),
            }
        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source": "file_fallback",
            "source_path": str(path),
        }


def _load_control_master(workspace: Path, service: Any = None) -> dict[str, Any]:
    """Load control master governance state."""
    if service is not None:
        try:
            state = service.current_state()
            return {
                "status": "ok",
                "vision": state.current_vision,
                "active_objectives_count": len(state.active_objective_ids),
                "completed_objectives_count": len(state.completed_objective_ids),
                "risks_count": len(state.current_risks),
                "rules_count": len(state.global_rules),
                "recent_decisions_count": len(state.recent_decisions),
                "unresolved_items_count": len(state.unresolved_items),
                "source": "live_service",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "live_service",
            }

    # Fallback: read from file
    path = workspace / "data" / "evolution" / "control_master" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "vision": data.get("current_vision", ""),
                "active_objectives_count": len(data.get("active_objective_ids", [])),
                "completed_objectives_count": len(
                    data.get("completed_objective_ids", [])
                ),
                "risks_count": len(data.get("current_risks", [])),
                "rules_count": len(data.get("global_rules", [])),
                "recent_decisions_count": len(data.get("recent_decisions", [])),
                "unresolved_items_count": len(data.get("unresolved_items", [])),
                "source": "file_fallback",
                "source_path": str(path),
            }
        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source": "file_fallback",
            "source_path": str(path),
        }


def _load_operational_learning(workspace: Path, experiment_lab: Any = None) -> dict[str, Any]:
    """Load operational learning (experiments, recommendations)."""
    if experiment_lab is not None:
        try:
            # Get recent experiments
            recent_runs = experiment_lab.repository.list_runs(limit=10)
            recent_recommendations = experiment_lab.repository.list_recommendations(
                limit=10
            )
            return {
                "status": "ok",
                "recent_runs_count": len(recent_runs),
                "recent_recommendations_count": len(recent_recommendations),
                "source": "live_service",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "live_service",
            }

    # Fallback: read from file
    path = workspace / "data" / "evolution" / "experiment_lab" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "recent_runs_count": len(data.get("recent_runs", [])),
                "recent_recommendations_count": len(
                    data.get("recent_recommendations", [])
                ),
                "source": "file_fallback",
                "source_path": str(path),
            }
        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source": "file_fallback",
            "source_path": str(path),
        }


def _track_evidence_sources(snapshot: dict[str, Any]) -> None:
    """Track which evidence sources were successfully read."""
    sources = []

    if snapshot["runtime_knowledge"].get("runtime_organ_state", {}).get("status") == "ok":
        sources.append("runtime_organs")
    if (
        snapshot["runtime_knowledge"]
        .get("portable_context_summary", {})
        .get("status")
        == "ok"
    ):
        sources.append("portable_context")
    if snapshot["self_examination"].get("status") == "ok":
        sources.append(f"self_examination:{snapshot['self_examination']['source']}")
    if snapshot["world_model"].get("status") == "ok":
        sources.append(f"world_model:{snapshot['world_model']['source']}")
    if snapshot["control_master"].get("status") == "ok":
        sources.append(f"control_master:{snapshot['control_master']['source']}")
    if snapshot["operational_learning"].get("status") == "ok":
        sources.append(
            f"operational_learning:{snapshot['operational_learning']['source']}"
        )

    snapshot["evidence_sources"] = sources


def render_organism_state_markdown(snapshot: dict[str, Any]) -> str:
    """Render the organism state snapshot as human-readable markdown."""
    lines = [
        "# IABV Organism State Snapshot",
        "",
        f"- Generated: {snapshot['timestamp']}",
        f"- Workspace: {snapshot['workspace_root']}",
        "",
        "## Runtime Knowledge",
    ]

    rk = snapshot.get("runtime_knowledge", {})
    organ_state = rk.get("runtime_organ_state", {})
    portable_context = rk.get("portable_context_summary", {})

    lines.append(f"- Status: {organ_state.get('status', 'unknown')}")
    if organ_state.get("status") == "ok":
        lines.append(f"- Organ count: {organ_state.get('organ_count', 0)}")
    lines.append(f"- Portable Context: {portable_context.get('status', 'unknown')}")

    lines.extend(["", "## Self Examination"])
    se = snapshot.get("self_examination", {})
    lines.append(f"- Status: {se.get('status', 'unknown')}")
    if se.get("status") == "ok":
        lines.append(f"- Findings: {se.get('findings_count', 0)}")
        lines.append(f"- Source: {se.get('source', 'unknown')}")

    lines.extend(["", "## World Model"])
    wm = snapshot.get("world_model", {})
    lines.append(f"- Status: {wm.get('status', 'unknown')}")
    if wm.get("status") == "ok":
        lines.append(f"- Windows: {wm.get('windows_count', 0)}")
        lines.append(f"- Tools: {wm.get('tools_count', 0)}")
        lines.append(f"- Network: {wm.get('network_status', 'unknown')}")
        lines.append(f"- Blockers: {wm.get('blockers_count', 0)}")
        lines.append(f"- Source: {wm.get('source', 'unknown')}")

    lines.extend(["", "## Control Master"])
    cm = snapshot.get("control_master", {})
    lines.append(f"- Status: {cm.get('status', 'unknown')}")
    if cm.get("status") == "ok":
        lines.append(f"- Vision: {cm.get('vision', 'none')[:100]}")
        lines.append(f"- Active objectives: {cm.get('active_objectives_count', 0)}")
        lines.append(f"- Completed objectives: {cm.get('completed_objectives_count', 0)}")
        lines.append(f"- Risks: {cm.get('risks_count', 0)}")
        lines.append(f"- Rules: {cm.get('rules_count', 0)}")
        lines.append(f"- Recent decisions: {cm.get('recent_decisions_count', 0)}")
        lines.append(f"- Unresolved: {cm.get('unresolved_items_count', 0)}")
        lines.append(f"- Source: {cm.get('source', 'unknown')}")

    lines.extend(["", "## Operational Learning"])
    ol = snapshot.get("operational_learning", {})
    lines.append(f"- Status: {ol.get('status', 'unknown')}")
    if ol.get("status") == "ok":
        lines.append(f"- Recent runs: {ol.get('recent_runs_count', 0)}")
        lines.append(f"- Recent recommendations: {ol.get('recent_recommendations_count', 0)}")
        lines.append(f"- Source: {ol.get('source', 'unknown')}")

    lines.extend(["", "## GPU Health"])
    gh = snapshot.get("gpu_health", {})
    lines.append(f"- Status: {gh.get('status', 'unknown')}")
    if gh.get("status") == "ok":
        lines.append(f"- GPU Status: {gh.get('gpu_status', 'unknown')}")
        lines.append(f"- GPU Name: {gh.get('gpu_name', 'unknown')}")
        lines.append(f"- GPU Driver: {gh.get('gpu_driver', 'unknown')}")
        lines.append(f"- GPU Temp: {gh.get('gpu_temperature_c', 'N/A')}°C")
        lines.append(f"- GPU Util: {gh.get('gpu_utilization_pct', 'N/A')}%")
        lines.append(f"- Degradation Reason: {gh.get('gpu_degradation_reason', 'none')}")
        lines.append(f"- Source: {gh.get('source', 'unknown')}")

    lines.extend(["", "## Unresolved Fields"])
    uf = snapshot.get("unresolved_fields", [])
    lines.append(f"- Count: {len(uf)}")
    if uf:
        lines.extend([f"- {field}" for field in uf[:10]])

    lines.extend(["", "## Evidence Sources"])
    for source in snapshot.get("evidence_sources", []):
        lines.append(f"- {source}")

    return "\n".join(lines) + "\n"


def _load_gpu_health(workspace: Path, environment_self_awareness_service: Any = None) -> dict[str, Any]:
    """Load GPU health from environment self-awareness service.

    Prefers fresh data from the live service if available, otherwise falls back
    to the persisted file. This ensures the surface reflects the current GPU state
    rather than stale cached data.
    """
    # Try to get fresh data from the live service first
    if environment_self_awareness_service is not None:
        try:
            current_model = environment_self_awareness_service.current_model()
            hardware_profile = current_model.hardware_profile if hasattr(current_model, 'hardware_profile') else {}

            if hardware_profile:
                gpu_status = hardware_profile.get("gpu_status", "unavailable")
                gpu_name = hardware_profile.get("gpu_name", "")
                gpu_degradation_reason = hardware_profile.get("gpu_degradation_reason", "")
                gpu_degradation_detail = hardware_profile.get("gpu_degradation_detail", "")

                return {
                    "status": "ok",
                    "gpu_status": gpu_status,
                    "gpu_name": gpu_name,
                    "gpu_driver": hardware_profile.get("gpu_driver", ""),
                    "gpu_memory_total_mb": hardware_profile.get("gpu_memory_total_mb"),
                    "gpu_memory_free_mb": hardware_profile.get("gpu_memory_free_mb"),
                    "gpu_temperature_c": hardware_profile.get("gpu_temperature_c"),
                    "gpu_utilization_pct": hardware_profile.get("gpu_utilization_pct"),
                    "gpu_degradation_reason": gpu_degradation_reason,
                    "gpu_degradation_detail": gpu_degradation_detail,
                    "source": "live_service",
                    "updated_at": current_model.last_scan.isoformat() if hasattr(current_model, 'last_scan') else None,
                    "age_seconds": 0.0,
                    "stale_capable": False,
                }
        except Exception:
            # Fall back to file if live service fails
            pass

    # Fallback: read from persisted file (stale-capable)
    path = workspace / "data" / "evolution" / "environment_self_model" / "latest.json"
    try:
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            hardware_profile = data.get("hardware_profile", {})

            # Extract GPU status information
            gpu_status = hardware_profile.get("gpu_status", "unavailable")
            gpu_name = hardware_profile.get("gpu_name", "")
            gpu_degradation_reason = hardware_profile.get("gpu_degradation_reason", "")
            gpu_degradation_detail = hardware_profile.get("gpu_degradation_detail", "")

            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)

            return {
                "status": "ok",
                "gpu_status": gpu_status,
                "gpu_name": gpu_name,
                "gpu_driver": hardware_profile.get("gpu_driver", ""),
                "gpu_memory_total_mb": hardware_profile.get("gpu_memory_total_mb"),
                "gpu_memory_free_mb": hardware_profile.get("gpu_memory_free_mb"),
                "gpu_temperature_c": hardware_profile.get("gpu_temperature_c"),
                "gpu_utilization_pct": hardware_profile.get("gpu_utilization_pct"),
                "gpu_degradation_reason": gpu_degradation_reason,
                "gpu_degradation_detail": gpu_degradation_detail,
                "source": "environment_self_model",
                "source_path": str(path),
                "updated_at": datetime.fromtimestamp(updated_at, tz=timezone.utc).isoformat(),
                "age_seconds": age_seconds,
                "stale_capable": True,
            }
        return {
            "status": "unavailable",
            "gpu_status": "unavailable",
            "source": "file_fallback",
            "source_path": str(path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "gpu_status": "unavailable",
            "source": "file_fallback",
            "source_path": str(path),
        }


def _load_unresolved_fields(workspace: Path, environment_self_awareness_service: Any = None) -> list[str]:
    """Load unresolved fields from environment self-awareness service.

    Includes GPU degradation signals and other unresolved hardware states.
    """
    unresolved = []

    # Try to get fresh data from the live service first
    if environment_self_awareness_service is not None:
        try:
            current_model = environment_self_awareness_service.current_model()
            if hasattr(current_model, 'unresolved_fields'):
                unresolved.extend(current_model.unresolved_fields)
        except Exception:
            # Fall back to file if live service fails
            pass

    # Fallback: read from persisted file
    path = workspace / "data" / "evolution" / "environment_self_model" / "latest.json"
    try:
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            file_unresolved = data.get("unresolved_fields", [])
            unresolved.extend(file_unresolved)
    except Exception:
        pass

    return unresolved
