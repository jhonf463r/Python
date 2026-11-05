from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
import json
from uuid import uuid4

from iabv_v15.domain.models import CapturedStep, EpisodeManifest
from iabv_v15.infra.persistence.database import AppDatabase


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EpisodeRepository:
    def __init__(self, base_dir: str, db: AppDatabase):
        self.base_dir = Path(base_dir).resolve(strict=False)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir = self.base_dir.resolve(strict=True)
        self.db = db

    def _episode_directory(self, episode_id: str) -> Path:
        """Validate an episode ID as one safe path component before filesystem access."""
        if not isinstance(episode_id, str) or not episode_id or episode_id.strip() != episode_id:
            raise ValueError("Episode ID must be a non-empty, trimmed string.")
        windows = PureWindowsPath(episode_id)
        if (
            episode_id in {".", ".."}
            or "/" in episode_id
            or "\\" in episode_id
            or "\x00" in episode_id
            or Path(episode_id).is_absolute()
            or windows.is_absolute()
            or windows.drive
            or len(windows.parts) != 1
        ):
            raise ValueError("Episode ID must be a single safe path component.")
        candidate = (self.base_dir / episode_id).resolve(strict=False)
        root = self.base_dir.resolve(strict=True)
        if candidate != root and root not in candidate.parents:
            raise ValueError("Episode path is outside the configured episodes directory.")
        return candidate

    def create_episode(self, title: str, tags: list[str] | None = None, notes: str = "") -> EpisodeManifest:
        manifest = EpisodeManifest(
            episode_id=str(uuid4()),
            title=title,
            tags=tags or [],
            notes=notes,
        )
        self._write_manifest(manifest)
        self.db.execute(
            """
            INSERT OR REPLACE INTO episodes (episode_id, title, manifest_json, step_count, updated_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                manifest.episode_id,
                manifest.title,
                manifest.model_dump_json(),
                manifest.step_count,
                manifest.updated_at_utc.isoformat(),
            ),
        )
        return manifest

    def save_step(self, episode_id: str, step: CapturedStep) -> CapturedStep:
        if step.episode_id != episode_id:
            raise ValueError("Captured step episode_id does not match the target episode.")
        episode_dir = self._episode_directory(episode_id)
        episode_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = episode_dir / "episode.jsonl"
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(step.model_dump_json() + "\n")
        manifest = self.get_manifest(episode_id)
        manifest.step_count += 1
        manifest.updated_at_utc = datetime.now(timezone.utc)
        self._write_manifest(manifest)
        self.db.execute(
            """
            INSERT OR REPLACE INTO episodes (episode_id, title, manifest_json, step_count, updated_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                manifest.episode_id,
                manifest.title,
                manifest.model_dump_json(),
                manifest.step_count,
                manifest.updated_at_utc.isoformat(),
            ),
        )
        return step

    def load_episode(self, episode_id: str) -> list[CapturedStep]:
        jsonl_path = self._episode_directory(episode_id) / "episode.jsonl"
        if not jsonl_path.exists():
            return []
        return [
            CapturedStep.model_validate_json(line)
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def get_manifest(self, episode_id: str) -> EpisodeManifest:
        path = self._episode_directory(episode_id) / "manifest.json"
        if path.exists():
            return EpisodeManifest.model_validate_json(path.read_text(encoding="utf-8"))
        row = self.db.fetchone("SELECT manifest_json FROM episodes WHERE episode_id = ?", (episode_id,))
        if row is None:
            raise FileNotFoundError(f"Episode {episode_id} not found.")
        return EpisodeManifest.model_validate_json(row["manifest_json"])

    def count(self) -> int:
        row = self.db.fetchone("SELECT COUNT(*) AS cnt FROM episodes")
        return int(row["cnt"]) if row else 0

    def list_recent(self, limit: int = 20) -> list[EpisodeManifest]:
        rows = self.db.fetchall(
            "SELECT manifest_json FROM episodes ORDER BY updated_at_utc DESC LIMIT ?",
            (limit,),
        )
        manifests = [EpisodeManifest.model_validate_json(row["manifest_json"]) for row in rows]
        for manifest in manifests:
            self._episode_directory(manifest.episode_id)
        return manifests

    def _write_manifest(self, manifest: EpisodeManifest) -> None:
        episode_dir = self._episode_directory(manifest.episode_id)
        episode_dir.mkdir(parents=True, exist_ok=True)
        (episode_dir / "manifest.json").write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
