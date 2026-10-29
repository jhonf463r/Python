"""Side-effect-bounded reader for existing Control Master context artifacts.

This module intentionally uses only the Python standard library. It does not
construct application services or create, refresh, or persist artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


_MAX_ARTIFACT_BYTES = 2 * 1024 * 1024


class ContextArtifact(str, Enum):
    CONTROL_MASTER = "control_master"
    PORTABLE_CONTEXT = "portable_context"


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class Freshness(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class TargetMatch(str, Enum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    UNVERIFIED = "UNVERIFIED"
    NOT_REQUESTED = "NOT_REQUESTED"


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.max_age_seconds, int) or isinstance(self.max_age_seconds, bool) or self.max_age_seconds < 0:
            raise ValueError("max_age_seconds must be a non-negative integer")


@dataclass(frozen=True)
class ContextReadResult:
    availability: Availability
    artifact: ContextArtifact | None
    source_path: str
    source_identity: str | None
    schema_version: str | None
    source_timestamp_utc: datetime | None
    observed_at_utc: datetime | None
    age_seconds: float | None
    freshness: Freshness
    freshness_policy: FreshnessPolicy | None
    target_objective_id: str | None
    target_match: TargetMatch
    unresolved_fields: tuple[str, ...]
    content_sha256: str | None
    content: Mapping[str, Any] | None
    reason: str | None = None


_ARTIFACT_PATHS: dict[ContextArtifact, str] = {
    ContextArtifact.CONTROL_MASTER: "data/evolution/control_master/latest.json",
    ContextArtifact.PORTABLE_CONTEXT: "data/evolution/portable_context/latest.json",
}


class _DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_json_constant(token: str) -> Any:
    raise ValueError(f"non-standard JSON constant: {token}")


def _parse_source_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _is_datetime_string(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _file_identity(stat_result: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(stat_result.st_dev),
        int(stat_result.st_ino),
        int(stat_result.st_size),
        int(stat_result.st_mtime_ns),
    )


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_object(value: Any) -> bool:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _is_object_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_object(item) for item in value)


def _valid_optional_fields(
    payload: Mapping[str, Any],
    string_fields: tuple[str, ...] = (),
    string_list_fields: tuple[str, ...] = (),
    object_fields: tuple[str, ...] = (),
    object_list_fields: tuple[str, ...] = (),
    timestamp_fields: tuple[str, ...] = (),
) -> bool:
    for field in string_fields:
        if field in payload and not _is_string(payload[field]):
            return False
    for field in string_list_fields:
        if field in payload and not _is_string_list(payload[field]):
            return False
    for field in object_fields:
        if field in payload and not _is_object(payload[field]):
            return False
    for field in object_list_fields:
        if field in payload and not _is_object_list(payload[field]):
            return False
    for field in timestamp_fields:
        if field in payload and not _is_datetime_string(payload[field]):
            return False
    return True


def _valid_control_rule(value: Any) -> bool:
    if not _is_object(value) or not _is_string(value.get("title")):
        return False
    if not _valid_optional_fields(
        value,
        string_fields=("rule_id", "title", "description", "severity", "rationale", "status"),
        string_list_fields=("applies_to", "source_refs"),
        timestamp_fields=("created_at_utc", "updated_at_utc"),
    ):
        return False
    return value.get("severity", "advisory") in {
        "info", "advisory", "strict", "irrevocable"
    } and value.get("status", "active") in {
        "active", "deprecated", "superseded"
    }


def _valid_control_decision(value: Any) -> bool:
    if not _is_object(value) or not _is_string(value.get("summary")):
        return False
    if not _valid_optional_fields(
        value,
        string_fields=("decision_id", "summary", "reason", "impact", "status"),
        string_list_fields=(
            "affected_modules", "evidence", "linked_tests", "related_rule_ids",
            "related_objective_ids", "unresolved_notes",
        ),
        timestamp_fields=("timestamp",),
    ):
        return False
    return value.get("status", "proposed") in {
        "proposed", "accepted", "implemented", "reverted"
    }


def _valid_portable_section(value: Any) -> bool:
    if not _is_object(value):
        return False
    if not _valid_optional_fields(
        value,
        string_fields=("section_id", "title", "summary", "source_kind"),
        string_list_fields=("source_refs", "unresolved_fields"),
        object_fields=("metadata",),
        object_list_fields=("items",),
        timestamp_fields=("last_updated",),
    ):
        return False
    if "confidence" in value and (
        not isinstance(value["confidence"], (int, float))
        or isinstance(value["confidence"], bool)
    ):
        return False
    return True


def _valid_control_master(payload: Mapping[str, Any]) -> bool:
    if not _valid_optional_fields(
        payload,
        string_fields=("state_id", "version", "current_vision"),
        string_list_fields=(
            "active_objective_ids", "completed_objective_ids", "paused_objective_ids",
            "discarded_objective_ids", "unresolved_items", "evidence_links",
        ),
        object_fields=("current_tests_state", "metadata"),
        object_list_fields=("technical_backlog", "current_risks"),
        timestamp_fields=(),
    ):
        return False
    if "global_rules" in payload and (
        not isinstance(payload["global_rules"], list)
        or not all(_valid_control_rule(item) for item in payload["global_rules"])
    ):
        return False
    if "recent_decisions" in payload and (
        not isinstance(payload["recent_decisions"], list)
        or not all(_valid_control_decision(item) for item in payload["recent_decisions"])
    ):
        return False
    return True


def _valid_portable_context(payload: Mapping[str, Any]) -> bool:
    if not _valid_optional_fields(
        payload,
        string_fields=(
            "package_id", "package_version", "project_id", "summary", "assistant_brief",
            "package_path", "markdown_path",
        ),
        string_list_fields=("unresolved_fields",),
        object_fields=("metadata",),
        timestamp_fields=("created_at_utc",),
    ):
        return False
    if "sections" in payload and (
        not isinstance(payload["sections"], list)
        or not all(_valid_portable_section(item) for item in payload["sections"])
    ):
        return False
    return True


class ControlMasterContextReader:
    """Reads one allowlisted, already-existing context JSON artifact."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or _utc_now

    def read_existing(
        self,
        *,
        workspace_root: str | Path,
        artifact: ContextArtifact | str,
        freshness_policy: FreshnessPolicy,
        target_objective_id: str | None = None,
    ) -> ContextReadResult:
        try:
            selected_artifact = ContextArtifact(artifact)
        except (TypeError, ValueError):
            return self._unavailable(
                source_path="",
                reason="ARTIFACT_NOT_ALLOWLISTED",
                target_objective_id=target_objective_id,
                freshness_policy=freshness_policy,
            )

        if not isinstance(freshness_policy, FreshnessPolicy):
            return self._unavailable(
                artifact=selected_artifact,
                source_path=_ARTIFACT_PATHS[selected_artifact],
                reason="FRESHNESS_POLICY_INVALID",
                target_objective_id=target_objective_id,
            )

        if target_objective_id is not None and (
            not isinstance(target_objective_id, str) or not target_objective_id.strip()
        ):
            return self._unavailable(
                artifact=selected_artifact,
                source_path=_ARTIFACT_PATHS[selected_artifact],
                reason="TARGET_OBJECTIVE_INVALID",
                target_objective_id=target_objective_id,
                freshness_policy=freshness_policy,
                target_match=TargetMatch.UNVERIFIED,
            )

        source_path = _ARTIFACT_PATHS[selected_artifact]
        try:
            root = Path(workspace_root).resolve(strict=True)
            if not root.is_dir():
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="WORKSPACE_ROOT_NOT_DIRECTORY",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                )

            candidate = root.joinpath(*Path(source_path).parts)
            resolved = candidate.resolve(strict=True)
            if not _inside(root, resolved):
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="PATH_ESCAPES_WORKSPACE",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                )
            if not resolved.is_file():
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="ARTIFACT_NOT_A_FILE",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                )

            with resolved.open("rb") as stream:
                before = os.fstat(stream.fileno())
                raw = stream.read(_MAX_ARTIFACT_BYTES + 1)
                after = os.fstat(stream.fileno())
            if len(raw) > _MAX_ARTIFACT_BYTES:
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="ARTIFACT_TOO_LARGE",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                )
            if _file_identity(before) != _file_identity(after):
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="ARTIFACT_CHANGED_DURING_READ",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                )

            resolved_after = candidate.resolve(strict=True)
            if resolved_after != resolved or not _inside(root, resolved_after):
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="PATH_CHANGED_DURING_READ",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                )

            digest = hashlib.sha256(raw).hexdigest()
            payload = json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonstandard_json_constant,
            )
            if not isinstance(payload, dict):
                raise ValueError("artifact root must be a JSON object")

            identity_key = (
                "state_id"
                if selected_artifact is ContextArtifact.CONTROL_MASTER
                else "package_id"
            )
            version_key = (
                "version"
                if selected_artifact is ContextArtifact.CONTROL_MASTER
                else "package_version"
            )
            source_time_key = (
                "last_updated"
                if selected_artifact is ContextArtifact.CONTROL_MASTER
                else "updated_at_utc"
            )
            identity = payload.get(identity_key)
            version = payload.get(version_key)
            if not isinstance(identity, str) or not identity.strip():
                raise ValueError("source identity is missing")
            if not isinstance(version, str) or not version.strip():
                raise ValueError("schema version is missing")
            expected_version = (
                "control_master.v1"
                if selected_artifact is ContextArtifact.CONTROL_MASTER
                else "portable_context.v1"
            )
            if version != expected_version:
                raise ValueError("unsupported schema version")
            schema_valid = (
                _valid_control_master(payload)
                if selected_artifact is ContextArtifact.CONTROL_MASTER
                else _valid_portable_context(payload)
            )
            if not schema_valid:
                raise ValueError("artifact fields do not match the declared schema")

            source_time_value = payload.get(source_time_key)
            if source_time_value is not None and (
                not isinstance(source_time_value, str)
                or _parse_source_timestamp(source_time_value) is None
            ):
                raise ValueError("source timestamp has an invalid shape")
            source_timestamp = _parse_source_timestamp(source_time_value)
            if source_timestamp is None:
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="SOURCE_TIMESTAMP_UNKNOWN",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                    source_identity=identity,
                    schema_version=version,
                    content_sha256=digest,
                )

            unresolved_key = (
                "unresolved_items"
                if selected_artifact is ContextArtifact.CONTROL_MASTER
                else "unresolved_fields"
            )
            unresolved_value = payload.get(unresolved_key, [])
            if not isinstance(unresolved_value, list) or any(
                not isinstance(item, str) for item in unresolved_value
            ):
                raise ValueError("unresolved fields have an invalid shape")
            if not self._has_context(selected_artifact, payload, unresolved_value):
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="EMPTY_CONTEXT",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                    source_identity=identity,
                    schema_version=version,
                    source_timestamp_utc=source_timestamp,
                    content_sha256=digest,
                )

            observed_at = self._clock()
            if observed_at.tzinfo is None or observed_at.utcoffset() is None:
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="READER_CLOCK_UNKNOWN",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                    source_identity=identity,
                    schema_version=version,
                    source_timestamp_utc=source_timestamp,
                    content_sha256=digest,
                )
            observed_at = observed_at.astimezone(timezone.utc)
            age_seconds = (observed_at - source_timestamp).total_seconds()
            if age_seconds < 0:
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="SOURCE_TIMESTAMP_IN_FUTURE",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                    source_identity=identity,
                    schema_version=version,
                    source_timestamp_utc=source_timestamp,
                    observed_at_utc=observed_at,
                    content_sha256=digest,
                )

            target_match = self._match_target(
                selected_artifact,
                payload,
                target_objective_id,
            )
            if target_match is TargetMatch.MISMATCH:
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="TARGET_OBJECTIVE_MISMATCH",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                    source_identity=identity,
                    schema_version=version,
                    source_timestamp_utc=source_timestamp,
                    observed_at_utc=observed_at,
                    age_seconds=age_seconds,
                    target_match=target_match,
                    unresolved_fields=tuple(unresolved_value),
                    content_sha256=digest,
                )
            if target_objective_id is not None and target_match is not TargetMatch.MATCHED:
                return self._unavailable(
                    artifact=selected_artifact,
                    source_path=source_path,
                    reason="TARGET_OBJECTIVE_UNVERIFIED",
                    target_objective_id=target_objective_id,
                    freshness_policy=freshness_policy,
                    source_identity=identity,
                    schema_version=version,
                    source_timestamp_utc=source_timestamp,
                    observed_at_utc=observed_at,
                    age_seconds=age_seconds,
                    target_match=target_match,
                    unresolved_fields=tuple(unresolved_value),
                    content_sha256=digest,
                )

            if age_seconds > freshness_policy.max_age_seconds:
                return ContextReadResult(
                    availability=Availability.STALE,
                    artifact=selected_artifact,
                    source_path=source_path,
                    source_identity=identity,
                    schema_version=version,
                    source_timestamp_utc=source_timestamp,
                    observed_at_utc=observed_at,
                    age_seconds=age_seconds,
                    freshness=Freshness.STALE,
                    freshness_policy=freshness_policy,
                    target_objective_id=target_objective_id,
                    target_match=target_match,
                    unresolved_fields=tuple(unresolved_value),
                    content_sha256=digest,
                    content=None,
                    reason="SOURCE_EXCEEDS_FRESHNESS_POLICY",
                )

            return ContextReadResult(
                availability=Availability.AVAILABLE,
                artifact=selected_artifact,
                source_path=source_path,
                source_identity=identity,
                schema_version=version,
                source_timestamp_utc=source_timestamp,
                observed_at_utc=observed_at,
                age_seconds=age_seconds,
                freshness=Freshness.FRESH,
                freshness_policy=freshness_policy,
                target_objective_id=target_objective_id,
                target_match=target_match,
                unresolved_fields=tuple(unresolved_value),
                content_sha256=digest,
                content=payload,
            )
        except FileNotFoundError:
            return self._unavailable(
                artifact=selected_artifact,
                source_path=source_path,
                reason="ARTIFACT_NOT_FOUND",
                target_objective_id=target_objective_id,
                freshness_policy=freshness_policy,
            )
        except (
            OSError,
            RuntimeError,
            TypeError,
            UnicodeError,
            json.JSONDecodeError,
            _DuplicateKeyError,
            ValueError,
        ):
            return self._unavailable(
                artifact=selected_artifact,
                source_path=source_path,
                reason="ARTIFACT_INVALID_OR_UNREADABLE",
                target_objective_id=target_objective_id,
                freshness_policy=freshness_policy,
            )

    @staticmethod
    def _has_context(
        artifact: ContextArtifact,
        payload: Mapping[str, Any],
        unresolved_fields: list[str],
    ) -> bool:
        if unresolved_fields:
            return True
        if artifact is ContextArtifact.CONTROL_MASTER:
            keys = (
                "current_vision",
                "active_objective_ids",
                "completed_objective_ids",
                "paused_objective_ids",
                "discarded_objective_ids",
                "global_rules",
                "technical_backlog",
                "recent_decisions",
                "current_risks",
                "current_tests_state",
                "evidence_links",
            )
        else:
            keys = ("summary", "assistant_brief", "sections")
        return any(bool(payload.get(key)) for key in keys)

    @staticmethod
    def _match_target(
        artifact: ContextArtifact,
        payload: Mapping[str, Any],
        target_objective_id: str | None,
    ) -> TargetMatch:
        if target_objective_id is None:
            return TargetMatch.NOT_REQUESTED
        if not isinstance(target_objective_id, str) or not target_objective_id.strip():
            return TargetMatch.UNVERIFIED

        if artifact is ContextArtifact.CONTROL_MASTER:
            fields = (
                "active_objective_ids",
                "completed_objective_ids",
                "paused_objective_ids",
                "discarded_objective_ids",
            )
            values: list[str] = []
            fields_present = False
            for field in fields:
                field_value = payload.get(field)
                if field_value is None:
                    continue
                fields_present = True
                if not isinstance(field_value, list) or any(
                    not isinstance(item, str) for item in field_value
                ):
                    return TargetMatch.UNVERIFIED
                values.extend(field_value)
            if not fields_present:
                return TargetMatch.UNVERIFIED
            return (
                TargetMatch.MATCHED
                if target_objective_id in values
                else TargetMatch.MISMATCH
            )

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return TargetMatch.UNVERIFIED
        source_objective = metadata.get("active_objective_id")
        if not isinstance(source_objective, str) or not source_objective.strip():
            return TargetMatch.UNVERIFIED
        return (
            TargetMatch.MATCHED
            if source_objective == target_objective_id
            else TargetMatch.MISMATCH
        )

    @staticmethod
    def _unavailable(
        *,
        source_path: str,
        reason: str,
        artifact: ContextArtifact | None = None,
        target_objective_id: str | None = None,
        freshness_policy: FreshnessPolicy | None = None,
        source_identity: str | None = None,
        schema_version: str | None = None,
        source_timestamp_utc: datetime | None = None,
        observed_at_utc: datetime | None = None,
        age_seconds: float | None = None,
        target_match: TargetMatch = TargetMatch.UNVERIFIED,
        unresolved_fields: tuple[str, ...] = (),
        content_sha256: str | None = None,
    ) -> ContextReadResult:
        return ContextReadResult(
            availability=Availability.UNAVAILABLE,
            artifact=artifact,
            source_path=source_path,
            source_identity=source_identity,
            schema_version=schema_version,
            source_timestamp_utc=source_timestamp_utc,
            observed_at_utc=observed_at_utc,
            age_seconds=age_seconds,
            freshness=Freshness.UNKNOWN,
            freshness_policy=freshness_policy,
            target_objective_id=(
                target_objective_id
                if isinstance(target_objective_id, str)
                else None
            ),
            target_match=target_match,
            unresolved_fields=unresolved_fields,
            content_sha256=content_sha256,
            content=None,
            reason=reason,
        )
