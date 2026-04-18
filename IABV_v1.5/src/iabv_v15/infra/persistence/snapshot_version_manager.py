from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


class SnapshotVersionManager:
    """Compact versioned snapshot manager adapted from the v1.3 ideas."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot_atomic(self, relative_path: str, snapshot: dict[str, Any]) -> str:
        path = self.root_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(snapshot)
        payload.setdefault("meta", {})
        payload["meta"].setdefault("saved_at", _now_iso())
        payload["meta"]["snapshot_hash"] = _stable_hash(payload.get("payload", payload))
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
        return str(path)

    def load_snapshot(self, relative_path: str) -> dict[str, Any]:
        path = self.root_dir / relative_path
        return json.loads(path.read_text(encoding="utf-8"))

    def check_compatibility(self, snapshot: dict[str, Any], new_spec: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        old_spec = snapshot.get("spec", {})
        old_keys = set(old_spec.keys())
        new_keys = set(new_spec.keys())
        missing = sorted(old_keys - new_keys)
        added = sorted(new_keys - old_keys)
        common_changed = sorted(
            key for key in old_keys & new_keys if old_spec.get(key) != new_spec.get(key)
        )
        details = {"missing": missing, "added": added, "changed": common_changed}
        if missing:
            return "breaking", details
        if common_changed or added:
            return "adaptable", details
        return "compatible", details

    def migrate_snapshot(self, snapshot: dict[str, Any], new_spec: dict[str, Any]) -> dict[str, Any]:
        compatibility, details = self.check_compatibility(snapshot, new_spec)
        if compatibility == "breaking":
            raise ValueError(f"Breaking snapshot change: {details}")
        migrated = dict(snapshot)
        migrated["spec"] = dict(new_spec)
        migrated.setdefault("meta", {})
        migrated["meta"]["migrated_at"] = _now_iso()
        migrated["meta"]["compatibility"] = compatibility
        return migrated
