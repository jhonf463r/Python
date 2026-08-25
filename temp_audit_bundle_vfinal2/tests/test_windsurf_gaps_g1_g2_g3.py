"""Tests for Windsurf audit gaps G1, G2, G3.

G1: ``_read_with_retry()`` — exponential backoff for SQLite reads.
G2: Centralized category constants in ``platform_pending_queue``.
G3: ``list_tasks()`` alias on ``PlatformPendingQueue``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import PendingTaskStatus, PlatformPendingTask
from iabv_v15.services.evolution.platform_pending_queue import (
    CATEGORY_CAPABILITY_DISCOVERY,
    CATEGORY_MISSING_TOOL,
    CATEGORY_OSES_FINDING,
    CATEGORY_PERMISSION_REQUIRED,
    CATEGORY_WINDOWS_NATIVE,
    PlatformPendingQueue,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def queue(tmp_path: Path) -> PlatformPendingQueue:
    return PlatformPendingQueue(evolution_dir=str(tmp_path / 'evolution'))


# ==================================================================
# G1: _read_with_retry
# ==================================================================


class TestReadWithRetry:
    """Verify ``AppBootstrap._read_with_retry`` handles SQLite lock contention."""

    @staticmethod
    def _get_retry():
        """Import the static method without constructing a full bootstrap."""
        from iabv_v15.bootstrap import AppBootstrap
        return AppBootstrap._read_with_retry

    def test_succeeds_on_first_attempt(self):
        retry = self._get_retry()
        result = retry(lambda: 42)
        assert result == 42

    def test_retries_on_database_locked(self):
        retry = self._get_retry()
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise sqlite3.OperationalError('database is locked')
            return 'ok'

        result = retry(flaky, base_delay=0.01)
        assert result == 'ok'
        assert call_count == 3

    def test_raises_after_max_retries(self):
        retry = self._get_retry()

        def always_locked():
            raise sqlite3.OperationalError('database is locked')

        with pytest.raises(sqlite3.OperationalError, match='database is locked'):
            retry(always_locked, max_retries=2, base_delay=0.01)

    def test_does_not_retry_non_lock_errors(self):
        retry = self._get_retry()
        call_count = 0

        def syntax_error():
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError('near syntax error')

        with pytest.raises(sqlite3.OperationalError, match='syntax'):
            retry(syntax_error, base_delay=0.01)
        assert call_count == 1

    def test_retries_on_os_error_with_locked_message(self):
        retry = self._get_retry()
        call_count = 0

        def flaky_os():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise OSError('database is locked')
            return 'recovered'

        result = retry(flaky_os, base_delay=0.01)
        assert result == 'recovered'
        assert call_count == 2


# ==================================================================
# G2: Centralized category constants
# ==================================================================


class TestCategoryConstants:
    """Verify category constants are importable and consistent."""

    def test_constants_are_strings(self):
        assert isinstance(CATEGORY_MISSING_TOOL, str)
        assert isinstance(CATEGORY_PERMISSION_REQUIRED, str)
        assert isinstance(CATEGORY_OSES_FINDING, str)
        assert isinstance(CATEGORY_CAPABILITY_DISCOVERY, str)
        assert isinstance(CATEGORY_WINDOWS_NATIVE, str)

    def test_constant_values(self):
        assert CATEGORY_MISSING_TOOL == 'missing_tool'
        assert CATEGORY_PERMISSION_REQUIRED == 'permission_required'
        assert CATEGORY_OSES_FINDING == 'oses_finding'
        assert CATEGORY_CAPABILITY_DISCOVERY == 'capability_discovery'
        assert CATEGORY_WINDOWS_NATIVE == 'windows_native'

    def test_autonomy_cycle_uses_constants(self):
        """Verify autonomy_cycle_service imports and uses the centralized constants."""
        from iabv_v15.services.evolution import autonomy_cycle_service as acs_mod
        assert hasattr(acs_mod, 'CATEGORY_OSES_FINDING')
        assert hasattr(acs_mod, 'CATEGORY_PERMISSION_REQUIRED')

    def test_bootstrap_seed_uses_constant(self):
        """Verify _seed_missing_tools_as_pending references CATEGORY_MISSING_TOOL."""
        import inspect
        from iabv_v15.bootstrap import AppBootstrap
        source = inspect.getsource(AppBootstrap._seed_missing_tools_as_pending)
        assert 'CATEGORY_MISSING_TOOL' in source

    def test_capability_discovery_uses_constant(self):
        """Verify seed_from_capability_graph uses CATEGORY_CAPABILITY_DISCOVERY."""
        import inspect
        source = inspect.getsource(PlatformPendingQueue.seed_from_capability_graph)
        assert 'CATEGORY_CAPABILITY_DISCOVERY' in source


# ==================================================================
# G3: list_tasks alias
# ==================================================================


class TestListTasksAlias:
    """Verify ``list_tasks`` is an alias for ``list_all``."""

    def test_list_tasks_exists(self, queue: PlatformPendingQueue):
        assert hasattr(queue, 'list_tasks')
        assert callable(queue.list_tasks)

    def test_list_tasks_returns_same_as_list_all(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='a', title='A', priority='high'))
        queue.upsert(PlatformPendingTask(id='b', title='B', priority='low'))

        all_tasks = queue.list_all()
        via_alias = queue.list_tasks()
        assert len(all_tasks) == len(via_alias)
        assert [t.id for t in all_tasks] == [t.id for t in via_alias]

    def test_list_tasks_on_empty_queue(self, queue: PlatformPendingQueue):
        assert queue.list_tasks() == []

    def test_list_tasks_is_same_method(self):
        assert PlatformPendingQueue.list_tasks is PlatformPendingQueue.list_all


# ==================================================================
# Backward compatibility: existing category string values still work
# ==================================================================


class TestBackwardCompatibility:
    """Ensure tasks created with raw category strings still match constants."""

    def test_raw_string_matches_constant(self, queue: PlatformPendingQueue):
        task = PlatformPendingTask(
            id='tool_test',
            title='Test',
            category='missing_tool',
        )
        queue.upsert(task)
        retrieved = queue.get('tool_test')
        assert retrieved.category == CATEGORY_MISSING_TOOL

    def test_permission_task_matches_constant(self, queue: PlatformPendingQueue):
        task = PlatformPendingTask(
            id='perm_test',
            title='Perm test',
            category='permission_required',
        )
        queue.upsert(task)
        retrieved = queue.get('perm_test')
        assert retrieved.category == CATEGORY_PERMISSION_REQUIRED
