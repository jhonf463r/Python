"""MCP bridge status/preferences with fail-closed, non-starting UI runners.

The UI-owned service cannot supply a client-managed stdio pipe. Network
transports remain disabled until transport authentication and independent
operation-level authorization are implemented and verified. This service
therefore preserves preference/status reporting but never launches a server
or tunnel. A local MCP client may start the server explicitly through stdio.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 8765
DEFAULT_TRANSPORT = "stdio"
DEFAULT_TUNNEL_TIMEOUT_S = 30.0


# ----------------------------------------------------------------------
# Modelos públicos del service


@dataclass
class MCPBridgeStatus:
    """Foto instantánea del estado del bridge (lo que consume el ViewModel)."""

    enabled_pref: bool = False           # preferencia guardada del usuario
    running: bool = False                # server + tunnel vivos
    state: str = "stopped"               # stopped | starting | running | failed | stopping
    tunnel_url: str | None = None
    transport: str = DEFAULT_TRANSPORT
    bind_host: str = DEFAULT_BIND_HOST
    bind_port: int = DEFAULT_BIND_PORT
    last_error: str | None = None
    last_updated: float = field(default_factory=time.time)
    governance_blocked: bool = False
    governance_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled_pref": self.enabled_pref,
            "running": self.running,
            "state": self.state,
            "tunnel_url": self.tunnel_url,
            "transport": self.transport,
            "bind_host": self.bind_host,
            "bind_port": self.bind_port,
            "last_error": self.last_error,
            "last_updated": self.last_updated,
            "governance_blocked": self.governance_blocked,
            "governance_reason": self.governance_reason,
        }


# ----------------------------------------------------------------------
# Protocolos delgados para los colaboradores (inyectables y mockeables)


class _ServerRunner:
    """Protocolo mínimo que el service necesita de un MCP server runner."""

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread: ...
    def stop(self) -> None: ...


class _TunnelRunner:
    """Protocolo mínimo para lanzar/detener cloudflared."""

    def start(self, bind_host: str, bind_port: int) -> None: ...
    def stop(self) -> None: ...
    def wait_for_url(self, timeout_s: float) -> str | None: ...
    @property
    def url(self) -> str | None: ...
    @property
    def last_error(self) -> str | None: ...


# ----------------------------------------------------------------------
# Default implementations (reales, usadas en producción)


class FastMCPServerRunner:
    """Compatibility shim that refuses UI-owned server startup."""

    def __init__(self, container: Any) -> None:
        self._container = container

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread:
        raise RuntimeError(
            "MCPBridgeService cannot own an MCP process; use an explicitly "
            "client-managed local stdio connection"
        )

    def stop(self) -> None:
        return None


class CloudflaredTunnelRunner:
    """Compatibility shim that refuses to start a public tunnel."""

    def __init__(
        self,
        *,
        cloudflared_bin: str | None = None,
        named_tunnel: str | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self._last_error = "Public tunnels are disabled pending transport authorization."

    @property
    def url(self) -> str | None:
        return None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def start(self, bind_host: str, bind_port: int) -> None:
        raise RuntimeError(self._last_error)

    def wait_for_url(self, timeout_s: float) -> str | None:
        return None

    def stop(self) -> None:
        return None


# ----------------------------------------------------------------------
# Service principal


class MCPBridgeService:
    """Expose bridge preference/status while refusing unsafe auto-start.

    Ciclo de vida:
      - __init__: carga preferencia persistida; no arranca nada.
      - attach_listener(callback): suscribe un observador (p.ej. ViewModel) al
        cambio de estado. Recibe un dict via `MCPBridgeStatus.to_dict()`.
      - ensure_started(): if enabled, fails closed before invoking a runner.
      - set_enabled(enabled: bool): cambia preferencia persistida y refleja
        el estado (arranca o detiene según valor).
      - stop(): detiene en caliente sin tocar preferencia.
      - status(): devuelve la foto actual (safe para UI / MCP tool).
    """

    def __init__(
        self,
        *,
        container: Any,
        workspace_root: Path | str | None = None,
        server_runner: _ServerRunner | None = None,
        tunnel_runner: _TunnelRunner | None = None,
        transport: str = DEFAULT_TRANSPORT,
        bind_host: str = DEFAULT_BIND_HOST,
        bind_port: int = DEFAULT_BIND_PORT,
        tunnel_timeout_s: float = DEFAULT_TUNNEL_TIMEOUT_S,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._container = container
        self._workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self._server_runner: _ServerRunner = server_runner or FastMCPServerRunner(container)
        self._tunnel_runner: _TunnelRunner = tunnel_runner or CloudflaredTunnelRunner()
        self._transport = transport if transport in {"stdio", "sse", "streamable-http"} else DEFAULT_TRANSPORT
        self._bind_host = bind_host
        self._bind_port = int(bind_port)
        self._tunnel_timeout_s = float(tunnel_timeout_s)
        self._clock = clock or time.time

        self._lock = threading.RLock()
        # `_lock` se libera durante las operaciones de I/O largas
        # (`run_threaded`, `tunnel.start`, `wait_for_url`). `_operation_lock`
        # serializa el ciclo completo de start/stop para que una llamada
        # concurrente a `set_enabled(False)` no pueda terminar antes que un
        # start en vuelo y perder la carrera final (bridge quedaba `running`
        # con `enabled_pref=False`).
        self._operation_lock = threading.Lock()
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

        self._status = MCPBridgeStatus(
            transport=self._transport,
            bind_host=self._bind_host,
            bind_port=self._bind_port,
            last_updated=self._clock(),
        )
        self._status.enabled_pref = self._load_enabled_preference()

    # ------------------------------------------------------------------
    # API pública

    def attach_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
                # Enviar estado inicial para que la UI pinte de una.
                callback(self._status.to_dict())

    def status(self) -> MCPBridgeStatus:
        with self._lock:
            return MCPBridgeStatus(**self._status.to_dict())

    def status_dict(self) -> dict[str, Any]:
        return self.status().to_dict()

    def ensure_started(self) -> MCPBridgeStatus:
        """Idempotente: si la preferencia está en True y no hay bloqueo, arranca."""

        with self._lock:
            if not self._status.enabled_pref:
                return self.status()
            if self._status.running and self._status.state == "running":
                return self.status()
        with self._operation_lock:
            # Re-chequeo dentro del operation_lock: otro hilo pudo haber
            # completado el start o un set_enabled(False) en el intervalo.
            with self._lock:
                if not self._status.enabled_pref:
                    return self.status()
                if self._status.running and self._status.state == "running":
                    return self.status()
            return self._start_locked()

    def set_enabled(self, enabled: bool) -> MCPBridgeStatus:
        """Persiste preferencia y refleja el estado."""

        with self._lock:
            self._status.enabled_pref = bool(enabled)
            self._persist_enabled_preference(bool(enabled))
            self._touch()
        with self._operation_lock:
            # La preferencia ya está persistida; si entre el release de
            # `_lock` y la adquisición de `_operation_lock` hubo otro toggle,
            # el estado actual de `enabled_pref` es la intención ganadora.
            with self._lock:
                pref_now = self._status.enabled_pref
            if pref_now:
                return self._start_locked()
            return self._stop_locked()

    def stop(self) -> MCPBridgeStatus:
        with self._operation_lock:
            return self._stop_locked()

    def _stop_locked(self) -> MCPBridgeStatus:
        """Detiene tunnel + server; debe llamarse con `_operation_lock` tomado."""

        with self._lock:
            if not self._status.running and self._status.state == "stopped":
                return self.status()
            self._update_state("stopping")
        try:
            self._tunnel_runner.stop()
        except Exception as exc:  # pragma: no cover - defensa
            logger.exception("tunnel.stop() falló: %s", exc)
        try:
            self._server_runner.stop()
        except Exception as exc:  # pragma: no cover - defensa
            logger.exception("server.stop() falló: %s", exc)
        with self._lock:
            self._status.running = False
            self._status.tunnel_url = None
            self._update_state("stopped")
        return self.status()

    def shutdown(self) -> None:
        """Llamado desde AppBootstrap.shutdown(). No toca la preferencia."""

        self.stop()

    # ------------------------------------------------------------------
    # Internals

    def _start_locked(self) -> MCPBridgeStatus:
        block = self._governance_gate_block()
        with self._lock:
            if block is not None:
                self._status.running = False
                self._status.tunnel_url = None
                self._status.governance_blocked = True
                self._status.governance_reason = block
                self._status.last_error = None
                self._update_state("failed")
                return self.status()

            # This UI-owned service cannot provide a client-managed stdio
            # channel, and unauthenticated network transports are not
            # authorized. Refuse before starting either runner.
            self._status.running = False
            self._status.tunnel_url = None
            self._status.last_error = (
                "MCPBridgeService no puede iniciar un canal stdio propiedad "
                "del cliente; sse/streamable-http permanecen deshabilitados "
                "hasta verificar autenticación de transporte y autorización "
                "independiente por operación"
            )
            self._update_state("failed")
            return self.status()

    def _governance_gate_block(self) -> str | None:
        """Consulta WorldModelSnapshot antes de exponer el puente.

        Devuelve motivo del bloqueo o None si la ruta es viable.
        """

        wm_service = getattr(self._container, "world_model_service", None)
        if wm_service is None:
            # Sin world_model no bloqueamos porque el bridge es local (no
            # ejecuta rutas externas por sí mismo; cada tool tiene su propio
            # gate). Pero sí lo registramos en log.
            logger.warning("world_model_service no disponible; bridge arranca sin verificación")
            return None
        try:
            snapshot = wm_service.current_model()
        except Exception as exc:
            logger.warning("No se pudo leer WorldModelSnapshot: %s", exc)
            return None
        if snapshot is None:
            return None

        for record in getattr(snapshot, "block_records", []) or []:
            if getattr(record, "status", "active") != "active":
                continue
            scope = str(getattr(record, "assistant_kind", "") or "").lower()
            # Solo bloqueamos si el scope apunta explícitamente al bridge o es
            # un bloqueo global ("*"). assistant_kind="" (default del modelo)
            # se usa para condiciones operativas generales (network_slow, ram_pressure,
            # focus_unresolved, etc.) que NO deben bloquear el bridge MCP.
            if scope in ("*", "mcp_bridge"):
                title = getattr(record, "title", "") or getattr(record, "block_type", "operational_block")
                return f"Bloqueo operativo activo: {title}"
        return None

    def _update_state(self, new_state: str) -> None:
        # Asume lock tomado.
        self._status.state = new_state
        self._touch()
        snapshot = self._status.to_dict()
        for callback in list(self._listeners):
            try:
                callback(dict(snapshot))
            except Exception:  # pragma: no cover - defensa
                logger.exception("listener de MCPBridgeService levantó excepción")

    def _touch(self) -> None:
        self._status.last_updated = self._clock()

    # ------------------------------------------------------------------
    # Preferencia persistida

    def _config_path(self) -> Path:
        return self._workspace_root / "data" / "evolution" / "config" / "mcp_bridge.json"

    def _load_enabled_preference(self) -> bool:
        path = self._config_path()
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return bool(data.get("enabled_pref", False))
        except Exception as exc:
            logger.warning("No se pudo leer %s: %s", path, exc)
            return False

    def _persist_enabled_preference(self, enabled: bool) -> None:
        path = self._config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"enabled_pref": bool(enabled)}, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("No se pudo persistir preferencia en %s: %s", path, exc)


# ----------------------------------------------------------------------
# Factory para bootstrap


def build_mcp_bridge_service(
    container: Any,
    *,
    workspace_root: Path | str | None = None,
) -> MCPBridgeService:
    """Construye el service con defaults razonables para AppBootstrap."""

    transport = os.environ.get("IABV_MCP_TRANSPORT", DEFAULT_TRANSPORT)
    bind_host = os.environ.get("IABV_MCP_BIND_HOST", DEFAULT_BIND_HOST)
    try:
        bind_port = int(os.environ.get("IABV_MCP_BIND_PORT", str(DEFAULT_BIND_PORT)))
    except ValueError:
        bind_port = DEFAULT_BIND_PORT
    return MCPBridgeService(
        container=container,
        workspace_root=workspace_root,
        transport=transport,
        bind_host=bind_host,
        bind_port=bind_port,
    )
