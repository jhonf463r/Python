"""Tests for CodeAuditTrail service."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from iabv_v15.services.evolution.code_audit_trail import (
    AuditEnvironment,
    AuditFinding,
    AuditRound,
    AuditSource,
    CodeAuditTrail,
    FindingSeverity,
    FindingStatus,
)

# AuditEnvironment is also used by TestAuditorPerformanceSummary


@pytest.fixture
def trail(tmp_path: Path) -> CodeAuditTrail:
    return CodeAuditTrail(data_root=tmp_path)


def _make_finding(**overrides) -> AuditFinding:
    defaults = dict(
        bug_id='R18-1',
        module_path='services/auto_correction_engine.py',
        category='wiring',
        title='ToolRegistry wrong constructor',
        description='Calls ToolRegistry(workspace_root=...) but constructor requires (repository, adapters)',
        impact='Deductive reasoning never sees available tools',
        severity=FindingSeverity.HIGH,
        status=FindingStatus.FIXED,
        fix_description='Added optional tool_registry parameter',
        pr_url='https://github.com/jhonf463r/Python/pull/244',
        pattern_tag='constructor_mismatch',
        needs_windows_verification=False,
        confidence=0.95,
    )
    defaults.update(overrides)
    return AuditFinding(**defaults)


def _make_round(**overrides) -> AuditRound:
    defaults = dict(
        round_number=18,
        auditor_name='devin',
        source=AuditSource.EXTERNAL_AGENT,
        environment=AuditEnvironment.LINUX_VM,
        modules_audited=['services/auto_correction_engine.py'],
        total_loc_audited=2134,
        findings=[_make_finding()],
        tests_added=5,
        tests_passed=5,
        tests_failed=0,
        pr_url='https://github.com/jhonf463r/Python/pull/244',
        ci_status='green',
    )
    defaults.update(overrides)
    return AuditRound(**defaults)


class TestAuditFinding:
    def test_to_dict_has_all_fields(self):
        f = _make_finding()
        d = f.to_dict()
        assert d['bug_id'] == 'R18-1'
        assert d['severity'] == 'high'
        assert d['status'] == 'fixed'
        assert d['pattern_tag'] == 'constructor_mismatch'
        assert d['confidence'] == 0.95
        assert isinstance(d['finding_id'], str)
        assert len(d['finding_id']) > 0

    def test_auto_generated_finding_id(self):
        f1 = _make_finding()
        f2 = _make_finding()
        assert f1.finding_id != f2.finding_id


class TestAuditRound:
    def test_to_dict_includes_findings(self):
        r = _make_round()
        d = r.to_dict()
        assert d['round_number'] == 18
        assert d['auditor_name'] == 'devin'
        assert d['source'] == 'external_agent'
        assert d['environment'] == 'linux_vm'
        assert d['findings_count'] == 1
        assert d['bugs_found'] == 1
        assert d['tests_added'] == 5

    def test_timestamp_auto_generated(self):
        r = _make_round()
        assert 'T' in r.timestamp_utc


class TestCodeAuditTrailPersistence:
    def test_record_and_load_round(self, trail: CodeAuditTrail):
        r = _make_round()
        trail.record_round(r)
        rounds = trail.load_rounds()
        assert len(rounds) == 1
        assert rounds[0]['round_number'] == 18
        assert rounds[0]['bugs_found'] == 1

    def test_multiple_rounds(self, trail: CodeAuditTrail):
        trail.record_round(_make_round(round_number=14))
        trail.record_round(_make_round(round_number=15))
        trail.record_round(_make_round(round_number=18))
        rounds = trail.load_rounds()
        assert len(rounds) == 3
        assert [r['round_number'] for r in rounds] == [14, 15, 18]

    def test_load_rounds_limit(self, trail: CodeAuditTrail):
        for i in range(5):
            trail.record_round(_make_round(round_number=i))
        rounds = trail.load_rounds(limit=2)
        assert len(rounds) == 2
        assert rounds[0]['round_number'] == 3

    def test_empty_trail(self, trail: CodeAuditTrail):
        assert trail.load_rounds() == []
        assert trail.load_all_findings() == []
        assert trail.pending_cross_verifications() == []

    def test_corrupt_line_resilience(self, trail: CodeAuditTrail):
        trail.record_round(_make_round(round_number=14))
        with open(trail._log_path, 'a', encoding='utf-8') as f:
            f.write('CORRUPT JSON LINE\n')
        trail.record_round(_make_round(round_number=15))
        rounds = trail.load_rounds()
        assert len(rounds) == 2
        assert rounds[0]['round_number'] == 14
        assert rounds[1]['round_number'] == 15


class TestRecordFindingConvenience:
    def test_record_finding_creates_round(self, trail: CodeAuditTrail):
        result = trail.record_finding(
            module_path='services/foo.py',
            title='Test bug',
            bug_id='T1',
            severity='high',
            status='fixed',
            auditor_name='devin',
            round_number=20,
        )
        assert result['bug_id'] == 'T1'
        assert result['title'] == 'Test bug'
        rounds = trail.load_rounds()
        assert len(rounds) == 1
        assert rounds[0]['round_number'] == 20


class TestLoadAllFindings:
    def test_flattens_findings_from_rounds(self, trail: CodeAuditTrail):
        f1 = _make_finding(bug_id='R14-1', pattern_tag='jsonl_resilience')
        f2 = _make_finding(bug_id='R15-1', pattern_tag='jsonl_resilience')
        f3 = _make_finding(bug_id='R18-1', pattern_tag='constructor_mismatch')
        trail.record_round(_make_round(round_number=14, findings=[f1]))
        trail.record_round(_make_round(round_number=15, findings=[f2]))
        trail.record_round(_make_round(round_number=18, findings=[f3]))
        findings = trail.load_all_findings()
        assert len(findings) == 3
        assert findings[0]['round_number'] == 14
        assert findings[2]['bug_id'] == 'R18-1'


class TestPendingCrossVerifications:
    def test_returns_windows_verification_needed(self, trail: CodeAuditTrail):
        f1 = _make_finding(needs_windows_verification=True, title='Win32 API test')
        f2 = _make_finding(needs_windows_verification=False)
        trail.record_round(_make_round(findings=[f1, f2]))
        pending = trail.pending_cross_verifications()
        assert len(pending) == 1
        assert pending[0]['title'] == 'Win32 API test'


class TestBugPatternAnalysis:
    def test_detects_recurring_pattern(self, trail: CodeAuditTrail):
        f1 = _make_finding(bug_id='R10-1', pattern_tag='jsonl_resilience', module_path='services/a.py')
        f2 = _make_finding(bug_id='R14-2', pattern_tag='jsonl_resilience', module_path='services/b.py')
        f3 = _make_finding(bug_id='R15-1', pattern_tag='jsonl_resilience', module_path='services/c.py')
        trail.record_round(_make_round(round_number=10, findings=[f1]))
        trail.record_round(_make_round(round_number=14, findings=[f2]))
        trail.record_round(_make_round(round_number=15, findings=[f3]))
        patterns = trail.analyze_bug_patterns()
        assert len(patterns) >= 1
        jsonl_pattern = next(p for p in patterns if p['pattern_tag'] == 'jsonl_resilience')
        assert jsonl_pattern['occurrences'] == 3
        assert len(jsonl_pattern['affected_modules']) == 3

    def test_empty_trail_no_patterns(self, trail: CodeAuditTrail):
        assert trail.analyze_bug_patterns() == []


class TestCoverageSummary:
    def test_full_summary(self, trail: CodeAuditTrail):
        trail.record_round(_make_round(round_number=14, auditor_name='devin'))
        trail.record_round(_make_round(round_number=15, auditor_name='devin'))
        summary = trail.audit_coverage_summary()
        assert summary['total_rounds'] == 2
        assert summary['total_loc_audited'] == 2134 * 2
        assert 'devin' in summary['auditors']
        assert summary['latest_round'] == 15

    def test_empty_summary(self, trail: CodeAuditTrail):
        summary = trail.audit_coverage_summary()
        assert summary['total_rounds'] == 0


class TestPortableContextSummary:
    def test_builds_compact_summary(self, trail: CodeAuditTrail):
        trail.record_round(_make_round(round_number=14))
        trail.record_round(_make_round(round_number=15))
        summary = trail.summary_for_portable_context()
        assert 'coverage' in summary
        assert 'recurring_patterns' in summary
        assert 'recent_rounds' in summary
        assert 'pending_cross_verifications' in summary
        assert len(summary['recent_rounds']) == 2


class TestOSESCrossReference:
    def test_returns_formatted_findings(self, trail: CodeAuditTrail):
        trail.record_round(_make_round())
        results = trail.findings_for_oses_cross_reference()
        assert len(results) == 1
        assert results[0]['auditor'] == 'devin'
        assert results[0]['source'] == 'external_agent'
        assert results[0]['environment'] == 'linux_vm'
        assert results[0]['pattern_tag'] == 'constructor_mismatch'


class TestAuditorPerformanceSummary:
    def test_single_auditor(self, trail: CodeAuditTrail):
        trail.record_round(_make_round(round_number=14, auditor_name='devin'))
        trail.record_round(_make_round(round_number=15, auditor_name='devin'))
        summary = trail.auditor_performance_summary()
        assert 'devin' in summary['auditors']
        devin = summary['auditors']['devin']
        assert devin['rounds'] == 2
        assert devin['bugs_found'] == 2
        assert len(summary['comparison']) == 1
        assert 'Solo devin' in summary['recommendation']

    def test_multiple_auditors_comparison(self, trail: CodeAuditTrail):
        f1 = _make_finding(bug_id='R14-1', pattern_tag='jsonl_resilience')
        f2 = _make_finding(bug_id='R14-2', pattern_tag='jsonl_resilience')
        f3 = _make_finding(bug_id='R18-1', pattern_tag='constructor_mismatch')
        trail.record_round(_make_round(
            round_number=14, auditor_name='devin',
            findings=[f1, f2], total_loc_audited=3000, tests_added=4,
        ))
        trail.record_round(_make_round(
            round_number=20, auditor_name='codex',
            findings=[f3], total_loc_audited=1500, tests_added=2,
        ))
        summary = trail.auditor_performance_summary()
        assert 'devin' in summary['auditors']
        assert 'codex' in summary['auditors']
        assert len(summary['comparison']) == 2
        assert summary['comparison'][0]['auditor'] == 'devin'
        assert summary['comparison'][0]['bugs_found'] == 2
        assert summary['comparison'][1]['auditor'] == 'codex'
        assert summary['comparison'][1]['bugs_found'] == 1
        assert 'devin' in summary['recommendation']

    def test_pattern_specialties(self, trail: CodeAuditTrail):
        f1 = _make_finding(pattern_tag='jsonl_resilience')
        f2 = _make_finding(pattern_tag='jsonl_resilience')
        f3 = _make_finding(pattern_tag='wiring')
        trail.record_round(_make_round(
            auditor_name='devin', findings=[f1, f2, f3],
        ))
        summary = trail.auditor_performance_summary()
        devin = summary['auditors']['devin']
        assert 'jsonl_resilience' in devin['pattern_specialties']
        assert devin['pattern_specialties']['jsonl_resilience'] == 2

    def test_environments_tracked(self, trail: CodeAuditTrail):
        trail.record_round(_make_round(
            auditor_name='devin',
            environment=AuditEnvironment.LINUX_VM,
        ))
        trail.record_round(_make_round(
            auditor_name='iabv_self',
            environment=AuditEnvironment.WINDOWS_NATIVE,
        ))
        summary = trail.auditor_performance_summary()
        assert 'linux_vm' in summary['auditors']['devin']['environments']
        assert 'windows_native' in summary['auditors']['iabv_self']['environments']

    def test_empty_trail(self, trail: CodeAuditTrail):
        summary = trail.auditor_performance_summary()
        assert summary['auditors'] == {}
        assert summary['comparison'] == []


class TestExperimentLabPublishing:
    def test_publishes_when_lab_available(self, trail: CodeAuditTrail, tmp_path):
        from unittest.mock import MagicMock
        mock_lab = MagicMock()
        mock_lab.record_outcome = MagicMock(return_value=(MagicMock(), MagicMock()))
        trail.experiment_lab = mock_lab

        trail.record_round(_make_round(round_number=18, auditor_name='devin'))

        mock_lab.record_outcome.assert_called_once()
        call_kwargs = mock_lab.record_outcome.call_args.kwargs
        assert call_kwargs['candidate_label'] == 'devin'
        assert call_kwargs['suite_name'] == 'code_audit'
        assert call_kwargs['metadata']['assistant_kind'] == 'devin'
        assert call_kwargs['metadata']['comparison_scope_key'] == 'code_audit'
        assert call_kwargs['metadata']['round_number'] == 18

    def test_skips_when_no_lab(self, trail: CodeAuditTrail):
        trail.experiment_lab = None
        trail.record_round(_make_round())

    def test_survives_lab_error(self, trail: CodeAuditTrail):
        from unittest.mock import MagicMock
        mock_lab = MagicMock()
        mock_lab.record_outcome = MagicMock(side_effect=RuntimeError('boom'))
        trail.experiment_lab = mock_lab
        trail.record_round(_make_round())
