"""Focalized tests for account/resource health in PortableContext + OSES.

Covers the slice added in this PR:
- :meth:`PortableContextService._account_resource_snapshot`
- :meth:`PortableContextService._account_resource_section`
- :meth:`OperationalSelfExaminationService._account_resource_health_findings`

No new service, no new persistence — reads existing scanner functions.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_portable_service(root: Path) -> PortableContextService:
    storage = ArtifactStorage(str(root / 'data' / 'evolution'))
    return PortableContextService(
        workspace_root=str(root),
        storage=storage,
    )


def _make_oses(root: Path) -> OperationalSelfExaminationService:
    storage = ArtifactStorage(str(root / 'data' / 'evolution'))
    return OperationalSelfExaminationService(
        workspace_root=str(root),
        storage=storage,
    )


# --------------------------------------------------------------------------- #
# PortableContextService._account_resource_snapshot
# --------------------------------------------------------------------------- #


def test_snapshot_returns_ok_when_no_quotas_tracked() -> None:
    """When scanner works but no messages have been sent, snapshot is ok
    with zero counts."""
    root = _workspace('acct_snap_empty')
    svc = _make_portable_service(root)

    def mock_quotas():
        return {'statuses': [], 'total_tracked': 0, 'exhausted_count': 0,
                'available_count': 0, 'exhausted_keys': [], 'available_keys': []}

    def mock_workers():
        return {'workers': [], 'exhausted': [], 'available_count': 0,
                'exhausted_count': 0, 'by_tool': {}, 'total_remaining_messages': 0,
                'tools_available': []}

    def mock_secrets():
        return {'configured': ['GITHUB_TOKEN'], 'missing': ['OPENAI_API_KEY'],
                'configured_count': 1, 'missing_count': 1,
                'secrets_file_exists': False, 'secrets_in_file': []}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', mock_workers), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets):
        snap = svc._account_resource_snapshot()

    assert snap['status'] == 'ok'
    assert snap['quota_total_tracked'] == 0
    assert snap['worker_available_count'] == 0
    assert snap['secrets_configured'] == 1
    assert 'OPENAI_API_KEY' in snap['secrets_missing']


def test_snapshot_includes_exhausted_accounts() -> None:
    """Exhausted accounts appear in the snapshot."""
    root = _workspace('acct_snap_exhausted')
    svc = _make_portable_service(root)

    def mock_quotas():
        return {
            'statuses': [
                {'tool': 'chatgpt', 'email': 'user@test.com', 'exhausted': True,
                 'remaining': 0, 'limit': 15, 'resets_at': '2026-04-21T00:00:00Z',
                 'used_in_window': 15, 'window_hours': 3, 'total_sent_all_time': 30,
                 'label': 'ChatGPT Free'},
                {'tool': 'claude', 'email': 'user@test.com', 'exhausted': False,
                 'remaining': 15, 'limit': 20, 'resets_at': None,
                 'used_in_window': 5, 'window_hours': 8, 'total_sent_all_time': 10,
                 'label': 'Claude Free'},
            ],
            'total_tracked': 2, 'exhausted_count': 1, 'available_count': 1,
            'exhausted_keys': ['chatgpt:user@test.com'],
            'available_keys': ['claude:user@test.com'],
        }

    def mock_workers():
        return {
            'workers': [
                {'tool': 'claude', 'email': 'user@test.com',
                 'remaining_messages': 15, 'limit': 20, 'exhausted': False,
                 'browser': 'Chrome', 'profile': 'Default'},
            ],
            'exhausted': [], 'available_count': 1, 'exhausted_count': 0,
            'by_tool': {'claude': []}, 'total_remaining_messages': 15,
            'tools_available': ['claude'],
        }

    def mock_secrets():
        return {'configured': [], 'missing': [], 'configured_count': 0,
                'missing_count': 0, 'secrets_file_exists': False, 'secrets_in_file': []}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', mock_workers), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets):
        snap = svc._account_resource_snapshot()

    assert snap['status'] == 'ok'
    assert snap['quota_exhausted_count'] == 1
    assert snap['quota_available_count'] == 1
    assert len(snap['exhausted_accounts']) == 1
    assert snap['exhausted_accounts'][0]['tool'] == 'chatgpt'
    assert snap['worker_available_count'] == 1
    assert snap['worker_total_remaining_messages'] == 15
    assert 'claude' in snap['workers_by_tool']


def test_snapshot_survives_scanner_import_failure() -> None:
    """If account_resource_scanner can't be imported, snapshot degrades gracefully."""
    root = _workspace('acct_snap_import_fail')
    svc = _make_portable_service(root)

    with patch.dict('sys.modules', {'iabv_v15.services.account_resource_scanner': None}):
        snap = svc._account_resource_snapshot()

    assert snap['status'] == 'scanner_unavailable'


