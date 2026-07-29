"""
Organism State Snapshot - Derived Read-Only Observability View (P0.165)

Derived read-only observability view of organism state.
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
This is NOT a single source of truth - it is a derived view that
projects existing canonical state for inspection.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def export_organism_state_snapshot(
    workspace_root: str | Path,
    *,
    self_examination_service: Any = None,
    world_model_service: Any = None,
    control_master_service: Any = None,
    experiment_lab: Any = None,
) -> dict[str, Any]:
    """Export a unified read-only snapshot of the organism state.

    This function aggregates existing state from canonical services
    without introducing new authority or memory. It's purely for observability.

    Args:
        workspace_root: Path to the IABV workspace root
        self_examination_service: Optional OperationalSelfExaminationService instance
        world_model_service: Optional WorldModelService instance
        control_master_service: Optional ControlMasterService instance
        experiment_lab: Optional ExperimentLab instance

    Returns:
        Unified snapshot dictionary with:
        - timestamp
        - workspace_root
        - runtime_knowledge (organs, portable context)
        - self_examination (findings, health)
        - world_model (environment, tools, network)
        - control_master (governance state)
        - operational_learning (experiments, recommendations)
        - organ_health_matrix (derived health metrics)
        - stability_signals (stability indicators)
        - learning_reuse_summary (learning efficiency)
        - active_hypotheses (active learning hypotheses)
        - discarded_hypotheses (discarded hypotheses)
        - temporal_delta_summary (temporal changes)
        - source_confidence (confidence in sources)
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
        "organ_health_matrix": _load_organ_health_matrix(
            workspace, self_examination_service
        ),
        "stability_signals": _load_stability_signals(
            workspace, experiment_lab
        ),
        "learning_reuse_summary": _load_learning_reuse_summary(
            workspace, experiment_lab
        ),
        "active_hypotheses": _load_active_hypotheses(
            workspace, experiment_lab
        ),
        "discarded_hypotheses": _load_discarded_hypotheses(
            workspace, experiment_lab
        ),
        "temporal_delta_summary": _load_temporal_delta_summary(
            workspace
        ),
        "source_confidence": _load_source_confidence(
            workspace
        ),
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

    # Fallback: read from file (stale-capable)
    path = workspace / "data" / "evolution" / "self_examination" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "findings_count": len(data.get("findings", [])),
                "findings": data.get("findings", [])[:20],
                "health_indicators": data.get("health_indicators", {}),
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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

    # Fallback: read from file (stale-capable)
    path = workspace / "data" / "evolution" / "world_model" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "windows_count": len(data.get("windows", [])),
                "tools_count": len(data.get("tools", [])),
                "network_status": data.get("network_status", "unknown"),
                "blockers_count": len(data.get("blockers", [])),
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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

    # Fallback: read from file (stale-capable)
    path = workspace / "data" / "evolution" / "control_master" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
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
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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

    # Fallback: read from file (stale-capable)
    path = workspace / "data" / "evolution" / "experiment_lab" / "latest.json"
    try:
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "recent_runs_count": len(data.get("recent_runs", [])),
                "recent_recommendations_count": len(
                    data.get("recent_recommendations", [])
                ),
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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


def _load_organ_health_matrix(workspace: Path, service: Any = None) -> dict[str, Any]:
    """Load organ health matrix derived from self-examination and runtime organs."""
    try:
        # Try to get health from self_examination
        if service is not None:
            try:
                snapshot = service.take_snapshot()
                health_indicators = snapshot.health_indicators
                return {
                    "status": "ok",
                    "overall_health": health_indicators.get("overall_health", "unknown"),
                    "organ_health": health_indicators.get("organ_health", {}),
                    "source": "live_service",
                }
            except Exception:
                pass

        # Fallback: read from self_examination file
        path = workspace / "data" / "evolution" / "self_examination" / "latest.json"
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            health_indicators = data.get("health_indicators", {})
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "overall_health": health_indicators.get("overall_health", "unknown"),
                "organ_health": health_indicators.get("organ_health", {}),
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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
        }


