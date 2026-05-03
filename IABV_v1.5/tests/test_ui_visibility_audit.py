"""Focused tests for ui_visibility_audit operational wiring.

Validates:
1. SplashAuditAdapter wiring is active
2. SubprocessAuditWrapper wiring is active
3. Win32PopupWatcher wiring is active
4. dialog_closed tracking works end-to-end
5. ControlMasterService reads visibility audit signals
"""
from __future__ import annotations

import pytest


# ------------------------------------------------------------------
# 1. SplashAuditAdapter wiring
# ------------------------------------------------------------------

class _FakeSplash:
    """Minimal splash controller stub with connectable signals."""

    def __init__(self) -> None:
        self._status_handlers: list = []
        self._error_handlers: list = []
        self._ready_handlers: list = []
        self._closing_handlers: list = []
        self._status = "Loading..."
        self._error_detail = ""

    @property
    def status(self) -> str:
        return self._status

    @property
    def errorDetail(self) -> str:
        return self._error_detail

    class _Signal:
        def __init__(self) -> None:
            self._handlers: list = []

        def connect(self, handler) -> None:
            self._handlers.append(handler)

        def emit(self) -> None:
            for h in self._handlers:
                h()

    statusChanged = _Signal()
    hasErrorChanged = _Signal()
    readyChanged = _Signal()
    closingNow = _Signal()


def test_splash_audit_adapter_connects() -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService
    from iabv_v15.services.audit.splash_audit_adapter import SplashAuditAdapter

    audit = UIVisibilityAuditService()
    splash = _FakeSplash()
    # Re-create signals per instance so we can test independently
    splash.statusChanged = _FakeSplash._Signal()
    splash.hasErrorChanged = _FakeSplash._Signal()
    splash.readyChanged = _FakeSplash._Signal()
    splash.closingNow = _FakeSplash._Signal()

    adapter = SplashAuditAdapter(
        splash_controller=splash,
        visibility_audit=audit,
    )
    assert adapter.is_connected is True

    # Fire status change and verify event recorded
    splash.statusChanged.emit()
    events = audit.events()
    assert len(events) >= 1
    assert events[0]["category"] == "splash"
    assert events[0]["kind"] == "status"


def test_splash_audit_adapter_noop_without_splash() -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService
    from iabv_v15.services.audit.splash_audit_adapter import SplashAuditAdapter

    audit = UIVisibilityAuditService()
    adapter = SplashAuditAdapter(
        splash_controller=None,
        visibility_audit=audit,
    )
    assert adapter.is_connected is False
    assert len(audit.events()) == 0


# ------------------------------------------------------------------
# 2. SubprocessAuditWrapper wiring
# ------------------------------------------------------------------

def test_subprocess_audit_wrapper_records_lifecycle() -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService
    from iabv_v15.services.audit.subprocess_audit_wrapper import SubprocessAuditWrapper

    audit = UIVisibilityAuditService()
    wrapper = SubprocessAuditWrapper(visibility_audit=audit)
    assert wrapper.is_active is True

    wrapper.record_start(process_name="mcp_server", pid=12345, command="python -m mcp")
    wrapper.record_exit(process_name="mcp_server", returncode=0)

    events = audit.events()
    assert len(events) == 2
    assert events[0]["category"] == "subprocess"
    assert events[0]["kind"] == "start"
    assert events[0]["summary"] == "mcp_server"
    assert events[1]["kind"] == "exit"


def test_subprocess_audit_wrapper_noop_without_audit() -> None:
    from iabv_v15.services.audit.subprocess_audit_wrapper import SubprocessAuditWrapper

    wrapper = SubprocessAuditWrapper(visibility_audit=None)
    assert wrapper.is_active is False
    # Should not raise
    wrapper.record_start(process_name="test", pid=1)
    wrapper.record_exit(process_name="test")
    wrapper.record_error(process_name="test", error="boom")


# ------------------------------------------------------------------
# 3. Win32PopupWatcher wiring
# ------------------------------------------------------------------

def test_win32_popup_watcher_records_popup() -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService
    from iabv_v15.services.audit.win32_popup_watcher import Win32PopupWatcher

    audit = UIVisibilityAuditService()
    watcher = Win32PopupWatcher(visibility_audit=audit)
    assert watcher.is_active is True

    watcher.record_popup(title="Error Dialog", window_class="#32770")
    watcher.record_popup_dismissed(title="Error Dialog", window_class="#32770")

    events = audit.events()
    assert len(events) == 2
    assert events[0]["category"] == "win32_popup"
    assert events[0]["kind"] == "detected"
    assert events[1]["kind"] == "dismissed"


