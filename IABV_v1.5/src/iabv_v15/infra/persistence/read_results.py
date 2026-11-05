from __future__ import annotations

import json
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
    ) -> "RepositoryReadReport[T]":
        return cls(
            scope=scope,
            results=(),
            observed_at_utc=datetime.now(timezone.utc).isoformat(),
            collection_error_type=type(error).__name__,
            collection_error_message=str(error)[:300],
        )

    @property
    def status(self) -> RepositoryReadStatus:
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
        """Return loaded values only when every observed index row was read.

        A query with no indexed rows returns an empty list, but its separate
        NO_RECORDS_OBSERVED status must not be interpreted as a filesystem-wide
        empty inventory.
        """
        if self.status in (RepositoryReadStatus.READ_PARTIAL, RepositoryReadStatus.READ_FAILED):
            raise RepositoryReadError(self)
        return self.items


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
            error_message=str(exc)[:300],
        )
    except OSError as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.READ_FAILED,
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
        )

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.CORRUPT,
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
        )

    try:
        value = model_type.model_validate(payload)
    except ValidationError as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.SCHEMA_UNSUPPORTED,
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
        )
    except Exception as exc:
        return ArtifactReadResult(
            artifact_id=artifact_id,
            path=str(path),
            status=ArtifactReadStatus.READ_FAILED,
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
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
