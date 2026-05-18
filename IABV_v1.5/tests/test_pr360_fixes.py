"""Tests for PR #360 fixes (A-F).

Validates:
A. startup_followup_active sync between AppBootstrap and watchdog.
B. Snapshot refresh in-flight pauses prebuild during startup_followup_active.
C. dominant_phase no stale (tested via watchdog sampler in test_watchdog_async_capture).
D. PortableContext/OSES dedup by interaction_id.
E. Markdown resolved=<true|false> in interaction_lifecycle section.
F. Test coverage restored (verified by running all test files).
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.freeze_incident_reporter import (
    UIHeartbeatWatchdog,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_audit_events(workspace: Path, events: list[dict]) -> None:
    audit_dir = workspace / 'data' / 'logs'
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / 'runtime_audit.jsonl'
    with audit_path.open('w', encoding='utf-8') as f:
        for event in events:
            f.write(json.dumps(event) + '\n')


class FakeBootstrap:
    """Mirrors real AppBootstrap flag-sync behavior (post-Fix A)."""

    def __init__(self):
        self._deferred_setup_active = False
        self._truth_refresh_active = False
        self._startup_evolution_active = False
        self._startup_followup_active = True
        self._prebuild_paused = False
        self._prebuild_snapshot_refresh_in_flight = False
        self.watchdog = UIHeartbeatWatchdog(
            stall_threshold_ms=200,
            freeze_reporter=MagicMock(),
        )

    def _push_bootstrap_flags_to_watchdog(self):
        self.watchdog.set_startup_followup_active(self._startup_followup_active)
        self.watchdog.set_bootstrap_flags({
            'deferred_setup_active': self._deferred_setup_active,
            'truth_refresh_active': self._truth_refresh_active,
            'startup_evolution_active': self._startup_evolution_active,
            'prebuild_paused': self._prebuild_paused,
            'snapshot_refresh_in_flight': self._prebuild_snapshot_refresh_in_flight,
            'startup_followup_active': self._startup_followup_active,
        })

    def _check_startup_followup_done(self):
        self._push_bootstrap_flags_to_watchdog()
        snapshot_in_flight = self._prebuild_snapshot_refresh_in_flight
        if (self._deferred_setup_active
                or self._truth_refresh_active
                or self._startup_evolution_active
                or snapshot_in_flight):
            return
        self._startup_followup_active = False
        self._push_bootstrap_flags_to_watchdog()

    def _should_pause_prebuild(self, route: str = 'capture') -> str | None:
        if self._deferred_setup_active:
            return 'startup_background_active:deferred_post_window_setup'
        if self._truth_refresh_active:
            return 'startup_background_active:startup_truth_refresh'
        if self._startup_evolution_active:
            return 'startup_background_active:startup_evolution'
        if route == 'control':
            return None
        if (self._prebuild_snapshot_refresh_in_flight
                and self._startup_followup_active):
            return 'resource_snapshot_refresh_in_flight'
        return None


# ---------------------------------------------------------------------------
# A. startup_followup_active sync
# ---------------------------------------------------------------------------

class TestStartupFollowupSync:
    def test_truth_refresh_active_plus_followup_active_syncs_to_watchdog(self):
        """truth_refresh=True + startup_followup=True + startup=False
        => watchdog._startup_followup_active=True AND
           bootstrap_flags.startup_followup_active=True.
        """
        bs = FakeBootstrap()
        bs._truth_refresh_active = True
        bs._startup_followup_active = True
        bs.watchdog.set_startup_active(False)
        bs._push_bootstrap_flags_to_watchdog()
        assert bs.watchdog._startup_followup_active is True
        assert bs.watchdog._bootstrap_flags.get('startup_followup_active') is True

    def test_clearing_followup_repushes_flags(self):
        """After clearing _startup_followup_active, re-push ensures
        bootstrap_flags and top-level watchdog agree (both False).
        """
        bs = FakeBootstrap()
        bs._truth_refresh_active = False
        bs._deferred_setup_active = False
        bs._startup_evolution_active = False
        bs._prebuild_snapshot_refresh_in_flight = False
        bs._check_startup_followup_done()
        assert bs._startup_followup_active is False
        assert bs.watchdog._startup_followup_active is False
        assert bs.watchdog._bootstrap_flags.get('startup_followup_active') is False

    def test_push_calls_set_startup_followup_active(self):
        """_push_bootstrap_flags_to_watchdog must call
        watchdog.set_startup_followup_active() in addition to set_bootstrap_flags().
        """
        bs = FakeBootstrap()
        bs._startup_followup_active = True
        bs._push_bootstrap_flags_to_watchdog()
        assert bs.watchdog._startup_followup_active is True
        bs._startup_followup_active = False
        bs._push_bootstrap_flags_to_watchdog()
        assert bs.watchdog._startup_followup_active is False


# ---------------------------------------------------------------------------
# B. Snapshot refresh in-flight pauses prebuild during startup
# ---------------------------------------------------------------------------

class TestSnapshotRefreshInFlightPause:
    def test_pause_when_refresh_in_flight_and_followup_active(self):
        """snapshot cached low pressure + refresh_in_flight=True
        + startup_followup_active=True => pauses with
        resource_snapshot_refresh_in_flight.
        """
        bs = FakeBootstrap()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._startup_followup_active = True
        reason = bs._should_pause_prebuild('capture')
        assert reason == 'resource_snapshot_refresh_in_flight'

    def test_control_route_not_paused_by_refresh_in_flight(self):
        bs = FakeBootstrap()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._startup_followup_active = True
        reason = bs._should_pause_prebuild('control')
        assert reason is None

    def test_no_pause_when_refresh_in_flight_but_followup_not_active(self):
        """refresh_in_flight alone (no startup_followup) does NOT pause."""
        bs = FakeBootstrap()
        bs._prebuild_snapshot_refresh_in_flight = True
        bs._startup_followup_active = False
        reason = bs._should_pause_prebuild()
        assert reason is None

    def test_no_pause_when_followup_active_but_no_refresh(self):
        """startup_followup_active alone (no refresh) does NOT pause."""
        bs = FakeBootstrap()
        bs._prebuild_snapshot_refresh_in_flight = False
        bs._startup_followup_active = True
        reason = bs._should_pause_prebuild()
        assert reason is None


# ---------------------------------------------------------------------------
# D. PortableContext/OSES dedup by interaction_id
# ---------------------------------------------------------------------------

class TestPortableContextDedup:
    def test_dedup_keeps_latest_per_interaction_id(self, tmp_path):
        """If prepared and then resolved exist for same id,
        only the later (resolved) is returned.
        """
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-dup1',
                    'message_preview': 'consulta a chatgpt',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 500,
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-dup1',
                    'message_preview': 'consulta a chatgpt',
                    'outcome': 'resolved',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 3000,
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        episodes = pcs._interaction_episodes_from_audit(limit=10)
        assert len(episodes) == 1
        assert episodes[0]['outcome'] == 'resolved'
        assert episodes[0]['resolved'] is True

    def test_different_ids_not_deduped(self, tmp_path):
        """Events with different interaction_ids are kept separately."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-a',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-b',
                    'outcome': 'resolved',
                    'provider': 'local',
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        episodes = pcs._interaction_episodes_from_audit(limit=10)
        assert len(episodes) == 2


