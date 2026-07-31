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
    environment_self_awareness_service: Any = None,
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
        - organ_health_matrix (derived health metrics)
        - stability_signals (stability indicators)
        - learning_reuse_summary (learning efficiency)
        - active_hypotheses (active learning hypotheses)
        - discarded_hypotheses (discarded hypotheses)
        - temporal_delta_summary (temporal changes)
        - human_vision_readout (project direction, phase, AI recommendations)
        - source_confidence (confidence in sources)
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
        "human_vision_readout": _load_human_vision_readout(
            workspace, control_master_service
        ),
        "source_confidence": _load_source_confidence(
            workspace
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

    # Fallback: read from actual data directories
    # Count experiment runs from experiment_runs directory
    runs_dir = workspace / "data" / "evolution" / "experiment_runs"
    recommendations_dir = workspace / "data" / "evolution" / "experiment_recommendations"

    try:
        runs_count = 0
        recommendations_count = 0
        updated_at = None
        age_seconds = None

        if runs_dir.exists():
            import json
            runs_files = list(runs_dir.glob("*.json"))
            runs_count = len(runs_files)
            if runs_files:
                updated_at = max(f.stat().st_mtime for f in runs_files)

        if recommendations_dir.exists():
            recommendations_files = list(recommendations_dir.glob("*.json"))
            recommendations_count = len(recommendations_files)
            if recommendations_files:
                rec_mtime = max(f.stat().st_mtime for f in recommendations_files)
                updated_at = max(updated_at, rec_mtime) if updated_at else rec_mtime

        if updated_at is not None:
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)

        return {
            "status": "ok",
            "recent_runs_count": runs_count,
            "recent_recommendations_count": recommendations_count,
            "source": "file_fallback",
            "source_path": f"{runs_dir}, {recommendations_dir}",
            "updated_at": updated_at,
            "age_seconds": age_seconds,
            "stale_capable": True,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "source": "file_fallback",
            "source_path": f"{runs_dir}, {recommendations_dir}",
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

        # Fallback: read from experiment_runs directory (real source)
        experiment_runs_dir = workspace / "data" / "evolution" / "experiment_runs"
        if experiment_runs_dir.exists():
            import json

            # Read recent experiment runs
            run_files = list(experiment_runs_dir.glob("*.json"))
            if run_files:
                # Sort by modification time, get most recent 20
                run_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                recent_files = run_files[:20]

                recent_runs = []
                for f in recent_files:
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        recent_runs.append(data)
                    except Exception:
                        continue

                if recent_runs:
                    success_rate = sum(1 for r in recent_runs if r.get("success", False)) / len(recent_runs)
                else:
                    success_rate = 0.0

                updated_at = recent_files[0].stat().st_mtime if recent_files else None
                age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at) if updated_at else None

                return {
                    "status": "ok",
                    "success_rate": success_rate,
                    "recent_runs_count": len(recent_runs),
                    "source": "file_fallback",
                    "source_path": str(experiment_runs_dir),
                    "updated_at": updated_at,
                    "age_seconds": age_seconds,
                    "stale_capable": True,
                }

        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(experiment_runs_dir),
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

        # Fallback: read from experience directory (real source)
        experience_dir = workspace / "data" / "evolution" / "experience"
        if experience_dir.exists():
            import json

            # Read experience JSONL files
            experience_files = list(experience_dir.glob("*.jsonl"))
            if experience_files:
                total_runs = 0
                reused_patterns_count = 0

                for exp_file in experience_files:
                    try:
                        lines = exp_file.read_text(encoding="utf-8").strip().split("\n")
                        for line in lines:
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    total_runs += 1
                                    # Check for reuse indicators in experience data
                                    if data.get("reused") or data.get("pattern_reused"):
                                        reused_patterns_count += 1
                                except Exception:
                                    continue
                    except Exception:
                        continue

                reuse_rate = reused_patterns_count / total_runs if total_runs > 0 else 0.0

                # Get most recent file for timestamp
                experience_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                updated_at = experience_files[0].stat().st_mtime if experience_files else None
                age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at) if updated_at else None

                return {
                    "status": "ok",
                    "total_runs": total_runs,
                    "reused_patterns_count": reused_patterns_count,
                    "reuse_rate": reuse_rate,
                    "source": "file_fallback",
                    "source_path": str(experience_dir),
                    "updated_at": updated_at,
                    "age_seconds": age_seconds,
                    "stale_capable": True,
                }

        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(experience_dir),
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

        # Fallback: read from experiment_recommendations directory
        recommendations_dir = workspace / "data" / "evolution" / "experiment_recommendations"
        if recommendations_dir.exists():
            import json

            recommendations_files = list(recommendations_dir.glob("*.json"))
            # Read up to 5 most recent recommendations
            recommendations_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            recent_recommendations = []
            for f in recommendations_files[:5]:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    recent_recommendations.append(data)
                except Exception:
                    pass

            updated_at = recommendations_files[0].stat().st_mtime if recommendations_files else None
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at) if updated_at else None
            return {
                "status": "ok",
                "active_count": len(recommendations_files),
                "hypotheses": recent_recommendations[:5],
                "source": "file_fallback",
                "source_path": str(recommendations_dir),
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
            }

        return {
            "status": "unavailable",
            "source": "file_fallback",
            "source_path": str(recommendations_dir),
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

        # Fallback: No canonical source for discarded hypotheses
        # This data is not currently tracked in a dedicated file
        return {
            "status": "unavailable",
            "source": "file_fallback",
            "note": "No canonical source for discarded hypotheses - unresolved",
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
        # Try to read from decision audit trail (actual path: decision_audit/decisions.jsonl)
        path = workspace / "data" / "evolution" / "decision_audit" / "decisions.jsonl"
        if path.exists():
            import json

            # Read JSONL file and count recent decisions
            decisions = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            decisions.append(json.loads(line))
                        except Exception:
                            pass

            # Get last 10 decisions
            recent_decisions = decisions[-10:] if decisions else []
            updated_at = path.stat().st_mtime
            age_seconds = (datetime.now(timezone.utc).timestamp() - updated_at)
            return {
                "status": "ok",
                "recent_decisions_count": len(recent_decisions),
                "last_decision_timestamp": recent_decisions[-1].get("timestamp") if recent_decisions else None,
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


def _load_human_vision_readout(workspace: Path, control_master_service: Any = None) -> dict[str, Any]:
    """Load human vision readout (project direction, phase, AI recommendations).

    This is a derived read-only section that aggregates:
    - PortableContext for persistent user intent
    - ControlMaster for vision/objectives
    - platform_pending for open tasks
    - agent_session_gate for current briefing
    - DecisionAuditTrail/ExperimentLab only if evidence exists for better AI by task type
    """
    import json

    unresolved_fields = []
    evidence_sources = []

    # Load from PortableContext (persistent user intent)
    portable_context_path = workspace / "data" / "evolution" / "portable_context" / "latest.json"
    portable_context_data = None
    user_intent_summary = "UNRESOLVED"
    stable_principles = []
    ai_preference = None  # Initialize before conditional block

    if portable_context_path.exists():
        try:
            portable_context_data = json.loads(portable_context_path.read_text(encoding="utf-8"))
            sections = portable_context_data.get("sections", [])

            # Extract user intent from user_metacognitive_intent section
            for section in sections:
                if section.get("section_id") == "user_metacognitive_intent":
                    user_intent_summary = section.get("summary", "UNRESOLVED")
                    for item in section.get("items", []):
                        stable_principles.append({
                            "label": item.get("label", ""),
                            "detail": item.get("detail", "")
                        })
                    evidence_sources.append("portable_context:user_metacognitive_intent")
                    break

            # Extract project state
            for section in sections:
                if section.get("section_id") == "project_state":
                    project_state_items = section.get("items", [])
                    for item in project_state_items:
                        if item.get("label") == "Objetivo activo":
                            user_intent_summary = item.get("value", user_intent_summary)
                    evidence_sources.append("portable_context:project_state")
                    break

            # Extract learning for AI recommendations
            for section in sections:
                if section.get("section_id") == "learning":
                    learning_items = section.get("items", [])
                    for item in learning_items:
                        if item.get("label") == "Preferencia actual":
                            ai_preference = {
                                "assistant_kind": item.get("assistant_kind"),
                                "route": item.get("route"),
                                "reasons": item.get("reasons", []),
                                "confidence": item.get("confidence", 0.0)
                            }
                            evidence_sources.append("portable_context:learning")
                            break
        except Exception as e:
            unresolved_fields.append(f"portable_context_read_error:{str(e)}")
    else:
        unresolved_fields.append("portable_context_file_not_found")

    # Load from ControlMaster (vision/objectives)
    control_master_path = workspace / "data" / "evolution" / "control_master" / "latest.json"
    control_master_vision = "UNRESOLVED"
    active_objectives = []

    if control_master_service is not None:
        try:
            state = control_master_service.current_state()
            control_master_vision = state.current_vision or "UNRESOLVED"
            active_objectives = state.active_objective_ids or []
            evidence_sources.append("control_master:live_service")
        except Exception as e:
            unresolved_fields.append(f"control_master_service_error:{str(e)}")
    elif control_master_path.exists():
        try:
            control_master_data = json.loads(control_master_path.read_text(encoding="utf-8"))
            control_master_vision = control_master_data.get("current_vision", "UNRESOLVED")
            active_objectives = control_master_data.get("active_objective_ids", [])
            evidence_sources.append("control_master:file_fallback")
        except Exception as e:
            unresolved_fields.append(f"control_master_file_error:{str(e)}")
    else:
        unresolved_fields.append("control_master_not_available")

    # Load from agent_session_gate (current briefing)
    session_gate_path = workspace / "data" / "evolution" / "agent_session_gate" / "latest.json"
    current_briefing = "UNRESOLVED"
    current_phase = "UNRESOLVED"

    if session_gate_path.exists():
        try:
            session_gate_data = json.loads(session_gate_path.read_text(encoding="utf-8"))
            active_objectives_gate = session_gate_data.get("active_objectives", [])
            if active_objectives_gate:
                # Get the first critical objective as current briefing
                for obj in active_objectives_gate:
                    if obj.get("priority") == "critical":
                        current_briefing = obj.get("title", "UNRESOLVED")
                        current_phase = obj.get("status", "UNRESOLVED")
                        break
                if current_briefing == "UNRESOLVED" and active_objectives_gate:
                    current_briefing = active_objectives_gate[0].get("title", "UNRESOLVED")
                    current_phase = active_objectives_gate[0].get("status", "UNRESOLVED")
                evidence_sources.append("agent_session_gate:latest.json")
        except Exception as e:
            unresolved_fields.append(f"agent_session_gate_error:{str(e)}")
    else:
        unresolved_fields.append("agent_session_gate_not_available")

    # Load from platform_pending (open tasks)
    platform_pending_dir = workspace / "data" / "evolution" / "platform_pending"
    pending_tasks_count = 0
    recommended_next_step = "UNRESOLVED"
    selected_task_evidence = None
    active_external_blocks = []

    if platform_pending_dir.exists():
        try:
            task_files = list(platform_pending_dir.glob("*.json"))
            pending_tasks_count = len(task_files)

            if task_files:
                # Load all tasks and sort by priority and status
                actionable_tasks = []

                for task_file in task_files:
                    try:
                        task_data = json.loads(task_file.read_text(encoding="utf-8"))
                        status = task_data.get("status", "")
                        priority = task_data.get("priority", "")

                        # Exclude COMPLETED tasks
                        if status == "COMPLETED":
                            continue

                        execution_evidence = task_data.get("execution_evidence", {})
                        if execution_evidence.get("external_dependency_blocked"):
                            active_external_blocks.append({
                                "task_id": task_data.get("id", ""),
                                "dependency": task_data.get("dependency_missing", ""),
                                "type": execution_evidence.get("external_dependency_type", ""),
                                "reason": task_data.get("reason", ""),
                                "status": task_data.get("status", ""),
                                "verification_status": task_data.get("verification_status", ""),
                                "verdict": execution_evidence.get("verdict", ""),
                                "execution_summary": execution_evidence.get("execution_summary", ""),
                                "execution_error": execution_evidence.get("error", ""),
                                "human_review_required": execution_evidence.get("human_review_required", True),
                                "evidence_source": f"platform_pending:{task_file.name}",
                            })

                        # Score tasks for selection
                        score = 0
                        if priority == "critical":
                            score += 100
                        elif priority == "high":
                            score += 50

                        if status == "PENDING":
                            score += 20
                        elif status == "READY_FOR_NEXT_SLICE":
                            score += 10

                        actionable_tasks.append({
                            "score": score,
                            "task": task_data,
                            "file": str(task_file.name)
                        })
                    except Exception:
                        continue

                # Sort by score (descending)
                actionable_tasks.sort(key=lambda x: x["score"], reverse=True)

                if actionable_tasks:
                    selected = actionable_tasks[0]
                    task = selected["task"]
                    selected_task_evidence = {
                        "id": task.get("id", ""),
                        "title": task.get("title", ""),
                        "status": task.get("status", ""),
                        "priority": task.get("priority", ""),
                        "file": selected["file"]
                    }

                    # Use next_action if exists, otherwise title
                    recommended_next_step = task.get("next_action") or task.get("title", "UNRESOLVED")
                    evidence_sources.append(f"platform_pending:{selected['file']}")
                    
                    # Include external dependency block information if present
                    if task.get("dependency_missing"):
                        selected_task_evidence["dependency_missing"] = task.get("dependency_missing")
                    if task.get("reason"):
                        selected_task_evidence["reason"] = task.get("reason")
                    
                    # Include execution evidence if present
                    execution_evidence = task.get("execution_evidence", {})
                    if execution_evidence.get("external_dependency_blocked"):
                        selected_task_evidence["external_dependency_blocked"] = execution_evidence.get("external_dependency_blocked")
                    if execution_evidence.get("external_dependency_type"):
                        selected_task_evidence["external_dependency_type"] = execution_evidence.get("external_dependency_type")
                    if execution_evidence.get("error"):
                        selected_task_evidence["execution_error"] = execution_evidence.get("error")
                    if execution_evidence.get("execution_summary"):
                        selected_task_evidence["execution_summary"] = execution_evidence.get("execution_summary")
                else:
                    unresolved_fields.append("platform_pending_no_actionable_tasks")
        except Exception as e:
            unresolved_fields.append(f"platform_pending_error:{str(e)}")
    else:
        unresolved_fields.append("platform_pending_directory_not_found")

    # Determine AI recommendation (only if evidence exists and is fresh)
    recommended_ai_route = "UNRESOLVED"
    ai_evidence = []
    ai_preference_stale = False

    # Calculate freshness thresholds (in seconds)
    FRESHNESS_THRESHOLD = 86400  # 24 hours
    STALE_THRESHOLD = 604800  # 7 days

    # Calculate source freshness
    source_freshness = {}
    now = datetime.now(timezone.utc).timestamp()

    if portable_context_path.exists():
        pc_age = now - portable_context_path.stat().st_mtime
        source_freshness["portable_context"] = {
            "age_seconds": pc_age,
            "is_fresh": pc_age < FRESHNESS_THRESHOLD,
            "is_stale": pc_age > STALE_THRESHOLD
        }
        if pc_age > STALE_THRESHOLD:
            unresolved_fields.append(f"portable_context_stale:{int(pc_age)}s")
            ai_preference_stale = True

    if control_master_path.exists():
        cm_age = now - control_master_path.stat().st_mtime
        source_freshness["control_master"] = {
            "age_seconds": cm_age,
            "is_fresh": cm_age < FRESHNESS_THRESHOLD,
            "is_stale": cm_age > STALE_THRESHOLD
        }
        if cm_age > STALE_THRESHOLD:
            unresolved_fields.append(f"control_master_stale:{int(cm_age)}s")

    if session_gate_path.exists():
        sg_age = now - session_gate_path.stat().st_mtime
        source_freshness["agent_session_gate"] = {
            "age_seconds": sg_age,
            "is_fresh": sg_age < FRESHNESS_THRESHOLD,
            "is_stale": sg_age > STALE_THRESHOLD
        }
        if sg_age > STALE_THRESHOLD:
            unresolved_fields.append(f"agent_session_gate_stale:{int(sg_age)}s")

    if platform_pending_dir.exists():
        pp_age = now - platform_pending_dir.stat().st_mtime
        source_freshness["platform_pending"] = {
            "age_seconds": pp_age,
            "is_fresh": pp_age < FRESHNESS_THRESHOLD,
            "is_stale": pp_age > STALE_THRESHOLD
        }
        if pp_age > STALE_THRESHOLD:
            unresolved_fields.append(f"platform_pending_stale:{int(pp_age)}s")

    # Only use AI preference if it's from a fresh source
    if ai_preference:
        if ai_preference_stale:
            # AI preference exists but is from stale source
            recommended_ai_route = f"{ai_preference.get('assistant_kind', 'unknown')}:{ai_preference.get('route', 'unknown')}_STALE"
            ai_evidence = ai_preference.get("reasons", [])
            evidence_sources.append("portable_context:ai_preference_stale")
            unresolved_fields.append("ai_preference_source_stale")
        else:
            recommended_ai_route = f"{ai_preference.get('assistant_kind', 'unknown')}:{ai_preference.get('route', 'unknown')}"
            ai_evidence = ai_preference.get("reasons", [])
            evidence_sources.append("portable_context:ai_preference")
    else:
        unresolved_fields.append("ai_preference_no_evidence")

    # Build current project direction from available sources
    if user_intent_summary != "UNRESOLVED":
        current_project_direction = user_intent_summary
    elif control_master_vision != "UNRESOLVED":
        current_project_direction = control_master_vision
    elif current_briefing != "UNRESOLVED":
        current_project_direction = current_briefing
    else:
        current_project_direction = "UNRESOLVED"
        unresolved_fields.append("project_direction_no_source")

    # Calculate staleness metadata (use most recent source)
    updated_at = None
    age_seconds = None
    stale_capable = False

    if source_freshness:
        # Use the freshest source for overall staleness
        freshest_source = min(source_freshness.items(), key=lambda x: x[1]["age_seconds"])
        updated_at = now - freshest_source[1]["age_seconds"]
        age_seconds = freshest_source[1]["age_seconds"]
        stale_capable = any(s["is_stale"] for s in source_freshness.values())

    return {
        "status": "ok",
        "current_project_direction": current_project_direction,
        "stable_user_principles": stable_principles,
        "current_phase": current_phase,
        "recommended_next_step": recommended_next_step,
        "recommended_ai_route": recommended_ai_route,
        "ai_evidence": ai_evidence,
        "evidence_sources": evidence_sources,
        "unresolved_fields": unresolved_fields,
        "selected_task_evidence": selected_task_evidence,
        "active_external_blocks": active_external_blocks,
        "source": "derived",
        "source_path": str(portable_context_path) if portable_context_path.exists() else "multiple_sources",
        "updated_at": updated_at,
        "age_seconds": age_seconds,
        "stale_capable": stale_capable,
        "source_freshness": source_freshness,
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
                "updated_at": updated_at,
                "age_seconds": age_seconds,
                "stale_capable": True,
            }
        return {
            "status": "unavailable",
            "gpu_status": "unavailable",
            "source": "environment_self_model",
            "source_path": str(path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "gpu_status": "error",
            "source": "environment_self_model",
            "source_path": str(path),
        }


def _load_unresolved_fields(workspace: Path, environment_self_awareness_service: Any = None) -> list[str]:
    """Load unresolved fields from environment self-awareness service.
    
    Prefers fresh data from the live service if available, otherwise falls back
    to the persisted file. This ensures the surface reflects current unresolved
    signals including GPU degradation.
    """
    # Try to get fresh data from the live service first
    if environment_self_awareness_service is not None:
        try:
            current_model = environment_self_awareness_service.current_model()
            if hasattr(current_model, 'unresolved_fields'):
                return current_model.unresolved_fields
        except Exception:
            # Fall back to file if live service fails
            pass
    
    # Fallback: read from persisted file (stale-capable)
    path = workspace / "data" / "evolution" / "environment_self_model" / "latest.json"
    try:
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            unresolved = data.get("unresolved_fields", [])
            return unresolved if isinstance(unresolved, list) else []
        return []
    except Exception:
        return []


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
    if snapshot["human_vision_readout"].get("status") == "ok":
        sources.append(f"human_vision_readout:{snapshot['human_vision_readout']['source']}")
    if snapshot["source_confidence"].get("status") == "ok":
        sources.append(f"source_confidence:{snapshot['source_confidence']['source']}")
    if snapshot["gpu_health"].get("status") == "ok":
        sources.append(f"gpu_health:{snapshot['gpu_health']['source']}")

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

    lines.extend(["", "## Human Vision Readout"])
    hvr = snapshot.get("human_vision_readout", {})
    lines.append(f"- Status: {hvr.get('status', 'unknown')}")
    if hvr.get("status") == "ok":
        lines.append(f"- Project direction: {hvr.get('current_project_direction', 'UNRESOLVED')[:100]}")
        lines.append(f"- Current phase: {hvr.get('current_phase', 'UNRESOLVED')}")
        lines.append(f"- Recommended next step: {hvr.get('recommended_next_step', 'UNRESOLVED')[:100]}")
        lines.append(f"- Recommended AI route: {hvr.get('recommended_ai_route', 'UNRESOLVED')}")
        lines.append(f"- Evidence sources: {', '.join(hvr.get('evidence_sources', []))}")
        if hvr.get("unresolved_fields"):
            lines.append(f"- UNRESOLVED: {', '.join(hvr.get('unresolved_fields', []))}")
        lines.append(f"- Source: {hvr.get('source', 'unknown')}")

    lines.extend(["", "## Source Confidence"])
    sc = snapshot.get("source_confidence", {})
    lines.append(f"- Status: {sc.get('status', 'unknown')}")
    if sc.get("status") == "ok":
        lines.append(f"- Overall confidence: {sc.get('overall_confidence', 0.0):.2%}")
        lines.append(f"- Source: {sc.get('source', 'unknown')}")

    lines.extend(["", "## GPU Health"])
    gh = snapshot.get("gpu_health", {})
    lines.append(f"- Status: {gh.get('status', 'unknown')}")
    if gh.get("status") == "ok":
        lines.append(f"- GPU Status: {gh.get('gpu_status', 'unknown')}")
        lines.append(f"- GPU Name: {gh.get('gpu_name', 'N/A')}")
        if gh.get('gpu_status') == 'degraded':
            lines.append(f"- Degradation Reason: {gh.get('gpu_degradation_reason', 'N/A')}")
            lines.append(f"- Detail: {gh.get('gpu_degradation_detail', 'N/A')}")
        lines.append(f"- Source: {gh.get('source', 'unknown')}")

    lines.extend(["", "## Unresolved Fields"])
    unresolved = snapshot.get("unresolved_fields", [])
    if unresolved:
        for field in unresolved:
            lines.append(f"- {field}")
    else:
        lines.append("- None")

    lines.extend(["", "## Evidence Sources"])
    for source in snapshot.get("evidence_sources", []):
        lines.append(f"- {source}")

    return "\n".join(lines) + "\n"


def export_observatory_surface_contract(
    workspace_root: str | Path,
    *,
    self_examination_service: Any = None,
    world_model_service: Any = None,
    control_master_service: Any = None,
    experiment_lab: Any = None,
    environment_self_awareness_service: Any = None,
) -> dict[str, Any]:
    """Export a compact read-only surface contract for living interface.

    This is a derived, compact view of organism state designed for future
    UI consumption without introducing new authority, memory, or orchestration.

    It extracts the most relevant observability data from the full snapshot
    for display purposes: human vision, health, stability, learning, and
    confidence metrics.

    This is NOT a decision layer. It is purely for observability.
    This is NOT a single source of truth - it is a derived view.

    Args:
        workspace_root: Path to the IABV workspace root
        self_examination_service: Optional OperationalSelfExaminationService instance
        world_model_service: Optional WorldModelService instance
        control_master_service: Optional ControlMasterService instance
        experiment_lab: Optional ExperimentLab instance

    Returns:
        Compact surface contract dictionary with:
        - timestamp
        - workspace_root
        - human_vision (project direction, phase, next step, AI route)
        - organ_health (health metrics with temporal metadata)
        - stability (stability signals with temporal metadata)
        - learning (learning reuse with temporal metadata)
        - confidence (source confidence with temporal metadata)
        - evidence_sources (traceability)
        - unresolved_fields (missing evidence markers)
    """
    # Get the full snapshot first
    full_snapshot = export_organism_state_snapshot(
        workspace_root,
        self_examination_service=self_examination_service,
        world_model_service=world_model_service,
        control_master_service=control_master_service,
        experiment_lab=experiment_lab,
        environment_self_awareness_service=environment_self_awareness_service,
    )

    # Extract compact surface contract
    surface_contract = {
        "timestamp": full_snapshot["timestamp"],
        "workspace_root": full_snapshot["workspace_root"],
        "human_vision": _extract_human_vision_surface(full_snapshot.get("human_vision_readout", {})),
        "organ_health": _extract_health_surface(full_snapshot.get("organ_health_matrix", {})),
        "stability": _extract_stability_surface(full_snapshot.get("stability_signals", {})),
        "learning": _extract_learning_surface(full_snapshot.get("learning_reuse_summary", {})),
        "confidence": _extract_confidence_surface(full_snapshot.get("source_confidence", {})),
        "gpu_health": _extract_gpu_health_surface(full_snapshot.get("gpu_health", {})),
        "evidence_sources": full_snapshot.get("evidence_sources", []),
        "unresolved_fields": _extract_unresolved_fields(full_snapshot),
    }

    return surface_contract


def _extract_human_vision_surface(hvr: dict[str, Any]) -> dict[str, Any]:
    """Extract compact human vision data with temporal metadata."""
    if hvr.get("status") != "ok":
        return {
            "status": hvr.get("status", "unavailable"),
            "current_project_direction": "UNRESOLVED",
            "current_phase": "UNRESOLVED",
            "recommended_next_step": "UNRESOLVED",
            "recommended_ai_route": "UNRESOLVED",
            "source": hvr.get("source", "unknown"),
        }

    return {
        "status": hvr["status"],
        "current_project_direction": hvr.get("current_project_direction", "UNRESOLVED"),
        "current_phase": hvr.get("current_phase", "UNRESOLVED"),
        "recommended_next_step": hvr.get("recommended_next_step", "UNRESOLVED"),
        "recommended_ai_route": hvr.get("recommended_ai_route", "UNRESOLVED"),
        "evidence_sources": hvr.get("evidence_sources", []),
        "source": hvr.get("source", "derived"),
        "updated_at": hvr.get("updated_at"),
        "age_seconds": hvr.get("age_seconds"),
        "stale_capable": hvr.get("stale_capable", False),
        "source_freshness": hvr.get("source_freshness", {}),
        "selected_task_evidence": hvr.get("selected_task_evidence", {}),
        "active_external_blocks": hvr.get("active_external_blocks", []),
    }


def _extract_health_surface(health: dict[str, Any]) -> dict[str, Any]:
    """Extract compact organ health data with temporal metadata."""
    if health.get("status") != "ok":
        return {
            "status": health.get("status", "unavailable"),
            "overall_health": "UNRESOLVED",
            "source": health.get("source", "unknown"),
        }

    return {
        "status": health["status"],
        "overall_health": health.get("overall_health", "unknown"),
        "critical_findings_count": health.get("critical_findings_count", 0),
        "warning_findings_count": health.get("warning_findings_count", 0),
        "source": health.get("source", "derived"),
        "source_path": health.get("source_path"),
        "updated_at": health.get("updated_at"),
        "age_seconds": health.get("age_seconds"),
        "stale_capable": health.get("stale_capable", False),
    }


def _extract_stability_surface(stability: dict[str, Any]) -> dict[str, Any]:
    """Extract compact stability signals with temporal metadata."""
    if stability.get("status") != "ok":
        return {
            "status": stability.get("status", "unavailable"),
            "success_rate": 0.0,
            "source": stability.get("source", "unknown"),
        }

    return {
        "status": stability["status"],
        "success_rate": stability.get("success_rate", 0.0),
        "recent_runs_count": stability.get("recent_runs_count", 0),
        "source": stability.get("source", "derived"),
        "source_path": stability.get("source_path"),
        "updated_at": stability.get("updated_at"),
        "age_seconds": stability.get("age_seconds"),
        "stale_capable": stability.get("stale_capable", False),
    }


def _extract_learning_surface(learning: dict[str, Any]) -> dict[str, Any]:
    """Extract compact learning reuse data with temporal metadata."""
    if learning.get("status") != "ok":
        return {
            "status": learning.get("status", "unavailable"),
            "reuse_rate": 0.0,
            "source": learning.get("source", "unknown"),
        }

    return {
        "status": learning["status"],
        "total_runs": learning.get("total_runs", 0),
        "reused_patterns_count": learning.get("reused_patterns_count", 0),
        "reuse_rate": learning.get("reuse_rate", 0.0),
        "source": learning.get("source", "derived"),
        "source_path": learning.get("source_path"),
        "updated_at": learning.get("updated_at"),
        "age_seconds": learning.get("age_seconds"),
        "stale_capable": learning.get("stale_capable", False),
    }


def _extract_confidence_surface(confidence: dict[str, Any]) -> dict[str, Any]:
    """Extract compact source confidence data with temporal metadata."""
    if confidence.get("status") != "ok":
        return {
            "status": confidence.get("status", "unavailable"),
            "overall_confidence": 0.0,
            "source": confidence.get("source", "unknown"),
        }

    return {
        "status": confidence["status"],
        "overall_confidence": confidence.get("overall_confidence", 0.0),
        "source": confidence.get("source", "derived"),
        "source_path": confidence.get("source_path"),
        "updated_at": confidence.get("updated_at"),
        "age_seconds": confidence.get("age_seconds"),
        "stale_capable": confidence.get("stale_capable", False),
    }


def _extract_gpu_health_surface(gpu_health: dict[str, Any]) -> dict[str, Any]:
    """Extract compact GPU health data with temporal metadata."""
    if gpu_health.get("status") != "ok":
        return {
            "status": gpu_health.get("status", "unavailable"),
            "gpu_status": "unavailable",
            "source": gpu_health.get("source", "unknown"),
        }

    return {
        "status": gpu_health["status"],
        "gpu_status": gpu_health.get("gpu_status", "unknown"),
        "gpu_name": gpu_health.get("gpu_name", ""),
        "gpu_driver": gpu_health.get("gpu_driver", ""),
        "gpu_memory_total_mb": gpu_health.get("gpu_memory_total_mb"),
        "gpu_memory_free_mb": gpu_health.get("gpu_memory_free_mb"),
        "gpu_temperature_c": gpu_health.get("gpu_temperature_c"),
        "gpu_utilization_pct": gpu_health.get("gpu_utilization_pct"),
        "gpu_degradation_reason": gpu_health.get("gpu_degradation_reason"),
        "gpu_degradation_detail": gpu_health.get("gpu_degradation_detail"),
        "source": gpu_health.get("source", "derived"),
        "source_path": gpu_health.get("source_path"),
        "updated_at": gpu_health.get("updated_at"),
        "age_seconds": gpu_health.get("age_seconds"),
        "stale_capable": gpu_health.get("stale_capable", False),
    }


def _extract_unresolved_fields(snapshot: dict[str, Any]) -> list[str]:
    """Extract all unresolved fields from snapshot sections."""
    unresolved = []

    # Include global unresolved fields from environment self-awareness (includes GPU degradation)
    global_unresolved = snapshot.get("unresolved_fields", [])
    if global_unresolved:
        unresolved.extend(global_unresolved)

    # Check human vision readout
    hvr = snapshot.get("human_vision_readout", {})
    if hvr.get("unresolved_fields"):
        unresolved.extend(hvr["unresolved_fields"])

    # Check if any section is unavailable
    for section_name in ["organ_health_matrix", "stability_signals", "learning_reuse_summary", "source_confidence"]:
        section = snapshot.get(section_name, {})
        if section.get("status") in ["unavailable", "error"]:
            unresolved.append(f"{section_name}:{section.get('status', 'unknown')}")

    return unresolved
