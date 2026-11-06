from __future__ import annotations

import json
from hashlib import sha256
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Sequence, TypeVar

from pydantic import ValidationError

T = TypeVar("T")


class ArtifactReadStatus(str, Enum):
    FOUND = "FOUND"
    CONFIRMED_NOT_FOUND = "CONFIRMED_NOT_FOUND"
    READ_FAILED = "READ_FAILED"
    CORRUPT = "CORRUPT"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"


class RepositoryReadStatus(str, Enum):
    READ_OK = "READ_OK"
    READ_PARTIAL = "READ_PARTIAL"
    READ_FAILED = "READ_FAILED"
    NO_RECORDS_OBSERVED = "NO_RECORDS_OBSERVED"
    QUERY_NOT_EXECUTED = "QUERY_NOT_EXECUTED"


@dataclass(frozen=True)
class ArtifactReadResult(Generic[T]):
    """Outcome of reading one indexed JSON artifact; never mutates its index."""

    artifact_id: str
    path: str
    status: ArtifactReadStatus
    value: T | None = None
    error_type: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class RepositoryReadReport(Generic[T]):
    """Per-record outcomes for one bounded repository query.

    `scope` identifies what was enumerated (for example, SQLite index rows).
    NO_RECORDS_OBSERVED is deliberately not an assertion that the filesystem
    contains no unindexed artifacts.
    """

    scope: str
    results: tuple[ArtifactReadResult[T], ...]
    observed_at_utc: str
    collection_error_type: str = ""
    collection_error_message: str = ""
    query_not_executed: bool = False
    requested_artifact_id: str = ""

    @classmethod
    def from_results(
        cls,
        scope: str,
        results: Sequence[ArtifactReadResult[T]],
    ) -> "RepositoryReadReport[T]":
        return cls(
            scope=scope,
            results=tuple(results),
            observed_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def from_collection_error(
        cls,
        scope: str,
        error: Exception,
        *,
        requested_artifact_id: str = "",
    ) -> "RepositoryReadReport[T]":
        return cls(
            scope=scope,
            results=(),
            observed_at_utc=datetime.now(timezone.utc).isoformat(),
            collection_error_type=type(error).__name__,
            collection_error_message="Repository collection read failed.",
            requested_artifact_id=requested_artifact_id,
        )

    @classmethod
    def from_not_executed(
        cls,
        scope: str,
    ) -> "RepositoryReadReport[T]":
        return cls(
            scope=scope,
            results=(),
            observed_at_utc=datetime.now(timezone.utc).isoformat(),
            query_not_executed=True,
        )

    @property
    def status(self) -> RepositoryReadStatus:
        if self.query_not_executed:
            return RepositoryReadStatus.QUERY_NOT_EXECUTED
        if self.collection_error_type:
            return RepositoryReadStatus.READ_FAILED
        if not self.results:
            return RepositoryReadStatus.NO_RECORDS_OBSERVED
        found = sum(r.status == ArtifactReadStatus.FOUND for r in self.results)
        if found == len(self.results):
            return RepositoryReadStatus.READ_OK
        if found:
            return RepositoryReadStatus.READ_PARTIAL
        return RepositoryReadStatus.READ_FAILED

    @property
    def items(self) -> list[T]:
        return [r.value for r in self.results if r.status == ArtifactReadStatus.FOUND and r.value is not None]

    @property
    def records_seen(self) -> int:
        return len(self.results)

    @property
    def records_loaded(self) -> int:
        return sum(r.status == ArtifactReadStatus.FOUND for r in self.results)

    @property
    def missing_ids(self) -> list[str]:
        return [r.artifact_id for r in self.results if r.status == ArtifactReadStatus.CONFIRMED_NOT_FOUND]

    @property
    def failed_ids(self) -> list[str]:
        return [
            r.artifact_id
            for r in self.results
            if r.status in (ArtifactReadStatus.READ_FAILED, ArtifactReadStatus.CORRUPT, ArtifactReadStatus.SCHEMA_UNSUPPORTED)
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "status": self.status.value,
            "query_not_executed": self.query_not_executed,
            "requested_artifact_id": self.requested_artifact_id,
            "observed_at_utc": self.observed_at_utc,
            "records_seen": self.records_seen,
            "records_loaded": self.records_loaded,
            "records_missing": len(self.missing_ids),
            "records_failed": len(self.failed_ids),
            "missing_ids": self.missing_ids,
            "failed_ids": self.failed_ids,
            "collection_error_type": self.collection_error_type,
            "collection_error_message": self.collection_error_message,
            "records": [
                {
                    "artifact_id": result.artifact_id,
                    "path": result.path,
                    "status": result.status.value,
                    "error_type": result.error_type,
                    "error_message": result.error_message,
                }
                for result in self.results
            ],
        }

    def require_complete(self) -> list[T]:
        """Return loaded values only when the read contract is complete.

        NO_RECORDS_OBSERVED is a completed query with zero indexed rows.
        QUERY_NOT_EXECUTED is not a completed read and is fail-closed for
        generic consumers; a legacy caller may handle its known no-op explicitly.
        """
        if self.status in (
            RepositoryReadStatus.READ_PARTIAL,
            RepositoryReadStatus.READ_FAILED,
            RepositoryReadStatus.QUERY_NOT_EXECUTED,
        ):
            raise RepositoryReadError(self)
        return self.items


def inspect_model_file_with_digest(
    path: Path,
    artifact_id: str,
    model_type: type[T],
) -> tuple[ArtifactReadResult[T], str, int]:
    """Read one model once, returning its typed outcome and exact byte digest."""
    try:
        raw_bytes = path.read_bytes()
    except FileNotFoundError:
        return (
            ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
                error_type="FileNotFoundError",
            ),
            "",
            0,
        )
    except OSError as exc:
        return (
            ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Artifact read failed.",
            ),
            "",
            0,
        )

    digest = sha256(raw_bytes).hexdigest()
    size_bytes = len(raw_bytes)
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeError as exc:
        return (
            ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.CORRUPT,
                error_type=type(exc).__name__,
                error_message="Artifact bytes are not valid UTF-8.",
            ),
            digest,
            size_bytes,
        )

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return (
            ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.CORRUPT,
                error_type=type(exc).__name__,
                error_message="Artifact bytes are not valid JSON.",
            ),
            digest,
            size_bytes,
        )

    try:
        value = model_type.model_validate(payload)
    except ValidationError as exc:
        return (
            ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.SCHEMA_UNSUPPORTED,
                error_type=type(exc).__name__,
                error_message="Artifact JSON does not match the supported schema.",
            ),
            digest,
            size_bytes,
        )
    except Exception as exc:
        return (
            ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Artifact validation failed unexpectedly.",
            ),
            digest,
            size_bytes,
        )

    return (
        ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.FOUND,
            value=value,
        ),
        digest,
        size_bytes,
    )