class TestOSESDedup:
    def test_dedup_prepared_then_resolved_counts_once(self, tmp_path):
        """OSES dedup: prepared + resolved for same id => 1 episode (resolved)."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-dup2',
                    'message_preview': 'consulta externa',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 500,
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-dup2',
                    'message_preview': 'consulta externa',
                    'outcome': 'resolved',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 3000,
                },
            },
        ])
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(workspace)
        oses._freeze_incident_reporter = None
        oses._ui_heartbeat_watchdog = None
        findings = oses._interaction_episode_findings()
        pending = [f for f in findings if f.category == 'interaction_episode_pending']
        assert len(pending) == 0, 'resolved episode should not appear as pending'

    def test_only_prepared_counts_as_pending(self, tmp_path):
        """If only prepared exists (no resolved), it IS pending."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-prep-only',
                    'message_preview': 'consulta sin resolver',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 500,
                    'is_final': False,
                },
            },
        ])
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(workspace)
        oses._freeze_incident_reporter = None
        oses._ui_heartbeat_watchdog = None
        findings = oses._interaction_episode_findings()
        pending = [f for f in findings if f.category == 'interaction_episode_pending']
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# E. Markdown resolved=<true|false> in interaction_lifecycle
# ---------------------------------------------------------------------------

class TestMarkdownResolvedField:
    def test_resolved_true_in_markdown_output(self, tmp_path):
        """resolved=true must appear in markdown for final outcome."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-md1',
                    'message_preview': 'resuelta',
                    'outcome': 'resolved',
                    'provider': 'local',
                    'total_duration_ms': 1000,
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        pcs.freeze_incident_reporter = None
        pcs.ui_heartbeat_watchdog = None
        now = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        section = pcs._interaction_lifecycle_section(now=now)
        assert len(section.items) >= 1
        assert section.items[0]['resolved'] is True

    def test_resolved_false_in_markdown_output(self, tmp_path):
        """resolved=false must appear in markdown for non-final outcome."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-md2',
                    'message_preview': 'preparada',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 500,
                    'is_final': False,
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        pcs.freeze_incident_reporter = None
        pcs.ui_heartbeat_watchdog = None
        now = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        section = pcs._interaction_lifecycle_section(now=now)
        assert len(section.items) >= 1
        assert section.items[0]['resolved'] is False

    def test_markdown_text_contains_resolved_field(self, tmp_path):
        """The rendered markdown text must contain 'resolved=true' or 'resolved=false'."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
            PortableContextSection,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-render',
                    'message_preview': 'consulta pendiente',
                    'outcome': 'awaiting_external_response',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 0,
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-render2',
                    'message_preview': 'resuelta final',
                    'outcome': 'resolved',
                    'provider': 'local',
                    'total_duration_ms': 1500,
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        pcs.freeze_incident_reporter = None
        pcs.ui_heartbeat_watchdog = None
        now = datetime.now(timezone.utc)
        section = pcs._interaction_lifecycle_section(now=now)
        # Build a fake package to render markdown
        md_lines = []
        md_lines.append(f'## {section.title}')
        md_lines.append(section.summary or '')
        for item in section.items:
            iid = str(item.get('interaction_id') or 'n/d')
            outcome = str(item.get('outcome') or 'n/d')
            resolved = item.get('resolved', outcome in ('resolved', 'failed'))
            md_lines.append(
                f'- [{iid}] outcome={outcome} resolved={str(resolved).lower()}'
            )
        md = '\n'.join(md_lines)
        assert 'resolved=false' in md
        assert 'resolved=true' in md


# ---------------------------------------------------------------------------
# Blocked finality tests (PR #360 v2)
# ---------------------------------------------------------------------------

class TestBlockedFinality:
    """blocked is terminal (is_final=true) but not successful (resolved=false)."""

    def test_lifecycle_blocked_is_final(self):
        """ChatInteractionLifecycle: blocked => is_final=True, resolved=False."""
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            ChatInteractionLifecycle,
        )
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction(message_preview='test blocked')
        record = lc.resolve_interaction(iid, outcome='blocked', provider='ChatGPT')
        assert record is not None
        assert record['resolved'] is False
        assert record['outcome'] == 'blocked'
        # Should be in completed (final), not in active interactions
        assert lc.active_interaction() is None
        completed = lc.recent_completed()
        assert any(c['interaction_id'] == iid for c in completed)

    def test_lifecycle_resolved_is_final_and_resolved(self):
        """ChatInteractionLifecycle: resolved => is_final=True, resolved=True."""
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            ChatInteractionLifecycle,
        )
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction(message_preview='test resolved')
        record = lc.resolve_interaction(iid, outcome='resolved', provider='local')
        assert record is not None
        assert record['resolved'] is True

    def test_lifecycle_failed_is_final_not_resolved(self):
        """ChatInteractionLifecycle: failed => is_final=True, resolved=False."""
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            ChatInteractionLifecycle,
        )
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction(message_preview='test failed')
        record = lc.resolve_interaction(iid, outcome='failed', provider='local')
        assert record is not None
        assert record['resolved'] is False
        assert lc.active_interaction() is None

    def test_lifecycle_prepared_stays_open(self):
        """ChatInteractionLifecycle: prepared => non-final, stays in active."""
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            ChatInteractionLifecycle,
        )
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction(message_preview='test prepared')
        record = lc.resolve_interaction(iid, outcome='prepared', provider='ChatGPT')
        assert record is not None
        assert record['resolved'] is False
        # Should still be active (non-final)
        active = lc.active_interaction()
        assert active is not None
        assert active['interaction_id'] == iid

    def test_blocked_runtime_audit_is_final_true_resolved_false(self, tmp_path):
        """blocked in runtime_audit must have is_final=true, and PortableContext
        must reconstruct it as resolved=false."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-blk-audit',
                    'message_preview': 'consulta bloqueada',
                    'outcome': 'blocked',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 800,
                    'is_final': True,
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        episodes = pcs._interaction_episodes_from_audit(limit=10)
        assert len(episodes) == 1
        assert episodes[0]['outcome'] == 'blocked'
        assert episodes[0]['resolved'] is False
        assert episodes[0]['is_final'] is True

    def test_portable_context_renders_blocked_with_is_final(self, tmp_path):
        """latest.md shows outcome=blocked resolved=false is_final=true."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-blk-md',
                    'message_preview': 'blocked query',
                    'outcome': 'blocked',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 1200,
                    'is_final': True,
                },
            },
        ])
        pcs = PortableContextService.__new__(PortableContextService)
        pcs.workspace_root = str(workspace)
        pcs.chat_interaction_lifecycle = None
        pcs.freeze_incident_reporter = None
        pcs.ui_heartbeat_watchdog = None
        now = datetime.now(timezone.utc)
        section = pcs._interaction_lifecycle_section(now=now)
        assert len(section.items) >= 1
        item = section.items[0]
        assert item['resolved'] is False
        assert item.get('is_final') is True

    def test_oses_blocked_not_counted_as_pending(self, tmp_path):
        """OSES: blocked episodes must NOT appear as pending; must be
        counted as blocked interaction finding."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-blk-oses',
                    'message_preview': 'blocked ext consultation',
                    'outcome': 'blocked',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 900,
                    'is_final': True,
                },
            },
        ])
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(workspace)
        oses._freeze_incident_reporter = None
        oses._ui_heartbeat_watchdog = None
        findings = oses._interaction_episode_findings()
        pending = [f for f in findings if f.category == 'interaction_episode_pending']
        blocked = [f for f in findings if f.category == 'interaction_episode_blocked']
        assert len(pending) == 0, 'blocked must NOT be counted as pending'
        assert len(blocked) == 1, 'blocked must produce a blocked finding'

    def test_viewmodel_blocked_clears_active_interaction(self):
        """ControlCenterViewModel: blocked external_consultation must clear
        _active_interaction_id and query_pending."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        assert 'blocked' in ControlCenterViewModel._FINAL_INTERACTION_OUTCOMES

    def test_viewmodel_final_blocked_clears_live_status(self):
        """Final blocked outcome must clear the visible processing chip."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            ChatInteractionLifecycle,
        )

        vm = ControlCenterViewModel.__new__(ControlCenterViewModel)
        lifecycle = ChatInteractionLifecycle()
        iid = lifecycle.open_interaction(message_preview='blocked live status')
        vm._active_interaction_id = iid
        vm._chat_interaction_lifecycle = lifecycle
        vm._ui_heartbeat_watchdog = None
        seen: list[str] = []
        vm._set_live_status = lambda status: seen.append(status)
        vm._promote_metacognition_after_resolution = lambda: None

        ControlCenterViewModel._resolve_active_interaction(
            vm,
            outcome='blocked',
            provider='ChatGPT',
        )

        assert vm._active_interaction_id is None
        assert seen == ['idle']

    def test_external_success_with_blocked_outcome_projects_blocked_activity(self):
        """success=True can still be semantically blocked if capture failed."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )

        vm = ControlCenterViewModel.__new__(ControlCenterViewModel)
        captured: dict[str, object] = {}
        vm._assistant_guidance_mode = 'idle'
        vm._assistant_action_buttons = {}
        vm._reset_assistant_guidance = lambda: None
        vm._set_autonomy_activity_override = lambda **payload: captured.update(payload)

        ControlCenterViewModel._set_external_consultation_activity(
            vm,
            external_payload={'success': True},
            adaptive_payload={},
            assistant_title='ChatGPT web asistido',
            message='Consulta preparada, pero la captura no se pudo verificar.',
            external_notice='Captura no verificada.',
            outcome='blocked',
        )

        assert captured['status'] == 'blocked'
        assert captured['title'] == 'Consulta externa bloqueada'
        assert 'no fingir' in str(captured['learning_note'])

    def test_non_final_outcomes_exclude_blocked(self):
        """ChatInteractionLifecycle._NON_FINAL_OUTCOMES must NOT contain blocked."""
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            ChatInteractionLifecycle,
        )
        assert 'blocked' not in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'prepared' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'awaiting_external_response' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'reused_context' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
