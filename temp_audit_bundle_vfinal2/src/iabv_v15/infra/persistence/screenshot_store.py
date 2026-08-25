from __future__ import annotations

from pathlib import Path
from typing import Any

from iabv_v15.infra.persistence.storage import ArtifactStorage

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional at runtime
    Image = None


class ScreenshotStore:
    def __init__(self, storage: ArtifactStorage):
        self.storage = storage

    def save_bytes(self, episode_id: str, file_name: str, data: bytes) -> str:
        relative_path = f"{episode_id}/{file_name}"
        return self.storage.save_bytes(relative_path, data)

    def save_image(self, episode_id: str, file_name: str, image: Any) -> str:
        if Image is None:
            raise RuntimeError("Pillow is required to save image objects.")
        path = self.storage.resolve(f"{episode_id}/{file_name}")
        image.save(path)
        return str(path)

    def crop(self, source_path: str, bbox: tuple[int, int, int, int], out_path: str) -> str:
        if Image is None:
            raise RuntimeError("Pillow is required to crop screenshots.")
        image = Image.open(source_path)
        cropped = image.crop(bbox)
        target = Path(out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(target)
        return str(target)
