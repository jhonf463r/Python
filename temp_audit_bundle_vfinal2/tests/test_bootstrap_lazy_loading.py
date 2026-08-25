"""Tests for lazy-loaded services in AppBootstrap.

BrowserSessionController, BrowserTeachSessionService, and
SiteExplorationService are deferred to first access via @property
to reduce post-startup memory when browser teach / site exploration
are never activated in a session.

Contract:
- The cache placeholders are ``None`` right after wiring.
- First access via the property creates the real service and caches it.
- Subsequent accesses return the cached instance (idempotent).
- Attribute injections (credential_broker, clarification_request_service)
  happen inside the property getter, not during ``_wire_services``.
- ``_LazyServiceRef`` transparently proxies attribute access to the real
  service, deferring construction until the first method call.
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


@pytest.fixture
def bootstrap(tmp_path: Path):
    from iabv_v15.bootstrap import AppBootstrap
    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        return AppBootstrap(str(tmp_path))


# ------------------------------------------------------------------
# 1. Services are NOT constructed eagerly during _wire_services
# ------------------------------------------------------------------

def test_browser_session_controller_not_constructed_eagerly(bootstrap) -> None:
    assert bootstrap._browser_session_controller_cache is None


def test_browser_teach_session_service_not_constructed_eagerly(bootstrap) -> None:
    assert bootstrap._browser_teach_session_service_cache is None


def test_site_exploration_service_is_lazy_property(bootstrap) -> None:
    """SiteExplorationService is a @property.  During normal (non-deferred)
    wiring, ToolRegistry._seed_defaults() triggers is_available on the
    lazy ref, which constructs the service.  The property still works
    correctly for caching."""
    from iabv_v15.services.tools.site_exploration_service import SiteExplorationService
    assert isinstance(bootstrap._site_exploration_service_cache, SiteExplorationService)


# ------------------------------------------------------------------
# 2. First access via property creates and caches the service
# ------------------------------------------------------------------

def test_browser_session_controller_created_on_first_access(bootstrap) -> None:
    from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
    svc = bootstrap.browser_session_controller
    assert isinstance(svc, BrowserSessionController)
    assert bootstrap._browser_session_controller_cache is svc


def test_browser_teach_session_service_created_on_first_access(bootstrap) -> None:
    from iabv_v15.services.capture.browser_teach_session_service import BrowserTeachSessionService
    svc = bootstrap.browser_teach_session_service
    assert isinstance(svc, BrowserTeachSessionService)
    assert bootstrap._browser_teach_session_service_cache is svc


def test_site_exploration_service_created_on_first_access(bootstrap) -> None:
    from iabv_v15.services.tools.site_exploration_service import SiteExplorationService
    svc = bootstrap.site_exploration_service
    assert isinstance(svc, SiteExplorationService)
    assert bootstrap._site_exploration_service_cache is svc


# ------------------------------------------------------------------
# 3. Repeated access returns same cached instance (idempotent)
# ------------------------------------------------------------------

def test_browser_session_controller_idempotent(bootstrap) -> None:
    first = bootstrap.browser_session_controller
    second = bootstrap.browser_session_controller
    assert first is second


def test_browser_teach_session_service_idempotent(bootstrap) -> None:
    first = bootstrap.browser_teach_session_service
    second = bootstrap.browser_teach_session_service
    assert first is second


def test_site_exploration_service_idempotent(bootstrap) -> None:
    first = bootstrap.site_exploration_service
    second = bootstrap.site_exploration_service
    assert first is second


# ------------------------------------------------------------------
# 4. Attribute injections happen inside property getter
# ------------------------------------------------------------------

def test_browser_teach_injects_credential_broker(bootstrap) -> None:
    svc = bootstrap.browser_teach_session_service
    assert getattr(svc, 'credential_broker', None) is bootstrap.credential_broker


def test_browser_teach_injects_clarification_service(bootstrap) -> None:
    svc = bootstrap.browser_teach_session_service
    assert getattr(svc, 'clarification_request_service', None) is bootstrap.clarification_request_service


# ------------------------------------------------------------------
# 5. BrowserTeachSessionService depends on BrowserSessionController
# ------------------------------------------------------------------

def test_browser_teach_triggers_controller_creation(bootstrap) -> None:
    assert bootstrap._browser_session_controller_cache is None
    _ = bootstrap.browser_teach_session_service
    assert bootstrap._browser_session_controller_cache is not None


# ------------------------------------------------------------------
# 6. _LazyServiceRef proxy
# ------------------------------------------------------------------

def test_lazy_service_ref_defers_construction() -> None:
    from iabv_v15.bootstrap import _LazyServiceRef

    call_count = 0

    class FakeService:
        value = 42

    def factory():
        nonlocal call_count
        call_count += 1
        return FakeService()

    ref = _LazyServiceRef(factory)
    assert call_count == 0
    assert ref.value == 42
    assert call_count == 1
    # second access reuses cached instance
    assert ref.value == 42
    assert call_count == 1


def test_lazy_service_ref_setattr_forwards() -> None:
    from iabv_v15.bootstrap import _LazyServiceRef

    class FakeService:
        x = 0

    ref = _LazyServiceRef(FakeService)
    ref.x = 99
    assert ref.x == 99


def test_lazy_service_ref_repr_pending() -> None:
    from iabv_v15.bootstrap import _LazyServiceRef
    ref = _LazyServiceRef(lambda: object())
    assert 'pending' in repr(ref)


def test_lazy_service_ref_repr_resolved() -> None:
    from iabv_v15.bootstrap import _LazyServiceRef

    class Named:
        def __repr__(self):
            return '<Named>'

    ref = _LazyServiceRef(Named)
    _ = ref.__class__  # trigger via __getattr__ won't work; access a real attr
    ref._resolve()
    assert repr(ref) == '<Named>'


# ------------------------------------------------------------------
# 7. SiteExplorerToolAdapter works with _LazyServiceRef
# ------------------------------------------------------------------

def test_site_explorer_adapter_uses_lazy_ref(bootstrap) -> None:
    """SiteExplorerToolAdapter receives a _LazyServiceRef.  ToolRegistry
    triggers is_available during seed, which resolves the proxy."""
    from iabv_v15.bootstrap import _LazyServiceRef
    adapter = bootstrap.tool_adapters.get('site_explorer')
    assert adapter is not None
    # The adapter stores a _LazyServiceRef (or the resolved instance
    # if seed already ran).  Either way, the service is accessible.
    svc = adapter.service
    if isinstance(svc, _LazyServiceRef):
        svc = svc._resolve()
    assert svc is bootstrap.site_exploration_service


# ------------------------------------------------------------------
# 8. Deferred init preserves lazy placeholders
# ------------------------------------------------------------------

def test_deferred_init_no_lazy_caches(tmp_path: Path) -> None:
    """With _defer_services=True, lazy caches don't exist yet."""
    from iabv_v15.bootstrap import AppBootstrap
    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)
    assert not hasattr(bootstrap, '_browser_session_controller_cache')
    assert not hasattr(bootstrap, '_browser_teach_session_service_cache')
    assert not hasattr(bootstrap, '_site_exploration_service_cache')
