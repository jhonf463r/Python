from __future__ import annotations

import builtins
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from iabv_v15.infra.persistence.control_master_context_reader import (
    Availability,
    ContextArtifact,
    ControlMasterContextReader,
    Freshness,
    FreshnessPolicy,
    TargetMatch,
)


NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def _portable_package(**updates):
    payload = {
        "package_id": "portable-package-1",
        "package_version": "portable_context.v1",
        "created_at_utc": "2026-10-28T11:00:00Z",
        "updated_at_utc": "2026-10-28T11:00:00Z",
        "summary": "Contexto vigente",
        "sections": [],
        "assistant_brief": "Objetivo obj-a; unresolved: none",
        "unresolved_fields": [],
        "metadata": {"active_objective_id": "obj-a"},
    }
    payload.update(updates)
    return payload


def _write_artifact(root: Path, artifact: ContextArtifact, content: bytes) -> Path:
    relative = (
        Path("data/evolution/control_master/latest.json")
        if artifact is ContextArtifact.CONTROL_MASTER
        else Path("data/evolution/portable_context/latest.json")
    )
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _reader() -> ControlMasterContextReader:
    return ControlMasterContextReader(clock=lambda: NOW)


def _policy(max_age_seconds: int = 3600) -> FreshnessPolicy:
    return FreshnessPolicy(max_age_seconds=max_age_seconds)


def test_reads_existing_artifact_without_bootstrap_or_filesystem_writes(tmp_path, monkeypatch):
    raw = json.dumps(_portable_package(), separators=(",", ":")).encode("utf-8")
    artifact_path = _write_artifact(tmp_path, ContextArtifact.PORTABLE_CONTEXT, raw)
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}

    def forbidden_mkdir(*args, **kwargs):
        raise AssertionError("reader must not create directories")

    real_import = builtins.__import__
    forbidden_imports = {
        "iabv_v15.bootstrap",
        "iabv_v15.infra.persistence.storage",
        "iabv_v15.infra.persistence.control_master_repository",
        "iabv_v15.services.evolution.control_master_service",
        "iabv_v15.services.evolution.portable_context_service",
    }

    def guarded_import(name, *args, **kwargs):
        if name in forbidden_imports:
            raise AssertionError(f"forbidden application import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", forbidden_mkdir)
    monkeypatch.setattr(builtins, "__import__", guarded_import)

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
        target_objective_id="obj-a",
    )

    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert result.availability is Availability.AVAILABLE
    assert result.target_match is TargetMatch.MATCHED
    assert result.source_identity == "portable-package-1"
    assert result.source_timestamp_utc == datetime(2026, 10, 28, 11, 0, tzinfo=timezone.utc)
    assert result.content_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.content is not None
    assert after == before
    assert artifact_path.read_bytes() == raw


def test_missing_artifact_is_unavailable_without_creating_it(tmp_path):
    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.CONTROL_MASTER,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_NOT_FOUND"
    assert not (tmp_path / "data").exists()


def test_invalid_json_is_unavailable(tmp_path):
    _write_artifact(tmp_path, ContextArtifact.PORTABLE_CONTEXT, b'{"package_id":')

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_INVALID_OR_UNREADABLE"


def test_duplicate_json_keys_are_rejected(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        b'{"package_id":"first","package_id":"second"}',
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE


def test_missing_source_timestamp_is_unknown_not_fabricated(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(_portable_package(updated_at_utc=None)).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.freshness is Freshness.UNKNOWN
    assert result.source_timestamp_utc is None
    assert result.reason == "SOURCE_TIMESTAMP_UNKNOWN"


def test_old_artifact_is_stale_under_explicit_policy(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(
            _portable_package(updated_at_utc="2026-10-28T10:00:00Z")
        ).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(max_age_seconds=60),
    )

    assert result.availability is Availability.STALE
    assert result.freshness is Freshness.STALE
    assert result.content is None
    assert result.reason == "SOURCE_EXCEEDS_FRESHNESS_POLICY"


def test_matching_and_mismatching_objectives_are_not_inferred(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(_portable_package()).encode("utf-8"),
    )
    reader = _reader()

    matching = reader.read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
        target_objective_id="obj-a",
    )
    mismatching = reader.read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
        target_objective_id="obj-b",
    )

    assert matching.availability is Availability.AVAILABLE
    assert matching.target_match is TargetMatch.MATCHED
    assert mismatching.availability is Availability.UNAVAILABLE
    assert mismatching.target_match is TargetMatch.MISMATCH
    assert mismatching.content is None


