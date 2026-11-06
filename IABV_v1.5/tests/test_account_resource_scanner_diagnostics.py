from __future__ import annotations

from pathlib import Path

import pytest

from iabv_v15.services import account_resource_scanner


def test_browser_account_scan_reports_directory_enumeration_failure(monkeypatch) -> None:
    root = Path("synthetic-browser-root")

    def fail_iterdir(self):
        if self == root:
            raise PermissionError("synthetic directory denial")
        return iter(())

    monkeypatch.setattr(
        account_resource_scanner,
        "_chromium_browser_dirs_with_diagnostics",
        lambda: ([("Chrome", root)], [], "READ_OK"),
    )
    monkeypatch.setattr(
        account_resource_scanner,
        "_firefox_accounts_scan_with_coverage",
        lambda: ([], [], "CONFIRMED_NOT_FOUND"),
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
        "_chromium_browser_dirs_with_diagnostics",
        lambda: ([("Chrome", root)], [], "READ_OK"),
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


def test_secret_file_read_failure_is_not_reported_as_missing(monkeypatch, tmp_path) -> None:
    secret_path = tmp_path / '.iabv_secrets.ps1'
    secret_path.write_text('$env:OPENAI_API_KEY=synthetic\n', encoding='utf-8')
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    for name in (
        'GITHUB_TOKEN_IABV', 'IABV_GITHUB_TOKEN', 'GITHUB_TOKEN', 'GH_TOKEN',
        'DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY', 'DEVIN_API_KEY',
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'CLOUDFLARE_TUNNEL_TOKEN',
        'CLOUDFLARED_TOKEN', 'IABV_MCP_API_KEY',
    ):
        monkeypatch.delenv(name, raising=False)
    original_read_text = Path.read_text

    def fail_secret_read(self, *args, **kwargs):
        if self == secret_path:
            raise PermissionError('synthetic secret file denial')
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', fail_secret_read)

    result = account_resource_scanner.scan_configured_secrets()

    assert result['source_coverage']['environment'] == 'READ_OK'
    assert result['source_coverage']['secrets_file'] == 'READ_FAILED'
    assert result['source_errors']['secrets_file'] == 'PermissionError'
    assert result['secrets_file_exists'] is True
    assert result['missing'] == []
    assert result['missing_count'] == 0
    assert 'OPENAI_API_KEY' in result['unverified']
    assert result['configured'] == []


def test_account_resource_scan_exposes_secret_file_coverage(monkeypatch) -> None:
    monkeypatch.setattr(account_resource_scanner, 'scan_github_api', lambda: {'available': False, 'reason': 'no_token'})
    monkeypatch.setattr(account_resource_scanner, 'scan_devin_api', lambda: {'available': False, 'reason': 'no_token'})
    monkeypatch.setattr(account_resource_scanner, 'scan_ollama_api', lambda: {'available': False, 'reason': 'not_running'})
    monkeypatch.setattr(account_resource_scanner, 'scan_browser_accounts', lambda: {
        'accounts': [], 'count': 0, 'source_coverage': {'browser_accounts': 'READ_PARTIAL'},
        'source_errors': {'browser_accounts': 'PermissionError'},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_configured_secrets', lambda: {
        'configured_count': 0, 'missing_count': 0, 'unverified': ['OPENAI_API_KEY'],
        'source_coverage': {'environment': 'READ_OK', 'secrets_file': 'READ_FAILED'},
        'source_errors': {'secrets_file': 'PermissionError'},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_cloudflare_tunnel', lambda: {'available': False})

    result = account_resource_scanner.account_resource_scan()

    assert result['source_coverage']['browser_accounts'] == 'READ_PARTIAL'
    assert result['source_coverage']['secrets_file'] == 'READ_FAILED'
    assert result['source_errors'] == {
        'browser_accounts': 'PermissionError',
        'secrets_file': 'PermissionError',
    }
    assert any('parcialmente no verificable' in alert for alert in result['summary']['alerts'])


def test_github_api_without_token_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv('GITHUB_TOKEN_IABV', raising=False)
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)

    result = account_resource_scanner.scan_github_api()

    assert result['available'] is False
    assert result['source_coverage']['github_api'] == 'NOT_CONFIGURED'
    assert result['source_errors'] == {}


def test_github_api_http_failure_is_preserved(monkeypatch) -> None:
    monkeypatch.setenv('GITHUB_TOKEN_IABV', 'synthetic-test-token')
    monkeypatch.setattr(account_resource_scanner, '_safe_request', lambda *args, **kwargs: {
        'ok': False, 'status': 403, 'error': 'synthetic forbidden',
    })

    result = account_resource_scanner.scan_github_api()

    assert result['available'] is False
    assert result['source_coverage']['github_api'] == 'READ_FAILED'
    assert result['source_errors']['github_api'] == 'synthetic forbidden'


def test_ollama_invalid_json_is_not_reported_as_available(monkeypatch) -> None:
    monkeypatch.setattr(account_resource_scanner, '_safe_request', lambda *args, **kwargs: {
        'ok': True, 'body': '{invalid-json',
    })

    result = account_resource_scanner.scan_ollama_api()

    assert result['available'] is False
    assert result['source_coverage']['ollama_api'] == 'READ_FAILED'
    assert result['models'] == []


def test_ollama_malformed_model_entry_is_read_partial(monkeypatch) -> None:
    monkeypatch.setattr(account_resource_scanner, '_safe_request', lambda *args, **kwargs: {
        'ok': True, 'body': '{"models": [{"name": "valid-model", "size": 1024}, null]}',
    })

    result = account_resource_scanner.scan_ollama_api()

    assert result['available'] is True
    assert result['models_count'] == 2
    assert result['models_valid_count'] == 1
    assert result['models'][0]['name'] == 'valid-model'
    assert result['source_coverage']['ollama_api'] == 'READ_PARTIAL'
    assert result['source_errors']['ollama_api'] == 'invalid_model_entries:1'


def test_cloudflared_process_enumeration_failure_is_not_not_running(monkeypatch) -> None:
    import subprocess

    monkeypatch.setattr(account_resource_scanner.os, 'name', 'nt')
    def run(command, **kwargs):
        if command == ['cloudflared', 'version']:
            return subprocess.CompletedProcess(command, 0, stdout='cloudflared version synthetic', stderr='')
        raise PermissionError('synthetic tasklist denial')
    monkeypatch.setattr(account_resource_scanner.subprocess, 'run', run)

    result = account_resource_scanner.scan_cloudflare_tunnel()

    assert result['available'] is True
    assert result['tunnel_running'] is None
    assert result['source_coverage']['cloudflared_binary'] == 'READ_OK'
    assert result['source_coverage']['cloudflared_processes'] == 'READ_FAILED'
    assert result['source_errors']['cloudflared_processes'] == 'PermissionError'


def test_account_resource_scan_merges_api_and_tunnel_coverage(monkeypatch) -> None:
    monkeypatch.setattr(account_resource_scanner, 'scan_github_api', lambda: {
        'available': False, 'source_coverage': {'github_api': 'NOT_CONFIGURED'}, 'source_errors': {},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_devin_api', lambda: {
        'available': False, 'source_coverage': {'devin_api': 'READ_FAILED'}, 'source_errors': {'devin_api': 'TimeoutError'},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_ollama_api', lambda: {
        'available': False, 'source_coverage': {'ollama_api': 'READ_FAILED'}, 'source_errors': {'ollama_api': 'ConnectionError'},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_browser_accounts', lambda: {
        'accounts': [], 'count': 0, 'source_coverage': {'browser_accounts': 'READ_PARTIAL'},
        'source_errors': {'browser_accounts': 'PermissionError'},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_configured_secrets', lambda: {
        'configured_count': 0, 'missing_count': 0, 'unverified': [],
        'source_coverage': {'environment': 'READ_OK', 'secrets_file': 'CONFIRMED_NOT_FOUND'},
        'source_errors': {},
    })
    monkeypatch.setattr(account_resource_scanner, 'scan_cloudflare_tunnel', lambda: {
        'available': True, 'source_coverage': {'cloudflared_binary': 'READ_OK', 'cloudflared_processes': 'READ_FAILED'},
        'source_errors': {'cloudflared_processes': 'PermissionError'},
    })

    result = account_resource_scanner.account_resource_scan()

    assert result['source_coverage'] == {
        'github_api': 'NOT_CONFIGURED',
        'devin_api': 'READ_FAILED',
        'ollama_api': 'READ_FAILED',
        'cloudflared_binary': 'READ_OK',
        'cloudflared_processes': 'READ_FAILED',
        'browser_accounts': 'READ_PARTIAL',
        'secrets_environment': 'READ_OK',
        'secrets_file': 'CONFIRMED_NOT_FOUND',
    }
    assert result['source_errors']['devin_api'] == 'TimeoutError'
    assert result['source_errors']['ollama_api'] == 'ConnectionError'
    assert result['source_errors']['cloudflared_processes'] == 'PermissionError'


def test_cloudflared_missing_binary_is_confirmed_not_found(monkeypatch) -> None:
    def missing_binary(*args, **kwargs):
        raise FileNotFoundError('synthetic cloudflared absence')
    monkeypatch.setattr(account_resource_scanner.subprocess, 'run', missing_binary)

    result = account_resource_scanner.scan_cloudflare_tunnel()

    assert result['available'] is False
    assert result['tunnel_running'] is None
    assert result['source_coverage']['cloudflared_binary'] == 'CONFIRMED_NOT_FOUND'
    assert result['source_coverage']['cloudflared_processes'] == 'NOT_EXECUTED'


def test_ollama_missing_models_field_is_not_verified_empty(monkeypatch) -> None:
    monkeypatch.setattr(account_resource_scanner, '_safe_request', lambda *args, **kwargs: {
        'ok': True, 'body': '{"unexpected": []}',
    })

    result = account_resource_scanner.scan_ollama_api()

    assert result['available'] is False
    assert result['source_coverage']['ollama_api'] == 'READ_FAILED'
    assert result['source_errors']['ollama_api'] == 'TypeError'

def test_chromium_root_discovery_confirms_absent_known_roots(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    dirs, errors, status = account_resource_scanner._chromium_browser_dirs_with_diagnostics()

    assert dirs == []
    assert errors == []
    assert status == "CONFIRMED_NOT_FOUND"


def test_chromium_root_discovery_preserves_access_denial(monkeypatch, tmp_path) -> None:
    root = tmp_path / ".config" / "google-chrome"
    original_stat = Path.stat
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    def stat_with_denial(self, *args, **kwargs):
        if self == root:
            raise PermissionError("synthetic browser root denial")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_with_denial)

    dirs, errors, status = account_resource_scanner._chromium_browser_dirs_with_diagnostics()

    assert dirs == []
    assert status == "READ_FAILED"
    assert "chromium_root:Chrome:PermissionError" in errors


def test_browser_scans_do_not_report_unconfigured_roots_as_clean_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        account_resource_scanner,
        "_chromium_browser_dirs_with_diagnostics",
        lambda: ([], ["chromium_root_config:LOCALAPPDATA_NOT_CONFIGURED"], "NOT_CONFIGURED"),
    )
    monkeypatch.setattr(
        account_resource_scanner,
        "_firefox_accounts_scan_with_coverage",
        lambda: ([], [], "NOT_CONFIGURED"),
    )

    accounts = account_resource_scanner.scan_browser_accounts()
    sessions = account_resource_scanner.scan_browser_sessions()

    assert accounts["accounts"] == []
    assert accounts["source_coverage"]["browser_accounts"] == "NOT_CONFIGURED"
    assert sessions["sessions"] == []
    assert sessions["source_coverage"]["browser_sessions"] == "NOT_CONFIGURED"

def test_firefox_legacy_diagnostics_preserve_unconfigured_root(monkeypatch) -> None:
    monkeypatch.setattr(
        account_resource_scanner,
        "_firefox_accounts_scan_with_coverage",
        lambda: ([], [], "NOT_CONFIGURED"),
    )

    accounts, errors = account_resource_scanner._firefox_accounts_with_diagnostics()

    assert accounts == []
    assert errors == ["firefox_root:NOT_CONFIGURED"]


def test_windows_browser_roots_are_not_reported_as_confirmed_empty(monkeypatch) -> None:
    monkeypatch.setattr(account_resource_scanner.os, "name", "nt")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)

    dirs, errors, status = account_resource_scanner._chromium_browser_dirs_with_diagnostics()
    firefox_accounts, firefox_errors, firefox_status = account_resource_scanner._firefox_accounts_scan_with_coverage()

    assert dirs == []
    assert status == "NOT_CONFIGURED"
    assert "chromium_root_config:LOCALAPPDATA_NOT_CONFIGURED" in errors
    assert firefox_accounts == []
    assert firefox_status == "NOT_CONFIGURED"
    assert firefox_errors == []


