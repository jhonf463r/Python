"""Focused tests for register_audit_round batch tool and _safe_enum fix.

Covers:
- _safe_enum parses valid enum values correctly
- _safe_enum returns default on invalid values
- record_finding uses _safe_enum (enum fix regression)
- register_audit_round via MCP produces 1 round with N findings
- register_audit_round integrates with summary and auditor_comparison
- register_audit_round with empty findings list
- register_audit_round with partial/missing finding fields
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.services.evolution.code_audit_trail import (
    AuditEnvironment,
    AuditFinding,
    AuditRound,
    AuditSource,
    CodeAuditTrail,
    FindingSeverity,
    FindingStatus,
    _safe_enum,
)


@pytest.fixture
def trail(tmp_path: Path) -> CodeAuditTrail:
    return CodeAuditTrail(data_root=tmp_path)


# ------------------------------------------------------------------
# _safe_enum helper
# ------------------------------------------------------------------


class TestSafeEnum:
    def test_valid_severity(self):
        assert _safe_enum(FindingSeverity, 'high', FindingSeverity.MEDIUM) == FindingSeverity.HIGH

    def test_valid_status(self):
        assert _safe_enum(FindingStatus, 'fixed', FindingStatus.FOUND) == FindingStatus.FIXED

    def test_valid_source(self):
        assert _safe_enum(AuditSource, 'human', AuditSource.EXTERNAL_AGENT) == AuditSource.HUMAN

    def test_valid_environment(self):
        assert _safe_enum(AuditEnvironment, 'windows_native', AuditEnvironment.UNKNOWN) == AuditEnvironment.WINDOWS_NATIVE

    def test_invalid_returns_default(self):
        assert _safe_enum(FindingSeverity, 'ultra_mega', FindingSeverity.MEDIUM) == FindingSeverity.MEDIUM

    def test_empty_string_returns_default(self):
        assert _safe_enum(FindingSeverity, '', FindingSeverity.MEDIUM) == FindingSeverity.MEDIUM

    def test_all_severity_values_parse(self):
        for member in FindingSeverity:
            assert _safe_enum(FindingSeverity, member.value, FindingSeverity.MEDIUM) == member

    def test_all_status_values_parse(self):
        for member in FindingStatus:
            assert _safe_enum(FindingStatus, member.value, FindingStatus.FOUND) == member


# ------------------------------------------------------------------
# record_finding enum fix regression
# ------------------------------------------------------------------


class TestRecordFindingEnumFix:
    def test_severity_high_is_preserved(self, trail: CodeAuditTrail):
        result = trail.record_finding(
            module_path='services/foo.py',
            title='High severity bug',
            severity='high',
            status='found',
        )
        assert result['severity'] == 'high'

    def test_severity_critical_is_preserved(self, trail: CodeAuditTrail):
        result = trail.record_finding(
            module_path='services/bar.py',
            title='Critical bug',
            severity='critical',
            status='unresolved',
        )
        assert result['severity'] == 'critical'
        assert result['status'] == 'unresolved'

    def test_status_wont_fix_is_preserved(self, trail: CodeAuditTrail):
        result = trail.record_finding(
            module_path='services/baz.py',
            title='Wont fix',
            severity='low',
            status='wont_fix',
        )
        assert result['severity'] == 'low'
        assert result['status'] == 'wont_fix'

    def test_invalid_severity_defaults_medium(self, trail: CodeAuditTrail):
        result = trail.record_finding(
            module_path='services/x.py',
            title='Unknown severity',
            severity='extreme',
        )
        assert result['severity'] == 'medium'

    def test_source_and_environment_preserved(self, trail: CodeAuditTrail):
        trail.record_finding(
            module_path='services/y.py',
            title='Win bug',
            source='human',
            environment='windows_native',
        )
        rounds = trail.load_rounds()
        assert rounds[0]['source'] == 'human'
        assert rounds[0]['environment'] == 'windows_native'


# ------------------------------------------------------------------
# register_audit_round (batch) — core behavior
# ------------------------------------------------------------------


def _build_round_via_tool(trail: CodeAuditTrail, **overrides) -> dict[str, Any]:
    """Simulate what the MCP tool does: build AuditRound from dicts."""
    from iabv_v15.services.evolution.code_audit_trail import (
        AuditEnvironment,
        AuditFinding,
        AuditRound,
        AuditSource,
        FindingSeverity,
        FindingStatus,
        _safe_enum,
    )

    defaults: dict[str, Any] = {
        'auditor_name': 'devin',
        'source': 'external_agent',
        'environment': 'linux_vm',
        'round_number': 25,
        'modules_audited': ['services/foo.py', 'services/bar.py'],
        'total_loc_audited': 3400,
        'pr_url': 'https://github.com/jhonf463r/Python/pull/280',
        'ci_status': 'passed',
        'unresolved_items': ['OSES cross-ref needs manual check'],
        'findings': [
            {
                'module_path': 'services/foo.py',
                'title': 'Missing null check',
                'description': 'get_value() can return None',
                'severity': 'high',
                'status': 'fixed',
                'category': 'null_safety',
                'pattern_tag': 'null_check_missing',
                'bug_id': 'R25-1',
                'fix_description': 'Added None guard',
            },
            {
                'module_path': 'services/bar.py',
                'title': 'Unused import',
                'description': 'os imported but never used',
                'severity': 'low',
                'status': 'fixed',
                'category': 'cleanup',
                'pattern_tag': 'unused_import',
                'bug_id': 'R25-2',
            },
            {
                'module_path': 'services/bar.py',
                'title': 'Thread safety gap',
                'description': 'Shared dict accessed without lock',
                'severity': 'critical',
                'status': 'unresolved',
                'category': 'concurrency',
                'pattern_tag': 'thread_safety',
                'bug_id': 'R25-3',
                'needs_windows_verification': True,
            },
        ],
        'tests_added': 4,
        'tests_passed': 4,
        'tests_failed': 0,
        'auditor_session_url': 'https://app.devin.ai/sessions/test123',
    }
    defaults.update(overrides)

    raw_findings = defaults.pop('findings')
    parsed_findings: list[AuditFinding] = []
    for fd in (raw_findings or []):
        parsed_findings.append(AuditFinding(
            round_id='',
            bug_id=fd.get('bug_id', ''),
            module_path=fd.get('module_path', ''),
            line_range=fd.get('line_range', ''),
            category=fd.get('category', ''),
            title=fd.get('title', ''),
            description=fd.get('description', ''),
            impact=fd.get('impact', ''),
            severity=_safe_enum(FindingSeverity, fd.get('severity', 'medium'), FindingSeverity.MEDIUM),
            status=_safe_enum(FindingStatus, fd.get('status', 'found'), FindingStatus.FOUND),
            fix_description=fd.get('fix_description', ''),
            pr_url=fd.get('pr_url', ''),
            pattern_tag=fd.get('pattern_tag', ''),
            needs_windows_verification=bool(fd.get('needs_windows_verification', False)),
            needs_linux_verification=bool(fd.get('needs_linux_verification', False)),
            confidence=float(fd.get('confidence', 0.9)),
        ))

    audit_round = AuditRound(
        round_number=defaults['round_number'],
        auditor_name=defaults['auditor_name'],
        auditor_session_url=defaults.get('auditor_session_url', ''),
        source=_safe_enum(AuditSource, defaults['source'], AuditSource.EXTERNAL_AGENT),
        environment=_safe_enum(AuditEnvironment, defaults['environment'], AuditEnvironment.UNKNOWN),
        modules_audited=defaults.get('modules_audited') or [],
        total_loc_audited=defaults.get('total_loc_audited', 0),
        findings=parsed_findings,
        tests_added=defaults.get('tests_added', 0),
        tests_passed=defaults.get('tests_passed', 0),
        tests_failed=defaults.get('tests_failed', 0),
        pr_url=defaults.get('pr_url', ''),
        ci_status=defaults.get('ci_status', ''),
        unresolved_items=defaults.get('unresolved_items') or [],
    )

    trail.record_round(audit_round)

    return {
        'round_id': audit_round.round_id,
        'round_number': audit_round.round_number,
        'auditor_name': audit_round.auditor_name,
        'source': audit_round.source.value,
        'environment': audit_round.environment.value,
        'findings_count': len(parsed_findings),
        'modules_audited': audit_round.modules_audited,
        'total_loc_audited': audit_round.total_loc_audited,
        'tests_added': audit_round.tests_added,
        'unresolved_items': audit_round.unresolved_items,
        'pr_url': audit_round.pr_url,
        'timestamp_utc': audit_round.timestamp_utc,
    }


class TestRegisterAuditRoundBatch:
    """Core test: N findings in 1 call produce exactly 1 round, not N mini-rounds."""

    def test_three_findings_produce_one_round(self, trail: CodeAuditTrail):
        result = _build_round_via_tool(trail)

        rounds = trail.load_rounds()
        assert len(rounds) == 1, f"Expected 1 round, got {len(rounds)}"

        r = rounds[0]
        assert r['round_number'] == 25
        assert r['auditor_name'] == 'devin'
        assert r['findings_count'] == 3
        assert r['bugs_found'] == 3
        assert r['bugs_fixed'] == 2
        assert r['tests_added'] == 4
        assert r['source'] == 'external_agent'
        assert r['environment'] == 'linux_vm'

    def test_return_value_has_expected_fields(self, trail: CodeAuditTrail):
        result = _build_round_via_tool(trail)

        assert 'round_id' in result
        assert result['round_number'] == 25
        assert result['auditor_name'] == 'devin'
        assert result['source'] == 'external_agent'
        assert result['environment'] == 'linux_vm'
        assert result['findings_count'] == 3
        assert result['modules_audited'] == ['services/foo.py', 'services/bar.py']
        assert result['total_loc_audited'] == 3400
        assert result['tests_added'] == 4
        assert result['unresolved_items'] == ['OSES cross-ref needs manual check']
        assert result['pr_url'] == 'https://github.com/jhonf463r/Python/pull/280'
        assert 'timestamp_utc' in result

    def test_findings_severity_preserved_in_round(self, trail: CodeAuditTrail):
        _build_round_via_tool(trail)
        findings = trail.load_all_findings()
        severities = {f['bug_id']: f['severity'] for f in findings}
        assert severities['R25-1'] == 'high'
        assert severities['R25-2'] == 'low'
        assert severities['R25-3'] == 'critical'

    def test_findings_status_preserved(self, trail: CodeAuditTrail):
        _build_round_via_tool(trail)
        findings = trail.load_all_findings()
        statuses = {f['bug_id']: f['status'] for f in findings}
        assert statuses['R25-1'] == 'fixed'
        assert statuses['R25-2'] == 'fixed'
        assert statuses['R25-3'] == 'unresolved'

    def test_cross_verification_flag_preserved(self, trail: CodeAuditTrail):
        _build_round_via_tool(trail)
        pending = trail.pending_cross_verifications()
        assert len(pending) == 1
        assert pending[0]['title'] == 'Thread safety gap'

    def test_empty_findings_list(self, trail: CodeAuditTrail):
        result = _build_round_via_tool(trail, findings=[])
        assert result['findings_count'] == 0
        rounds = trail.load_rounds()
        assert len(rounds) == 1
        assert rounds[0]['findings_count'] == 0

    def test_none_findings(self, trail: CodeAuditTrail):
        result = _build_round_via_tool(trail, findings=None)
        assert result['findings_count'] == 0

    def test_partial_finding_fields_use_defaults(self, trail: CodeAuditTrail):
        result = _build_round_via_tool(trail, findings=[
            {'title': 'Minimal finding'},
        ])
        assert result['findings_count'] == 1
        findings = trail.load_all_findings()
        assert findings[0]['title'] == 'Minimal finding'
        assert findings[0]['severity'] == 'medium'
        assert findings[0]['status'] == 'found'

    def test_invalid_enum_in_finding_uses_default(self, trail: CodeAuditTrail):
        result = _build_round_via_tool(trail, findings=[
            {'title': 'Bad enum', 'severity': 'mega_ultra', 'status': 'dunno'},
        ])
        findings = trail.load_all_findings()
        assert findings[0]['severity'] == 'medium'
        assert findings[0]['status'] == 'found'


# ------------------------------------------------------------------
# Integration with summary and auditor_comparison
# ------------------------------------------------------------------


class TestRegisterAuditRoundIntegration:
    def test_summary_reflects_batch_round(self, trail: CodeAuditTrail):
        _build_round_via_tool(trail)
        summary = trail.summary_for_portable_context()
        coverage = summary['coverage']
        assert coverage['total_rounds'] == 1
        assert coverage['total_bugs_found'] == 3
        assert coverage['total_loc_audited'] == 3400

    def test_auditor_comparison_counts_one_round(self, trail: CodeAuditTrail):
        _build_round_via_tool(trail)
        comparison = trail.auditor_performance_summary()
        devin = comparison['auditors']['devin']
        assert devin['rounds'] == 1
        assert devin['bugs_found'] == 3
        assert devin['findings_total'] == 3
        assert devin['tests_added'] == 4

    def test_pattern_analysis_groups_correctly(self, trail: CodeAuditTrail):
        _build_round_via_tool(trail)
        patterns = trail.analyze_bug_patterns()
        tags = {p['pattern_tag'] for p in patterns}
        assert 'null_check_missing' in tags
        assert 'thread_safety' in tags
        assert 'unused_import' in tags

    def test_batch_vs_atomic_round_count(self, trail: CodeAuditTrail):
        """The key test: batch produces 1 round, atomic would produce 3."""
        _build_round_via_tool(trail)

        rounds = trail.load_rounds()
        assert len(rounds) == 1, (
            "Batch register_audit_round must produce exactly 1 round, "
            f"but got {len(rounds)}"
        )

        # Compare: 3 atomic calls would produce 3 rounds
        trail2 = CodeAuditTrail(data_root=trail._data_root.parent / 'trail2')
        trail2.record_finding(
            module_path='services/foo.py', title='Bug 1',
            severity='high', auditor_name='devin', round_number=25,
        )
        trail2.record_finding(
            module_path='services/bar.py', title='Bug 2',
            severity='low', auditor_name='devin', round_number=25,
        )
        trail2.record_finding(
            module_path='services/bar.py', title='Bug 3',
            severity='critical', auditor_name='devin', round_number=25,
        )
        rounds2 = trail2.load_rounds()
        assert len(rounds2) == 3, "Atomic calls should produce 3 separate rounds"

    def test_experiment_lab_receives_batch_round(self, trail: CodeAuditTrail):
        mock_lab = MagicMock()
        mock_lab.record_outcome = MagicMock(return_value=(MagicMock(), MagicMock()))
        trail.experiment_lab = mock_lab

        _build_round_via_tool(trail)

        mock_lab.record_outcome.assert_called_once()
        kwargs = mock_lab.record_outcome.call_args.kwargs
        assert kwargs['candidate_label'] == 'devin'
        assert kwargs['metadata']['findings_count'] == 3
        assert kwargs['metadata']['round_number'] == 25
