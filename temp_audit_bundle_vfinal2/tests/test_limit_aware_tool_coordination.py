"""Limit-aware free-tool coordination — mandatory tests.

Covers:
1. Task/tool affinity: live audit prefers desktop-validation-capable tool
2. Long-running task prefers long_running_capable tool
3. Quota fallback: exhausted tool yields to healthy one with traceable reason
4. Unknown quota: never invents exhaustion
5. PortableContext / RunHistory / metadata: selection summary and fallback
6. Regression guard for existing tests
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from iabv_v15.domain.models import (
    InferenceRequest,
    InteractionMode,
    ToolCard,
    ToolType,
)
from iabv_v15.services.tools.interaction_mode_selector import (
    InteractionModeSelector,
    _TASK_KIND_TOKENS,
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex[:8]}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_selector(workspace: Path):
    """Create a minimal InteractionModeSelector with real DB."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.storage import ArtifactStorage
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.services.tools.tool_registry import ToolRegistry

    db = AppDatabase(str(workspace / 'test.db'))
    storage = ArtifactStorage(str(workspace))
    repository = ToolRecordRepository(db, storage)
    registry = ToolRegistry(repository, adapters={})
    return InteractionModeSelector(registry, repository)


def _windsurf_card() -> ToolCard:
    return ToolCard(
        tool_id='windsurf_installed',
        title='Windsurf instalado',
        tool_type=ToolType.CODE_EDITOR,
        adapter_key='external_assistant',
        available=True,
        metadata={
            'assistant_kind': 'windsurf',
            'task_affinities': ['live_audit', 'desktop_validation', 'visual_feedback', 'windows_verification'],
            'interaction_cost': 'high',
            'manual_effort': 'high',
            'long_running_capable': False,
            'live_desktop_validation_capable': True,
            'repo_patch_capable': True,
            'reasoning_synthesis_capable': False,
        },
    )


def _devin_card() -> ToolCard:
    return ToolCard(
        tool_id='devin_api',
        title='Devin (Cognition AI)',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        available=True,
        metadata={
            'assistant_kind': 'devin',
            'task_affinities': ['long_implementation', 'pr_creation', 'refactor', 'test_writing', 'ci_fix'],
            'interaction_cost': 'low',
            'manual_effort': 'none',
            'long_running_capable': True,
            'live_desktop_validation_capable': False,
            'repo_patch_capable': True,
            'reasoning_synthesis_capable': True,
        },
    )


def _chatgpt_card() -> ToolCard:
    return ToolCard(
        tool_id='chatgpt_installed',
        title='ChatGPT instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        available=True,
        metadata={
            'assistant_kind': 'chatgpt',
            'task_affinities': ['reasoning_contrast', 'explanation', 'synthesis', 'brainstorm'],
            'interaction_cost': 'medium',
            'manual_effort': 'medium',
            'long_running_capable': False,
            'live_desktop_validation_capable': False,
            'repo_patch_capable': False,
            'reasoning_synthesis_capable': True,
        },
    )


def _codex_card() -> ToolCard:
    return ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        available=True,
        metadata={
            'assistant_kind': 'codex',
            'task_affinities': ['code_review', 'diagnostics', 'surgical_fix', 'architecture_audit'],
            'interaction_cost': 'low',
            'manual_effort': 'low',
            'long_running_capable': False,
            'live_desktop_validation_capable': False,
            'repo_patch_capable': True,
            'reasoning_synthesis_capable': True,
        },
    )


