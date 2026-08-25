"""Provider de screenshot basado en python-mss (fallback).

Se usa cuando ``QtScreenshotProvider`` no puede capturar (no hay
`QApplication` viva en el proceso, típico cuando el MCP server arranca
como proceso separado del UI host). ``mss`` captura a nivel de display
server sin depender del event loop Qt.

Cumple el Protocol ``UIScreenshotProvider``:

    class UIScreenshotProvider(Protocol):
        def capture(self, region: str) -> bytes: ...

Semántica de `region`:
    * ``"control_center"``, ``"evolution_center"``, ``"main"``, ``"window"``:
      mss no conoce la ventana IABV a nivel de proceso; por ahora cae a
      monitor primario. El consumidor puede extender con regiones custom
      registradas como ``"monitor_2"``, ``"monitor_3"``, etc.
    * ``"screen"``, ``"primary"``, ``"desktop"``, ``""``: monitor primario.
    * ``"monitor_N"``: monitor con índice N (1-based en mss).
    * ``"all"``: todos los monitores juntos (screen completo de mss[0]).

Nunca levanta: cualquier error se traduce a bytes vacíos.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MssScreenshotProvider:
    """Captura screenshots via python-mss."""

    _MONITOR_RE = re.compile(r"^monitor[_\-]?(\d+)$")

    def __init__(self, *, mss_factory: Any | None = None) -> None:
        """Args:
            mss_factory: callable opcional que devuelve un context manager
                equivalente a `mss.mss()`. Usado en tests para inyectar un
                fake sin depender de una pantalla real.
        """
        self._mss_factory = mss_factory

    # ------------------------------------------------------------------
    # Contrato UIScreenshotProvider

    def capture(self, region: str) -> bytes:
        try:
            return self._capture_impl(region)
        except Exception as exc:  # pragma: no cover - defensa
            logger.warning("MssScreenshotProvider.capture falló: %r", exc)
            return b""

    # ------------------------------------------------------------------
    # Implementación

    def _capture_impl(self, region: str) -> bytes:
        factory = self._mss_factory or self._default_factory
        # `_default_factory` es un bound method (siempre truthy), así que
        # el None check sobre `factory` era dead code. Validamos sobre el
        # context manager real que la factory devuelve.
        ctx = factory()
        if ctx is None:
            return b""
        with ctx as sct:
            monitor = self._resolve_monitor(sct, region)
            if monitor is None:
                return b""
            shot = sct.grab(monitor)

        return self._png_from_shot(shot)

    def _default_factory(self) -> Any:
        try:
            import mss  # type: ignore
        except Exception as exc:  # pragma: no cover - depende del entorno
            logger.debug("python-mss no disponible: %r", exc)
            return None
        return mss.mss()

    def _resolve_monitor(self, sct: Any, region: str) -> Any:
        region_key = (region or "").strip().lower()
        monitors = list(getattr(sct, "monitors", []) or [])
        if not monitors:
            return None
        if region_key in {"all"}:
            return monitors[0]
        match = self._MONITOR_RE.match(region_key)
        if match:
            idx = int(match.group(1))
            if 0 <= idx < len(monitors):
                return monitors[idx]
            return None
        # Default: monitor primario = índice 1 en mss (monitors[0] es "all").
        if len(monitors) > 1:
            return monitors[1]
        return monitors[0]

    def _png_from_shot(self, shot: Any) -> bytes:
        # mss expone `.rgb` (bytes) + .size. Convertimos a PNG via Pillow si
        # está disponible, o vía `mss.tools.to_png` como fallback.
        try:
            from mss.tools import to_png  # type: ignore

            size = getattr(shot, "size", None)
            # `mss.tools.to_png` espera BGRA (4 bytes/pixel). `.rgb` ya
            # viene convertido (3 bytes/pixel) y produciría un byte-count
            # mismatch. Por eso preferimos `.bgra` y sólo caemos a `.rgb`
            # si el backend no expone el buffer BGRA.
            raw = getattr(shot, "bgra", None) or getattr(shot, "rgb", None)
            if size is None or raw is None:
                return b""
            width, height = size
            # mss.tools.to_png firma: `output: Path | str | None`. Si
            # `output` es None devuelve los bytes PNG directo (mss v10+
            # usa `open(output, "wb")` internamente, así que pasar un
            # BytesIO levanta TypeError).
            data = to_png(raw, (int(width), int(height)))
            if data:
                return bytes(data)
        except Exception as exc:  # pragma: no cover - fallback
            logger.debug("mss.tools.to_png falló: %r", exc)

        try:
            from PIL import Image  # type: ignore

            size = getattr(shot, "size", None)
            if size is None:
                return b""
            # mss 10.x expone `.bgra` como `@property` que crea un `bytes`
            # nuevo en cada acceso (`bytes(self.raw)` sobre un ctypes
            # array). Por eso NO podemos usar `is` para decidir qué
            # buffer tomamos — siempre daría False sobre ScreenShot
            # reales. Resolvemos con una flag explícita.
            raw = getattr(shot, "bgra", None)
            is_bgra = raw is not None
            if raw is None:
                raw = getattr(shot, "rgb", None)
            if raw is None:
                return b""
            width, height = size
            if is_bgra:
                mode = "RGBA"
                image = Image.frombytes(
                    mode, (int(width), int(height)), bytes(raw), "raw", "BGRA"
                )
            else:
                mode = "RGB"
                image = Image.frombytes(
                    mode, (int(width), int(height)), bytes(raw), "raw", "RGB"
                )
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as exc:  # pragma: no cover - fallback
            logger.debug("Pillow fallback falló: %r", exc)

        return b""