def test_snapshot_survives_quota_read_failure() -> None:
    """If get_all_quota_status() raises, snapshot still returns partial data."""
    root = _workspace('acct_snap_quota_fail')
    svc = _make_portable_service(root)

    def mock_quotas():
        raise RuntimeError('quota DB locked')

    def mock_workers():
        return {'workers': [], 'exhausted': [], 'available_count': 0,
                'exhausted_count': 0, 'by_tool': {}, 'total_remaining_messages': 0,
                'tools_available': []}

    def mock_secrets():
        return {'configured': [], 'missing': [], 'configured_count': 0,
                'missing_count': 0, 'secrets_file_exists': False, 'secrets_in_file': []}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', mock_workers), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets):
        snap = svc._account_resource_snapshot()

    assert snap['status'] == 'partial_failure'
    assert 'quota_read_failed' in snap['read_failures']
    assert snap['worker_available_count'] == 0


# --------------------------------------------------------------------------- #
# PortableContextService._account_resource_section
# --------------------------------------------------------------------------- #


def test_section_summary_shows_workers_and_messages() -> None:
    """Section summary includes worker count, remaining messages, tools."""
    root = _workspace('acct_section_summary')
    svc = _make_portable_service(root)
    from iabv_v15.domain.models import utc_now

    status = {
        'status': 'ok',
        'worker_available_count': 3,
        'quota_exhausted_count': 1,
        'worker_total_remaining_messages': 45,
        'workers_by_tool': ['chatgpt', 'claude'],
        'secrets_missing': ['DEVIN_API_KEY_IABV'],
        'secrets_configured': 2,
        'available_workers': [
            {'tool': 'chatgpt', 'email': 'a@test.com', 'remaining': 10, 'limit': 15},
            {'tool': 'chatgpt', 'email': 'b@test.com', 'remaining': 15, 'limit': 15},
            {'tool': 'claude', 'email': 'c@test.com', 'remaining': 20, 'limit': 20},
        ],
        'exhausted_accounts': [
            {'tool': 'chatgpt', 'email': 'd@test.com', 'resets_at': '2026-04-21T00:00:00Z'},
        ],
    }
    section = svc._account_resource_section(status=status, now=utc_now())

    assert section.section_id == 'account_resource_health'
    assert '3 workers disponibles' in section.summary
    assert '45 mensajes restantes' in section.summary
    assert '1 cuentas agotadas' in section.summary
    assert section.confidence > 0
    assert len(section.items) >= 3  # 3 available + 1 exhausted + 1 missing secret


def test_section_when_scanner_unavailable() -> None:
    """Section degrades when scanner is not available."""
    root = _workspace('acct_section_unavail')
    svc = _make_portable_service(root)
    from iabv_v15.domain.models import utc_now

    status = {'status': 'scanner_unavailable'}
    section = svc._account_resource_section(status=status, now=utc_now())

    assert 'no disponible' in section.summary.lower()
    assert section.confidence == 0.0