class IndexReconciliationStatus(str, Enum):
    IN_SYNC = "IN_SYNC"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READ_FAILED = "READ_FAILED"
    DIRECTORY_ABSENT = "DIRECTORY_ABSENT"

class IndexReconciliationPathStatus(str, Enum):
    SAFE_CANONICAL_PATH = "SAFE_CANONICAL_PATH"
    SAFE_NONCANONICAL_PATH = "SAFE_NONCANONICAL_PATH"
    MISSING_PATH = "MISSING_PATH"
    INVALID_PATH = "INVALID_PATH"
    READ_FAILED = "READ_FAILED"
    CORRUPT = "CORRUPT"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"


@dataclass(frozen=True)
class IndexReconciliationIndexPathResult:
    artifact_id: str
    status: IndexReconciliationPathStatus
    error_type: str = ""
    error_message: str = ""
    sha256: str = ""
    size_bytes: int = 0


@dataclass(frozen=True)
class IndexReconciliationFileResult:
    """Metadata-only result for one JSON filename discovered during a read-only scan."""

    artifact_id: str
    path: str
    status: ArtifactReadStatus
    error_type: str = ""
    error_message: str = ""
    sha256: str = ""
    size_bytes: int = 0


@dataclass(frozen=True)
class RepositoryIndexReconciliationReport:
    """Read-only comparison of one SQLite index with its managed JSON directory.

    The report contains IDs and outcomes only; it deliberately does not retain
    deserialized dossier/session payloads and provides no method that writes rows.
    """

    scope: str
    indexed_ids: tuple[str, ...]
    files: tuple[IndexReconciliationFileResult, ...]
    index_path_results: tuple[IndexReconciliationIndexPathResult, ...]
    directory_exists: bool
    observed_at_utc: str
    collection_error_type: str = ""
    collection_error_message: str = ""
    filesystem_error_type: str = ""
    filesystem_error_message: str = ""
    ignored_entries: int = 0

    @property
    def filesystem_ids(self) -> list[str]:
        return [item.artifact_id for item in self.files]

    @property
    def unindexed_valid_ids(self) -> list[str]:
        if self.collection_error_type or self.filesystem_error_type or not self.directory_exists:
            return []
        indexed = set(self.indexed_ids)
        return [
            item.artifact_id
            for item in self.files
            if item.status == ArtifactReadStatus.FOUND and item.artifact_id not in indexed
        ]

    @property
    def indexed_without_file_ids(self) -> list[str]:
        if self.collection_error_type or self.filesystem_error_type or not self.directory_exists:
            return []
        observed = set(self.filesystem_ids)
        return [item for item in self.indexed_ids if item not in observed]

    @property
    def index_path_issues(self) -> list[str]:
        return [
            item.artifact_id
            for item in self.index_path_results
            if item.status != IndexReconciliationPathStatus.SAFE_CANONICAL_PATH
        ]

    @property
    def invalid_file_ids(self) -> list[str]:
        return [
            item.artifact_id
            for item in self.files
            if item.status != ArtifactReadStatus.FOUND
        ]

    @property
    def status(self) -> IndexReconciliationStatus:
        if self.collection_error_type or self.filesystem_error_type:
            return IndexReconciliationStatus.READ_FAILED
        if self.unindexed_valid_ids or self.indexed_without_file_ids or self.invalid_file_ids or self.index_path_issues:
            return IndexReconciliationStatus.REVIEW_REQUIRED
        if not self.directory_exists:
            return IndexReconciliationStatus.DIRECTORY_ABSENT
        return IndexReconciliationStatus.IN_SYNC

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "status": self.status.value,
            "observed_at_utc": self.observed_at_utc,
            "directory_exists": self.directory_exists,
            "indexed_count": len(self.indexed_ids),
            "filesystem_count": len(self.files),
            "unindexed_valid_ids": self.unindexed_valid_ids,
            "indexed_without_file_ids": self.indexed_without_file_ids,
            "invalid_file_ids": self.invalid_file_ids,
            "index_path_issues": self.index_path_issues,
            "index_paths": [
                {
                    "artifact_id": item.artifact_id,
                    "status": item.status.value,
                    "error_type": item.error_type,
                    "error_message": item.error_message,
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                }
                for item in self.index_path_results
            ],
            "collection_error_type": self.collection_error_type,
            "collection_error_message": self.collection_error_message,
            "filesystem_error_type": self.filesystem_error_type,
            "filesystem_error_message": self.filesystem_error_message,
            "ignored_entries": self.ignored_entries,
            "files": [
                {
                    "artifact_id": item.artifact_id,
                    "path": item.path,
                    "status": item.status.value,
                    "error_type": item.error_type,
                    "error_message": item.error_message,
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                }
                for item in self.files
            ],
        }


