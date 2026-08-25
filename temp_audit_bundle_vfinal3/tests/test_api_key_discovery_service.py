"""Tests for ApiKeyDiscoveryService — provider scanning, key testing and health reports."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from iabv_v15.services.evolution.api_key_discovery_service import (
    ApiKeyDiscoveryService,
    CLOUD_PROVIDERS,
    KeyTestResult,
)


class TestCloudProviders:
    def test_all_have_required_fields(self) -> None:
        required = {'id', 'name', 'env_key', 'signup_url', 'api_test_url', 'model', 'tier'}
        for provider in CLOUD_PROVIDERS:
            missing = required - set(provider.keys())
            assert not missing, f"Provider {provider['id']} missing: {missing}"

    def test_known_providers_present(self) -> None:
        ids = {p['id'] for p in CLOUD_PROVIDERS}
        assert 'groq' in ids
        assert 'gemini' in ids
        assert 'openai' in ids

    def test_all_have_signup_urls(self) -> None:
        for p in CLOUD_PROVIDERS:
            assert p['signup_url'].startswith('https://'), f"{p['id']} missing signup URL"


class TestKeyTestResult:
    def test_defaults(self) -> None:
        r = KeyTestResult(provider_id='groq', env_key='GROQ_API_KEY')
        assert r.valid is False
        assert r.latency_ms == 0.0
        assert r.error == ''

    def test_to_dict(self) -> None:
        r = KeyTestResult(
            provider_id='groq', env_key='GROQ_API_KEY',
            valid=True, latency_ms=150.5, model_used='llama-3.3-70b',
        )
        d = r.to_dict()
        assert d['provider_id'] == 'groq'
        assert d['valid'] is True
        assert d['latency_ms'] == 150.5
        assert 'tested_at_utc' in d


class TestScanConfiguredKeys:
    def test_with_no_keys_set(self) -> None:
        with patch.dict(os.environ, {p['env_key']: '' for p in CLOUD_PROVIDERS}, clear=False):
            svc = ApiKeyDiscoveryService()
            scan = svc.scan_configured_keys()
            assert len(scan) == len(CLOUD_PROVIDERS)
            assert all(not s['configured'] for s in scan)

    def test_with_groq_key_set(self) -> None:
        env = {p['env_key']: '' for p in CLOUD_PROVIDERS}
        env['GROQ_API_KEY'] = 'gsk_test123'
        with patch.dict(os.environ, env, clear=False):
            svc = ApiKeyDiscoveryService()
            scan = svc.scan_configured_keys()
            groq = next(s for s in scan if s['provider_id'] == 'groq')
            assert groq['configured'] is True
            assert groq['prefix_match'] is True

    def test_find_missing_keys(self) -> None:
        env = {p['env_key']: '' for p in CLOUD_PROVIDERS}
        env['GROQ_API_KEY'] = 'gsk_test123'
        with patch.dict(os.environ, env, clear=False):
            svc = ApiKeyDiscoveryService()
            missing = svc.find_missing_keys()
            ids = {m['provider_id'] for m in missing}
            assert 'groq' not in ids
            assert 'gemini' in ids


class TestTestKey:
    def test_unknown_provider(self) -> None:
        svc = ApiKeyDiscoveryService()
        result = svc.test_key('nonexistent')
        assert not result.valid
        assert 'Unknown' in result.error

    def test_missing_key(self) -> None:
        with patch.dict(os.environ, {'GROQ_API_KEY': ''}, clear=False):
            svc = ApiKeyDiscoveryService()
            result = svc.test_key('groq')
            assert not result.valid
        assert 'not set' in result.error

    def test_successful_key(self) -> None:
        import httpx as _real_httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'model': 'llama-3.3-70b-versatile', 'choices': [{'message': {'content': 'OK'}}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch.dict(os.environ, {'GROQ_API_KEY': 'gsk_test123'}, clear=False):
            with patch.dict('sys.modules', {'httpx': mock_httpx}):
                svc = ApiKeyDiscoveryService()
                result = svc.test_key('groq')
                assert result.valid
                assert result.quota_info == 'Not exposed by test endpoint'


class TestPersistResults:
    def test_creates_file(self, tmp_path: Path) -> None:
        svc = ApiKeyDiscoveryService(data_root=tmp_path)
        results = {
            'summary': 'Test summary',
            'tested': [{'provider_id': 'groq', 'valid': True}],
            'recommended': None,
        }
        svc.save_test_results(results)
        audit_path = tmp_path / 'evolution' / 'autonomous_tasks' / 'api_key_management.json'
        assert audit_path.exists()
        data = json.loads(audit_path.read_text())
        assert len(data) == 1
        assert data[0]['results']['summary'] == 'Test summary'


class TestFullHealthReport:
    def test_report_structure(self) -> None:
        with patch.dict(os.environ, {p['env_key']: '' for p in CLOUD_PROVIDERS}, clear=False):
            svc = ApiKeyDiscoveryService()
            with patch.object(svc, 'save_test_results'):
                report = svc.compare_all_configured()
                assert 'summary' in report
                assert 'tested' in report
                assert 'recommended' in report
                assert report['recommended'] is None


class TestSecretProviders:
    def test_groq_in_providers(self) -> None:
        from iabv_v15.services.auto_correction_engine import _SECRET_PROVIDERS
        assert 'GROQ' in _SECRET_PROVIDERS
        url, desc, openable = _SECRET_PROVIDERS['GROQ']
        assert 'groq.com' in url
        assert openable is True

    def test_gemini_in_providers(self) -> None:
        from iabv_v15.services.auto_correction_engine import _SECRET_PROVIDERS
        assert 'GEMINI' in _SECRET_PROVIDERS
        url, desc, openable = _SECRET_PROVIDERS['GEMINI']
        assert 'aistudio.google.com' in url
        assert openable is True