def test_section_when_no_accounts_tracked() -> None:
    """Section shows helpful message when no accounts have been tracked."""
    root = _workspace('acct_section_no_track')
    svc = _make_portable_service(root)
    from iabv_v15.domain.models import utc_now

    status = {
        'status': 'ok',
        'worker_available_count': 0,
        'quota_exhausted_count': 0,
        'worker_total_remaining_messages': 0,
        'workers_by_tool': [],
        'secrets_missing': [],
        'secrets_configured': 0,
        'available_workers': [],
        'exhausted_accounts': [],
    }
    section = svc._account_resource_section(status=status, now=utc_now())

    assert 'rastreo comienza' in section.summary.lower()


# --------------------------------------------------------------------------- #
# OperationalSelfExaminationService._account_resource_health_findings
# --------------------------------------------------------------------------- #


def test_oses_finding_when_all_quotas_exhausted() -> None:
    """OSES produces HIGH severity finding when all accounts are exhausted."""
    root = _workspace('oses_all_exhausted')
    oses = _make_oses(root)

    def mock_quotas():
        return {'exhausted_count': 3, 'available_count': 0,
                'exhausted_keys': ['chatgpt:a@t.com', 'chatgpt:b@t.com', 'claude:a@t.com'],
                'statuses': []}

    def mock_secrets():
        return {'configured': ['GITHUB_TOKEN'], 'missing': [],
                'configured_count': 1, 'missing_count': 0}

    def mock_gh():
        return {'available': True, 'remaining': 4000, 'rate_limit': 5000}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets), \
         patch('iabv_v15.services.account_resource_scanner.scan_github_api', mock_gh), \
         patch('iabv_v15.services.account_resource_scanner.scan_ollama_api', lambda: {'available': True}):
        findings = oses._account_resource_health_findings()

    exhaustion_findings = [f for f in findings if f.category == 'resource_exhaustion']
    assert len(exhaustion_findings) == 1
    f = exhaustion_findings[0]
    assert f.severity.value == 'high'
    assert '3/3' in f.title
    assert f.metadata['exhaustion_ratio'] == 1.0


def test_oses_finding_when_half_quotas_exhausted() -> None:
    """OSES produces MEDIUM severity when >= 50% but not all exhausted."""
    root = _workspace('oses_half_exhausted')
    oses = _make_oses(root)

    def mock_quotas():
        return {'exhausted_count': 2, 'available_count': 1,
                'exhausted_keys': ['chatgpt:a@t.com', 'chatgpt:b@t.com'],
                'statuses': []}

    def mock_secrets():
        return {'configured': [], 'missing': [], 'configured_count': 0, 'missing_count': 0}

    def mock_gh():
        return {'available': True, 'remaining': 4000, 'rate_limit': 5000}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets), \
         patch('iabv_v15.services.account_resource_scanner.scan_github_api', mock_gh), \
         patch('iabv_v15.services.account_resource_scanner.scan_ollama_api', lambda: {'available': True}):
        findings = oses._account_resource_health_findings()

    exhaustion_findings = [f for f in findings if f.category == 'resource_exhaustion']
    assert len(exhaustion_findings) == 1
    assert exhaustion_findings[0].severity.value == 'medium'


def test_oses_no_finding_when_quotas_healthy() -> None:
    """No exhaustion finding when less than 50% exhausted."""
    root = _workspace('oses_quotas_healthy')
    oses = _make_oses(root)

    def mock_quotas():
        return {'exhausted_count': 1, 'available_count': 5,
                'exhausted_keys': ['chatgpt:a@t.com'], 'statuses': []}

    def mock_secrets():
        return {'configured': ['GITHUB_TOKEN'], 'missing': [],
                'configured_count': 1, 'missing_count': 0}

    def mock_gh():
        return {'available': True, 'remaining': 4000, 'rate_limit': 5000}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets), \
         patch('iabv_v15.services.account_resource_scanner.scan_github_api', mock_gh), \
         patch('iabv_v15.services.account_resource_scanner.scan_ollama_api', lambda: {'available': True}):
        findings = oses._account_resource_health_findings()

    exhaustion_findings = [f for f in findings if f.category == 'resource_exhaustion']
    assert len(exhaustion_findings) == 0