def test_browser_status_combination_preserves_unverified_component() -> None:
    assert account_resource_scanner._combine_browser_source_status(
        ["READ_OK", "NOT_CONFIGURED"]
    ) == "READ_PARTIAL"
    assert account_resource_scanner._combine_browser_source_status(
        ["CONFIRMED_NOT_FOUND", "NOT_CONFIGURED"]
    ) == "NOT_CONFIGURED"

def test_quota_tracker_requires_explicit_accounts_mapping(monkeypatch, tmp_path) -> None:
    workspace = tmp_path / "quota-schema-workspace"
    quota_path = workspace / "data" / "evolution" / "quota_tracker.json"
    quota_path.parent.mkdir(parents=True)
    quota_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("IABV_WORKSPACE", str(workspace))

    result = account_resource_scanner.get_all_quota_status()

    assert result["source_coverage"]["quota_tracker"] == "SCHEMA_UNSUPPORTED"
    assert result["statuses"] == []
    assert quota_path.read_text(encoding="utf-8") == "{}"


def test_quota_tracker_corruption_is_preserved_and_mutations_fail_closed(monkeypatch, tmp_path) -> None:
    workspace = tmp_path / "quota-corrupt-workspace"
    quota_path = workspace / "data" / "evolution" / "quota_tracker.json"
    quota_path.parent.mkdir(parents=True)
    original = "{"
    quota_path.write_text(original, encoding="utf-8")
    monkeypatch.setenv("IABV_WORKSPACE", str(workspace))

    result = account_resource_scanner.get_all_quota_status()

    assert result["source_coverage"]["quota_tracker"] == "CORRUPT"
    with pytest.raises(RuntimeError, match="quota_tracker_corrupt"):
        account_resource_scanner.record_message_sent("chatgpt", "account@example.test")
    assert quota_path.read_text(encoding="utf-8") == original


