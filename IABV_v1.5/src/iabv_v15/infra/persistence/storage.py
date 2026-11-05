from __future__ import annotations

from pathlib import Path, PureWindowsPath
import json
import logging
import os
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

# On Windows, os.replace() can fail with PermissionError (WinError 32)
# when the target file is temporarily locked by antivirus, indexer, or
# another thread.  _replace_with_retry wraps the call with short retries.
_IS_WINDOWS = sys.platform == 'win32'
_REPLACE_MAX_ATTEMPTS = 5 if _IS_WINDOWS else 1
_REPLACE_RETRY_DELAY = 0.15  # seconds between retries


def _replace_with_retry(src: str | Path, dst: str | Path) -> None:
    """os.replace with retry on Windows PermissionError."""
    last_err: Exception | None = None
    for attempt in range(_REPLACE_MAX_ATTEMPTS):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            last_err = exc
            if not _IS_WINDOWS or attempt >= _REPLACE_MAX_ATTEMPTS - 1:
                break
            logger.debug(
                'os.replace(%s -> %s) blocked (attempt %d/%d): %s',
                src, dst, attempt + 1, _REPLACE_MAX_ATTEMPTS, exc,
            )
            time.sleep(_REPLACE_RETRY_DELAY * (attempt + 1))
    # A direct copy over the destination is not an atomic replacement. If
    # Windows keeps the destination locked, fail closed and retain the source
    # temporary file for recovery; never overwrite the previous destination
    # with a copy that can be interrupted halfway through.
    if last_err is not None:
        logger.error(
            'os.replace(%s -> %s) failed after %d attempts; '
            'destination left untouched and source retained: %s',
            src, dst, max(1, _REPLACE_MAX_ATTEMPTS), last_err,
        )
        raise last_err
    raise OSError("os.replace did not execute because the retry count was zero.")


class ArtifactStorage:
    """Filesystem-backed artifact storage with atomic JSON helpers."""

    def __init__(self, root: str):
        self.root = Path(root).resolve(strict=False)
        self.root.mkdir(parents=True, exist_ok=True)
        self.root = self.root.resolve(strict=True)

    def resolve_managed_path(self, path_like: str | Path) -> Path:
        """Resolve an indexed or relative artifact path without leaving this storage root."""
        raw = str(path_like)
        if not raw or "\x00" in raw:
            raise ValueError("Artifact path must be a non-empty path without NUL bytes.")

        candidate = Path(raw)
        windows_candidate = PureWindowsPath(raw)
        if not candidate.is_absolute():
            if windows_candidate.is_absolute() or windows_candidate.drive:
                raise ValueError("Artifact path must be relative to ArtifactStorage.")
            if any(part == ".." for part in candidate.parts) or any(
                part == ".." for part in windows_candidate.parts
            ):
                raise ValueError("Artifact path traversal is not allowed.")
            candidate = self.root / candidate

        resolved = candidate.resolve(strict=False)
        root = self.root.resolve(strict=True)
        if resolved != root and root not in resolved.parents:
            raise ValueError("Artifact path is outside the configured storage root.")
        return resolved

    def resolve(self, relative_path: str) -> Path:
        """Resolve a relative path, rejecting traversal and symlink escapes."""
        raw = str(relative_path)
        candidate = Path(raw)
        windows_candidate = PureWindowsPath(raw)
        if candidate.is_absolute() or windows_candidate.is_absolute() or windows_candidate.drive:
            raise ValueError("ArtifactStorage.resolve() accepts relative paths only.")
        self.resolve_managed_path(raw).parent.mkdir(parents=True, exist_ok=True)
        # Re-check after parent creation so a pre-existing symlink cannot redirect
        # the path outside the storage root.
        return self.resolve_managed_path(raw)

    def exists(self, relative_path: str) -> bool:
        return self.resolve(relative_path).exists()

    def save_bytes(self, relative_path: str, data: bytes) -> str:
        path = self.resolve(relative_path)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(data)
        _replace_with_retry(temp, path)
        return str(path)

    def load_bytes(self, relative_path: str) -> bytes:
        return self.resolve(relative_path).read_bytes()

    def save_json_atomic(self, relative_path: str, payload: Any) -> str:
        path = self.resolve(relative_path)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        _replace_with_retry(temp, path)
        return str(path)

    def load_json(self, relative_path: str) -> Any:
        return json.loads(self.resolve(relative_path).read_text(encoding="utf-8"))

    def list(self, relative_dir: str) -> list[str]:
        directory = self.resolve(relative_dir)
        if not directory.exists():
            return []
        return sorted(str(item) for item in directory.iterdir())