def _load_stability_signals(workspace: Path, experiment_lab: Any = None) -> dict[str, Any]:
    """Load stability signals from operational learning."""
    try:
        if experiment_lab is not None:
            try:
                # Get recent runs to assess stability
                recent_runs = experiment_lab.repository.list_runs(limit=20)
                if recent_runs:
                    # Calculate stability metrics
                    success_rate = sum(1 for r in recent_runs if r.success) / len(recent_runs)
                    return {
                        "status": "ok",
                        "success_rate": success_rate,
                        "recent_runs_count": len(recent_runs),
                        "source": "live_service",
                    }
            except Exception:
                pass

        # Fallback: read from experiment_lab file
        path = workspace / "data" / "evolution" / "experiment_lab" / "latest.json"
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            recent_runs = data.get("recent_runs", [])
            if recent_runs:
                success_rate = sum(1 for r in recent_runs if r.get("success")) / len(recent_runs)
            else:
                success_rate = 0.0
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "success_rate": success_rate,
                "recent_runs_count": len(recent_runs),
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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
        }


def _load_learning_reuse_summary(workspace: Path, experiment_lab: Any = None) -> dict[str, Any]:
    """Load learning reuse summary from operational learning."""
    try:
        if experiment_lab is not None:
            try:
                recent_runs = experiment_lab.repository.list_runs(limit=50)
                # Count reused patterns
                reused_count = sum(1 for r in recent_runs if r.metadata.get("reused_pattern"))
                return {
                    "status": "ok",
                    "total_runs": len(recent_runs),
                    "reused_patterns_count": reused_count,
                    "reuse_rate": reused_count / len(recent_runs) if recent_runs else 0.0,
                    "source": "live_service",
                }
            except Exception:
                pass

        # Fallback: read from experiment_lab file
        path = workspace / "data" / "evolution" / "experiment_lab" / "latest.json"
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            recent_runs = data.get("recent_runs", [])
            reused_count = sum(1 for r in recent_runs if r.get("metadata", {}).get("reused_pattern"))
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "total_runs": len(recent_runs),
                "reused_patterns_count": reused_count,
                "reuse_rate": reused_count / len(recent_runs) if recent_runs else 0.0,
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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
        }


def _load_active_hypotheses(workspace: Path, experiment_lab: Any = None) -> dict[str, Any]:
    """Load active hypotheses from operational learning."""
    try:
        if experiment_lab is not None:
            try:
                recent_recommendations = experiment_lab.repository.list_recommendations(limit=10)
                return {
                    "status": "ok",
                    "active_count": len(recent_recommendations),
                    "hypotheses": [
                        {
                            "domain": r.domain.value,
                            "subject_key": r.subject_key,
                            "recommendation": r.recommended_action,
                        }
                        for r in recent_recommendations[:5]
                    ],
                    "source": "live_service",
                }
            except Exception:
                pass

        # Fallback: read from experiment_lab file
        path = workspace / "data" / "evolution" / "experiment_lab" / "latest.json"
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            recent_recommendations = data.get("recent_recommendations", [])
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "active_count": len(recent_recommendations),
                "hypotheses": recent_recommendations[:5],
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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
        }


def _load_discarded_hypotheses(workspace: Path, experiment_lab: Any = None) -> dict[str, Any]:
    """Load discarded hypotheses from operational learning."""
    try:
        if experiment_lab is not None:
            try:
                # This would require querying for rejected/failed experiments
                # For now, mark as unavailable since we don't have a direct query
                return {
                    "status": "unavailable",
                    "source": "live_service",
                    "note": "Discarded hypothesis tracking not yet implemented",
                }
            except Exception:
                pass

        # Fallback: read from experiment_lab file
        path = workspace / "data" / "evolution" / "experiment_lab" / "latest.json"
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            discarded = data.get("discarded_hypotheses", [])
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "discarded_count": len(discarded),
                "hypotheses": discarded[:5],
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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
        }


def _load_temporal_delta_summary(workspace: Path) -> dict[str, Any]:
    """Load temporal delta summary from audit trail."""
    try:
        # Try to read from decision audit trail
        path = workspace / "data" / "evolution" / "decision_audit_trail" / "latest.json"
        if path.exists():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            decisions = data.get("recent_decisions", [])
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "recent_decisions_count": len(decisions),
                "last_decision_timestamp": decisions[0].get("timestamp") if decisions else None,
                "source": "file_fallback",
                "source_path": str(path),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
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
        }


