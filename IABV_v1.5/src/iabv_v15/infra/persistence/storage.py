from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any


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
        os.replace(temp, path)
        return str(path)

    def load_bytes(self, relative_path: str) -> bytes:
        return self.resolve(relative_path).read_bytes()

    def save_json_atomic(self, relative_path: str, payload: Any) -> str:
        path = self.resolve(relative_path)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
        return str(path)

    def load_json(self, relative_path: str) -> Any:
        return json.loads(self.resolve(relative_path).read_text(encoding="utf-8"))

    def list(self, relative_dir: str) -> list[str]:
        directory = self.resolve(relative_dir)
        if not directory.exists():
            return []
        return sorted(str(item) for item in directory.iterdir())
