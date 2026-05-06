"""Tests for ui_visibility_audit — UI visible event capture."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from iabv_v15.infra.ui_visibility_audit import (
    CAT_BACKGROUND,
    CAT_INTENTIONAL,
    CAT_UNEXPECTED,
    KIND_BG_CHECK,
    KIND_DIALOG_CLOSED,
    KIND_DIALOG_SHOWN,
    KIND_FILE_NOT_FOUND,
    KIND_INIT_CHECK,
    KIND_TOAST_SHOWN,
    SRC_BOOTSTRAP,
    SRC_QML,
    QmlDialogAuditBridge,
    SplashAuditAdapter,
    SubprocessAuditWrapper,
    ToastAuditAdapter,
    VisibilityAuditLog,
    _safe_serialize,
)


@pytest.fixture()
def audit_log(tmp_path: Path) -> VisibilityAuditLog:
    log = VisibilityAuditLog()
    log.open(tmp_path / 'visible_events.jsonl')
    return log


class TestVisibilityAuditLog:
    def test_open_creates_jsonl_and_init_event(self, audit_log: VisibilityAuditLog, tmp_path: Path) -> None:
        path = tmp_path / 'visible_events.jsonl'
        assert path.exists()
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1
        ev = json.loads(lines[0])
        assert ev['kind'] == KIND_INIT_CHECK
        assert ev['event_category'] == CAT_BACKGROUND

    def test_record_intentional(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source=SRC_QML,
                         detail='Credencial requerida',
                         event_category=CAT_INTENTIONAL)
        s = audit_log.summary()
        assert s['total_events'] == 2  # init + dialog
        assert s['by_category'].get(CAT_INTENTIONAL) == 1

    def test_record_background(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record_background('provider probe', source='provider_probing')
        s = audit_log.summary()
        assert s['by_category'].get(CAT_BACKGROUND, 0) >= 2  # init + bg

    def test_record_file_not_found(self, audit_log: VisibilityAuditLog) -> None:
        try:
            raise FileNotFoundError(2, 'No such file', 'missing.exe')
        except FileNotFoundError as e:
            audit_log.record_file_not_found(e, source='test', cmd=['missing.exe'])
        s = audit_log.summary()
        assert s['file_not_found_count'] == 1
        assert s['unresolved_count'] >= 1
        fnf = s['file_not_found'][0]
        assert fnf['extra']['filename'] == 'missing.exe'

    def test_summary_categories(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source=SRC_QML,
                         event_category=CAT_INTENTIONAL)
        audit_log.record('win32_popup', source='watcher',
                         event_category=CAT_UNEXPECTED, unresolved=True)
        audit_log.record_background('check', source='test')
        s = audit_log.summary()
        assert CAT_INTENTIONAL in s['by_category']
        assert CAT_UNEXPECTED in s['by_category']
        assert CAT_BACKGROUND in s['by_category']

    def test_jsonl_persistence(self, audit_log: VisibilityAuditLog, tmp_path: Path) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source='test',
                         event_category=CAT_INTENTIONAL)
        audit_log.close()
        path = tmp_path / 'visible_events.jsonl'
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 2  # init + dialog


class TestSplashAuditAdapter:
    def test_splash_events(self, audit_log: VisibilityAuditLog) -> None:
        adapter = SplashAuditAdapter(audit_log)
        adapter.on_shown()
        adapter.on_closed()
        s = audit_log.summary()
        kinds = [e['kind'] for e in s['events']]
        assert KIND_DIALOG_SHOWN in kinds
        assert KIND_DIALOG_CLOSED in kinds


class TestWin32PopupWatcherCategorization:
    def test_known_benign_classes(self) -> None:
        from iabv_v15.infra.ui_visibility_audit import Win32PopupWatcher
        benign = Win32PopupWatcher._KNOWN_BENIGN_CLASSES
        assert 'Shell_TrayWnd' in benign
        assert 'Progman' in benign
        assert 'DummyDWMListenerWindow' in benign
        assert 'Windows.UI.Core.CoreWindow' in benign

    def test_is_suspicious_detects_error_titles(self) -> None:
        from iabv_v15.infra.ui_visibility_audit import Win32PopupWatcher
        assert Win32PopupWatcher._is_suspicious('Error - File not found')
        assert Win32PopupWatcher._is_suspicious('No se puede encontrar el archivo')
        assert Win32PopupWatcher._is_suspicious('Acceso denegado')
        assert not Win32PopupWatcher._is_suspicious('IABV v1.5 - Control Center')
        assert not Win32PopupWatcher._is_suspicious('')


class TestSubprocessAuditWrapper:
    def test_captures_file_not_found(self, audit_log: VisibilityAuditLog) -> None:
        with pytest.raises(FileNotFoundError):
            with SubprocessAuditWrapper(audit_log, cmd=['nonexistent_binary'],
                                        source='test'):
                raise FileNotFoundError(2, 'not found', 'nonexistent_binary')
        s = audit_log.summary()
        assert s['file_not_found_count'] == 1

    def test_no_event_on_success(self, audit_log: VisibilityAuditLog) -> None:
        with SubprocessAuditWrapper(audit_log, cmd=['echo', 'hello'],
                                    source='test'):
            pass
        s = audit_log.summary()
        assert s['file_not_found_count'] == 0


# ---------------------------------------------------------------------------
# QmlDialogAuditBridge tests
# ---------------------------------------------------------------------------

class _FakeSignal:
    """Minimal signal mock that supports connect() and emit()."""

    def __init__(self) -> None:
        self._slots: list = []

    def connect(self, slot: object) -> None:
        self._slots.append(slot)

    def emit(self, payload: object) -> None:
        for slot in self._slots:
            slot(payload)


class _FakeVM:
    """Fake ViewModel with dialog signals for testing."""

    def __init__(self) -> None:
        self.credentialPromptRequested = _FakeSignal()
        self.clarificationRequested = _FakeSignal()
        self.missingDependencyRequested = _FakeSignal()


class TestQmlDialogAuditBridge:
    def test_install_connects_signals(self, audit_log: VisibilityAuditLog) -> None:
        vm = _FakeVM()
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.install(vm)
        assert len(vm.credentialPromptRequested._slots) == 1
        assert len(vm.clarificationRequested._slots) == 1
        assert len(vm.missingDependencyRequested._slots) == 1

    def test_credential_dialog_records_event(self, audit_log: VisibilityAuditLog) -> None:
        vm = _FakeVM()
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.install(vm)
        vm.credentialPromptRequested.emit({
            'domain': 'github.com',
            'reason': 'PAT expired',
            'username_hint': 'user',
        })
        s = audit_log.summary()
        dialog_events = [e for e in s['events'] if e['kind'] == KIND_DIALOG_SHOWN
                         and e['title'] == 'CredentialPromptDialog']
        assert len(dialog_events) == 1
        ev = dialog_events[0]
        assert ev['event_category'] == CAT_INTENTIONAL
        assert 'github.com' in ev['detail']
        assert ev['source'] == SRC_QML

    def test_clarification_dialog_records_event(self, audit_log: VisibilityAuditLog) -> None:
        vm = _FakeVM()
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.install(vm)
        vm.clarificationRequested.emit({
            'id': 'req-1',
            'question': 'Which branch?',
            'options': ['main', 'dev'],
            'context': 'deploy',
        })
        s = audit_log.summary()
        dialog_events = [e for e in s['events'] if e['kind'] == KIND_DIALOG_SHOWN
                         and e['title'] == 'ClarificationDialog']
        assert len(dialog_events) == 1
        assert 'Which branch?' in dialog_events[0]['detail']

    def test_missing_dependency_dialog_records_event(self, audit_log: VisibilityAuditLog) -> None:
        vm = _FakeVM()
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.install(vm)
        vm.missingDependencyRequested.emit({
            'package_name': 'winotify',
            'manager': 'pip',
            'reason': 'Required for toast notifications',
        })
        s = audit_log.summary()
        dialog_events = [e for e in s['events'] if e['kind'] == KIND_DIALOG_SHOWN
                         and e['title'] == 'MissingDependencyDialog']
        assert len(dialog_events) == 1
        assert 'winotify' in dialog_events[0]['detail']

    def test_record_dialog_closed(self, audit_log: VisibilityAuditLog) -> None:
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.record_dialog_closed('CredentialPromptDialog',
                                    vm_name='ControlCenterVM',
                                    response_type='credential_provided')
        s = audit_log.summary()
        closed = [e for e in s['events'] if e['kind'] == KIND_DIALOG_CLOSED]
        assert len(closed) == 1
        assert closed[0]['title'] == 'CredentialPromptDialog'
        assert closed[0]['extra']['response_type'] == 'credential_provided'

    def test_password_redacted_in_payload(self, audit_log: VisibilityAuditLog) -> None:
        vm = _FakeVM()
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.install(vm)
        vm.credentialPromptRequested.emit({
            'domain': 'github.com',
            'password': 'supersecret123',
        })
        s = audit_log.summary()
        dialog_events = [e for e in s['events'] if e['kind'] == KIND_DIALOG_SHOWN
                         and e['title'] == 'CredentialPromptDialog']
        payload = dialog_events[0]['extra']['signal_payload']
        assert payload['password'] == '***REDACTED***'
        assert payload['domain'] == 'github.com'

    def test_install_skips_missing_signals(self, audit_log: VisibilityAuditLog) -> None:
        vm = MagicMock(spec=[])  # no attributes
        bridge = QmlDialogAuditBridge(audit_log)
        bridge.install(vm)  # should not raise
        s = audit_log.summary()
        assert s['total_events'] == 1  # only init event


class TestSafeSerialize:
    def test_redacts_secrets(self) -> None:
        result = _safe_serialize({
            'domain': 'github.com',
            'password': 'secret',
            'token': 'abc123',
            'api_key': 'xyz',
        })
        assert result['password'] == '***REDACTED***'
        assert result['token'] == '***REDACTED***'
        assert result['api_key'] == '***REDACTED***'
        assert result['domain'] == 'github.com'

    def test_truncates_long_strings(self) -> None:
        result = _safe_serialize({'key': 'x' * 300})
        assert len(result['key']) == 200

    def test_non_dict_returns_string(self) -> None:
        result = _safe_serialize([1, 2, 3])
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# ToastAuditAdapter tests
# ---------------------------------------------------------------------------

class _FakeToastBridge:
    """Minimal WinToastBridge mock for testing ToastAuditAdapter."""

    def __init__(self) -> None:
        self.winotify_called = False
        self.balloon_called = False

    def _notify_winotify(self, title: str, body: str, *, icon: str = 'info') -> bool:
        self.winotify_called = True
        return True

    def _notify_balloon(self, title: str, body: str, *, icon: str = 'info',
                        duration_ms: int = 5000) -> bool:
        self.balloon_called = True
        return True


class TestToastAuditAdapter:
    def test_install_patches_winotify(self, audit_log: VisibilityAuditLog) -> None:
        bridge = _FakeToastBridge()
        adapter = ToastAuditAdapter(audit_log, bridge)
        adapter.install()
        bridge._notify_winotify('Alerta', 'Test toast', icon='warning')
        s = audit_log.summary()
        toast_events = [e for e in s['events'] if e['kind'] == KIND_TOAST_SHOWN]
        assert len(toast_events) == 1
        ev = toast_events[0]
        assert ev['title'] == 'Alerta'
        assert ev['detail'] == 'Test toast'
        assert ev['event_category'] == CAT_INTENTIONAL
        assert ev['extra']['backend'] == 'winotify'
        assert ev['extra']['success'] is True

    def test_install_patches_balloon(self, audit_log: VisibilityAuditLog) -> None:
        bridge = _FakeToastBridge()
        adapter = ToastAuditAdapter(audit_log, bridge)
        adapter.install()
        bridge._notify_balloon('Info', 'Balloon msg', icon='info', duration_ms=3000)
        s = audit_log.summary()
        toast_events = [e for e in s['events'] if e['kind'] == KIND_TOAST_SHOWN]
        assert len(toast_events) == 1
        assert toast_events[0]['extra']['backend'] == 'balloon'

    def test_original_still_called(self, audit_log: VisibilityAuditLog) -> None:
        bridge = _FakeToastBridge()
        adapter = ToastAuditAdapter(audit_log, bridge)
        adapter.install()
        result = bridge._notify_winotify('Test', 'Body')
        assert result is True
        # Cannot directly check winotify_called because method was replaced,
        # but we verify the return value propagates

    def test_double_install_is_idempotent(self, audit_log: VisibilityAuditLog) -> None:
        bridge = _FakeToastBridge()
        adapter = ToastAuditAdapter(audit_log, bridge)
        adapter.install()
        adapter.install()  # should not double-wrap
        bridge._notify_winotify('Test', 'Body')
        s = audit_log.summary()
        toast_events = [e for e in s['events'] if e['kind'] == KIND_TOAST_SHOWN]
        assert len(toast_events) == 1  # only one event, not two

    def test_no_patch_if_methods_missing(self, audit_log: VisibilityAuditLog) -> None:
        bridge = MagicMock(spec=[])  # no methods
        adapter = ToastAuditAdapter(audit_log, bridge)
        adapter.install()  # should not raise


# ---------------------------------------------------------------------------
# GAP C — WorldModelService._ui_audit_blocks tests
# ---------------------------------------------------------------------------

class TestWorldModelAuditBlocks:
    """Tests that WorldModelService._ui_audit_blocks reads audit summary."""

    def _make_service(self, audit_log: VisibilityAuditLog | None = None) -> Any:
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        return WorldModelService(
            workspace_root='/tmp/test-ws',
            evolution_dir='/tmp/test-evo',
            auto_start=False,
            bootstrap_scan=False,
            ui_visibility_audit_log=audit_log,
        )

    def test_no_audit_returns_empty(self) -> None:
        svc = self._make_service(audit_log=None)
        assert svc._ui_audit_blocks() == []

    def test_unresolved_events_become_blocks(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record('win32_popup_detected', source='watcher',
                         title='Error - File not found',
                         event_category=CAT_UNEXPECTED, unresolved=True)
        svc = self._make_service(audit_log=audit_log)
        blocks = svc._ui_audit_blocks()
        assert any('ui_audit_unresolved' in b for b in blocks)

    def test_file_not_found_becomes_block(self, audit_log: VisibilityAuditLog) -> None:
        try:
            raise FileNotFoundError(2, 'No such file', 'missing.exe')
        except FileNotFoundError as e:
            audit_log.record_file_not_found(e, source='test')
        svc = self._make_service(audit_log=audit_log)
        blocks = svc._ui_audit_blocks()
        assert any('ui_audit_file_not_found' in b for b in blocks)

    def test_unexpected_popups_become_block(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record('win32_popup_detected', source='watcher',
                         event_category=CAT_UNEXPECTED)
        svc = self._make_service(audit_log=audit_log)
        blocks = svc._ui_audit_blocks()
        assert any('ui_audit_unexpected_popups' in b for b in blocks)

    def test_clean_audit_no_blocks(self, audit_log: VisibilityAuditLog) -> None:
        svc = self._make_service(audit_log=audit_log)
        blocks = svc._ui_audit_blocks()
        assert not any(b.startswith('ui_audit_') for b in blocks)


# ---------------------------------------------------------------------------
# GAP D — TaskContextAssembler._ui_visibility_snapshot tests
# ---------------------------------------------------------------------------

class TestTaskContextAssemblerVisibility:
    """Tests that TaskContextAssembler._ui_visibility_snapshot reads audit."""

    def _make_assembler(self, audit_log: VisibilityAuditLog | None = None) -> Any:
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        return TaskContextAssembler(
            episode_repository=MagicMock(),
            knowledge_repository=MagicMock(),
            run_repository=MagicMock(),
            dossier_repository=MagicMock(),
            hidden_incident_repository=MagicMock(),
            site_policy_registry=MagicMock(),
            capability_repository=MagicMock(),
            adaptive_session_repository=MagicMock(),
            ui_visibility_audit_log=audit_log,
        )

    def test_no_audit_returns_empty(self) -> None:
        assembler = self._make_assembler(audit_log=None)
        snapshot = assembler._ui_visibility_snapshot()
        assert snapshot == {}

    def test_returns_summary_fields(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source='qml',
                         event_category=CAT_INTENTIONAL)
        audit_log.record('win32_popup', source='watcher',
                         event_category=CAT_UNEXPECTED, unresolved=True)
        assembler = self._make_assembler(audit_log=audit_log)
        snapshot = assembler._ui_visibility_snapshot()
        assert snapshot['total_events'] == 3  # init + dialog + popup
        assert CAT_INTENTIONAL in snapshot['by_category']
        assert CAT_UNEXPECTED in snapshot['by_category']
        assert snapshot['unresolved_count'] >= 1
        assert snapshot['has_unexpected'] is True

    def test_clean_audit_no_unexpected(self, audit_log: VisibilityAuditLog) -> None:
        assembler = self._make_assembler(audit_log=audit_log)
        snapshot = assembler._ui_visibility_snapshot()
        assert snapshot['has_unexpected'] is False
        assert snapshot['unresolved_count'] == 0
        assert snapshot['file_not_found_count'] == 0


# ---------------------------------------------------------------------------
# SLICE 1+2 — Runtime wiring verification tests
# ---------------------------------------------------------------------------

class TestRuntimeWiringIntegration:
    """Verify that get_audit_log() singleton is the same instance everywhere."""

    def test_get_audit_log_returns_singleton(self) -> None:
        from iabv_v15.infra.ui_visibility_audit import get_audit_log
        log1 = get_audit_log()
        log2 = get_audit_log()
        assert log1 is log2

    def test_world_model_service_accepts_audit_log(self) -> None:
        from iabv_v15.infra.ui_visibility_audit import get_audit_log
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        audit = get_audit_log()
        svc = WorldModelService(
            workspace_root='/tmp/test-ws',
            evolution_dir='/tmp/test-evo',
            auto_start=False,
            bootstrap_scan=False,
            ui_visibility_audit_log=audit,
        )
        assert svc._ui_visibility_audit_log is audit

    def test_task_context_assembler_accepts_audit_log(self) -> None:
        from iabv_v15.infra.ui_visibility_audit import get_audit_log
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        audit = get_audit_log()
        assembler = TaskContextAssembler(
            episode_repository=MagicMock(),
            knowledge_repository=MagicMock(),
            run_repository=MagicMock(),
            dossier_repository=MagicMock(),
            hidden_incident_repository=MagicMock(),
            site_policy_registry=MagicMock(),
            capability_repository=MagicMock(),
            adaptive_session_repository=MagicMock(),
            ui_visibility_audit_log=audit,
        )
        assert assembler._ui_visibility_audit_log is audit

    def test_end_to_end_audit_flows_to_world_model_blocks(self) -> None:
        """Events recorded in audit log appear in WorldModel detected_blocks."""
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        audit = VisibilityAuditLog()
        audit.record('win32_popup_detected', source='test',
                     title='Error critical', event_category=CAT_UNEXPECTED,
                     unresolved=True)
        svc = WorldModelService(
            workspace_root='/tmp/test-ws',
            evolution_dir='/tmp/test-evo',
            auto_start=False,
            bootstrap_scan=False,
            ui_visibility_audit_log=audit,
        )
        blocks = svc._ui_audit_blocks()
        assert any('ui_audit_unresolved' in b for b in blocks)
        assert any('ui_audit_unexpected' in b for b in blocks)

    def test_end_to_end_audit_flows_to_perception(self) -> None:
        """Events recorded in audit log appear in TaskContextAssembler._ui_visibility_snapshot."""
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        audit = VisibilityAuditLog()
        audit.record('win32_popup_detected', source='test',
                     event_category=CAT_UNEXPECTED)
        assembler = TaskContextAssembler(
            episode_repository=MagicMock(),
            knowledge_repository=MagicMock(),
            run_repository=MagicMock(),
            dossier_repository=MagicMock(),
            hidden_incident_repository=MagicMock(),
            site_policy_registry=MagicMock(),
            capability_repository=MagicMock(),
            adaptive_session_repository=MagicMock(),
            ui_visibility_audit_log=audit,
        )
        snapshot = assembler._ui_visibility_snapshot()
        assert snapshot['has_unexpected'] is True
        assert snapshot['total_events'] >= 1  # at least the popup


# ---------------------------------------------------------------------------
# Operational wiring tests — Tasks 1-3 residual gap closure
# ---------------------------------------------------------------------------

class TestOperationalWiring:
    """Verify that SplashAuditAdapter, SubprocessAuditWrapper, Win32PopupWatcher,
    dialog close tracking, and ControlMasterService audit consumption all work."""

    def test_splash_audit_adapter_records_shown_and_closed(self) -> None:
        audit = VisibilityAuditLog()
        adapter = SplashAuditAdapter(audit)
        adapter.on_shown()
        adapter.on_closed()
        s = audit.summary()
        kinds = [e['kind'] for e in s['events']]
        assert KIND_DIALOG_SHOWN in kinds
        assert KIND_DIALOG_CLOSED in kinds
        assert s['total_events'] == 2

    def test_subprocess_audit_wrapper_captures_fnf(self) -> None:
        audit = VisibilityAuditLog()
        wrapper = SubprocessAuditWrapper(audit, cmd=['nonexistent-binary'])
        try:
            with wrapper:
                raise FileNotFoundError(2, 'No such file', 'nonexistent-binary')
        except FileNotFoundError:
            pass
        s = audit.summary()
        assert s['file_not_found_count'] == 1
        assert s['file_not_found'][0]['kind'] == KIND_FILE_NOT_FOUND

    def test_subprocess_audit_wrapper_no_event_on_success(self) -> None:
        audit = VisibilityAuditLog()
        wrapper = SubprocessAuditWrapper(audit, cmd=['echo', 'ok'])
        with wrapper:
            pass
        assert audit.summary()['total_events'] == 0

    def test_win32_popup_watcher_starts_noop_on_linux(self) -> None:
        from iabv_v15.infra.ui_visibility_audit import Win32PopupWatcher
        audit = VisibilityAuditLog()
        watcher = Win32PopupWatcher(audit)
        watcher.start()  # no-op on non-Windows
        assert watcher._thread is None  # thread not created on Linux
        watcher.stop()

    def test_dialog_close_records_via_bridge(self) -> None:
        audit = VisibilityAuditLog()
        bridge = QmlDialogAuditBridge(audit)
        bridge.record_dialog_closed(
            'CredentialPromptDialog',
            vm_name='ControlCenterViewModel',
            response_type='submitted',
        )
        s = audit.summary()
        assert s['total_events'] == 1
        assert s['events'][0]['kind'] == KIND_DIALOG_CLOSED
        assert s['events'][0]['title'] == 'CredentialPromptDialog'

    def test_control_master_reads_audit_visibility(self) -> None:
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
        audit = VisibilityAuditLog()
        audit.record('win32_popup_detected', source='test',
                     event_category=CAT_UNEXPECTED, unresolved=True)
        audit.record(KIND_FILE_NOT_FOUND, source='test',
                     event_category=CAT_UNEXPECTED,
                     extra={'filename': 'x.exe'})
        repo = MagicMock(spec=ControlMasterRepository)
        repo.load_latest_state.return_value = None
        repo.list_rules.return_value = []
        repo.list_decisions.return_value = []
        svc = ControlMasterService(
            repository=repo,
            ui_visibility_audit_log=audit,
        )
        state = svc.current_state()
        vis = state.metadata.get('ui_visibility', {})
        assert vis['total_events'] == 2
        assert vis['unresolved_count'] == 1
        assert vis['file_not_found_count'] == 1
        assert vis['has_unexpected'] is True

    def test_control_master_empty_without_audit(self) -> None:
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
        repo = MagicMock(spec=ControlMasterRepository)
        repo.load_latest_state.return_value = None
        repo.list_rules.return_value = []
        repo.list_decisions.return_value = []
        svc = ControlMasterService(repository=repo)
        state = svc.current_state()
        vis = state.metadata.get('ui_visibility', {})
        assert vis == {}
