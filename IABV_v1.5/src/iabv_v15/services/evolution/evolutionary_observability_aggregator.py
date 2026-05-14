"""EvolutionaryObservabilityAggregator — read-only snapshot of the whole organism.

Pulls from existing services to produce a unified ``OrganismHealthSnapshot``
suitable for the Centro de Control Evolutivo UI.

This class:
- Does NOT decide routes, trigger actions, or mutate state.
- Does NOT duplicate any service. It only reads from them.
- Does NOT replace CentroVivoViewModel — it provides a richer, typed
  snapshot that any ViewModel or diagnostic tool can consume.

Respects P1-P4 closed layers and AGENTS.md constraints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OrganismHealthSnapshot:
    """Unified health snapshot of the digital organism."""

    timestamp_utc: str = ""

    # Vital signs
    health_score: float = 0.0
    cognitive_pressure: str = "UNKNOWN"
    network_status: str = "unknown"
    network_latency_ms: float = 0.0
    context_freshness_seconds: int = -1

    # Counters
    active_experiments: int = 0
    active_anomalies: int = 0
    recent_decisions_count: int = 0
    recent_decisions_success_rate: float = 0.0
    last_learning_seconds_ago: int = -1

    # Sub-snapshots
    world_model_summary: dict[str, Any] = field(default_factory=dict)
    oses_summary: dict[str, Any] = field(default_factory=dict)
    decision_audit_summary: dict[str, Any] = field(default_factory=dict)
    portable_context_summary: dict[str, Any] = field(default_factory=dict)
    validation_cycle_summary: dict[str, Any] = field(default_factory=dict)
    control_master_summary: dict[str, Any] = field(default_factory=dict)

    # Active alerts
    active_alerts: list[dict[str, Any]] = field(default_factory=list)

    # Recent unified events
    recent_events: list[dict[str, Any]] = field(default_factory=list)


class EvolutionaryObservabilityAggregator:
    """Aggregates evolution data from existing services into a single snapshot.

    All dependencies are optional. Missing services produce empty/default
    sections — the aggregator never fails because a service is not wired.
    """

    _CACHE_TTL_SECONDS = 10.0

    def __init__(
        self,
        *,
        decision_audit_trail: Any | None = None,
        self_examination_service: Any | None = None,
        portable_context_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        world_model_service: Any | None = None,
        control_master_service: Any | None = None,
        experiment_lab_repository: Any | None = None,
    ) -> None:
        self.decision_audit_trail = decision_audit_trail
        self.self_examination_service = self_examination_service
        self.portable_context_service = portable_context_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.world_model_service = world_model_service
        self.control_master_service = control_master_service
        self.experiment_lab_repository = experiment_lab_repository
        self._cached_snapshot: OrganismHealthSnapshot | None = None
        self._cache_monotonic: float = 0.0

    def snapshot(self, *, force_refresh: bool = False) -> OrganismHealthSnapshot:
        """Produce a unified snapshot. Cached for ``_CACHE_TTL_SECONDS``."""
        now_mono = time.monotonic()
        if (
            not force_refresh
            and self._cached_snapshot is not None
            and (now_mono - self._cache_monotonic) < self._CACHE_TTL_SECONDS
        ):
            return self._cached_snapshot

        snap = OrganismHealthSnapshot(
            timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        snap.decision_audit_summary = self._read_decision_audit()
        snap.oses_summary = self._read_oses()
        snap.portable_context_summary = self._read_portable_context()
        snap.validation_cycle_summary = self._read_validation_cycle()
        snap.world_model_summary = self._read_world_model()
        snap.control_master_summary = self._read_control_master()

        self._compute_vital_signs(snap)
        snap.active_alerts = self._collect_alerts(snap)
        snap.recent_events = self._collect_recent_events(snap)

        self._cached_snapshot = snap
        self._cache_monotonic = now_mono
        return snap

    # ------------------------------------------------------------------
    # Service readers — each returns {} on failure
    # ------------------------------------------------------------------

    def _read_decision_audit(self) -> dict[str, Any]:
        svc = self.decision_audit_trail
        if svc is None:
            return {}
        try:
            return svc.self_examination_summary()
        except Exception:
            return {"status": "error", "message": "Failed to read decision audit"}

    def _read_oses(self) -> dict[str, Any]:
        svc = self.self_examination_service
        if svc is None:
            return {}
        try:
            review = svc.current_review()
            if review is None:
                return {"status": "no_data"}
            if hasattr(review, "model_dump"):
                return review.model_dump(mode="json")
            dumped: dict[str, Any] = {}
            for attr in ("summary", "status", "findings", "recurring_issues",
                         "recommended_adjustments", "validated_improvements"):
                val = getattr(review, attr, None)
                if val is not None:
                    dumped[attr] = val
            return dumped
        except Exception:
            return {"status": "error"}

    def _read_portable_context(self) -> dict[str, Any]:
        svc = self.portable_context_service
        if svc is None:
            return {}
        try:
            pkg = svc.current_package()
            if pkg is None:
                return {"status": "no_data"}
            if hasattr(pkg, "model_dump"):
                return pkg.model_dump(mode="json")
            result: dict[str, Any] = {}
            for attr in ("package_id", "summary", "created_at_utc", "updated_at_utc", "sections"):
                val = getattr(pkg, attr, None)
                if val is not None:
                    result[attr] = val
            return result
        except Exception:
            return {"status": "error"}

    def _read_validation_cycle(self) -> dict[str, Any]:
        svc = self.autonomous_validation_cycle
        if svc is None:
            return {}
        try:
            snap = svc.current_snapshot()
            if snap is None:
                return {"status": "no_data"}
            if isinstance(snap, dict):
                return snap
            if hasattr(snap, "model_dump"):
                return snap.model_dump(mode="json")
            return {"status": str(getattr(snap, "status", "unknown"))}
        except Exception:
            return {"status": "error"}

    def _read_world_model(self) -> dict[str, Any]:
        svc = self.world_model_service
        if svc is None:
            return {}
        try:
            model = svc.current_model()
            if model is None:
                return {}
            if hasattr(model, "model_dump"):
                return model.model_dump(mode="json")
            result: dict[str, Any] = {}
            for attr in ("window_count", "focus_window", "network_status",
                         "operational_blocks", "tool_cards"):
                val = getattr(model, attr, None)
                if val is not None:
                    if hasattr(val, "model_dump"):
                        result[attr] = val.model_dump(mode="json")
                    else:
                        result[attr] = val
            return result
        except Exception:
            return {}

    def _read_control_master(self) -> dict[str, Any]:
        svc = self.control_master_service
        if svc is None:
            return {}
        try:
            state = svc.current_state()
            if state is None:
                return {}
            if hasattr(state, "model_dump"):
                return state.model_dump(mode="json")
            return {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Derived computations
    # ------------------------------------------------------------------

    def _compute_vital_signs(self, snap: OrganismHealthSnapshot) -> None:
        # Health score from decision audit
        das = snap.decision_audit_summary
        snap.health_score = float(das.get("health_score", 0.0))
        snap.recent_decisions_count = int(das.get("total_decisions", 0))
        snap.recent_decisions_success_rate = float(das.get("health_score", 0.0))

        # Network from world model
        wm = snap.world_model_summary
        net = wm.get("network_status")
        if isinstance(net, dict):
            latency = net.get("latency_ms")
            error = net.get("error", "")
            if error:
                snap.network_status = "degraded"
            elif latency is not None:
                snap.network_status = "ok"
                snap.network_latency_ms = float(latency)
            else:
                snap.network_status = "unknown"
        elif isinstance(net, str):
            snap.network_status = net
        else:
            snap.network_status = "unknown"

        # Context freshness from portable context
        pcs = snap.portable_context_summary
        updated = pcs.get("updated_at_utc") or pcs.get("created_at_utc")
        if updated:
            try:
                updated_str = str(updated)
                if updated_str.endswith("Z"):
                    updated_str = updated_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(updated_str)
                delta = datetime.now(timezone.utc) - dt
                snap.context_freshness_seconds = int(delta.total_seconds())
            except (ValueError, TypeError):
                pass

        # Anomalies from OSES
        oses = snap.oses_summary
        findings = oses.get("findings") or []
        high_findings = [
            f for f in findings
            if isinstance(f, dict) and f.get("severity") in ("high", "critical")
        ]
        snap.active_anomalies = len(high_findings)

        # Cognitive pressure heuristic
        if snap.active_anomalies >= 3 or snap.health_score < 0.3:
            snap.cognitive_pressure = "CRITICAL"
        elif snap.active_anomalies >= 1 or snap.health_score < 0.6:
            snap.cognitive_pressure = "HIGH"
        elif snap.health_score >= 0.8:
            snap.cognitive_pressure = "NORMAL"
        else:
            snap.cognitive_pressure = "MODERATE"

        # Active experiments
        vcs = snap.validation_cycle_summary
        snap.active_experiments = int(vcs.get("active_experiments", 0))

        # Last learning
        if self.experiment_lab_repository is not None:
            try:
                runs = self.experiment_lab_repository.list_runs(limit=1)
                if runs:
                    last_run = runs[0]
                    created = getattr(last_run, "created_at_utc", None) or (
                        last_run.get("created_at_utc") if isinstance(last_run, dict) else None
                    )
                    if created:
                        created_str = str(created)
                        if created_str.endswith("Z"):
                            created_str = created_str[:-1] + "+00:00"
                        dt = datetime.fromisoformat(created_str)
                        delta = datetime.now(timezone.utc) - dt
                        snap.last_learning_seconds_ago = int(delta.total_seconds())
            except Exception:
                pass

    def _collect_alerts(self, snap: OrganismHealthSnapshot) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        # From OSES recommended adjustments
        oses = snap.oses_summary
        for adj in (oses.get("recommended_adjustments") or []):
            if not isinstance(adj, dict):
                continue
            alerts.append({
                "source": "self_examination",
                "severity": adj.get("severity", "medium"),
                "title": adj.get("title", ""),
                "detail": adj.get("recommended_change", ""),
            })

        # From decision audit recommendations
        das = snap.decision_audit_summary
        for rec in (das.get("recommendations") or []):
            alerts.append({
                "source": "decision_audit",
                "severity": "medium",
                "title": str(rec)[:80],
                "detail": str(rec),
            })

        # From world model operational blocks
        wm = snap.world_model_summary
        for block in (wm.get("operational_blocks") or []):
            if isinstance(block, dict):
                alerts.append({
                    "source": "world_model",
                    "severity": block.get("severity", "medium"),
                    "title": block.get("title", "Blocker"),
                    "detail": block.get("detail", ""),
                })

        return alerts

    def _collect_recent_events(self, snap: OrganismHealthSnapshot) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        # Decision events from audit trail
        if self.decision_audit_trail is not None:
            try:
                entries = self.decision_audit_trail.load_recent(limit=20)
                for entry in entries:
                    events.append({
                        "kind": "decision",
                        "timestamp_utc": entry.get("timestamp_utc", ""),
                        "source": "DecisionAuditTrail",
                        "summary": (
                            f"{entry.get('phase', '?')}: "
                            f"{entry.get('provider_id', '?')} → "
                            f"{entry.get('outcome', '?')}"
                        ),
                        "severity": "warning" if entry.get("outcome") != "success" else "info",
                    })
            except Exception:
                pass

        # OSES findings
        for finding in (snap.oses_summary.get("findings") or []):
            if isinstance(finding, dict):
                events.append({
                    "kind": "anomaly",
                    "timestamp_utc": finding.get("detected_at", ""),
                    "source": "OSES",
                    "summary": finding.get("summary", finding.get("title", "")),
                    "severity": finding.get("severity", "medium"),
                })

        # OSES recurring issues
        for issue in (snap.oses_summary.get("recurring_issues") or []):
            if isinstance(issue, dict):
                events.append({
                    "kind": "anomaly",
                    "timestamp_utc": "",
                    "source": "OSES",
                    "summary": f"Recurrente: {issue.get('title', '')} ({issue.get('summary', '')})",
                    "severity": issue.get("severity", "medium"),
                })

        # Sort by timestamp descending (empty timestamps at end)
        events.sort(key=lambda e: e.get("timestamp_utc", ""), reverse=True)
        return events[:50]