def _pool_with_chatgpt_exhausted() -> dict[str, Any]:
    """Pool where chatgpt is exhausted, windsurf and devin are available."""
    return {
        'workers': [
            {'email': 'a@test.com', 'tool': 'windsurf', 'remaining_messages': 8, 'limit': 10, 'exhausted': False},
            {'email': 'b@test.com', 'tool': 'devin', 'remaining_messages': 50, 'limit': 100, 'exhausted': False},
        ],
        'exhausted': [
            {'email': 'c@test.com', 'tool': 'chatgpt', 'remaining_messages': 0, 'limit': 40, 'exhausted': True},
        ],
        'available_count': 2,
        'exhausted_count': 1,
        'by_tool': {
            'windsurf': [{'email': 'a@test.com', 'remaining_messages': 8}],
            'devin': [{'email': 'b@test.com', 'remaining_messages': 50}],
        },
        'total_remaining_messages': 58,
        'tools_available': ['windsurf', 'devin'],
    }


def _pool_all_healthy() -> dict[str, Any]:
    return {
        'workers': [
            {'email': 'a@test.com', 'tool': 'windsurf', 'remaining_messages': 8, 'limit': 10, 'exhausted': False},
            {'email': 'b@test.com', 'tool': 'devin', 'remaining_messages': 50, 'limit': 100, 'exhausted': False},
            {'email': 'c@test.com', 'tool': 'chatgpt', 'remaining_messages': 20, 'limit': 40, 'exhausted': False},
        ],
        'exhausted': [],
        'available_count': 3,
        'exhausted_count': 0,
        'by_tool': {
            'windsurf': [{'email': 'a@test.com', 'remaining_messages': 8}],
            'devin': [{'email': 'b@test.com', 'remaining_messages': 50}],
            'chatgpt': [{'email': 'c@test.com', 'remaining_messages': 20}],
        },
        'total_remaining_messages': 78,
        'tools_available': ['windsurf', 'devin', 'chatgpt'],
    }


# ──────────────────────────────────────────────────────────────
# 1. Task/tool affinity: live audit → desktop-capable tool
# ──────────────────────────────────────────────────────────────

class TestTaskToolAffinity:
    def test_live_audit_prefers_desktop_validation_capable(self):
        """A live Windows audit must prefer a tool with live_desktop_validation_capable=True."""
        windsurf = _windsurf_card()
        devin = _devin_card()
        chatgpt = _chatgpt_card()

        affinity_windsurf = InteractionModeSelector._affinity_score(windsurf, 'live_audit')
        affinity_devin = InteractionModeSelector._affinity_score(devin, 'live_audit')
        affinity_chatgpt = InteractionModeSelector._affinity_score(chatgpt, 'live_audit')

        assert affinity_windsurf > affinity_devin, \
            f'Windsurf ({affinity_windsurf}) should score higher than Devin ({affinity_devin}) for live_audit'
        assert affinity_windsurf > affinity_chatgpt, \
            f'Windsurf ({affinity_windsurf}) should score higher than ChatGPT ({affinity_chatgpt}) for live_audit'

    def test_task_kind_detection_live_audit(self):
        request = InferenceRequest(user_goal='verificar en windows que la app corre auditoria live')
        kind = InteractionModeSelector._detect_task_kind(request)
        assert kind == 'live_audit', f'Expected live_audit, got {kind}'

    def test_affinity_without_metadata_returns_neutral(self):
        card = ToolCard(tool_id='plain', title='Plain', tool_type=ToolType.SHELL, adapter_key='shell', metadata={})
        score = InteractionModeSelector._affinity_score(card, 'live_audit')
        assert score == 0.5, f'Expected neutral 0.5 for tool without affinities, got {score}'


# ──────────────────────────────────────────────────────────────
# 2. Long-running implementation → long_running_capable tool
# ──────────────────────────────────────────────────────────────

