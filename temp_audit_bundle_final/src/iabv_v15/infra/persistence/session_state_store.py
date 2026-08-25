from __future__ import annotations

from pathlib import Path
import json
import shutil
import time
from typing import Any


class SessionStateStore:
    """Portable JSON state store with timestamped backups."""

    def backup_file(self, path: str) -> str | None:
        file_path = Path(path)
        if not file_path.exists():
            return None
        ts = time.strftime("%Y%m%d%H%M%S")
        backup = file_path.with_suffix(file_path.suffix + f".{ts}.bak")
        shutil.copy(file_path, backup)
        return str(backup)

    def save_json_atomic(self, payload: dict[str, Any], path: str) -> str:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp = file_path.with_suffix(file_path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(file_path)
        return str(file_path)

    def load_json(self, path: str) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def save_with_backup(self, path: str, payload: dict[str, Any] | None = None) -> str | None:
        backup_path = self.backup_file(path)
        if payload is not None:
            self.save_json_atomic(payload, path)
        return backup_path