def test_win32_popup_watcher_noop_without_audit() -> None:
    from iabv_v15.services.audit.win32_popup_watcher import Win32PopupWatcher

    watcher = Win32PopupWatcher(visibility_audit=None)
    assert watcher.is_active is False
    result = watcher.record_popup(title="Test", window_class="Dialog")
    assert result is None


# ------------------------------------------------------------------
# 4. dialog_closed tracking
# ------------------------------------------------------------------

def test_dialog_closed_records_via_audit_service() -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService

    audit = UIVisibilityAuditService()

    audit.record_dialog_opened(dialog_type="credential_prompt", detail="test")
    audit.record_dialog_closed(dialog_type="credential_prompt", detail="provided")

    events = audit.events()
    assert len(events) == 2
    assert events[0]["kind"] == "opened:credential_prompt"
    assert events[1]["kind"] == "closed:credential_prompt"
    # The open event should be resolved after close
    assert events[0]["resolved"] is True


def test_dialog_closed_snapshot_counts() -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService

    audit = UIVisibilityAuditService()

    audit.record_dialog_opened(dialog_type="clarification")
    audit.record_dialog_opened(dialog_type="missing_dependency")
    audit.record_dialog_closed(dialog_type="clarification")

    snap = audit.snapshot()
    assert snap["total_events"] == 3
    # One dialog still open (missing_dependency opened, not closed)
    assert snap["unresolved"] >= 1
    assert snap["by_category"]["dialog"] == 3


# ------------------------------------------------------------------
# 5. ControlMasterService reads visibility audit signals
# ------------------------------------------------------------------

def test_control_master_reads_visibility_audit(tmp_path) -> None:
    from iabv_v15.services.audit.ui_visibility_audit_service import UIVisibilityAuditService
    from iabv_v15.services.evolution.control_master_service import ControlMasterService
    from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
    from iabv_v15.infra.persistence.storage import ArtifactStorage

    storage = ArtifactStorage(tmp_path / "evolution")
    repo = ControlMasterRepository(storage)
    audit = UIVisibilityAuditService()

    # Generate some events
    audit.record_dialog_opened(dialog_type="credential_prompt")
    audit.record_file_not_found(path="/missing/file.txt")
    audit.record_event(category="unexpected", kind="crash", summary="oops")

    service = ControlMasterService(
        repository=repo,
        ui_visibility_audit=audit,
    )

    state = service.current_state()
    vis = state.metadata.get("ui_visibility_audit", {})
    assert vis["total_events"] == 3
    assert vis["unresolved"] >= 1
    assert vis["file_not_found"] == 1
    assert vis["unexpected"] == 1
    assert "dialog" in vis["by_category"]
    assert "file_not_found" in vis["by_category"]
    assert "unexpected" in vis["by_category"]


def test_control_master_without_visibility_audit(tmp_path) -> None:
    from iabv_v15.services.evolution.control_master_service import ControlMasterService
    from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
    from iabv_v15.infra.persistence.storage import ArtifactStorage

    storage = ArtifactStorage(tmp_path / "evolution")
    repo = ControlMasterRepository(storage)

    service = ControlMasterService(
        repository=repo,
        ui_visibility_audit=None,
    )
    state = service.current_state()
    # No visibility audit data in metadata — backward compat
    assert "ui_visibility_audit" not in state.metadata


# ------------------------------------------------------------------
# 6. Bootstrap wiring verification
# ------------------------------------------------------------------

def test_bootstrap_has_visibility_audit_services(tmp_path) -> None:
    """Verify bootstrap wires ui_visibility_audit, subprocess_audit_wrapper
    and win32_popup_watcher."""
    from unittest.mock import patch
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    assert hasattr(bootstrap, 'ui_visibility_audit')
    assert bootstrap.ui_visibility_audit is not None
    assert hasattr(bootstrap, 'subprocess_audit_wrapper')
    assert bootstrap.subprocess_audit_wrapper is not None
    assert bootstrap.subprocess_audit_wrapper.is_active is True
    assert hasattr(bootstrap, 'win32_popup_watcher')
    assert bootstrap.win32_popup_watcher is not None
    assert bootstrap.win32_popup_watcher.is_active is True
    # SplashAuditAdapter is None until run() creates the splash
    assert hasattr(bootstrap, 'splash_audit_adapter')


def test_control_master_service_receives_visibility_audit(tmp_path) -> None:
    """Verify bootstrap passes ui_visibility_audit to ControlMasterService."""
    from unittest.mock import patch
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    assert bootstrap.control_master_service.ui_visibility_audit is bootstrap.ui_visibility_audit