class TestLongRunningPreference:
    def test_long_implementation_prefers_long_running_capable(self):
        """A long implementation task must prefer a tool marked long_running_capable."""
        devin = _devin_card()
        windsurf = _windsurf_card()
        codex = _codex_card()

        affinity_devin = InteractionModeSelector._affinity_score(devin, 'long_implementation')
        affinity_windsurf = InteractionModeSelector._affinity_score(windsurf, 'long_implementation')
        affinity_codex = InteractionModeSelector._affinity_score(codex, 'long_implementation')

        assert affinity_devin > affinity_windsurf, \
            f'Devin ({affinity_devin}) should score higher than Windsurf ({affinity_windsurf}) for long_implementation'
        assert affinity_devin > affinity_codex, \
            f'Devin ({affinity_devin}) should score higher than Codex ({affinity_codex}) for long_implementation'

    def test_task_kind_detection_implementation(self):
        request = InferenceRequest(user_goal='implementa el sistema de afinidades y crea pr con tests')
        kind = InteractionModeSelector._detect_task_kind(request)
        assert kind == 'long_implementation', f'Expected long_implementation, got {kind}'


# ──────────────────────────────────────────────────────────────
# 3. Quota/usable fallback: exhausted → healthy with reason
# ──────────────────────────────────────────────────────────────

class TestQuotaFallback:
    def test_exhausted_tool_gets_zero_quota_score(self):
        """An exhausted tool's quota score must be 0.0."""
        chatgpt = _chatgpt_card()
        pool = _pool_with_chatgpt_exhausted()

        score = InteractionModeSelector._quota_score(chatgpt, pool)
        assert score == 0.0, f'Expected 0.0 for exhausted chatgpt, got {score}'

    def test_healthy_tool_gets_positive_quota_score(self):
        devin = _devin_card()
        pool = _pool_with_chatgpt_exhausted()

        score = InteractionModeSelector._quota_score(devin, pool)
        assert score > 0.0, f'Expected positive quota score for healthy devin, got {score}'

    def test_quota_status_label_exhausted(self):
        chatgpt = _chatgpt_card()
        pool = _pool_with_chatgpt_exhausted()

        label = InteractionModeSelector._quota_status_label(chatgpt, pool)
        assert label == 'exhausted', f'Expected exhausted, got {label}'

    def test_quota_status_label_available(self):
        devin = _devin_card()
        pool = _pool_with_chatgpt_exhausted()

        label = InteractionModeSelector._quota_status_label(devin, pool)
        assert label == 'available', f'Expected available, got {label}'

    def test_selection_changes_with_traceable_reason(self):
        """When a tool is exhausted and another is healthy, selection must change with reason."""
        chatgpt = _chatgpt_card()
        devin = _devin_card()
        pool = _pool_with_chatgpt_exhausted()

        chatgpt_q = InteractionModeSelector._quota_score(chatgpt, pool)
        devin_q = InteractionModeSelector._quota_score(devin, pool)

        assert devin_q > chatgpt_q, \
            f'Devin quota ({devin_q}) should exceed exhausted ChatGPT quota ({chatgpt_q})'

        chatgpt_status = InteractionModeSelector._quota_status_label(chatgpt, pool)
        assert chatgpt_status == 'exhausted'


# ──────────────────────────────────────────────────────────────
# 4. Unknown quota: must NOT invent exhaustion
# ──────────────────────────────────────────────────────────────

