"""Tests for Tasks 3 & 4 — Sovereign route ranking + governed quota rotation.

Task 3: sovereign_route_ranking in LocalRoleRouter
  - Unified ranking comparing API free, web session, local shadow
  - Returns ranked candidates with route_kind, score, traceability
  - Handles missing routes honestly via unresolved list

Task 4: governed_quota_rotation in account_resource_scanner
  - Keep current account when quota available
  - Rotate to best available account when current exhausted
  - Wait when all accounts exhausted (report earliest reset)
  - No accounts tracked returns 'no_accounts'
  - Rotation trace for audit
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from iabv_v15.services.account_resource_scanner import (
    governed_quota_rotation,
    get_all_quota_status,
    record_message_sent,
    _load_quota_state,
    _save_quota_state,
    _quota_file,
)
from iabv_v15.services.roles.local_role_router import LocalRoleRouter


# ──────────────────────────────────────────────────────────────
# Helpers — stubs for LocalRoleRouter
# ──────────────────────────────────────────────────────────────

class _StubProvider:
    name = 'stub'
    def health_check(self, **kw: Any) -> Any:
        from iabv_v15.domain.models import ProviderHealth, ProviderStatus
        return ProviderHealth(provider_name=self.name, status=ProviderStatus.HEALTHY, available=True)
    def infer(self, prompt: str, **kw: Any) -> str:
        return ''


class _StubEmbedding:
    def health_check(self, **kw: Any) -> Any:
        from iabv_v15.domain.models import ProviderHealth, ProviderStatus
        return ProviderHealth(provider_name='embedding', status=ProviderStatus.HEALTHY, available=True)


class _StubService:
    pass


def _workspace(tmp_path: Path, name: str) -> Path:
    p = tmp_path / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def _router(
    ws: Path,
    account_resource_scanner: Any = None,
) -> LocalRoleRouter:
    prov = _StubProvider()
    stub = _StubService()
    embed = _StubEmbedding()
    return LocalRoleRouter(
        workspace_root=str(ws),
        general_provider=prov,
        visual_provider=prov,
        optional_provider=prov,
        embedding_service=embed,
        sql_service=stub,
        analytics_service=stub,
        customer_support_service=stub,
        engineering_review_service=stub,
        teaching_gap_analyzer=stub,
        episode_repository=stub,
        knowledge_repository=stub,
        run_repository=stub,
        artifact_repository=stub,
        account_resource_scanner=account_resource_scanner,
    )


def _pool_chatgpt_available() -> dict[str, Any]:
    return {
        'available_count': 2,
        'exhausted_count': 0,
        'total_remaining_messages': 50,
        'workers': [
            {'email': 'a@t.com', 'tool': 'chatgpt', 'remaining_messages': 30, 'limit': 40, 'exhausted': False},
            {'email': 'b@t.com', 'tool': 'chatgpt', 'remaining_messages': 20, 'limit': 40, 'exhausted': False},
        ],
        'exhausted': [],
        'tools_available': ['chatgpt'],
    }


def _pool_all_exhausted() -> dict[str, Any]:
    return {
        'available_count': 0,
        'exhausted_count': 2,
        'total_remaining_messages': 0,
        'workers': [
            {'email': 'a@t.com', 'tool': 'chatgpt', 'remaining_messages': 0, 'limit': 40, 'exhausted': True},
        ],
        'exhausted': [],
        'tools_available': [],
    }


# ──────────────────────────────────────────────────────────────
# Task 3: Sovereign route ranking tests
# ──────────────────────────────────────────────────────────────

class TestSovereignRouteRanking:
    """sovereign_route_ranking returns unified ranking across route kinds."""

    def test_api_free_workers_appear_in_ranking(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'api_free'), _pool_chatgpt_available)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'unknown', 'tool': 'chatgpt'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': False}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        api_candidates = [c for c in result['ranked'] if c['route_kind'] == 'api_free']
        assert len(api_candidates) >= 1
        assert result['recommended'] is not None
        assert result['recommended']['route_kind'] == 'api_free'

    def test_web_session_active_appears_in_ranking(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'web_active'), _pool_all_exhausted)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'active', 'tool': 'chatgpt', 'account_email': 'web@t.com'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': False}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        web_candidates = [c for c in result['ranked'] if c['route_kind'] == 'web_session']
        assert len(web_candidates) == 1
        assert web_candidates[0]['tool'] == 'chatgpt'
        assert web_candidates[0]['score'] > 0

    def test_local_shadow_appears_when_ollama_available(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'local'), _pool_all_exhausted)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'unknown', 'tool': 'chatgpt'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': True, 'models_count': 3}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        local = [c for c in result['ranked'] if c['route_kind'] == 'local_shadow']
        assert len(local) == 1
        assert local[0]['tool'] == 'ollama'
        assert local[0]['score'] == 0.35

    def test_ranking_sorted_by_score_descending(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'sorted'), _pool_chatgpt_available)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'active', 'tool': 'chatgpt', 'account_email': 'w@t.com'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': True, 'models_count': 2}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        scores = [c['score'] for c in result['ranked']]
        assert scores == sorted(scores, reverse=True)

    def test_unresolved_reported_for_unavailable_routes(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'unresolved'), _pool_all_exhausted)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'unknown', 'tool': 'chatgpt'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': False}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        assert len(result['unresolved']) >= 1
        unresolved_text = ' '.join(result['unresolved'])
        assert 'UNRESOLVED' in unresolved_text

    def test_no_target_scans_all_web_tools(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'all_web'), _pool_all_exhausted)
        call_count = {'n': 0}
        def mock_ws(tool: str) -> dict:
            call_count['n'] += 1
            return {'session_status': 'unknown', 'tool': tool}
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status', side_effect=mock_ws):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': False}):
                router.sovereign_route_ranking(target_assistant='')
        assert call_count['n'] == 3  # chatgpt, claude, codex

    def test_include_local_false_skips_ollama(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'no_local'), _pool_chatgpt_available)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'unknown', 'tool': 'chatgpt'}):
            result = router.sovereign_route_ranking(
                target_assistant='chatgpt', include_local=False,
            )
        local = [c for c in result['ranked'] if c['route_kind'] == 'local_shadow']
        assert len(local) == 0

    def test_web_session_needs_refresh_has_low_score(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'refresh'), _pool_all_exhausted)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'needs_refresh', 'tool': 'chatgpt', 'account_email': 'r@t.com'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': False}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        web = [c for c in result['ranked'] if c['route_kind'] == 'web_session']
        assert len(web) == 1
        assert web[0]['score'] == 0.2
        assert web[0]['block_risk'] == 0.3

    def test_recommended_is_highest_scored(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'rec'), _pool_chatgpt_available)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'active', 'tool': 'chatgpt', 'account_email': 'w@t.com'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': True, 'models_count': 1}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        assert result['recommended'] is not None
        assert result['recommended']['score'] == max(c['score'] for c in result['ranked'])

    def test_candidate_count_matches_ranked_length(self, tmp_path: Path) -> None:
        router = _router(_workspace(tmp_path, 'count'), _pool_chatgpt_available)
        with patch('iabv_v15.services.account_resource_scanner.get_web_session_status',
                   return_value={'session_status': 'unknown', 'tool': 'chatgpt'}):
            with patch('iabv_v15.services.account_resource_scanner.scan_ollama_api',
                       return_value={'available': True, 'models_count': 1}):
                result = router.sovereign_route_ranking(target_assistant='chatgpt')

        assert result['candidate_count'] == len(result['ranked'])


# ──────────────────────────────────────────────────────────────
# Task 4: Governed quota rotation tests
# ──────────────────────────────────────────────────────────────

class TestGovernedQuotaRotation:
    """governed_quota_rotation picks the next account when quota exhausts."""

    def _setup_quota(self, tmp_path: Path) -> Path:
        """Create an isolated quota file for tests."""
        quota_dir = tmp_path / 'data' / 'evolution'
        quota_dir.mkdir(parents=True, exist_ok=True)
        quota_file = quota_dir / 'quota_tracker.json'
        quota_file.write_text('{"accounts": {}}', encoding='utf-8')
        return quota_file

    def test_no_accounts_returns_no_accounts_action(self, tmp_path: Path) -> None:
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': [], 'total_tracked': 0,
                                 'exhausted_count': 0, 'available_count': 0,
                                 'exhausted_keys': [], 'available_keys': []}):
            result = governed_quota_rotation('chatgpt', 'nobody@t.com')

        assert result['action'] == 'no_accounts'
        assert result['current'] is None
        assert result['next'] is None
        assert result['rotation_trace']['decision'] == 'no_accounts'

    def test_keep_when_current_has_quota(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'chatgpt', 'email': 'user@t.com', 'remaining': 10,
             'limit': 15, 'exhausted': False, 'used_in_window': 5,
             'window_hours': 3, 'resets_at': None, 'total_sent_all_time': 20, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 1,
                                 'exhausted_count': 0, 'available_count': 1,
                                 'exhausted_keys': [], 'available_keys': ['chatgpt:user@t.com']}):
            result = governed_quota_rotation('chatgpt', 'user@t.com')

        assert result['action'] == 'keep'
        assert result['current'] is not None
        assert result['current']['email'] == 'user@t.com'
        assert result['next'] is None
        assert result['rotation_trace']['decision'] == 'keep'

    def test_rotate_when_current_exhausted(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'chatgpt', 'email': 'exhausted@t.com', 'remaining': 0,
             'limit': 15, 'exhausted': True, 'used_in_window': 15,
             'window_hours': 3, 'resets_at': '2025-01-01T12:00:00+00:00',
             'total_sent_all_time': 50, 'label': 'ChatGPT'},
            {'tool': 'chatgpt', 'email': 'fresh@t.com', 'remaining': 12,
             'limit': 15, 'exhausted': False, 'used_in_window': 3,
             'window_hours': 3, 'resets_at': None,
             'total_sent_all_time': 10, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 2,
                                 'exhausted_count': 1, 'available_count': 1,
                                 'exhausted_keys': ['chatgpt:exhausted@t.com'],
                                 'available_keys': ['chatgpt:fresh@t.com']}):
            result = governed_quota_rotation('chatgpt', 'exhausted@t.com')

        assert result['action'] == 'rotate'
        assert result['next'] is not None
        assert result['next']['email'] == 'fresh@t.com'
        assert result['next']['remaining'] == 12
        assert result['rotation_trace']['decision'] == 'rotate'
        assert result['rotation_trace']['to_email'] == 'fresh@t.com'

    def test_wait_when_all_exhausted(self, tmp_path: Path) -> None:
        reset_time = '2025-01-01T15:00:00+00:00'
        statuses = [
            {'tool': 'chatgpt', 'email': 'a@t.com', 'remaining': 0,
             'limit': 15, 'exhausted': True, 'used_in_window': 15,
             'window_hours': 3, 'resets_at': reset_time,
             'total_sent_all_time': 30, 'label': 'ChatGPT'},
            {'tool': 'chatgpt', 'email': 'b@t.com', 'remaining': 0,
             'limit': 15, 'exhausted': True, 'used_in_window': 15,
             'window_hours': 3, 'resets_at': '2025-01-01T16:00:00+00:00',
             'total_sent_all_time': 30, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 2,
                                 'exhausted_count': 2, 'available_count': 0,
                                 'exhausted_keys': ['chatgpt:a@t.com', 'chatgpt:b@t.com'],
                                 'available_keys': []}):
            result = governed_quota_rotation('chatgpt', 'a@t.com')

        assert result['action'] == 'wait'
        assert result['wait_until'] == reset_time
        assert result['next'] is None
        assert result['rotation_trace']['decision'] == 'wait'

    def test_rotate_picks_account_with_most_remaining(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'claude', 'email': 'low@t.com', 'remaining': 3,
             'limit': 20, 'exhausted': False, 'used_in_window': 17,
             'window_hours': 8, 'resets_at': None,
             'total_sent_all_time': 40, 'label': 'Claude'},
            {'tool': 'claude', 'email': 'high@t.com', 'remaining': 18,
             'limit': 20, 'exhausted': False, 'used_in_window': 2,
             'window_hours': 8, 'resets_at': None,
             'total_sent_all_time': 5, 'label': 'Claude'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 2,
                                 'exhausted_count': 0, 'available_count': 2,
                                 'exhausted_keys': [],
                                 'available_keys': ['claude:low@t.com', 'claude:high@t.com']}):
            result = governed_quota_rotation('claude')

        assert result['action'] == 'rotate'
        assert result['next']['email'] == 'high@t.com'

    def test_rotation_trace_has_timestamp(self, tmp_path: Path) -> None:
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': [], 'total_tracked': 0,
                                 'exhausted_count': 0, 'available_count': 0,
                                 'exhausted_keys': [], 'available_keys': []}):
            result = governed_quota_rotation('chatgpt')

        assert 'timestamp' in result['rotation_trace']
        assert result['rotation_trace']['timestamp'].endswith('+00:00') or 'T' in result['rotation_trace']['timestamp']

    def test_case_insensitive_email_match(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'chatgpt', 'email': 'User@Test.com', 'remaining': 10,
             'limit': 15, 'exhausted': False, 'used_in_window': 5,
             'window_hours': 3, 'resets_at': None,
             'total_sent_all_time': 20, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 1,
                                 'exhausted_count': 0, 'available_count': 1,
                                 'exhausted_keys': [],
                                 'available_keys': ['chatgpt:User@Test.com']}):
            result = governed_quota_rotation('chatgpt', 'user@test.com')

        assert result['action'] == 'keep'

    def test_rotate_without_current_email(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'chatgpt', 'email': 'any@t.com', 'remaining': 8,
             'limit': 15, 'exhausted': False, 'used_in_window': 7,
             'window_hours': 3, 'resets_at': None,
             'total_sent_all_time': 15, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 1,
                                 'exhausted_count': 0, 'available_count': 1,
                                 'exhausted_keys': [],
                                 'available_keys': ['chatgpt:any@t.com']}):
            result = governed_quota_rotation('chatgpt')

        assert result['action'] == 'rotate'
        assert result['next']['email'] == 'any@t.com'

    def test_wait_without_reset_times(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'chatgpt', 'email': 'x@t.com', 'remaining': 0,
             'limit': 15, 'exhausted': True, 'used_in_window': 15,
             'window_hours': 3, 'resets_at': None,
             'total_sent_all_time': 30, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 1,
                                 'exhausted_count': 1, 'available_count': 0,
                                 'exhausted_keys': ['chatgpt:x@t.com'],
                                 'available_keys': []}):
            result = governed_quota_rotation('chatgpt', 'x@t.com')

        assert result['action'] == 'wait'
        assert result['wait_until'] is None

    def test_tool_name_case_insensitive(self, tmp_path: Path) -> None:
        statuses = [
            {'tool': 'chatgpt', 'email': 'u@t.com', 'remaining': 5,
             'limit': 15, 'exhausted': False, 'used_in_window': 10,
             'window_hours': 3, 'resets_at': None,
             'total_sent_all_time': 25, 'label': 'ChatGPT'},
        ]
        with patch('iabv_v15.services.account_resource_scanner.get_all_quota_status',
                   return_value={'statuses': statuses, 'total_tracked': 1,
                                 'exhausted_count': 0, 'available_count': 1,
                                 'exhausted_keys': [],
                                 'available_keys': ['chatgpt:u@t.com']}):
            result = governed_quota_rotation('  ChatGPT  ', 'u@t.com')

        assert result['action'] == 'keep'
