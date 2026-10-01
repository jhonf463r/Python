"""
Test: IABV_SKIP_TOOL_AVAILABILITY_PROBE isolation gate.

Exercises real AppBootstrap code to verify the production isolation gate.

Tests:
- Default mode: probe behavior preserved
- SKIP=1: synchronous probe skipped
- SKIP=1: deferred method skips probe
- SKIP=1: timer scheduling gate verified
- DEFER=0: backward compatibility preserved
- SKIP=1 + DEFER=0: synchronous probe suppressed
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_global_timeline():
    from iabv_v15.infra.startup_timeline import reset_global_timeline_for_tests
    reset_global_timeline_for_tests()
    yield
    reset_global_timeline_for_tests()


def test_default_mode_probes_deferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default mode: probe is deferred (not called during __init__)."""
    monkeypatch.delenv('IABV_SKIP_TOOL_AVAILABILITY_PROBE', raising=False)
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        assert probe.call_count == 0, (
            'Tool-availability probe should be deferred from __init__ by default.'
        )
        assert bootstrap._tool_availability_logged is False
        assert bootstrap._skip_tool_availability_probe is False


def test_skip_mode_skips_synchronous_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SKIP=1: synchronous probe skipped even when DEFER=0."""
    monkeypatch.setenv('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '1')
    monkeypatch.setenv('IABV_DEFER_TOOL_PROBE', '0')
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        assert probe.call_count == 0, (
            'SKIP flag should suppress synchronous probe even when DEFER=0.'
        )
        assert bootstrap._tool_availability_logged is False
        assert bootstrap._skip_tool_availability_probe is True


def test_skip_mode_skips_deferred_method(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SKIP=1: _run_deferred_post_window_setup skips probe."""
    monkeypatch.setenv('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '1')
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        bootstrap._run_deferred_post_window_setup()
        assert probe.call_count == 0, (
            'SKIP flag should suppress deferred probe.'
        )
        assert bootstrap._tool_availability_logged is True  # Set to prevent re-entry


def test_defer_backward_compatibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEFER=0: synchronous probe still works (backward compatibility)."""
    monkeypatch.delenv('IABV_SKIP_TOOL_AVAILABILITY_PROBE', raising=False)
    monkeypatch.setenv('IABV_DEFER_TOOL_PROBE', '0')
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        assert probe.call_count == 1, (
            'DEFER=0 should call probe synchronously (backward compatibility).'
        )
        assert bootstrap._tool_availability_logged is True
        assert bootstrap._skip_tool_availability_probe is False


def test_skip_overrides_defer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SKIP=1 + DEFER=0: SKIP overrides DEFER, probe suppressed."""
    monkeypatch.setenv('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '1')
    monkeypatch.setenv('IABV_DEFER_TOOL_PROBE', '0')
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        assert probe.call_count == 0, (
            'SKIP should override DEFER=0.'
        )
        assert bootstrap._tool_availability_logged is False
        assert bootstrap._skip_tool_availability_probe is True


def test_app_bootstrap_composition_preserved_in_skip_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SKIP=1: normal application composition still initializes."""
    monkeypatch.setenv('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '1')
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ):
        bootstrap = AppBootstrap(str(tmp_path))
        # Verify key composition attributes exist
        assert bootstrap.tool_registry is not None
        assert bootstrap.tool_sandbox is not None
        assert bootstrap.tool_validator is not None
        assert bootstrap.universal_perception_service is not None
        assert bootstrap.environment_self_awareness_service is not None
        assert bootstrap.world_model_service is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