def _load_source_confidence(workspace: Path) -> dict[str, Any]:
    """Load source confidence based on data freshness and availability."""
    try:
        # Calculate confidence based on available sources and their freshness
        confidence_scores = {}

        # Check runtime organs
        rk_path = workspace / "data" / "evolution" / "runtime_organs" / "latest.json"
        if rk_path.exists():
            age = datetime.now(timezone.utc).timestamp() - rk_path.stat().st_mtime
            confidence_scores["runtime_organs"] = max(0.0, 1.0 - age / 3600)  # Decay over 1 hour
        else:
            confidence_scores["runtime_organs"] = 0.0

        # Check self_examination
        se_path = workspace / "data" / "evolution" / "self_examination" / "latest.json"
        if se_path.exists():
            age = datetime.now(timezone.utc).timestamp() - se_path.stat().st_mtime
            confidence_scores["self_examination"] = max(0.0, 1.0 - age / 3600)
        else:
            confidence_scores["self_examination"] = 0.0

        # Check world_model
        wm_path = workspace / "data" / "evolution" / "world_model" / "latest.json"
        if wm_path.exists():
            age = datetime.now(timezone.utc).timestamp() - wm_path.stat().st_mtime
            confidence_scores["world_model"] = max(0.0, 1.0 - age / 3600)
        else:
            confidence_scores["world_model"] = 0.0

        # Calculate overall confidence
        overall_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0

        return {
            "status": "ok",
            "overall_confidence": overall_confidence,
            "source_confidences": confidence_scores,
            "source": "derived",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source": "derived",
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
    if snapshot["organ_health_matrix"].get("status") == "ok":
        sources.append(f"organ_health_matrix:{snapshot['organ_health_matrix']['source']}")
    if snapshot["stability_signals"].get("status") == "ok":
        sources.append(f"stability_signals:{snapshot['stability_signals']['source']}")
    if snapshot["learning_reuse_summary"].get("status") == "ok":
        sources.append(f"learning_reuse_summary:{snapshot['learning_reuse_summary']['source']}")
    if snapshot["active_hypotheses"].get("status") == "ok":
        sources.append(f"active_hypotheses:{snapshot['active_hypotheses']['source']}")
    if snapshot["discarded_hypotheses"].get("status") == "ok":
        sources.append(f"discarded_hypotheses:{snapshot['discarded_hypotheses']['source']}")
    if snapshot["temporal_delta_summary"].get("status") == "ok":
        sources.append(f"temporal_delta_summary:{snapshot['temporal_delta_summary']['source']}")
    if snapshot["source_confidence"].get("status") == "ok":
        sources.append(f"source_confidence:{snapshot['source_confidence']['source']}")

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

    lines.extend(["", "## Organ Health Matrix"])
    ohm = snapshot.get("organ_health_matrix", {})
    lines.append(f"- Status: {ohm.get('status', 'unknown')}")
    if ohm.get("status") == "ok":
        lines.append(f"- Overall health: {ohm.get('overall_health', 'unknown')}")
        lines.append(f"- Source: {ohm.get('source', 'unknown')}")

    lines.extend(["", "## Stability Signals"])
    ss = snapshot.get("stability_signals", {})
    lines.append(f"- Status: {ss.get('status', 'unknown')}")
    if ss.get("status") == "ok":
        lines.append(f"- Success rate: {ss.get('success_rate', 0.0):.2%}")
        lines.append(f"- Recent runs: {ss.get('recent_runs_count', 0)}")
        lines.append(f"- Source: {ss.get('source', 'unknown')}")

    lines.extend(["", "## Learning Reuse Summary"])
    lrs = snapshot.get("learning_reuse_summary", {})
    lines.append(f"- Status: {lrs.get('status', 'unknown')}")
    if lrs.get("status") == "ok":
        lines.append(f"- Total runs: {lrs.get('total_runs', 0)}")
        lines.append(f"- Reused patterns: {lrs.get('reused_patterns_count', 0)}")
        lines.append(f"- Reuse rate: {lrs.get('reuse_rate', 0.0):.2%}")
        lines.append(f"- Source: {lrs.get('source', 'unknown')}")

    lines.extend(["", "## Temporal Delta Summary"])
    tds = snapshot.get("temporal_delta_summary", {})
    lines.append(f"- Status: {tds.get('status', 'unknown')}")
    if tds.get("status") == "ok":
        lines.append(f"- Recent decisions: {tds.get('recent_decisions_count', 0)}")
        lines.append(f"- Source: {tds.get('source', 'unknown')}")

    lines.extend(["", "## Source Confidence"])
    sc = snapshot.get("source_confidence", {})
    lines.append(f"- Status: {sc.get('status', 'unknown')}")
    if sc.get("status") == "ok":
        lines.append(f"- Overall confidence: {sc.get('overall_confidence', 0.0):.2%}")
        lines.append(f"- Source: {sc.get('source', 'unknown')}")

    lines.extend(["", "## Evidence Sources"])
    for source in snapshot.get("evidence_sources", []):
        lines.append(f"- {source}")

    return "\n".join(lines) + "\n"
