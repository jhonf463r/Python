"""Verifica que `ControlCenterViewModel.toggleMcpBridge` no bloquea el hilo UI.

Regresión del finding de Devin Review en PR #32: el toggle llamaba
`service.set_enabled(True)` sincrónicamente, que a su vez bloquea hasta
`DEFAULT_TUNNEL_TIMEOUT_S` segundos mientras `cloudflared` publica la URL.
La corrección dispara `set_enabled` en un thread daemon; el listener del
service se encarga de reemitir las transiciones al hilo UI.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest


class _SlowService:
    """Simula MCPBridgeService con un `set_enabled` que tarda varios segundos.

    Reproduce el escenario real donde `wait_for_url(timeout_s=30)` demora.
    """

    def __init__(self, delay: float = 3.0) -> None:
        self._delay = delay
        self.calls: list[bool] = []
        self.done = threading.Event()

    def attach_listener(self, _listener: Any) -> None:
        return None

    def set_enabled(self, enabled: bool) -> None:
        time.sleep(self._delay)
        self.calls.append(bool(enabled))
        self.done.set()


def _make_viewmodel(service: _SlowService, tmp_path: Path):
    """Instancia `ControlCenterViewModel` mínimo con un fake service.

    Usa `AppBootstrap` para levantar las deps como en prod, pero reemplaza
    `mcp_bridge_service` con el fake antes de construir el ViewModel.
    """

    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path))
    bootstrap.mcp_bridge_service = service  # evita autostart del real
    bootstrap._build_ui_objects()
    return bootstrap, bootstrap.control_center_viewmodel


def test_toggle_mcp_bridge_does_not_block_ui_thread(tmp_path: Path) -> None:
    service = _SlowService(delay=3.0)
    bootstrap, vm = _make_viewmodel(service, tmp_path)
    try:
        start = time.monotonic()
        vm.toggleMcpBridge(True)  # debe retornar inmediato
        elapsed = time.monotonic() - start
        # Si estuviera bloqueando el hilo, tardaría >= delay (3 s).
        # Un dispatch a daemon thread devuelve en < 0.5 s en cualquier host razonable.
        assert elapsed < 1.0, f"toggleMcpBridge bloqueó el hilo UI {elapsed:.2f}s"
        # El trabajo sí debe completarse eventualmente en el thread de fondo.
        assert service.done.wait(timeout=6.0), "el thread daemon no ejecutó set_enabled"
        assert service.calls == [True]
    finally:
        stop = getattr(bootstrap, 'stop', None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass


def test_toggle_mcp_bridge_is_safe_when_service_is_none(tmp_path: Path) -> None:
    """Si por algún motivo no se wirea el service, el toggle es noop."""

    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path))
    # Forzamos el service a None antes del build_ui, simulando el camino
    # try/except del bootstrap cuando falla la instanciación.
    bootstrap.mcp_bridge_service = None
    bootstrap._build_ui_objects()
    try:
        vm = bootstrap.control_center_viewmodel
        # Cubrimos ambos paths (None en __init__ y re-asignación posterior).
        vm.mcp_bridge_service = None
        vm.toggleMcpBridge(True)  # no debe crashear
        vm.toggleMcpBridge(False)
    finally:
        stop = getattr(bootstrap, 'stop', None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
