from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import iabv_v15.services.security.host_enrollment_context as context_module
from iabv_v15.services.security.host_enrollment_context import (
    ContextStatus,
    HostEnrollmentContextProvider,
    ProcessIdentitySource,
    WorkspaceRootSource,
    _NativeProcessResult,
)


VALID_SID = "S-1-5-21-111-222-333-1001"


def _native_result(
    *, pid: int | None = 4321, image_path: str | None = None,
    sid: str | None = VALID_SID, errors: tuple[str, ...] = (),
) -> _NativeProcessResult:
    return _NativeProcessResult(pid, image_path or os.path.abspath(__file__), sid, errors)


def _provider(root: str | None, *, config_root: str | None = None) -> HostEnrollmentContextProvider:
    configured = config_root if config_root is not None else (root or os.getcwd())
    return HostEnrollmentContextProvider(SimpleNamespace(workspace_root=configured), root)


def test_explicit_host_context_is_typed_and_observed_without_granting_authority(monkeypatch, tmp_path) -> None:
    calls = []
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: (calls.append(True) or _native_result()))
    context = _provider(str(tmp_path)).observe()

    assert context.status is ContextStatus.OBSERVED
    assert context.is_complete_observation is True
    assert context.process_identity.source is ProcessIdentitySource.WINDOWS_PROCESS_TOKEN_AND_IMAGE_API
    assert context.process_identity.pid == 4321
    assert context.process_identity.image_path == os.path.abspath(__file__)
    assert context.process_identity.effective_user_sid == VALID_SID
    assert context.workspace_root_candidate == str(tmp_path.resolve())
    assert context.workspace_root_source is WorkspaceRootSource.APP_BOOTSTRAP_EXPLICIT_ARGUMENT
    assert calls == [True]
    assert not hasattr(context, "approved_workspace_root")
    assert not hasattr(context, "capabilities")


@pytest.mark.parametrize(
    ("result", "expected_error"),
    [
        (_NativeProcessResult(None, None, None, ("WINDOWS_API_UNAVAILABLE",)), "WINDOWS_API_UNAVAILABLE"),
        (_NativeProcessResult(1, os.path.abspath(__file__), None, ("PROCESS_TOKEN_UNREADABLE",)), "PROCESS_TOKEN_UNREADABLE"),
        (_NativeProcessResult(1, os.path.abspath(__file__), "not-a-sid", ()), "PROCESS_SID_INVALID"),
        (_NativeProcessResult(None, os.path.abspath(__file__), VALID_SID, ()), "PROCESS_ID_INCOMPLETE"),
        (_NativeProcessResult(1, None, VALID_SID, ()), "PROCESS_IMAGE_PATH_INVALID"),
    ],
)
def test_incomplete_or_invalid_process_identity_is_denied(monkeypatch, tmp_path, result, expected_error) -> None:
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: result)
    context = _provider(str(tmp_path)).observe()
    assert context.status is ContextStatus.DENIED
    assert expected_error in context.integrity_errors
    assert context.is_complete_observation is False


def test_native_sid_shape_is_checked_again_at_provider_boundary(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: _native_result(sid="S-1-bad"))
    context = _provider(str(tmp_path)).observe()
    assert context.status is ContextStatus.DENIED
    assert "PROCESS_SID_INVALID" in context.integrity_errors
    assert context.process_identity.effective_user_sid is None


@pytest.mark.parametrize(
    ("root", "config_root", "error"),
    [
        (None, os.getcwd(), "WORKSPACE_ROOT_CWD_FALLBACK_NOT_ALLOWED"),
        ("relative\\root", "relative\\root", "WORKSPACE_ROOT_NOT_ABSOLUTE"),
        ("", os.getcwd(), "WORKSPACE_ROOT_EXPLICIT_VALUE_INVALID"),
        ("Z:\\missing\\root", "Z:\\missing\\root", "WORKSPACE_ROOT_NOT_FOUND"),
    ],
)
def test_root_without_acceptable_explicit_provenance_is_denied(monkeypatch, root, config_root, error) -> None:
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: _native_result())
    context = _provider(root, config_root=config_root).observe()
    assert context.status is ContextStatus.DENIED
    assert error in context.integrity_errors
    assert context.workspace_root_candidate is None


def test_existing_file_is_not_a_workspace_root(monkeypatch, tmp_path) -> None:
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: _native_result())
    context = _provider(str(file_path)).observe()
    assert context.status is ContextStatus.DENIED
    assert "WORKSPACE_ROOT_NOT_DIRECTORY" in context.integrity_errors


def test_mutated_config_root_is_denied(monkeypatch, tmp_path) -> None:
    config = SimpleNamespace(workspace_root=str(tmp_path))
    provider = HostEnrollmentContextProvider(config, str(tmp_path))
    config.workspace_root = str(tmp_path.parent)
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: _native_result())
    context = provider.observe()
    assert context.status is ContextStatus.DENIED
    assert "WORKSPACE_ROOT_CONFIG_CHANGED" in context.integrity_errors


def test_requested_root_must_match_configured_root(monkeypatch, tmp_path) -> None:
    requested_root = tmp_path / "requested"
    configured_root = tmp_path / "configured"
    requested_root.mkdir()
    configured_root.mkdir()
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: _native_result())

    context = _provider(str(requested_root), config_root=str(configured_root)).observe()

    assert context.status is ContextStatus.DENIED
    assert "WORKSPACE_ROOT_ARGUMENT_CONFIG_MISMATCH" in context.integrity_errors
    assert context.workspace_root_candidate is None
    assert context.is_complete_observation is False


def test_request_cannot_replace_root_or_process_identity(monkeypatch, tmp_path) -> None:
    calls = []
    monkeypatch.setattr(context_module, "_read_windows_process_identity", lambda: (calls.append(True) or _native_result()))
    provider = _provider(str(tmp_path))
    with pytest.raises(TypeError):
        provider.observe(workspace_root=str(tmp_path.parent))
    with pytest.raises(TypeError):
        provider.observe(pid=9999, effective_user_sid="S-1-5-18")
    assert calls == []


def test_bootstrap_composes_provider_without_wiring_an_approved_root_or_fetchback(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "src" / "iabv_v15" / "bootstrap.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    bootstrap_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppBootstrap")
    init_method = next(node for node in bootstrap_class.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
    init_source = ast.get_source_segment(source, init_method) or ""
    assert "HostEnrollmentContextProvider" in init_source
    assert "observed_local_enrollment_context_provider" in init_source
    assert "approved_workspace_root_provider" not in init_source
    assert "verify_owner_manifest_fetchback" not in init_source


@pytest.mark.skipif(os.name != "nt", reason="native Windows token/image APIs are unavailable")
def test_native_windows_observation_does_not_emit_sid(monkeypatch, tmp_path, capsys) -> None:
    context = _provider(str(tmp_path)).observe()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert context.status is ContextStatus.OBSERVED
    assert isinstance(context.process_identity.pid, int) and context.process_identity.pid > 0
    assert context.process_identity.image_path and os.path.isabs(context.process_identity.image_path)
    assert context.process_identity.effective_user_sid is not None
    assert re.fullmatch(r"S-1-(?:[0-9]+-){1,14}[0-9]+", context.process_identity.effective_user_sid, re.IGNORECASE)
