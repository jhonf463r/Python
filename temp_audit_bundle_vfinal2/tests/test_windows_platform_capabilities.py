"""Tests for Windows platform capability discovery (Fix 18a).

These tests run on ALL platforms — on non-Windows they verify that the
discovery correctly returns ``not_applicable``.  On Windows they verify
that the probes execute without crashing and return valid structures.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from iabv_v15.domain.models import EnvironmentCapability, PendingTaskStatus, PlatformPendingTask


class TestWindowsPlatformCapabilitiesCrossPlatform:
    """Tests that work on both Windows and Linux."""

    @pytest.fixture(autouse=True)
    def _service(self):
        from iabv_v15.services.evolution.environment_self_awareness_service import (
            EnvironmentSelfAwarenessService,
        )
        self.svc = EnvironmentSelfAwarenessService.__new__(EnvironmentSelfAwarenessService)

    def test_non_windows_returns_not_applicable(self):
        with patch('os.name', 'posix'):
            caps = self.svc._windows_platform_capabilities()
        assert len(caps) == 1
        assert caps[0].capability_id == 'platform.windows'
        assert caps[0].available is False
        assert caps[0].status == 'not_applicable'

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_windows_returns_multiple_capabilities(self):
        caps = self.svc._windows_platform_capabilities()
        assert len(caps) >= 5
        ids = [c.capability_id for c in caps]
        assert 'platform.windows' in ids
        assert 'platform.windows_user_paths' in ids
        assert 'platform.windows_shell' in ids
        assert 'platform.clipboard' in ids
        assert 'platform.window_enumeration' in ids

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_windows_platform_cap_is_available(self):
        caps = self.svc._windows_platform_capabilities()
        win_cap = [c for c in caps if c.capability_id == 'platform.windows'][0]
        assert win_cap.available is True
        assert win_cap.status == 'ready'
        assert win_cap.metadata.get('major') is not None

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_windows_user_paths_detected(self):
        caps = self.svc._windows_platform_capabilities()
        paths_cap = [c for c in caps if c.capability_id == 'platform.windows_user_paths'][0]
        assert paths_cap.available is True
        assert 'appdata_local' in paths_cap.metadata

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_windows_version_detail(self):
        detail = self.svc._windows_version_detail()
        assert 'version' in detail
        assert 'release' in detail
        assert 'major' in detail
        assert detail['major'] >= 6  # Vista+

    @pytest.mark.skipif(os.name != 'nt', reason='Windows-only')
    def test_windows_user_paths_structure(self):
        paths = self.svc._windows_user_paths()
        assert 'userprofile' in paths
        assert 'appdata_local' in paths

    def test_capability_id_format(self):
        """All capability IDs should use dotted notation."""
        with patch('os.name', 'posix'):
            caps = self.svc._windows_platform_capabilities()
        for cap in caps:
            assert '.' in cap.capability_id, f'Bad format: {cap.capability_id}'

    def test_all_caps_are_environment_capability(self):
        with patch('os.name', 'posix'):
            caps = self.svc._windows_platform_capabilities()
        for cap in caps:
            assert isinstance(cap, EnvironmentCapability)


class TestOSESWindowsIntegrationFindings:
    """Test that _windows_integration_findings() works safely."""

    def test_non_windows_returns_empty(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ArtifactStorage(root=tmpdir)
            svc = OperationalSelfExaminationService(
                workspace_root=tmpdir,
                storage=storage,
            )
            with patch('os.name', 'posix'):
                findings = svc._windows_integration_findings()
            assert findings == []


class TestModelIntegrity:
    """Verify the new models don't break the import chain."""

    def test_pending_task_status_values(self):
        assert PendingTaskStatus.PENDING.value == 'PENDING'
        assert PendingTaskStatus.BLOCKED.value == 'BLOCKED'
        assert PendingTaskStatus.UNRESOLVED.value == 'UNRESOLVED'
        assert PendingTaskStatus.READY_FOR_NEXT_SLICE.value == 'READY_FOR_NEXT_SLICE'
        assert PendingTaskStatus.COMPLETED.value == 'COMPLETED'

    def test_platform_pending_task_importable(self):
        task = PlatformPendingTask(title='import test')
        assert task.title == 'import test'

    def test_models_module_exports(self):
        from iabv_v15.domain import models
        assert hasattr(models, 'PlatformPendingTask')
        assert hasattr(models, 'PlatformResumeHint')
        assert hasattr(models, 'PendingTaskStatus')
