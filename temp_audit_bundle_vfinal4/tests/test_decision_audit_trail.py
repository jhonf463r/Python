"""Tests for DecisionAuditTrail — recording, trend analysis and reporting."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from iabv_v15.services.evolution.decision_audit_trail import (
    DecisionAuditTrail,
    DecisionOutcome,
    DecisionPhase,
    DecisionRecord,
    ProviderTrend,
)


class TestDecisionRecord:
    def test_defaults(self) -> None:
        r = DecisionRecord(provider_id='groq')
        assert r.provider_id == 'groq'
        assert r.outcome == DecisionOutcome.SUCCESS
        assert r.phase == DecisionPhase.PLAN_GENERATION
        assert r.latency_ms == 0.0

    def test_to_dict(self) -> None:
        r = DecisionRecord(
            provider_id='gemini', model_used='gemini-2.0-flash',
            outcome=DecisionOutcome.RATE_LIMITED, latency_ms=350.0,
            user_goal='fix wplay', confidence=0.85,
            steps_total=4, steps_completed=3, steps_failed=1,
        )
        d = r.to_dict()
        assert d['provider_id'] == 'gemini'
        assert d['outcome'] == 'rate_limited'
        assert d['confidence'] == 0.85
        assert d['steps_failed'] == 1
        assert 'timestamp_utc' in d

    def test_fallback_chain(self) -> None:
        r = DecisionRecord(
            provider_id='ollama_local',
            outcome=DecisionOutcome.FALLBACK_USED,
            fallback_chain=['gemini_failed', 'groq_failed', 'ollama'],
        )
        assert len(r.fallback_chain) == 3


class TestDecisionOutcome:
    def test_all_values(self) -> None:
        assert DecisionOutcome.SUCCESS.value == 'success'
        assert DecisionOutcome.PARTIAL.value == 'partial'
        assert DecisionOutcome.FAILED.value == 'failed'
        assert DecisionOutcome.RATE_LIMITED.value == 'rate_limited'
        assert DecisionOutcome.TIMEOUT.value == 'timeout'
        assert DecisionOutcome.FALLBACK_USED.value == 'fallback_used'
        assert DecisionOutcome.REJECTED_BY_USER.value == 'rejected_by_user'


class TestDecisionPhase:
    def test_all_values(self) -> None:
        assert DecisionPhase.PROVIDER_SELECTION.value == 'provider_selection'
        assert DecisionPhase.PLAN_GENERATION.value == 'plan_generation'
        assert DecisionPhase.PLAN_EXECUTION.value == 'plan_execution'
        assert DecisionPhase.KEY_VALIDATION.value == 'key_validation'


class TestRecordAndLoad:
    def test_record_creates_file(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        record = DecisionRecord(
            provider_id='groq', outcome=DecisionOutcome.SUCCESS,
            latency_ms=200.0, confidence=0.9,
        )
        trail.record(record)
        log_path = tmp_path / 'evolution' / 'decision_audit' / 'decisions.jsonl'
        assert log_path.exists()
        entry = json.loads(log_path.read_text().strip())
        assert entry['provider_id'] == 'groq'
        assert entry['outcome'] == 'success'

    def test_load_recent(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        for i in range(5):
            trail.record(DecisionRecord(
                provider_id='groq' if i % 2 == 0 else 'gemini',
                outcome=DecisionOutcome.SUCCESS,
                latency_ms=100 + i * 50,
            ))
        entries = trail.load_recent(10)
        assert len(entries) == 5

    def test_load_recent_with_limit(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        for i in range(10):
            trail.record(DecisionRecord(provider_id='groq'))
        entries = trail.load_recent(3)
        assert len(entries) == 3

    def test_load_empty(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        entries = trail.load_recent()
        assert entries == []


class TestProviderTrends:
    def test_basic_trend(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        for _ in range(8):
            trail.record(DecisionRecord(
                provider_id='groq', outcome=DecisionOutcome.SUCCESS, latency_ms=150,
            ))
        for _ in range(2):
            trail.record(DecisionRecord(
                provider_id='groq', outcome=DecisionOutcome.FAILED, latency_ms=0,
            ))
        trends = trail.analyze_provider_trends()
        assert len(trends) == 1
        t = trends[0]
        assert t.provider_id == 'groq'
        assert t.total_decisions == 10
        assert t.success_count == 8
        assert t.failure_count == 2
        assert t.success_rate == 0.8

    def test_multiple_providers(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        for _ in range(5):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.SUCCESS, latency_ms=100))
        for _ in range(3):
            trail.record(DecisionRecord(provider_id='gemini', outcome=DecisionOutcome.SUCCESS, latency_ms=300))
        for _ in range(2):
            trail.record(DecisionRecord(provider_id='gemini', outcome=DecisionOutcome.RATE_LIMITED))
        trends = trail.analyze_provider_trends()
        assert len(trends) == 2
        # Sorted by success rate desc
        assert trends[0].provider_id == 'groq'
        assert trends[0].success_rate == 1.0
        assert trends[1].provider_id == 'gemini'

    def test_trend_direction_improving(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        # First half: mostly failures
        for _ in range(4):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.FAILED))
        # Second half: mostly successes
        for _ in range(4):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.SUCCESS))
        trends = trail.analyze_provider_trends()
        assert trends[0].trend_direction == 'improving'

    def test_trend_direction_degrading(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        # First half: mostly successes
        for _ in range(4):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.SUCCESS))
        # Second half: mostly failures
        for _ in range(4):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.FAILED))
        trends = trail.analyze_provider_trends()
        assert trends[0].trend_direction == 'degrading'

    def test_empty_trends(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        trends = trail.analyze_provider_trends()
        assert trends == []


class TestSelfExaminationSummary:
    def test_no_data(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        summary = trail.self_examination_summary()
        assert summary['status'] == 'no_data'
        assert summary['health_score'] == 0.0

    def test_with_data(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        for _ in range(7):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.SUCCESS, latency_ms=100))
        for _ in range(3):
            trail.record(DecisionRecord(provider_id='groq', outcome=DecisionOutcome.FAILED))
        summary = trail.self_examination_summary()
        assert summary['status'] == 'analyzed'
        assert summary['health_score'] == 0.7
        assert summary['total_decisions'] == 10
        assert summary['best_provider'] is not None


class TestFormatChatReport:
    def test_no_data_report(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        report = trail.format_chat_report()
        assert 'No hay decisiones' in report

    def test_report_with_data(self, tmp_path: Path) -> None:
        trail = DecisionAuditTrail(data_root=tmp_path)
        for _ in range(5):
            trail.record(DecisionRecord(
                provider_id='groq', outcome=DecisionOutcome.SUCCESS,
                latency_ms=150, confidence=0.85,
            ))
        report = trail.format_chat_report()
        assert 'groq' in report
        assert 'Audit Trail' in report
        assert 'exito' in report.lower() or 'éxito' in report.lower()


class TestProviderTrendModel:
    def test_to_dict(self) -> None:
        t = ProviderTrend(
            provider_id='groq', total_decisions=10,
            success_count=8, failure_count=2,
            avg_latency_ms=150.5, success_rate=0.8,
            trend_direction='improving',
        )
        d = t.to_dict()
        assert d['provider_id'] == 'groq'
        assert d['success_rate'] == 0.8
        assert d['trend_direction'] == 'improving'
