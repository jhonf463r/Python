"""Tests for Fase 3 — worker_pool_snapshot in WorldModelSnapshot.

Verifies:
1. WorldModelSnapshot accepts worker_pool_snapshot as dict
2. WorldModelSnapshot with worker_pool_snapshot={} is valid (default)
3. WorldModelService populates worker_pool_snapshot with real data
   when accounts are registered
4. WorldModelService leaves worker_pool_snapshot empty if
   account_resource_scanner fails
5. worker_pool_snapshot appears in WorldModelService.scan_now() result
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.domain.models import WorldModelSnapshot


# ------------------------------------------------------------------ #
# 1. WorldModelSnapshot accepts worker_pool_snapshot as dict
# ------------------------------------------------------------------ #


def test_world_model_snapshot_accepts_worker_pool_snapshot():
    """WorldModelSnapshot must accept a populated worker_pool_snapshot dict."""
    pool_data = {
        'tools': {
            'chatgpt': {
                'available_accounts': 2,
                'exhausted_accounts': 1,
                'total_accounts': 3,
                'usable': True,
                'top_worker': {'email': 'alice@test.com', 'score': 0.9},
            },
            'groq': {
                'available_accounts': 0,
                'exhausted_accounts': 2,
                'total_accounts': 2,
                'usable': False,
                'top_worker': None,
            },
        },
        'total_usable_tools': 1,
        'total_exhausted_tools': 1,
        'summary': '1/2 tools usable',
    }
    snap = WorldModelSnapshot(worker_pool_snapshot=pool_data)
    assert snap.worker_pool_snapshot == pool_data
    assert snap.worker_pool_snapshot['tools']['chatgpt']['usable'] is True
    assert snap.worker_pool_snapshot['tools']['groq']['usable'] is False


# ------------------------------------------------------------------ #
# 2. WorldModelSnapshot with worker_pool_snapshot={} is valid (default)
# ------------------------------------------------------------------ #


def test_world_model_snapshot_default_worker_pool_empty():
    """Default WorldModelSnapshot must have worker_pool_snapshot == {}."""
    snap = WorldModelSnapshot()
    assert snap.worker_pool_snapshot == {}


# ------------------------------------------------------------------ #
# 3. WorldModelService populates worker_pool_snapshot with real data
# ------------------------------------------------------------------ #


def _make_world_model_service(**overrides):
    """Create a minimal WorldModelService for testing."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    from iabv_v15.services.evolution.world_model_service import WorldModelService
    defaults = dict(
        workspace_root=tmpdir,
        evolution_dir=tmpdir,
        auto_start=False,
        bootstrap_scan=False,
    )
    defaults.update(overrides)
    return WorldModelService(**defaults)


def test_world_model_service_populates_worker_pool_snapshot():
    """When estimate_available_workers returns data, worker_pool_snapshot
    must contain per-tool summaries."""
    fake_pool = {
        'workers': [
            {'email': 'a@t.com', 'tool': 'chatgpt', 'remaining_messages': 10, 'exhausted': False},
            {'email': 'b@t.com', 'tool': 'chatgpt', 'remaining_messages': 5, 'exhausted': False},
        ],
        'exhausted': [
            {'email': 'c@t.com', 'tool': 'claude', 'remaining_messages': 0, 'exhausted': True},
        ],
        'available_count': 2,
        'exhausted_count': 1,
        'by_tool': {
            'chatgpt': [
                {'email': 'a@t.com', 'remaining_messages': 10},
                {'email': 'b@t.com', 'remaining_messages': 5},
            ],
        },
        'total_remaining_messages': 15,
        'tools_available': ['chatgpt'],
    }

    with patch(
        'iabv_v15.services.evolution.world_model_service.WorldModelService._worker_pool_snapshot'
    ) as mock_wps:
        # Instead of mocking the internal, let's test _worker_pool_snapshot directly
        pass

    # Test _worker_pool_snapshot directly with mocked scanner
    svc = _make_world_model_service()

    with patch(
        'iabv_v15.services.account_resource_scanner.estimate_available_workers',
        return_value=fake_pool,
    ):
        result = svc._worker_pool_snapshot()

    assert 'tools' in result
    assert 'chatgpt' in result['tools']
    chatgpt = result['tools']['chatgpt']
    assert chatgpt['available_accounts'] == 2
    assert chatgpt['usable'] is True
    assert chatgpt['top_worker'] is not None
    assert chatgpt['top_worker']['email'] == 'a@t.com'

    # claude should show as exhausted (only in exhausted list)
    assert 'claude' in result['tools']
    claude = result['tools']['claude']
    assert claude['available_accounts'] == 0
    assert claude['exhausted_accounts'] == 1
    assert claude['usable'] is False
    assert claude['top_worker'] is None

    assert result['total_usable_tools'] >= 1
    assert 'summary' in result


# ------------------------------------------------------------------ #
# 4. WorldModelService leaves worker_pool_snapshot empty on failure
# ------------------------------------------------------------------ #


def test_world_model_service_empty_on_scanner_failure():
    """If account_resource_scanner raises, worker_pool_snapshot must be {}."""
    svc = _make_world_model_service()

    with patch(
        'iabv_v15.services.account_resource_scanner.estimate_available_workers',
        side_effect=RuntimeError('scanner crash'),
    ):
        result = svc._worker_pool_snapshot()

    assert result == {}


# ------------------------------------------------------------------ #
# 5. worker_pool_snapshot appears in scan_now() result
# ------------------------------------------------------------------ #


def test_worker_pool_snapshot_in_scan_now():
    """scan_now() must include worker_pool_snapshot in the returned snapshot."""
    svc = _make_world_model_service()

    fake_pool_result = {
        'tools': {'chatgpt': {'available_accounts': 1, 'exhausted_accounts': 0,
                               'total_accounts': 1, 'usable': True,
                               'top_worker': {'email': 'x@t.com', 'score': 5}}},
        'total_usable_tools': 1,
        'total_exhausted_tools': 0,
        'summary': '1/3 tools usable',
    }

    with patch.object(svc, '_worker_pool_snapshot', return_value=fake_pool_result):
        snapshot = svc.scan_now(reason='test', full=False)

    assert hasattr(snapshot, 'worker_pool_snapshot')
    assert snapshot.worker_pool_snapshot == fake_pool_result
    assert snapshot.worker_pool_snapshot['total_usable_tools'] == 1
