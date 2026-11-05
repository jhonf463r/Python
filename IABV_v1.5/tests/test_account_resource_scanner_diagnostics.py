from __future__ import annotations

from pathlib import Path

from iabv_v15.services import account_resource_scanner


def test_browser_account_scan_reports_directory_enumeration_failure(monkeypatch) -> None:
    root = Path("synthetic-browser-root")

    def fail_iterdir(self):
        if self == root:
            raise PermissionError("synthetic directory denial")
        return iter(())

    monkeypatch.setattr(
        account_resource_scanner,
        "_chromium_browser_dirs",
        lambda: [("Chrome", root)],
    )
    monkeypatch.setattr(
        account_resource_scanner,
        "_firefox_accounts_with_diagnostics",
        lambda: ([], []),
    )
    monkeypatch.setattr(Path, "iterdir", fail_iterdir)

    result = account_resource_scanner.scan_browser_accounts()

    assert result["accounts"] == []
    assert result["source_coverage"]["browser_accounts"] == "READ_PARTIAL"
    assert "PermissionError" in result["source_errors"]["browser_accounts"]


def test_browser_session_scan_reports_directory_enumeration_failure(monkeypatch) -> None:
    root = Path("synthetic-session-root")

    def fail_iterdir(self):
        if self == root:
            raise PermissionError("synthetic directory denial")
        return iter(())

    monkeypatch.setattr(
        account_resource_scanner,
        "_chromium_browser_dirs",
        lambda: [("Chrome", root)],
    )
    monkeypatch.setattr(Path, "iterdir", fail_iterdir)

    result = account_resource_scanner.scan_browser_sessions()

    assert result["sessions"] == []
    assert result["source_coverage"]["browser_sessions"] == "READ_PARTIAL"
    assert "PermissionError" in result["source_errors"]["browser_sessions"]


def test_account_inventory_snapshot_carries_partial_source_coverage(monkeypatch) -> None:
    pool = {
        "workers": [],
        "exhausted": [],
        "source_coverage": {
            "browser_accounts": "READ_OK",
            "browser_sessions": "READ_PARTIAL",
        },
        "source_errors": {
            "browser_sessions": "cookie_database:Chrome:Default:PermissionError",
        },
    }
    quota = {
        "statuses": [],
        "source_coverage": {"quota_tracker": "READ_FAILED"},
        "source_errors": {"quota_tracker": "PermissionError"},
    }
    monkeypatch.setattr(
        account_resource_scanner, "estimate_available_workers", lambda: pool
    )
    monkeypatch.setattr(
        account_resource_scanner, "get_all_quota_status", lambda: quota
    )
    monkeypatch.setattr(
        account_resource_scanner, "rank_workers_for_target", lambda *args, **kwargs: []
    )

    snapshot = account_resource_scanner.build_inventory_snapshot()

    assert snapshot.entries == []
    assert snapshot.continuity_queue == []
    assert snapshot.source_coverage == {
        "browser_accounts": "READ_OK",
        "browser_sessions": "READ_PARTIAL",
        "quota_tracker": "READ_FAILED",
    }
    assert "UNRESOLVED:browser_sessions:READ_PARTIAL" in snapshot.unresolved_items
    assert "UNRESOLVED:quota_tracker:READ_FAILED" in snapshot.unresolved_items


def test_quota_tracker_path_lookup_does_not_create_directories(monkeypatch, tmp_path) -> None:
    workspace = tmp_path / 'synthetic-workspace'
    home = tmp_path / 'synthetic-home'
    monkeypatch.setenv('IABV_WORKSPACE', str(workspace))
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))

    path = account_resource_scanner._quota_file()

    assert path == workspace / 'data' / 'evolution' / 'quota_tracker.json'
    assert not path.parent.exists()
    _state, status, error = account_resource_scanner._load_quota_state_with_diagnostics()
    assert status == 'CONFIRMED_NOT_FOUND'
    assert error == 'quota_tracker_not_found'
    assert not path.parent.exists()


def test_worker_without_quota_tracking_is_not_available(monkeypatch) -> None:
    monkeypatch.setattr(
        account_resource_scanner,
        "verify_account_sessions",
        lambda: {
            "accounts": [{
                "email": "account@example.test",
                "browser": "Chrome",
                "profile": "Default",
                "tools": [{"tool": "chatgpt", "has_session": True}],
            }],
            "source_coverage": {"browser_accounts": "READ_OK", "browser_sessions": "READ_OK"},
            "source_errors": {},
        },
    )
    monkeypatch.setattr(
        account_resource_scanner,
        "get_all_quota_status",
        lambda: {
            "statuses": [],
            "source_coverage": {"quota_tracker": "CONFIRMED_NOT_FOUND"},
            "source_errors": {},
        },
    )

    pool = account_resource_scanner.estimate_available_workers()

    assert pool["workers"] == []
    assert pool["available_count"] == 0
    assert pool["tools_available"] == []
    assert pool["total_remaining_messages"] == 0
    assert pool["unverified_count"] == 1
    assert pool["unverified"][0]["quota_verified"] is False
    assert pool["source_coverage"]["quota_tracker"] == "CONFIRMED_NOT_FOUND"
    assert account_resource_scanner.rank_workers_for_target("chatgpt", pool=pool) == []


def test_inventory_keeps_untracked_quota_account_unresolved(monkeypatch) -> None:
    pool = {
        "workers": [],
        "exhausted": [],
        "unverified": [{
            "email": "account@example.test",
            "full_name": "",
            "tool": "chatgpt",
            "browser": "Chrome",
            "profile": "Default",
            "remaining_messages": 0,
            "used_in_window": 0,
            "limit": 80,
            "window_hours": 3,
            "exhausted": False,
            "quota_verified": False,
            "label": "ChatGPT",
            "resets_at": None,
        }],
        "source_coverage": {"browser_accounts": "READ_OK", "browser_sessions": "READ_OK", "quota_tracker": "CONFIRMED_NOT_FOUND"},
        "source_errors": {},
    }
    monkeypatch.setattr(account_resource_scanner, "estimate_available_workers", lambda: pool)
    monkeypatch.setattr(
        account_resource_scanner,
        "get_all_quota_status",
        lambda: {"statuses": [], "source_coverage": {"quota_tracker": "CONFIRMED_NOT_FOUND"}, "source_errors": {}},
    )
    monkeypatch.setattr(account_resource_scanner, "rank_workers_for_target", lambda *args, **kwargs: [])

    snapshot = account_resource_scanner.build_inventory_snapshot()

    from iabv_v15.domain.models import AccountStatus
    assert len(snapshot.entries) == 1
    assert snapshot.entries[0].status == AccountStatus.UNRESOLVED
    assert snapshot.entries[0].quota_remaining == 0
    assert snapshot.entries[0].metadata["quota_verified"] is False
    assert snapshot.continuity_queue == []
    assert snapshot.active_count == 0
    assert snapshot.unresolved_count == 1
    assert any("quota_never_tracked" in item for item in snapshot.unresolved_items)
