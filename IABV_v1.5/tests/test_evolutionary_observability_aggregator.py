"""Tests for EvolutionaryObservabilityAggregator — read-only organism snapshot."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import pytest

from iabv_v15.services.evolution.evolutionary_observability_aggregator import (
    EvolutionaryObservabilityAggregator,
    OrganismHealthSnapshot,
)


# ------------------------------------------------------------------
# Fakes — each mimics the real service's read API
# ------------------------------------------------------------------

class FakeDecisionAuditTrail:
    def __init__(
        self,
        summary: dict[str, Any] | None = None,
        recent: list[dict[str, Any]] | None = None,
    ):
        self._summary = summary or {}
        self._recent = recent or []

    def self_examination_summary(self) -> dict[str, Any]:
        return self._summary

    def load_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._recent[:limit]


class FakeSelfExaminationService:
    def __init__(self, review: Any = None):
        self._review = review

    def current_review(self, *, refresh: bool = False) -> Any:
        return self._review


class FakePortableContextService:
    def __init__(self, package: Any = None):
        self._package = package

    def current_package(self) -> Any:
        return self._package


class FakeValidationCycle:
    def __init__(self, snapshot: Any = None):
        self._snapshot = snapshot

    def current_snapshot(self) -> Any:
        return self._snapshot


class FakeWorldModelService:
    def __init__(self, model: Any = None):
        self._model = model

    def current_model(self) -> Any:
        return self._model


class FakeControlMasterService:
    def __init__(self, state: Any = None):
        self._state = state

    def current_state(self) -> Any:
        return self._state


class FakeExperimentLabRepository:
    def __init__(self, runs: list | None = None):
        self._runs = runs or []

    def list_runs(self, limit: int = 20, **kwargs) -> list:
        return self._runs[:limit]


class _DictLike:
    """Minimal object that supports model_dump(mode='json')."""
    def __init__(self, data: dict[str, Any]):
        self._data = data
        for k, v in data.items():
            setattr(self, k, v)

    def model_dump(self, mode: str = 'json') -> dict[str, Any]:
        return dict(self._data)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestAggregatorEmptyServices:
    """With all services None, produces a valid snapshot with defaults."""

    def test_all_none(self):
        agg = EvolutionaryObservabilityAggregator()
        snap = agg.snapshot()

        assert isinstance(snap, OrganismHealthSnapshot)
        assert snap.timestamp_utc != ""
        assert snap.health_score == 0.0
        assert snap.cognitive_pressure == "CRITICAL"  # health=0.0 → CRITICAL
        assert snap.network_status == "unknown"
        assert snap.context_freshness_seconds == -1
        assert snap.active_experiments == 0
        assert snap.active_anomalies == 0
        assert snap.recent_decisions_count == 0
        assert snap.recent_decisions_success_rate == 0.0
        assert snap.last_learning_seconds_ago == -1
        assert snap.world_model_summary == {}
        assert snap.oses_summary == {}
        assert snap.decision_audit_summary == {}
        assert snap.portable_context_summary == {}
        assert snap.validation_cycle_summary == {}
        assert snap.control_master_summary == {}
        assert snap.active_alerts == []
        assert snap.recent_events == []

    def test_snapshot_has_timestamp(self):
        agg = EvolutionaryObservabilityAggregator()
        snap = agg.snapshot()
        # Parseable ISO timestamp
        dt = datetime.fromisoformat(snap.timestamp_utc)
        assert dt.year >= 2026


class TestAggregatorHealthScore:
    """Health score is derived from DecisionAuditTrail."""

    def test_health_score_from_audit(self):
        dat = FakeDecisionAuditTrail(summary={
            "status": "analyzed",
            "health_score": 0.87,
            "total_decisions": 40,
            "overall_trend": "stable",
            "recommendations": [],
            "trends": [],
        })
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)
        snap = agg.snapshot()

        assert snap.health_score == pytest.approx(0.87)
        assert snap.recent_decisions_count == 40
        assert snap.cognitive_pressure == "NORMAL"

    def test_low_health_triggers_critical_pressure(self):
        dat = FakeDecisionAuditTrail(summary={
            "health_score": 0.2,
            "total_decisions": 10,
        })
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)
        snap = agg.snapshot()

        assert snap.health_score == pytest.approx(0.2)
        assert snap.cognitive_pressure == "CRITICAL"


class TestAggregatorAnomaliesFromOSES:
    """Anomalies count comes from OSES findings with severity >= high."""

    def test_no_findings(self):
        oses = FakeSelfExaminationService(review=_DictLike({
            "summary": "All good",
            "status": "complete",
            "findings": [],
            "recurring_issues": [],
            "recommended_adjustments": [],
        }))
        agg = EvolutionaryObservabilityAggregator(self_examination_service=oses)
        snap = agg.snapshot()

        assert snap.active_anomalies == 0
        # health_score=0.0 (no DAT) → CRITICAL
        assert snap.cognitive_pressure == "CRITICAL"

    def test_high_severity_findings_counted(self):
        oses = FakeSelfExaminationService(review=_DictLike({
            "summary": "Issues found",
            "status": "partial",
            "findings": [
                {"title": "low issue", "severity": "low"},
                {"title": "high issue", "severity": "high"},
                {"title": "critical issue", "severity": "critical"},
                {"title": "medium issue", "severity": "medium"},
            ],
            "recurring_issues": [],
            "recommended_adjustments": [],
        }))
        agg = EvolutionaryObservabilityAggregator(self_examination_service=oses)
        snap = agg.snapshot()

        assert snap.active_anomalies == 2  # high + critical
        # health_score=0.0 (no DAT) + 2 anomalies → CRITICAL
        assert snap.cognitive_pressure == "CRITICAL"

    def test_three_anomalies_trigger_critical(self):
        oses = FakeSelfExaminationService(review=_DictLike({
            "summary": "Bad",
            "status": "partial",
            "findings": [
                {"title": "a", "severity": "high"},
                {"title": "b", "severity": "high"},
                {"title": "c", "severity": "critical"},
            ],
            "recurring_issues": [],
            "recommended_adjustments": [],
        }))
        agg = EvolutionaryObservabilityAggregator(self_examination_service=oses)
        snap = agg.snapshot()

        assert snap.active_anomalies == 3
        assert snap.cognitive_pressure == "CRITICAL"


class TestAggregatorContextFreshness:
    """Context freshness measures seconds since last PCS update."""

    def test_fresh_context(self):
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        pcs = FakePortableContextService(package=_DictLike({
            "package_id": "test",
            "summary": "test",
            "created_at_utc": recent,
            "updated_at_utc": recent,
        }))
        agg = EvolutionaryObservabilityAggregator(portable_context_service=pcs)
        snap = agg.snapshot()

        assert 200 < snap.context_freshness_seconds < 400  # ~300s = 5 min

    def test_stale_context(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        pcs = FakePortableContextService(package=_DictLike({
            "package_id": "test",
            "summary": "test",
            "created_at_utc": old,
            "updated_at_utc": old,
        }))
        agg = EvolutionaryObservabilityAggregator(portable_context_service=pcs)
        snap = agg.snapshot()

        assert snap.context_freshness_seconds > 7000  # > ~2h


class TestAggregatorRecentEvents:
    """Recent events are unified from multiple sources."""

    def test_decision_events_included(self):
        dat = FakeDecisionAuditTrail(
            summary={"health_score": 0.9, "total_decisions": 5},
            recent=[
                {
                    "decision_id": "d1",
                    "timestamp_utc": "2026-05-14T00:00:00Z",
                    "phase": "plan_generation",
                    "provider_id": "groq",
                    "outcome": "success",
                },
                {
                    "decision_id": "d2",
                    "timestamp_utc": "2026-05-14T00:01:00Z",
                    "phase": "execution",
                    "provider_id": "ollama",
                    "outcome": "failed",
                },
            ],
        )
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)
        snap = agg.snapshot()

        decision_events = [e for e in snap.recent_events if e["kind"] == "decision"]
        assert len(decision_events) == 2

        failed = [e for e in decision_events if e["severity"] == "warning"]
        assert len(failed) == 1
        assert "ollama" in failed[0]["summary"]

    def test_oses_findings_as_anomaly_events(self):
        oses = FakeSelfExaminationService(review=_DictLike({
            "summary": "test",
            "status": "partial",
            "findings": [
                {"title": "latency_spike", "severity": "high", "summary": "Spike detected"},
            ],
            "recurring_issues": [
                {"title": "light_checks_warning", "severity": "medium", "summary": "Repeats 10x"},
            ],
            "recommended_adjustments": [],
        }))
        agg = EvolutionaryObservabilityAggregator(self_examination_service=oses)
        snap = agg.snapshot()

        anomaly_events = [e for e in snap.recent_events if e["kind"] == "anomaly"]
        assert len(anomaly_events) == 2

    def test_events_sorted_newest_first(self):
        dat = FakeDecisionAuditTrail(
            summary={},
            recent=[
                {"timestamp_utc": "2026-05-14T00:00:00Z", "phase": "a", "provider_id": "x", "outcome": "success"},
                {"timestamp_utc": "2026-05-14T02:00:00Z", "phase": "b", "provider_id": "y", "outcome": "success"},
                {"timestamp_utc": "2026-05-14T01:00:00Z", "phase": "c", "provider_id": "z", "outcome": "success"},
            ],
        )
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)
        snap = agg.snapshot()

        timestamps = [e["timestamp_utc"] for e in snap.recent_events if e.get("timestamp_utc")]
        assert timestamps == sorted(timestamps, reverse=True)


class TestAggregatorAlerts:
    """Alerts are collected from OSES adjustments, DAT recommendations, WM blocks."""

    def test_oses_adjustments_become_alerts(self):
        oses = FakeSelfExaminationService(review=_DictLike({
            "summary": "test",
            "status": "partial",
            "findings": [],
            "recurring_issues": [],
            "recommended_adjustments": [
                {"title": "Rotate groq key", "severity": "high", "recommended_change": "Key expiring soon"},
            ],
        }))
        agg = EvolutionaryObservabilityAggregator(self_examination_service=oses)
        snap = agg.snapshot()

        assert len(snap.active_alerts) == 1
        assert snap.active_alerts[0]["source"] == "self_examination"
        assert snap.active_alerts[0]["title"] == "Rotate groq key"

    def test_dat_recommendations_become_alerts(self):
        dat = FakeDecisionAuditTrail(summary={
            "health_score": 0.5,
            "total_decisions": 10,
            "recommendations": [
                "groq degrading, consider rotating key",
            ],
        })
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)
        snap = agg.snapshot()

        dat_alerts = [a for a in snap.active_alerts if a["source"] == "decision_audit"]
        assert len(dat_alerts) == 1

    def test_world_model_blocks_become_alerts(self):
        wm = FakeWorldModelService(model=_DictLike({
            "window_count": 3,
            "network_status": {"latency_ms": 23.0},
            "operational_blocks": [
                {"title": "API quota exhausted", "severity": "high", "detail": "Groq 429"},
            ],
        }))
        agg = EvolutionaryObservabilityAggregator(world_model_service=wm)
        snap = agg.snapshot()

        wm_alerts = [a for a in snap.active_alerts if a["source"] == "world_model"]
        assert len(wm_alerts) == 1
        assert wm_alerts[0]["title"] == "API quota exhausted"


class TestAggregatorNetworkStatus:
    """Network status derived from WorldModel."""

    def test_network_ok(self):
        wm = FakeWorldModelService(model=_DictLike({
            "network_status": {"latency_ms": 23.0},
        }))
        agg = EvolutionaryObservabilityAggregator(world_model_service=wm)
        snap = agg.snapshot()

        assert snap.network_status == "ok"
        assert snap.network_latency_ms == pytest.approx(23.0)

    def test_network_degraded(self):
        wm = FakeWorldModelService(model=_DictLike({
            "network_status": {"latency_ms": 500.0, "error": "timeout"},
        }))
        agg = EvolutionaryObservabilityAggregator(world_model_service=wm)
        snap = agg.snapshot()

        assert snap.network_status == "degraded"

    def test_network_string_status(self):
        wm = FakeWorldModelService(model=_DictLike({
            "network_status": "offline",
        }))
        agg = EvolutionaryObservabilityAggregator(world_model_service=wm)
        snap = agg.snapshot()

        assert snap.network_status == "offline"


class TestAggregatorCache:
    """Snapshot is cached for TTL seconds."""

    def test_cached_within_ttl(self):
        dat = FakeDecisionAuditTrail(summary={"health_score": 0.9, "total_decisions": 5})
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)

        snap1 = agg.snapshot()
        snap2 = agg.snapshot()

        assert snap1 is snap2  # same object = cached

    def test_force_refresh_bypasses_cache(self):
        dat = FakeDecisionAuditTrail(summary={"health_score": 0.9, "total_decisions": 5})
        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=dat)

        snap1 = agg.snapshot()
        snap2 = agg.snapshot(force_refresh=True)

        assert snap1 is not snap2  # different objects


class TestAggregatorNoSideEffects:
    """Aggregator must not call any write/mutate methods on services."""

    def test_no_writes_on_services(self):
        class TrackingDAT:
            def __init__(self):
                self.calls = []

            def self_examination_summary(self) -> dict:
                self.calls.append("self_examination_summary")
                return {"health_score": 0.5, "total_decisions": 1}

            def load_recent(self, limit: int = 100) -> list:
                self.calls.append("load_recent")
                return []

            def record(self, *args, **kwargs):
                self.calls.append("record")  # must NOT be called

        class TrackingOSES:
            def __init__(self):
                self.calls = []

            def current_review(self, *, refresh: bool = False) -> None:
                self.calls.append(f"current_review(refresh={refresh})")
                return None

            def force_refresh(self):
                self.calls.append("force_refresh")

        dat = TrackingDAT()
        oses = TrackingOSES()
        agg = EvolutionaryObservabilityAggregator(
            decision_audit_trail=dat,
            self_examination_service=oses,
        )
        agg.snapshot()

        assert "record" not in dat.calls
        assert "force_refresh" not in oses.calls
        # Only read methods should be called
        assert set(dat.calls) <= {"self_examination_summary", "load_recent"}


class TestAggregatorServiceErrors:
    """If a service throws, the aggregator gracefully degrades."""

    def test_dat_error_produces_error_summary(self):
        class BrokenDAT:
            def self_examination_summary(self):
                raise RuntimeError("DB corrupt")
            def load_recent(self, limit=100):
                raise RuntimeError("DB corrupt")

        agg = EvolutionaryObservabilityAggregator(decision_audit_trail=BrokenDAT())
        snap = agg.snapshot()

        assert snap.decision_audit_summary.get("status") == "error"
        assert snap.health_score == 0.0  # graceful default

    def test_oses_error_produces_error_summary(self):
        class BrokenOSES:
            def current_review(self, **kwargs):
                raise RuntimeError("crash")

        agg = EvolutionaryObservabilityAggregator(self_examination_service=BrokenOSES())
        snap = agg.snapshot()

        assert snap.oses_summary.get("status") == "error"

    def test_wm_error_graceful(self):
        class BrokenWM:
            def current_model(self):
                raise RuntimeError("Win32 not available")

        agg = EvolutionaryObservabilityAggregator(world_model_service=BrokenWM())
        snap = agg.snapshot()

        assert snap.world_model_summary == {}
        assert snap.network_status == "unknown"


class TestAggregatorValidationCycle:
    """Validation cycle snapshot is forwarded."""

    def test_dict_snapshot(self):
        vcs = FakeValidationCycle(snapshot={
            "status": "running",
            "active_experiments": 3,
            "pending_promotions": 1,
        })
        agg = EvolutionaryObservabilityAggregator(autonomous_validation_cycle=vcs)
        snap = agg.snapshot()

        assert snap.validation_cycle_summary["status"] == "running"
        assert snap.active_experiments == 3

    def test_none_snapshot(self):
        vcs = FakeValidationCycle(snapshot=None)
        agg = EvolutionaryObservabilityAggregator(autonomous_validation_cycle=vcs)
        snap = agg.snapshot()

        assert snap.validation_cycle_summary.get("status") == "no_data"


class TestAggregatorControlMaster:
    """Control master state is forwarded when available."""

    def test_control_master_with_model_dump(self):
        cms = FakeControlMasterService(state=_DictLike({
            "objectives": [{"id": "obj1", "status": "active"}],
            "backlog": [],
            "risks": [],
        }))
        agg = EvolutionaryObservabilityAggregator(control_master_service=cms)
        snap = agg.snapshot()

        assert "objectives" in snap.control_master_summary


class TestAggregatorExperimentLab:
    """Last learning time from experiment lab runs."""

    def test_last_learning_from_recent_run(self):
        recent = (datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat()
        run = _DictLike({"created_at_utc": recent, "run_id": "r1"})
        lab = FakeExperimentLabRepository(runs=[run])
        agg = EvolutionaryObservabilityAggregator(experiment_lab_repository=lab)
        snap = agg.snapshot()

        assert 600 < snap.last_learning_seconds_ago < 800  # ~720s = 12 min
