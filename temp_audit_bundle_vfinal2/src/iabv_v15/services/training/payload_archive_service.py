from __future__ import annotations

from pathlib import Path

from iabv_v15.domain.models import TrainingPayloadV2
from iabv_v15.infra.persistence.snapshot_version_manager import SnapshotVersionManager


class PayloadArchiveService:
    def __init__(self, root_dir: str, snapshot_manager: SnapshotVersionManager):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_manager = snapshot_manager

    def archive(self, payload: TrainingPayloadV2, name: str = "training_payload_v2.json") -> str:
        relative_path = name
        return self.snapshot_manager.save_snapshot_atomic(
            relative_path,
            {
                "spec": {
                    "version": payload.version,
                    "fields": [
                        "episodes",
                        "steps",
                        "artifacts",
                        "knowledge_items",
                        "run_records",
                        "capture_channels",
                        "site_context",
                        "redaction_summary",
                        "metadata",
                    ],
                },
                "payload": payload.model_dump(mode="json"),
            },
        )