def test_missing_objective_binding_is_explicitly_unverified(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(_portable_package(metadata={})).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
        target_objective_id="obj-a",
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.target_match is TargetMatch.UNVERIFIED
    assert result.reason == "TARGET_OBJECTIVE_UNVERIFIED"
    assert result.content is None


@pytest.mark.parametrize("target_objective_id", ["  ", 123])
def test_invalid_requested_objective_id_is_rejected(tmp_path, target_objective_id):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(_portable_package()).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
        target_objective_id=target_objective_id,
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.target_match is TargetMatch.UNVERIFIED
    assert result.reason == "TARGET_OBJECTIVE_INVALID"
    assert result.target_objective_id == (
        target_objective_id if isinstance(target_objective_id, str) else None
    )
    assert result.content is None


def test_control_master_target_matches_only_listed_objectives(tmp_path):
    payload = {
        "state_id": "state-1",
        "version": "control_master.v1",
        "last_updated": "2026-10-28T11:00:00Z",
        "active_objective_ids": ["obj-a"],
        "completed_objective_ids": [],
        "paused_objective_ids": [],
        "discarded_objective_ids": [],
        "unresolved_items": ["source:unknown"],
    }
    _write_artifact(
        tmp_path,
        ContextArtifact.CONTROL_MASTER,
        json.dumps(payload).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.CONTROL_MASTER,
        freshness_policy=_policy(),
        target_objective_id="obj-a",
    )

    assert result.availability is Availability.AVAILABLE
    assert result.source_identity == "state-1"
    assert result.target_match is TargetMatch.MATCHED
    assert result.unresolved_fields == ("source:unknown",)


def test_unallowlisted_path_selector_is_rejected(tmp_path):
    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact="../../outside.json",
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_NOT_ALLOWLISTED"


def test_invalid_workspace_root_is_unavailable():
    result = _reader().read_existing(
        workspace_root=None,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_INVALID_OR_UNREADABLE"


def test_invalid_freshness_policy_is_unavailable(tmp_path):
    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=None,
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "FRESHNESS_POLICY_INVALID"


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / "outside-context.json"
    outside.write_bytes(json.dumps(_portable_package()).encode("utf-8"))
    link = tmp_path / "data/evolution/portable_context/latest.json"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "PATH_ESCAPES_WORKSPACE"
    assert result.content is None


def test_future_source_timestamp_is_not_reported_as_fresh(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(
            _portable_package(updated_at_utc="2026-10-29T00:00:00Z")
        ).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.freshness is Freshness.UNKNOWN
    assert result.reason == "SOURCE_TIMESTAMP_IN_FUTURE"


def test_unknown_schema_version_is_unavailable(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(
            _portable_package(package_version="portable_context.v999")
        ).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_INVALID_OR_UNREADABLE"


def test_empty_context_artifact_is_unavailable(tmp_path):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(
            _portable_package(summary="", assistant_brief="", sections=[], unresolved_fields=[])
        ).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "EMPTY_CONTEXT"


@pytest.mark.parametrize(
    "updates",
    [
        {"metadata": []},
        {"sections": {}},
        {"sections": ["not-an-object"]},
        {"sections": [{"items": ["not-an-object"]}]},
        {"sections": [{"last_updated": "not-a-date"}]},
        {"sections": [{"last_updated": "2026-10-28T11:00:00"}]},
        {"unresolved_fields": [1]},
        {"updated_at_utc": 123},
    ],
)
def test_malformed_portable_context_structure_is_unavailable(tmp_path, updates):
    _write_artifact(
        tmp_path,
        ContextArtifact.PORTABLE_CONTEXT,
        json.dumps(_portable_package(**updates)).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.PORTABLE_CONTEXT,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_INVALID_OR_UNREADABLE"
    assert result.content is None


@pytest.mark.parametrize(
    "updates",
    [
        {"active_objective_ids": "obj-a"},
        {"current_tests_state": []},
        {"technical_backlog": ["not-an-object"]},
        {"global_rules": [{"title": "rule", "applies_to": "not-a-list"}]},
        {"global_rules": [{"title": "rule", "updated_at_utc": "2026-10-28T11:00:00"}]},
        {"recent_decisions": [{"summary": "decision", "timestamp": "bad-date"}]},
        {"unresolved_items": [None]},
        {"last_updated": 123},
    ],
)
def test_malformed_control_master_structure_is_unavailable(tmp_path, updates):
    payload = {
        "state_id": "state-1",
        "version": "control_master.v1",
        "last_updated": "2026-10-28T11:00:00Z",
        "active_objective_ids": ["obj-a"],
        "completed_objective_ids": [],
        "paused_objective_ids": [],
        "discarded_objective_ids": [],
        "unresolved_items": ["known gap"],
    }
    payload.update(updates)
    _write_artifact(
        tmp_path,
        ContextArtifact.CONTROL_MASTER,
        json.dumps(payload).encode("utf-8"),
    )

    result = _reader().read_existing(
        workspace_root=tmp_path,
        artifact=ContextArtifact.CONTROL_MASTER,
        freshness_policy=_policy(),
    )

    assert result.availability is Availability.UNAVAILABLE
    assert result.reason == "ARTIFACT_INVALID_OR_UNREADABLE"
    assert result.content is None
