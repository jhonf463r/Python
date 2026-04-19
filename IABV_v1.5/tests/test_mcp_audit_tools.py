"""Tests de los helpers puros en `iabv_v15.infra.mcp.audit_tools`.

Cubre:
- `resolve_workspace_path` rechaza absolutos, `..`, y paths fuera de root.
- `is_sensitive_path` reconoce `.env*`, `credentials*.json`, `*.key`, `*.pem`.
- `read_repo_file`: happy path, secrets blocked, binario > tope,
  directorio vs archivo, no-existe, ruta fuera.
- `list_repo_directory`: lista cap, marca `sensitive`, truncado.
- `validate_pytest_suite` / `validate_pytest_keyword`.
- `run_pytest`: runner fake que valida comando + parseo del resumen.
- `capture_ui_screenshot`: degrada a `ui_not_running` si no hay provider.
- `git_status_and_log`: runner fake con salida porcelain + log controlada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from iabv_v15.infra.mcp import audit_tools
from iabv_v15.infra.mcp.audit_tools import (
    AuditToolError,
    SubprocessResult,
    capture_ui_screenshot,
    git_status_and_log,
    is_sensitive_path,
    list_repo_directory,
    read_repo_file,
    resolve_workspace_path,
    run_pytest,
    validate_pytest_keyword,
    validate_pytest_suite,
)


# ----------------------------------------------------------------------
# resolve_workspace_path / is_sensitive_path


def test_resolve_workspace_path_accepts_subpath(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "file.md"
    target.write_text("x")
    resolved = resolve_workspace_path(tmp_path, "docs/file.md")
    assert resolved == target.resolve()


def test_resolve_workspace_path_rejects_absolute(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        resolve_workspace_path(tmp_path, "/etc/passwd")
    assert exc.value.code == "absolute_path_forbidden"


def test_resolve_workspace_path_rejects_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        resolve_workspace_path(tmp_path, "../outside")
    assert exc.value.code == "parent_traversal_forbidden"


def test_resolve_workspace_path_rejects_symlink_to_outside(tmp_path: Path) -> None:
    # Un symlink que apunta fuera del workspace debe rechazarse tras
    # `resolve()` — este guard cubre el caso en que alguien coloca un link
    # "amigable" dentro del repo que escapa por el realpath.
    outside = tmp_path.parent / "other_workspace_outside"
    outside.mkdir(exist_ok=True)
    sym = tmp_path / "link"
    sym.symlink_to(outside)
    with pytest.raises(AuditToolError) as exc:
        resolve_workspace_path(tmp_path, "link")
    assert exc.value.code == "outside_workspace"


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        ".env.local",
        ".env.production",
        "credentials.json",
        "credentials.backup.json",
        "id_rsa",
        "id_rsa.pub",
        "deploy.key",
        "server.pem",
        "mcp_bridge.json",
    ],
)
def test_is_sensitive_path_flags_known_secrets(name: str) -> None:
    assert is_sensitive_path(name) is True
    assert is_sensitive_path(f"config/{name}") is True


def test_is_sensitive_path_ignores_regular_files() -> None:
    assert is_sensitive_path("README.md") is False
    assert is_sensitive_path("src/iabv_v15/bootstrap.py") is False
    assert is_sensitive_path("tests/test_mcp_server.py") is False


# ----------------------------------------------------------------------
# read_repo_file


def test_read_repo_file_happy_path(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.md"
    target.write_text("hola mundo", encoding="utf-8")
    payload = read_repo_file(tmp_path, "docs/note.md")
    assert payload["path"] == "docs/note.md"
    assert payload["size"] == len("hola mundo".encode("utf-8"))
    assert payload["content"] == "hola mundo"


def test_read_repo_file_blocks_secrets(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=abc")
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, ".env")
    assert exc.value.code == "sensitive_file_blocked"


def test_read_repo_file_blocks_credentials_in_subdir(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "credentials.json").write_text("{}")
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "data/credentials.json")
    assert exc.value.code == "sensitive_file_blocked"


def test_read_repo_file_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "docs")
    assert exc.value.code == "is_directory"


def test_read_repo_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "does/not/exist.txt")
    assert exc.value.code == "not_found"


def test_read_repo_file_rejects_too_large(tmp_path: Path) -> None:
    target = tmp_path / "big.bin"
    target.write_bytes(b"A" * 32)
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "big.bin", max_bytes=8)
    assert exc.value.code == "file_too_large"


def test_read_repo_file_rejects_non_utf8(tmp_path: Path) -> None:
    target = tmp_path / "bin.dat"
    target.write_bytes(b"\x80\x81\x82")
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "bin.dat")
    assert exc.value.code == "binary_not_supported"


def test_read_repo_file_rejects_absolute(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "/etc/passwd")
    assert exc.value.code == "absolute_path_forbidden"


def test_read_repo_file_preserves_dotfile_names(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.pyc", encoding="utf-8")
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "settings.yml").write_text("key: 1", encoding="utf-8")

    payload = read_repo_file(tmp_path, ".gitignore")
    assert payload["path"] == ".gitignore"
    assert payload["content"] == "*.pyc"

    payload = read_repo_file(tmp_path, ".config/settings.yml")
    assert payload["path"] == ".config/settings.yml"
    assert payload["content"] == "key: 1"


def test_read_repo_file_strips_only_leading_dot_slash(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text("hola", encoding="utf-8")

    payload = read_repo_file(tmp_path, "./docs/note.md")
    assert payload["path"] == "docs/note.md"

    payload = read_repo_file(tmp_path, "././docs/note.md")
    assert payload["path"] == "docs/note.md"


# ----------------------------------------------------------------------
# list_repo_directory


def test_list_repo_directory_enumerates_entries(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("22")
    (tmp_path / ".env").write_text("S")
    (tmp_path / "docs").mkdir()
    payload = list_repo_directory(tmp_path, "")
    names = {e["name"]: e for e in payload["entries"]}
    assert set(names) == {"a.txt", "b.txt", ".env", "docs"}
    assert names["docs"]["type"] == "dir"
    assert names["a.txt"]["type"] == "file"
    assert names["a.txt"]["size"] == 1
    assert names[".env"]["sensitive"] is True
    assert names["a.txt"]["sensitive"] is False
    assert payload["truncated"] is False
    assert payload["total_listed"] == 4
    assert payload["total_available"] == 4


def test_list_repo_directory_truncates_at_max_entries(tmp_path: Path) -> None:
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x")
    payload = list_repo_directory(tmp_path, "", max_entries=2)
    assert len(payload["entries"]) == 2
    assert payload["truncated"] is True
    assert payload["total_listed"] == 2
    assert payload["total_available"] == 5


def test_list_repo_directory_not_a_directory(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1")
    with pytest.raises(AuditToolError) as exc:
        list_repo_directory(tmp_path, "a.txt")
    assert exc.value.code == "not_a_directory"


def test_list_repo_directory_not_found(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        list_repo_directory(tmp_path, "does/not/exist")
    assert exc.value.code == "not_found"


# ----------------------------------------------------------------------
# validate_pytest_suite / keyword


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "tests/"),
        ("", "tests/"),
        ("tests/", "tests/"),
        ("tests/ui", "tests/ui"),
        ("tests/ui/", "tests/ui/"),
        ("tests/test_mcp_server.py", "tests/test_mcp_server.py"),
        ("tests/ui/test_foo.py", "tests/ui/test_foo.py"),
    ],
)
def test_validate_pytest_suite_accepts(value: str | None, expected: str) -> None:
    assert validate_pytest_suite(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "/tmp/evil",
        "../etc",
        "src/",  # fuera de tests
        "tests/../outside",
        "tests/; rm -rf /",
    ],
)
def test_validate_pytest_suite_rejects(value: str) -> None:
    with pytest.raises(AuditToolError):
        validate_pytest_suite(value)


def test_validate_pytest_keyword_allows_and_rejects() -> None:
    assert validate_pytest_keyword(None) is None
    assert validate_pytest_keyword("") is None
    assert validate_pytest_keyword("foo and not bar") == "foo and not bar"
    with pytest.raises(AuditToolError):
        validate_pytest_keyword("foo`rm -rf`")


# ----------------------------------------------------------------------
# run_pytest


class _StubRunner:
    def __init__(self, result: SubprocessResult) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        cmd: list[str],
        cwd: str,
        env: dict[str, str],
        timeout_s: float,
    ) -> SubprocessResult:
        self.calls.append({"cmd": cmd, "cwd": cwd, "env": env, "timeout_s": timeout_s})
        return self.result


def test_run_pytest_default_suite_passes_expected_cmd(tmp_path: Path) -> None:
    runner = _StubRunner(
        SubprocessResult(
            returncode=0,
            stdout="24 passed in 1.20s\n",
            stderr="",
            duration_s=1.2,
        )
    )
    payload = run_pytest(
        tmp_path,
        runner=runner,
        python_executable="/fake/python",
    )
    assert payload["suite"] == "tests/"
    assert payload["keyword"] is None
    assert payload["passed"] == 24
    assert payload["failed"] == 0
    assert payload["errors"] == 0
    assert payload["returncode"] == 0
    assert payload["timed_out"] is False
    assert "24 passed" in payload["output_tail"]
    # cmd esperado
    call = runner.calls[0]
    assert call["cmd"] == [
        "/fake/python",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "tests/",
        "-q",
    ]
    assert call["cwd"] == str(tmp_path.resolve())
    # PYTHONPATH injecta src/
    assert str((tmp_path / "src").resolve()) in call["env"]["PYTHONPATH"]


def test_run_pytest_appends_keyword(tmp_path: Path) -> None:
    runner = _StubRunner(
        SubprocessResult(returncode=1, stdout="0 passed, 1 failed", stderr="", duration_s=0.5)
    )
    payload = run_pytest(
        tmp_path,
        suite="tests/test_mcp_server.py",
        keyword="governance",
        runner=runner,
        python_executable="/fake/python",
    )
    assert "-k" in runner.calls[0]["cmd"]
    idx = runner.calls[0]["cmd"].index("-k")
    assert runner.calls[0]["cmd"][idx + 1] == "governance"
    assert payload["passed"] == 0
    assert payload["failed"] == 1
    assert payload["returncode"] == 1


def test_run_pytest_invalid_suite_raises(tmp_path: Path) -> None:
    runner = _StubRunner(SubprocessResult(returncode=0, stdout="", stderr="", duration_s=0.0))
    with pytest.raises(AuditToolError) as exc:
        run_pytest(tmp_path, suite="../evil", runner=runner)
    assert exc.value.code == "invalid_suite"
    assert runner.calls == []


def test_run_pytest_timeout_flag(tmp_path: Path) -> None:
    runner = _StubRunner(
        SubprocessResult(
            returncode=-1,
            stdout="collected 0 items\n",
            stderr="",
            duration_s=60.0,
            timed_out=True,
        )
    )
    payload = run_pytest(tmp_path, runner=runner, python_executable="/fake/python")
    assert payload["timed_out"] is True


# ----------------------------------------------------------------------
# capture_ui_screenshot


class _FakeProvider:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.calls: list[str] = []

    def capture(self, region: str) -> bytes:
        self.calls.append(region)
        return self.data


def test_capture_ui_screenshot_with_provider_returns_base64() -> None:
    provider = _FakeProvider(b"\x89PNGDATA")
    payload = capture_ui_screenshot(provider, region="control_center")
    assert payload["region"] == "control_center"
    assert payload["format"] == "png"
    assert payload["size_bytes"] == len(b"\x89PNGDATA")
    assert "bytes_base64" in payload
    assert provider.calls == ["control_center"]


def test_capture_ui_screenshot_without_provider_degrades() -> None:
    payload = capture_ui_screenshot(None)
    assert payload["error"] == "ui_not_running"
    assert payload["region"] == "control_center"


def test_capture_ui_screenshot_empty_bytes_degrades() -> None:
    payload = capture_ui_screenshot(_FakeProvider(b""), region="evolution")
    assert payload["error"] == "ui_not_running"
    assert payload["region"] == "evolution"


# ----------------------------------------------------------------------
# git_status_and_log


_LOG_FIELD_SEP = "\x1f"
_LOG_RECORD_SEP = "\x1e"


class _GitScriptRunner:
    """Runner que responde según el subcomando git ejecutado."""

    def __init__(self, responses: dict[str, SubprocessResult]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(
        self,
        *,
        cmd: list[str],
        cwd: str,
        env: dict[str, str],
        timeout_s: float,
    ) -> SubprocessResult:
        self.calls.append(list(cmd))
        # mapear por segunda palabra del comando git
        if len(cmd) >= 2:
            key = cmd[1]
        else:
            key = ""
        if key in self.responses:
            return self.responses[key]
        return SubprocessResult(returncode=1, stdout="", stderr="unknown", duration_s=0.0)


def _commit_record(sha: str, short: str, author: str, date: str, msg: str) -> str:
    return _LOG_FIELD_SEP.join([sha, short, author, date, msg]) + _LOG_RECORD_SEP


def test_git_status_and_log_happy_path(tmp_path: Path) -> None:
    porcelain = (
        "## devin/1234-audit...origin/main [ahead 2, behind 1]\n"
        " M src/iabv_v15/infra/mcp/server.py\n"
        "?? tests/test_mcp_audit_tools.py\n"
    )
    log_out = _commit_record(
        "abcd1234ef567890abcd1234ef567890abcd1234",
        "abcd123",
        "Jhovanny <j@example.com>",
        "2026-04-19T10:00:00-03:00",
        "feat(audit): add audit tools",
    ) + _commit_record(
        "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "deadbee",
        "Devin <d@example.com>",
        "2026-04-18T22:00:00-03:00",
        "test(audit): coverage",
    )
    runner = _GitScriptRunner(
        {
            "rev-parse": SubprocessResult(returncode=0, stdout="true\n", stderr="", duration_s=0.01),
            "status": SubprocessResult(returncode=0, stdout=porcelain, stderr="", duration_s=0.02),
            "log": SubprocessResult(returncode=0, stdout=log_out, stderr="", duration_s=0.03),
        }
    )
    payload = git_status_and_log(tmp_path, limit=2, runner=runner)
    assert payload["branch"] == "devin/1234-audit"
    assert payload["ahead"] == 2
    assert payload["behind"] == 1
    assert payload["dirty_count"] == 2
    assert {f["path"] for f in payload["dirty_files"]} == {
        "src/iabv_v15/infra/mcp/server.py",
        "tests/test_mcp_audit_tools.py",
    }
    assert len(payload["last_commits"]) == 2
    assert payload["last_commits"][0]["short_sha"] == "abcd123"
    assert payload["last_commits"][0]["message"] == "feat(audit): add audit tools"


def test_git_status_and_log_not_a_repo(tmp_path: Path) -> None:
    runner = _GitScriptRunner(
        {
            "rev-parse": SubprocessResult(
                returncode=128,
                stdout="",
                stderr="fatal: not a git repository",
                duration_s=0.0,
            ),
        }
    )
    payload = git_status_and_log(tmp_path, runner=runner)
    assert payload["error"] == "not_a_git_repo"
    assert "fatal" in payload["detail"]


def test_git_status_and_log_caps_limit(tmp_path: Path) -> None:
    runner = _GitScriptRunner(
        {
            "rev-parse": SubprocessResult(returncode=0, stdout="true\n", stderr="", duration_s=0.01),
            "status": SubprocessResult(returncode=0, stdout="## main\n", stderr="", duration_s=0.0),
            "log": SubprocessResult(returncode=0, stdout="", stderr="", duration_s=0.0),
        }
    )
    git_status_and_log(tmp_path, limit=10_000, runner=runner)
    log_cmd = runner.calls[-1]
    # -n<limit> capeado a MAX_GIT_LOG_LIMIT
    assert any(part == f"-n{audit_tools.MAX_GIT_LOG_LIMIT}" for part in log_cmd)