def test_oses_finding_github_rate_limit_low() -> None:
    """OSES detects when GitHub API rate limit is critically low."""
    root = _workspace('oses_gh_rate_low')
    oses = _make_oses(root)

    def mock_quotas():
        return {'exhausted_count': 0, 'available_count': 0, 'exhausted_keys': [], 'statuses': []}

    def mock_secrets():
        return {'configured': [], 'missing': [], 'configured_count': 0, 'missing_count': 0}

    def mock_gh():
        return {'available': True, 'remaining': 12, 'rate_limit': 5000,
                'reset_at': '2026-04-21T01:00:00Z'}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets), \
         patch('iabv_v15.services.account_resource_scanner.scan_github_api', mock_gh), \
         patch('iabv_v15.services.account_resource_scanner.scan_ollama_api', lambda: {'available': True}):
        findings = oses._account_resource_health_findings()

    api_findings = [f for f in findings if f.category == 'resource_degradation']
    assert len(api_findings) == 1
    assert '12' in api_findings[0].title


def test_oses_finding_critical_secrets_missing() -> None:
    """OSES detects missing critical secrets."""
    root = _workspace('oses_secrets_missing')
    oses = _make_oses(root)

    def mock_quotas():
        return {'exhausted_count': 0, 'available_count': 0, 'exhausted_keys': [], 'statuses': []}

    def mock_secrets():
        return {'configured': [], 'missing': ['GITHUB_TOKEN_IABV', 'OPENAI_API_KEY'],
                'configured_count': 0, 'missing_count': 2}

    def mock_gh():
        return {'available': False, 'reason': 'no_token'}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets), \
         patch('iabv_v15.services.account_resource_scanner.scan_github_api', mock_gh), \
         patch('iabv_v15.services.account_resource_scanner.scan_ollama_api', lambda: {'available': True}):
        findings = oses._account_resource_health_findings()

    config_findings = [f for f in findings if f.category == 'configuration_gap']
    assert len(config_findings) == 1
    assert 'GITHUB_TOKEN_IABV' in config_findings[0].title
    assert config_findings[0].severity.value == 'high'


def test_oses_no_finding_when_non_critical_secrets_missing() -> None:
    """OSES does NOT flag non-critical missing secrets (OPENAI_API_KEY alone)."""
    root = _workspace('oses_noncrit_missing')
    oses = _make_oses(root)

    def mock_quotas():
        return {'exhausted_count': 0, 'available_count': 0, 'exhausted_keys': [], 'statuses': []}

    def mock_secrets():
        return {'configured': ['GITHUB_TOKEN_IABV'], 'missing': ['OPENAI_API_KEY'],
                'configured_count': 1, 'missing_count': 1}

    def mock_gh():
        return {'available': True, 'remaining': 5000, 'rate_limit': 5000}

    with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', mock_quotas), \
         patch('iabv_v15.services.account_resource_scanner.scan_configured_secrets', mock_secrets), \
         patch('iabv_v15.services.account_resource_scanner.scan_github_api', mock_gh), \
         patch('iabv_v15.services.account_resource_scanner.scan_ollama_api', lambda: {'available': True}):
        findings = oses._account_resource_health_findings()

    config_findings = [f for f in findings if f.category == 'configuration_gap']
    assert len(config_findings) == 0


def test_oses_survives_scanner_failure() -> None:
    """OSES returns empty findings if scanner import fails."""
    root = _workspace('oses_scanner_fail')
    oses = _make_oses(root)

    with patch.dict('sys.modules', {'iabv_v15.services.account_resource_scanner': None}):
        findings = oses._account_resource_health_findings()

    assert findings == []