class RepositoryReadError(RuntimeError):
    """Fail-closed compatibility error carrying its structured read report."""

    def __init__(self, report: RepositoryReadReport[Any]) -> None:
        self.report = report
        super().__init__(
            f"Repository read {report.status.value}: "
            f"{report.records_loaded}/{report.records_seen} indexed records loaded; "
            f"missing={len(report.missing_ids)}, failed={len(report.failed_ids)}"
        )


def read_model_file(
    path: Path,
    artifact_id: str,
    model_type: type[T],
) -> ArtifactReadResult[T]:
    """Read and validate one JSON model without creating directories or pruning rows."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
        )
    except UnicodeError as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.CORRUPT,
            error_type=type(exc).__name__,
            error_message="Artifact read or validation failed.",
        )
    except OSError as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.READ_FAILED,
            error_type=type(exc).__name__,
            error_message="Artifact read or validation failed.",
        )

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.CORRUPT,
            error_type=type(exc).__name__,
            error_message="Artifact read or validation failed.",
        )

    try:
        value = model_type.model_validate(payload)
    except ValidationError as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.SCHEMA_UNSUPPORTED,
            error_type=type(exc).__name__,
            error_message="Artifact read or validation failed.",
        )
    except Exception as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.READ_FAILED,
            error_type=type(exc).__name__,
            error_message="Artifact read or validation failed.",
        )

    return ArtifactReadResult(
        artifact_id=artifact_id,
        path=str(path),
        status=ArtifactReadStatus.FOUND,
        value=value,
    )


def read_model_from_paths(
    paths: Sequence[Path],
    artifact_id: str,
    model_type: type[T],
) -> ArtifactReadResult[T]:
    """Try the persisted absolute path then the repository-relative fallback.

    Only a confirmed FileNotFoundError permits trying the next candidate.
    Permission/I/O, JSON and schema failures stop the fallback so a broken
    primary record cannot be hidden by a second path.
    """
    attempted: list[str] = []
    for path in paths:
        attempted.append(str(path))
        result = read_model_file(path, artifact_id, model_type)
        if result.status != ArtifactReadStatus.CONFIRMED_NOT_FOUND:
            return result

    return ArtifactReadResult(
        artifact_id=artifact_id,
        path=" -> ".join(attempted),
        status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
        error_type="FileNotFoundError",
        error_message="No candidate artifact path exists.",
    )



def read_json_mapping_from_paths(
    paths: Sequence[Path],
    artifact_id: str,
) -> ArtifactReadResult[dict[str, Any]]:
    """Read a JSON object from indexed paths without hiding I/O or shape errors."""
    attempted: list[str] = []
    for path in paths:
        attempted.append(str(path))
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except UnicodeError as exc:
            return ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.CORRUPT,
                error_type=type(exc).__name__,
                error_message="Artifact read or validation failed.",
            )
        except OSError as exc:
            return ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.READ_FAILED,
                error_type=type(exc).__name__,
                error_message="Artifact read or validation failed.",
            )

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.CORRUPT,
                error_type=type(exc).__name__,
                error_message="Artifact read or validation failed.",
            )

        if not isinstance(payload, dict):
            return ArtifactReadResult(
                artifact_id=artifact_id,
                path=str(path),
                status=ArtifactReadStatus.SCHEMA_UNSUPPORTED,
                error_type="TypeError",
                error_message="Expected a JSON object at the artifact root.",
            )

        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.FOUND,
            value=payload,
        )

    return ArtifactReadResult(
        artifact_id=artifact_id,
        path=" -> ".join(attempted),
        status=ArtifactReadStatus.CONFIRMED_NOT_FOUND,
        error_type="FileNotFoundError",
        error_message="No candidate artifact path exists.",
    )