def test_quota_tracker_rejects_malformed_account_messages(monkeypatch, tmp_path) -> None:
    workspace = tmp_path / "quota-entry-workspace"
    quota_path = workspace / "data" / "evolution" / "quota_tracker.json"
    quota_path.parent.mkdir(parents=True)
    quota_path.write_text(
        '{"accounts":{"chatgpt:account@example.test":{"messages":"invalid"}}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("IABV_WORKSPACE", str(workspace))

    result = account_resource_scanner.get_all_quota_status()

    assert result["source_coverage"]["quota_tracker"] == "SCHEMA_UNSUPPORTED"
    with pytest.raises(RuntimeError, match="quota_tracker_schema_unsupported"):
        account_resource_scanner.record_message_sent("chatgpt", "account@example.test")
    assert '"messages":"invalid"' in quota_path.read_text(encoding="utf-8")



def test_browser_account_scan_does_not_export_absolute_browser_roots(monkeypatch, tmp_path) -> None:
    private_root = tmp_path / "private-user" / "Chrome" / "User Data"
    private_root.mkdir(parents=True)
    monkeypatch.setattr(
        account_resource_scanner,
        "_chromium_browser_dirs_with_diagnostics",
        lambda: ([("Chrome", private_root)], [], "READ_OK"),
    )
    monkeypatch.setattr(
        account_resource_scanner,
        "_firefox_accounts_scan_with_coverage",
        lambda: ([], [], "NOT_CONFIGURED"),
    )

    result = account_resource_scanner.scan_browser_accounts()

    assert result["browsers_scanned"] == ["Chrome"]
    assert "private-user" not in repr(result)
    assert str(tmp_path) not in repr(result)