class TestUnknownQuota:
    def test_no_pool_returns_neutral_score(self):
        """Without worker_pool, quota score must be neutral (0.5), not 0."""
        chatgpt = _chatgpt_card()
        score = InteractionModeSelector._quota_score(chatgpt, None)
        assert score == 0.5, f'Expected neutral 0.5 without pool, got {score}'

    def test_no_pool_returns_unknown_status(self):
        chatgpt = _chatgpt_card()
        label = InteractionModeSelector._quota_status_label(chatgpt, None)
        assert label == 'unknown', f'Expected unknown, got {label}'

    def test_tool_not_in_pool_returns_unknown(self):
        """A tool with no workers in the pool must be unknown, not exhausted."""
        codex = _codex_card()
        pool = _pool_with_chatgpt_exhausted()  # no codex workers

        label = InteractionModeSelector._quota_status_label(codex, pool)
        assert label == 'unknown', f'Expected unknown for codex not in pool, got {label}'

        score = InteractionModeSelector._quota_score(codex, pool)
        assert score == 0.5, f'Expected neutral 0.5 for codex not in pool, got {score}'

    def test_never_invents_exhaustion(self):
        """Even with an empty pool, must return unknown/neutral, never exhausted."""
        cards = [_windsurf_card(), _devin_card(), _chatgpt_card(), _codex_card()]
        empty_pool: dict[str, Any] = {
            'workers': [], 'exhausted': [], 'available_count': 0,
            'exhausted_count': 0, 'by_tool': {}, 'total_remaining_messages': 0,
            'tools_available': [],
        }
        for card in cards:
            label = InteractionModeSelector._quota_status_label(card, empty_pool)
            assert label == 'unknown', f'{card.tool_id} should be unknown in empty pool, got {label}'
            score = InteractionModeSelector._quota_score(card, empty_pool)
            assert score == 0.5, f'{card.tool_id} should have neutral score in empty pool, got {score}'


# ──────────────────────────────────────────────────────────────
# 5. PortableContext / RunHistory / metadata summary
# ──────────────────────────────────────────────────────────────

