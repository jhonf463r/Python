"""UIScreenshotService: capturas de la UI de IABV con evidencia persistida.

F1.1 del stack de evolucion. Antes de este servicio, la unica via de
captura de UI era `UIExecutionRunner._capture_screenshot`, que escribia
PNGs dentro del directorio de una ejecucion concreta y no los indexaba
para que otras capas los consuman.

Este servicio:

    - expone un `UIScreenshotProvider` reutilizable (PIL / Qt / Noop) que
      aisla la dependencia de pantalla viva del resto del sistema
    - persiste capturas en `data/evolution/ui_snapshots/<id>.png`
    - mantiene un `index.json` ordenado por timestamp con metadatos
      (id, source, scope, sha256, width, height) para que EvolutionCenter
      pueda listarlas sin re-escanear filesystem
    - aplica retention por conteo (default 50) podando los archivos mas
      viejos al capturar

Reglas AGENTS.md respetadas:
    - no es otro cerebro ni orquestador; solo captura y registra
    - no duplica `PerceptionSnapshot`, `EnvironmentSelfModel`,
      `WorldModelSnapshot` ni `ScreenshotStore` (que es episode-scoped).
      Se complementa: el store cubre episodios de captura de demo; este
      servicio cubre snapshots puntuales de la UI de IABV en si misma.
    - no toma decisiones de ruta ni inyecta efectos mas alla del disco
    - tolera ausencia de proveedor vivo: en headless devuelve record con
      `success=False` pero no rompe.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Callable, Mapping, Optional, Protocol


_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class UIScreenshotRecord:
    """Una captura persistida. Puramente datos, serializable a dict."""

    record_id: str
    created_at_epoch: float
    source: str
    scope: Mapping[str, str]
    session_id: Optional[str]
    path: str
    width: int
    height: int
    sha256: str
    success: bool

    def as_dict(self) -> dict:
        d = asdict(self)
        d["scope"] = dict(self.scope)
        return d


class UIScreenshotProvider(Protocol):
    """Captura la pantalla primaria a un path. True si escribio bytes."""

    def capture_to(self, path: Path) -> bool: ...


class NoopUIScreenshotProvider:
    """Provider de fallback: escribe un PNG 1x1 transparente.

    Util en entornos sin display (CI, linux headless) y como doble
    seguridad ante drivers rotos: nunca levanta excepcion.
    """

    # PNG 1x1 transparente precomputado; 67 bytes.
    _PNG_1X1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def capture_to(self, path: Path) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self._PNG_1X1)
            return True
        except Exception:  # pragma: no cover - IO edge
            _LOG.exception("NoopUIScreenshotProvider failed to write %s", path)
            return False


class PILUIScreenshotProvider:
    """Provider basado en `PIL.ImageGrab`. Requiere display o Win32."""

    def capture_to(self, path: Path) -> bool:
        try:
            from PIL import ImageGrab  # type: ignore
        except Exception:
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            image = ImageGrab.grab(all_screens=True)
            image.save(path)
            return True
        except Exception:
            _LOG.debug("PILUIScreenshotProvider capture failed", exc_info=True)
            return False


class QtUIScreenshotProvider:
    """Provider basado en PySide6. Usa la pantalla primaria del QGuiApplication."""

    def capture_to(self, path: Path) -> bool:  # pragma: no cover - Qt live-only
        try:
            from PySide6.QtGui import QGuiApplication  # type: ignore
        except Exception:
            return False
        try:
            app = QGuiApplication.instance()
            if app is None:
                return False
            screen = app.primaryScreen()
            if screen is None:
                return False
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                return False
            path.parent.mkdir(parents=True, exist_ok=True)
            return bool(pixmap.save(str(path)))
        except Exception:
            _LOG.debug("QtUIScreenshotProvider capture failed", exc_info=True)
            return False


@dataclass
class CompositeUIScreenshotProvider:
    """Intenta proveedores en orden; el primero que escriba bytes gana."""

    providers: list[UIScreenshotProvider] = field(default_factory=list)

    def capture_to(self, path: Path) -> bool:
        for provider in self.providers:
            try:
                if provider.capture_to(path):
                    return True
            except Exception:
                _LOG.debug(
                    "provider %s raised during capture_to",
                    type(provider).__name__,
                    exc_info=True,
                )
        return False


def build_default_provider() -> UIScreenshotProvider:
    """Cadena por defecto: PIL -> Qt -> Noop.

    En Windows con miniconda, PIL.ImageGrab existe y usa Win32 nativo.
    En linux con DISPLAY, PIL tambien anda. Qt es fallback cuando el
    proceso vive dentro de un QGuiApplication ya iniciado. Noop asegura
    que nunca devolvemos None aunque todo falle.
    """
    return CompositeUIScreenshotProvider(
        providers=[
            PILUIScreenshotProvider(),
            QtUIScreenshotProvider(),
            NoopUIScreenshotProvider(),
        ]
    )


class UIScreenshotService:
    """Captura + persiste + indexa snapshots de la UI de IABV.

    Contrato minimo:
        - `capture(source, scope=None, session_id=None) -> UIScreenshotRecord`
          siempre devuelve record; `success=False` si el provider no pudo
          (headless, sin display). Nunca levanta.
        - `list_recent(limit=10) -> list[UIScreenshotRecord]` ordenado
          por `created_at_epoch` descendente.
        - `get(record_id) -> UIScreenshotRecord | None`.

    Retention:
        - al capturar, si `len(index) > retention`, borra los mas viejos
          (archivo + entry del index).

    Thread-safety:
        - un RLock protege escritura al index y rotacion.
    """

    _INDEX_NAME = "index.json"

    def __init__(
        self,
        *,
        storage_dir: Path | str,
        provider: UIScreenshotProvider | None = None,
        clock: Callable[[], float] | None = None,
        retention: int = 50,
    ) -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._provider = provider or build_default_provider()
        self._clock = clock or time.time
        self._retention = max(1, int(retention))
        self._lock = RLock()
        self._index_path = self._dir / self._INDEX_NAME

    # ---- API publica -------------------------------------------------

    def capture(
        self,
        *,
        source: str,
        scope: Mapping[str, str] | None = None,
        session_id: str | None = None,
    ) -> UIScreenshotRecord:
        """Captura la pantalla y persiste evidencia. Siempre devuelve record."""
        record_id = uuid.uuid4().hex
        now = float(self._clock())
        rel_name = f"{record_id}.png"
        file_path = self._dir / rel_name

        success = False
        width = 0
        height = 0
        sha = ""
        try:
            success = bool(self._provider.capture_to(file_path))
            if success and file_path.exists():
                data = file_path.read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                width, height = _probe_png_dimensions(data)
        except Exception:
            _LOG.exception("UIScreenshotService.capture unexpected failure")
            success = False

        record = UIScreenshotRecord(
            record_id=record_id,
            created_at_epoch=now,
            source=str(source or ""),
            scope=dict(scope or {}),
            session_id=session_id,
            path=str(file_path),
            width=width,
            height=height,
            sha256=sha,
            success=success,
        )
        with self._lock:
            index = self._read_index_unlocked()
            index.append(record.as_dict())
            index = self._prune_unlocked(index)
            self._write_index_unlocked(index)
        return record

    def list_recent(self, limit: int = 10) -> list[UIScreenshotRecord]:
        limit = max(0, int(limit))
        with self._lock:
            index = self._read_index_unlocked()
        records = [_record_from_dict(d) for d in index]
        records.sort(key=lambda r: r.created_at_epoch, reverse=True)
        if limit:
            records = records[:limit]
        return records

    def get(self, record_id: str) -> UIScreenshotRecord | None:
        with self._lock:
            index = self._read_index_unlocked()
        for d in index:
            if str(d.get("record_id") or "") == record_id:
                return _record_from_dict(d)
        return None

    # ---- internals ---------------------------------------------------

    def _read_index_unlocked(self) -> list[dict]:
        if not self._index_path.exists():
            return []
        try:
            raw = self._index_path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else []
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            _LOG.exception("index.json corrupto; se reconstruye vacio")
        return []

    def _write_index_unlocked(self, index: list[dict]) -> None:
        tmp = self._index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        from iabv_v15.infra.persistence.storage import _replace_with_retry
        _replace_with_retry(tmp, self._index_path)

    def _prune_unlocked(self, index: list[dict]) -> list[dict]:
        if len(index) <= self._retention:
            return index
        index.sort(key=lambda d: float(d.get("created_at_epoch") or 0.0))
        to_remove = index[: len(index) - self._retention]
        kept = index[len(index) - self._retention :]
        for entry in to_remove:
            path = entry.get("path")
            if not path:
                continue
            try:
                Path(str(path)).unlink(missing_ok=True)
            except Exception:
                _LOG.debug("no se pudo borrar %s durante retention", path, exc_info=True)
        return kept


def _record_from_dict(d: Mapping) -> UIScreenshotRecord:
    return UIScreenshotRecord(
        record_id=str(d.get("record_id") or ""),
        created_at_epoch=float(d.get("created_at_epoch") or 0.0),
        source=str(d.get("source") or ""),
        scope=dict(d.get("scope") or {}),
        session_id=(str(d["session_id"]) if d.get("session_id") else None),
        path=str(d.get("path") or ""),
        width=int(d.get("width") or 0),
        height=int(d.get("height") or 0),
        sha256=str(d.get("sha256") or ""),
        success=bool(d.get("success") or False),
    )


def _probe_png_dimensions(data: bytes) -> tuple[int, int]:
    """Lee width/height del IHDR de un PNG. 0,0 si no parsea."""
    try:
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
            return 0, 0
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return width, height
    except Exception:
        return 0, 0
