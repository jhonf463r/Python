from __future__ import annotations

from pathlib import Path
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
    # All retries exhausted on Windows — fall back to non-atomic overwrite
    # so the process doesn't crash.
    if _IS_WINDOWS and last_err is not None:
        try:
            import shutil
            shutil.copy2(str(src), str(dst))
            try:
                os.unlink(str(src))
            except OSError:
                pass
            logger.warning(
                'os.replace(%s -> %s) failed after %d attempts; '
                'used shutil.copy2 fallback: %s',
                src, dst, _REPLACE_MAX_ATTEMPTS, last_err,
            )
            return
        except Exception:
            pass
    raise last_err  # type: ignore[misc]


class ArtifactStorage:
    """Filesystem-backed artifact storage with atomic JSON helpers."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

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