class TestSelectionSummary:
    def test_selection_summary_contains_required_fields(self):
        """The _selection_summary must contain selected_tool, reason, quota_status."""
        from iabv_v15.services.tools.interaction_mode_selector import _CandidateAssessment

        best = _CandidateAssessment(
            card=_windsurf_card(),
            mode=InteractionMode.UI,
            scores={'affinity': 1.0, 'quota': 0.8},
            total_score=12.5,
            reason='modo=ui | afinidad=1.00 | cuota=0.80',
            quota_status='available',
        )
        runner_up = _CandidateAssessment(
            card=_devin_card(),
            mode=InteractionMode.BACKGROUND,
            scores={'affinity': 0.2, 'quota': 0.5},
            total_score=9.0,
            reason='modo=background | afinidad=0.20',
            quota_status='available',
        )
        summary = InteractionModeSelector._selection_summary(best, [best, runner_up], task_kind='live_audit')

        assert summary['selected_tool'] == 'windsurf_installed'
        assert summary['quota_status'] == 'available'
        assert summary.get('task_kind') == 'live_audit'
        assert 'alternatives_discarded' in summary
        assert len(summary['alternatives_discarded']) >= 1

    def test_build_tool_selection_summary_gate_not_ran(self):
        """When gate didn't run, summary must indicate it."""
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import _build_tool_selection_summary

        result = _build_tool_selection_summary(
            worker_gate={}, gate_ran=False, governance={}, session_metadata={},
        )
        assert result['reason'] == 'gate_not_ran'
        assert result['fallback_used'] is False

    def test_build_tool_selection_summary_with_gate(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import _build_tool_selection_summary

        gate = {
            'usable': True,
            'top_worker': {'tool': 'chatgpt', 'email': 'user@test.com', 'remaining': 15},
            'recommended_account': {'tool': 'chatgpt', 'email': 'user@test.com'},
            'ranked_workers': [
                {'tool': 'chatgpt', 'email': 'user@test.com'},
                {'tool': 'devin', 'email': 'dev@test.com'},
            ],
            'account_selection_source': 'auto_ranked',
            'fallback_used': False,
        }
        result = _build_tool_selection_summary(
            worker_gate=gate,
            gate_ran=True,
            governance={'assistant_kind': 'chatgpt'},
            session_metadata={},
        )
        assert result['selected_tool'] == 'chatgpt'
        assert result['selected_email'] == 'user@test.com'
        assert result['fallback_used'] is False
        assert result['quota_confirmed'] is True
        assert len(result['alternatives_discarded']) >= 1

    def test_build_tool_selection_summary_with_fallback(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import _build_tool_selection_summary

        gate = {
            'usable': True,
            'top_worker': {'tool': 'devin', 'email': 'dev@test.com', 'remaining': 50},
            'recommended_account': {'tool': 'chatgpt', 'email': 'user@test.com'},
            'ranked_workers': [],
            'account_selection_source': 'user_approved_fallback',
            'fallback_used': True,
        }
        result = _build_tool_selection_summary(
            worker_gate=gate,
            gate_ran=True,
            governance={'assistant_kind': 'devin'},
            session_metadata={},
        )
        assert result['fallback_used'] is True
        assert result['fallback_origin'] == 'chatgpt'


# ──────────────────────────────────────────────────────────────
# 6. Regression — existing tests must still pass
# ──────────────────────────────────────────────────────────────

class TestRegressionToolRegistry:
    """Ensure ToolRegistry seed_defaults still works with affinity metadata."""

    def test_seed_defaults_include_affinities(self):
        workspace = _workspace('seed_affinities')
        try:
            from iabv_v15.infra.persistence.database import AppDatabase
            from iabv_v15.infra.persistence.storage import ArtifactStorage
            from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
            from iabv_v15.services.tools.tool_registry import ToolRegistry

            db = AppDatabase(str(workspace / 'test.db'))
            storage = ArtifactStorage(str(workspace))
            repository = ToolRecordRepository(db, storage)
            registry = ToolRegistry(repository, adapters={})

            cards = registry.list_cards()
            external_tools_with_affinities = [
                c for c in cards
                if c.metadata.get('task_affinities')
            ]
            assert len(external_tools_with_affinities) >= 5, \
                f'Expected at least 5 tools with task_affinities, got {len(external_tools_with_affinities)}'

            for card in external_tools_with_affinities:
                meta = card.metadata
                assert isinstance(meta.get('task_affinities'), list), \
                    f'{card.tool_id} task_affinities should be list'
                assert 'interaction_cost' in meta, f'{card.tool_id} missing interaction_cost'
                assert 'long_running_capable' in meta, f'{card.tool_id} missing long_running_capable'
                assert 'live_desktop_validation_capable' in meta, f'{card.tool_id} missing live_desktop_validation_capable'
                assert 'repo_patch_capable' in meta, f'{card.tool_id} missing repo_patch_capable'
                assert 'reasoning_synthesis_capable' in meta, f'{card.tool_id} missing reasoning_synthesis_capable'
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_windsurf_has_desktop_validation(self):
        workspace = _workspace('windsurf_cap')
        try:
            from iabv_v15.infra.persistence.database import AppDatabase
            from iabv_v15.infra.persistence.storage import ArtifactStorage
            from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
            from iabv_v15.services.tools.tool_registry import ToolRegistry

            db = AppDatabase(str(workspace / 'test.db'))
            storage = ArtifactStorage(str(workspace))
            repository = ToolRecordRepository(db, storage)
            registry = ToolRegistry(repository, adapters={})

            card = registry.get_card('windsurf_installed')
            assert card is not None, 'windsurf_installed card should exist'
            assert card.metadata.get('live_desktop_validation_capable') is True
            assert 'live_audit' in card.metadata.get('task_affinities', [])
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_devin_has_long_running(self):
        workspace = _workspace('devin_cap')
        try:
            from iabv_v15.infra.persistence.database import AppDatabase
            from iabv_v15.infra.persistence.storage import ArtifactStorage
            from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
            from iabv_v15.services.tools.tool_registry import ToolRegistry

            db = AppDatabase(str(workspace / 'test.db'))
            storage = ArtifactStorage(str(workspace))
            repository = ToolRecordRepository(db, storage)
            registry = ToolRegistry(repository, adapters={})

            card = registry.get_card('devin_api')
            assert card is not None, 'devin_api card should exist'
            assert card.metadata.get('long_running_capable') is True
            assert 'long_implementation' in card.metadata.get('task_affinities', [])
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
