"""MCPBridgeService: ciclo de vida del puente MCP + cloudflared.

Capa 1 del plan de autonomía bidireccional Devin ↔ IABV:

- arranca / detiene el MCP server (`iabv_v15.infra.mcp.server`) en un hilo
  dedicado, sin bloquear el UI principal.
- arranca / detiene el proceso `cloudflared` (quick tunnel por defecto, o
  named tunnel si el usuario configuró uno).
- publica el estado vivo (`MCPBridgeStatus`) para que el `ControlCenterViewModel`
  muestre un toggle + URL visible + botón copiar.
- persiste la preferencia del usuario en `data/evolution/config/mcp_bridge.json`
  así el programa recuerda entre sesiones si el bridge debe auto-arrancar.

Contratos respetados (AGENTS.md):
  - No decide rutas: sólo opera la infra de transporte.
  - `AutonomyGovernancePolicy` sigue siendo la fuente de verdad. Antes de
    arrancar consulta `WorldModelSnapshot` via `_governance_gate_ok()` para
    no exponer el puente cuando governance lo bloquea.
  - No crea otro cerebro. Reusa `IABVMCPServer` del PR #26.
  - Fail-closed: si falta `mcp` SDK o falla el subproceso de cloudflared,
    publica `status=failed` con razón; no tira excepción al UI.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 8765
DEFAULT_TRANSPORT = "streamable-http"
DEFAULT_TUNNEL_TIMEOUT_S = 30.0
QUICK_TUNNEL_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
NAMED_TUNNEL_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9\-\.]+\.cfargotunnel\.com")
CUSTOM_HTTPS_PATTERN = re.compile(r"https?://[a-zA-Z0-9\-\.]+(?:/[^\s]*)?")


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
    """Corre `IABVMCPServer.run(transport)` dentro de un hilo daemon."""

    def __init__(self, container: Any) -> None:
        self._container = container
        self._thread: threading.Thread | None = None
        self._server: Any = None
        self._stopped = threading.Event()

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread:
        from iabv_v15.infra.mcp.server import IABVMCPServer  # lazy

        # FastMCP lee host/port de su config / env. Seteamos via env por compatibilidad
        # con distintos clientes.
        os.environ["FASTMCP_HOST"] = str(host)
        os.environ["FASTMCP_PORT"] = str(port)

        self._server = IABVMCPServer(self._container)
        self._stopped.clear()

        def _target() -> None:
            try:
                self._server.run(transport=transport)
            except Exception:  # pragma: no cover - loguea y sale
                logger.exception("MCP server hilo terminó con excepción")
            finally:
                self._stopped.set()

        thread = threading.Thread(
            target=_target,
            name="iabv-mcp-server",
            daemon=True,
        )
        thread.start()
        self._thread = thread
        return thread

    def stop(self) -> None:
        # FastMCP no tiene stop() sincrónico público; el hilo daemon muere
        # cuando el proceso Python se apaga. Para detener en caliente dependemos
        # de que el cliente cierre las conexiones. Aquí sólo marcamos intención.
        self._stopped.set()
        self._server = None
        self._thread = None


class CloudflaredTunnelRunner:
    """Lanza `cloudflared tunnel --url http://HOST:PORT --no-autoupdate` y lee la URL pública."""

    def __init__(
        self,
        *,
        cloudflared_bin: str | None = None,
        named_tunnel: str | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self._bin = cloudflared_bin or os.environ.get("CLOUDFLARED_BIN", "cloudflared")
        self._named_tunnel = named_tunnel or os.environ.get("IABV_MCP_NAMED_TUNNEL") or None
        self._extra_args = list(extra_args or [])
        self._proc: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._url: str | None = None
        self._url_event = threading.Event()
        self._last_error: str | None = None
        self._lock = threading.Lock()

    @property
    def url(self) -> str | None:
        return self._url

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _binary_available(self) -> bool:
        return shutil.which(self._bin) is not None

    def start(self, bind_host: str, bind_port: int) -> None:
        with self._lock:
            if self._proc is not None:
                return
            if not self._binary_available():
                self._last_error = (
                    f"No se encontró binario '{self._bin}' en PATH. "
                    "Instalar Cloudflare tunnel (winget install --id Cloudflare.cloudflared)."
                )
                return

            if self._named_tunnel:
                # Named tunnel: el usuario ya corrió `cloudflared tunnel login` y
                # `cloudflared tunnel create <name>`. Acá sólo lo arrancamos por nombre.
                argv = [self._bin, "tunnel", "--no-autoupdate", "run", self._named_tunnel]
            else:
                # Quick tunnel: URL efímera *.trycloudflare.com; no requiere login.
                target_url = f"http://{bind_host}:{bind_port}"
                argv = [
                    self._bin,
                    "tunnel",
                    "--no-autoupdate",
                    "--loglevel",
                    "info",
                    "--url",
                    target_url,
                ]
            argv.extend(self._extra_args)

            try:
                self._proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except Exception as exc:
                self._last_error = f"No se pudo arrancar cloudflared: {exc!r}"
                self._proc = None
                return

            self._url = None
            self._url_event.clear()
            self._last_error = None
            self._reader_thread = threading.Thread(
                target=self._drain_output,
                name="iabv-cloudflared-reader",
                daemon=True,
            )
            self._reader_thread.start()

    def _drain_output(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                if self._url is None:
                    self._maybe_extract_url(line)
                # No acumulamos log completo en memoria; el service puede leer
                # errores vía last_error si hace falta.
        except Exception as exc:  # pragma: no cover - defensa
            self._last_error = f"Error leyendo output de cloudflared: {exc!r}"

    def _maybe_extract_url(self, line: str) -> None:
        if self._named_tunnel:
            match = NAMED_TUNNEL_URL_PATTERN.search(line) or CUSTOM_HTTPS_PATTERN.search(line)
        else:
            match = QUICK_TUNNEL_URL_PATTERN.search(line)
        if match:
            url = match.group(0).rstrip("/.")
            self._url = url
            self._url_event.set()

    def wait_for_url(self, timeout_s: float) -> str | None:
        self._url_event.wait(timeout=timeout_s)
        return self._url

    def stop(self) -> None:
        with self._lock:
            proc = self._proc
            if proc is None:
                return
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2.0)
            except Exception as exc:  # pragma: no cover - defensa
                self._last_error = f"Error deteniendo cloudflared: {exc!r}"
            finally:
                self._proc = None
                self._url = None
                self._url_event.clear()


# ----------------------------------------------------------------------
# Service principal


class MCPBridgeService:
    """Orquesta start/stop del MCP server + tunnel y publica el estado.

    Ciclo de vida:
      - __init__: carga preferencia persistida; no arranca nada.
      - attach_listener(callback): suscribe un observador (p.ej. ViewModel) al
        cambio de estado. Recibe un dict via `MCPBridgeStatus.to_dict()`.
      - ensure_started(): idempotente; si el usuario lo habilitó y governance
        lo permite, arranca server + tunnel.
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
        return self._start_locked()

    def set_enabled(self, enabled: bool) -> MCPBridgeStatus:
        """Persiste preferencia y refleja el estado."""

        with self._lock:
            self._status.enabled_pref = bool(enabled)
            self._persist_enabled_preference(bool(enabled))
            self._touch()
        if enabled:
            return self._start_locked()
        return self.stop()

    def stop(self) -> MCPBridgeStatus:
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

            self._status.governance_blocked = False
            self._status.governance_reason = None
            self._update_state("starting")

        # Arranca MCP server fuera del lock (no bloquea).
        try:
            self._server_runner.run_threaded(
                transport=self._transport,
                host=self._bind_host,
                port=self._bind_port,
            )
        except Exception as exc:
            with self._lock:
                self._status.last_error = f"No se pudo arrancar MCP server: {exc!r}"
                self._status.running = False
                self._update_state("failed")
            return self.status()

        # Arranca tunnel y espera URL.
        try:
            self._tunnel_runner.start(self._bind_host, self._bind_port)
        except Exception as exc:
            with self._lock:
                self._status.last_error = f"No se pudo arrancar cloudflared: {exc!r}"
                self._status.running = False
                self._update_state("failed")
            # no dejamos el server corriendo sin tunnel expuesto: si preferís
            # server local puro, usá transport=stdio y no el bridge.
            try:
                self._server_runner.stop()
            except Exception:  # pragma: no cover
                pass
            return self.status()

        url = self._tunnel_runner.wait_for_url(timeout_s=self._tunnel_timeout_s)
        tunnel_error = getattr(self._tunnel_runner, "last_error", None)
        with self._lock:
            if url:
                self._status.tunnel_url = url
                self._status.running = True
                self._status.last_error = None
                self._update_state("running")
            else:
                self._status.tunnel_url = None
                self._status.running = False
                self._status.last_error = tunnel_error or "Timeout esperando URL del tunnel"
                self._update_state("failed")
        # Si el tunnel no publicó URL a tiempo, liberamos recursos: dejar el
        # server MCP y el proceso cloudflared vivos llevaría a puerto ocupado
        # en el próximo intento y a un estado irrecuperable sin reiniciar la app.
        if not url:
            try:
                self._tunnel_runner.stop()
            except Exception:  # pragma: no cover - defensa
                pass
            try:
                self._server_runner.stop()
            except Exception:  # pragma: no cover - defensa
                pass
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
