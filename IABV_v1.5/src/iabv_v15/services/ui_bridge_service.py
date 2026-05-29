"""UIBridgeService: puente IPC entre el MCP server y la UI PySide6.

Problema: el MCP server y la UI PySide6 son procesos separados (o hilos
aislados) sin canal de comunicacion directo. Esto impide que agentes
externos (via MCP) puedan:
  - Enviar texto al chat de la UI
  - Leer las respuestas que aparecen en el chat
  - Capturar screenshots de la ventana de la UI
  - Navegar por las paginas/tabs de la UI

Solucion: un servicio IPC basado en localhost TCP con protocolo JSON-line.
La UI arranca un servidor TCP en un puerto local (por defecto 18921).
El MCP server (o cualquier cliente interno) se conecta y envia comandos.

Protocolo:
  - Cada mensaje es una linea JSON terminada en newline.
  - Request:  {"id": "uuid", "method": "send_message", "params": {...}}
  - Response: {"id": "uuid", "result": {...}} o {"id": "uuid", "error": "..."}

Metodos soportados:
  - send_message(text) -> envia texto al chat de la UI
  - read_messages(limit) -> lee los ultimos N mensajes del chat
  - get_ui_state() -> estado actual de la UI (pagina activa, tabs, etc.)
  - navigate(page) -> navega a una pagina/tab de la UI
  - capture_screenshot() -> captura screenshot de la ventana UI

Contratos respetados (AGENTS.md):
  - No decide rutas: solo transporta comandos entre MCP y UI.
  - No crea otro cerebro; es un adaptador IPC delgado.
  - Fail-closed: si la UI no esta corriendo o no acepta conexion,
    retorna error explicito sin crashear.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 18921
RECV_TIMEOUT_S = 5.0
CONNECT_TIMEOUT_S = 2.0


@dataclass
class UIBridgeStatus:
    """Estado observable del puente UI."""
    running: bool = False
    host: str = DEFAULT_BRIDGE_HOST
    port: int = DEFAULT_BRIDGE_PORT
    connected_clients: int = 0
    last_error: str = ""
    ui_available: bool = False
    # P0.71: truth contract fields
    ui_process_pid: int = 0
    bridge_owner_pid: int = 0
    control_vm_bound: bool = False
    chat_ready: bool = False


class UIBridgeServer:
    """Servidor TCP que corre en el proceso de la UI.

    Escucha conexiones del MCP server y despacha comandos a la UI
    via callbacks registrados.
    """

    def __init__(
        self,
        host: str = DEFAULT_BRIDGE_HOST,
        port: int = DEFAULT_BRIDGE_PORT,
    ) -> None:
        self._host = host
        self._port = port
        self._server_socket: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()
        self._status = UIBridgeStatus(host=host, port=port)
        self._listeners: list[Callable[[UIBridgeStatus], None]] = []
        # --- Readiness handshake (Task 2 / Task 7) ---
        # Messages arriving before the shell is interactive are buffered
        # and flushed once ``mark_shell_ready()`` is called.
        self._shell_ready = False
        self._pending_messages: list[dict[str, Any]] = []
        self._ready_lock = threading.Lock()
        self._ready_source: str = ''
        self._ready_at: float = 0.0
        self._deferred_setup_active = False

    @property
    def status(self) -> UIBridgeStatus:
        return self._status

    def register_handler(self, method: str, handler: Callable[..., Any]) -> None:
        """Registra un handler para un metodo IPC."""
        self._handlers[method] = handler

    def attach_listener(self, listener: Callable[[UIBridgeStatus], None]) -> None:
        self._listeners.append(listener)

    @property
    def shell_ready(self) -> bool:
        """Whether the main shell is interactive and ready for traffic."""
        return self._shell_ready

    def mark_shell_ready(self, source: str = 'unknown') -> None:
        """Signal that the main shell is interactive.

        Called by bootstrap when ``shell_loader_ready`` (honest) or the
        fallback fires.  Flushes any messages that arrived while the
        splash was still visible.
        """
        with self._ready_lock:
            if self._shell_ready:
                return
            self._shell_ready = True
            self._ready_source = source
            self._ready_at = time.time()
            pending = list(self._pending_messages)
            self._pending_messages.clear()
        logger.info(
            'UIBridgeServer: shell_ready (source=%s, flushing %d pending)',
            source, len(pending),
        )
        # Flush pending send_message calls now that the shell can process them.
        handler = self._handlers.get('send_message')
        if handler is not None:
            for msg in pending:
                try:
                    handler(**msg)
                except Exception:
                    logger.debug('UIBridgeServer: flush pending failed', exc_info=True)
        self._status.ui_available = True
        self._notify_listeners()

    def enqueue_pending_message(self, params: dict[str, Any]) -> dict[str, Any]:
        """Buffer a send_message call until the shell is ready."""
        with self._ready_lock:
            if self._shell_ready:
                return {}  # empty means "not buffered, process normally"
            self._pending_messages.append(dict(params))
            return {
                'status': 'pending_shell_ready',
                'queue_position': len(self._pending_messages),
                'detail': 'Message buffered until shell is interactive.',
            }

    def readiness_snapshot(self) -> dict[str, Any]:
        """Observable readiness state for diagnostics."""
        with self._ready_lock:
            return {
                'shell_ready': self._shell_ready,
                'ready_source': self._ready_source,
                'ready_at': self._ready_at,
                'pending_count': len(self._pending_messages),
                'deferred_setup_active': self._deferred_setup_active,
            }

    def set_deferred_setup_active(self, active: bool) -> None:
        """Track whether deferred post-window setup is running."""
        self._deferred_setup_active = active

    def mark_control_vm_bound(self, bound: bool = True) -> None:
        """P0.71: signal that ControlCenterViewModel is wired to the bridge."""
        self._status.control_vm_bound = bound
        self._status.chat_ready = bound and self._shell_ready
        self._notify_listeners()

    @staticmethod
    def _detect_port_owner() -> int | None:
        """Try to detect which PID owns DEFAULT_BRIDGE_PORT (best-effort)."""
        try:
            import subprocess
            import sys
            if sys.platform == 'win32':
                out = subprocess.check_output(
                    ['netstat', '-ano'],
                    timeout=3,
                    text=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
                for line in out.splitlines():
                    if f':{DEFAULT_BRIDGE_PORT}' in line and 'LISTENING' in line:
                        parts = line.split()
                        return int(parts[-1])
            else:
                out = subprocess.check_output(
                    ['ss', '-tlnp', f'sport = :{DEFAULT_BRIDGE_PORT}'],
                    timeout=3,
                    text=True,
                )
                for line in out.splitlines():
                    if 'pid=' in line:
                        import re
                        m = re.search(r'pid=(\d+)', line)
                        if m:
                            return int(m.group(1))
        except Exception:
            pass
        return None

    @staticmethod
    def _emit_trace(event: str, data: dict[str, Any] | None = None) -> None:
        """Emit a structured trace event to runtime_audit via logger."""
        payload = {'event': event, **(data or {})}
        logger.info('ui_bridge_trace: %s', json.dumps(payload, default=str))

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener(self._status)
            except Exception:
                pass

    def start(self) -> None:
        """Inicia el servidor TCP en un hilo daemon.

        P0.71: checks for port conflict before binding.  If another process
        already owns the port, logs a ``ui_bridge_port_conflict`` event and
        refuses to start (prevents two UIBridgeServers on the same port).
        """
        if self._running:
            return
        # P0.71: detect port conflict before binding
        conflict_pid = self._detect_port_owner()
        if conflict_pid and conflict_pid != os.getpid():
            msg = (
                f'UIBridgeServer: port {self._port} already owned by PID '
                f'{conflict_pid} (this PID {os.getpid()}). '
                f'Refusing to start — ui_bridge_port_conflict.'
            )
            self._status.last_error = msg
            self._status.running = False
            logger.warning(msg)
            self._emit_trace('ui_bridge_port_conflict', {
                'port': self._port,
                'owner_pid': conflict_pid,
                'this_pid': os.getpid(),
            })
            self._notify_listeners()
            return
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(4)
            self._server_socket.settimeout(1.0)
            self._running = True
            self._status.running = True
            self._status.ui_available = True
            self._status.bridge_owner_pid = os.getpid()
            self._status.ui_process_pid = os.getpid()
            self._status.last_error = ""
            self._thread = threading.Thread(
                target=self._accept_loop,
                name="ui-bridge-server",
                daemon=True,
            )
            self._thread.start()
            logger.info("UIBridgeServer started on %s:%d", self._host, self._port)
            self._emit_trace('ui_bridge_owner_verified', {
                'port': self._port,
                'owner_pid': os.getpid(),
            })
            self._notify_listeners()
        except OSError as exc:
            # Port already in use — likely duplicate UI instance
            self._status.last_error = str(exc)
            self._status.running = False
            logger.warning("UIBridgeServer failed to start: %s", exc)
            self._emit_trace('ui_bridge_port_conflict', {
                'port': self._port,
                'error': str(exc),
                'this_pid': os.getpid(),
            })
            self._notify_listeners()
        except Exception as exc:
            self._status.last_error = str(exc)
            self._status.running = False
            logger.warning("UIBridgeServer failed to start: %s", exc)
            self._notify_listeners()

    def stop(self) -> None:
        """Detiene el servidor."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        with self._lock:
            for client in self._clients:
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
        self._status.running = False
        self._status.connected_clients = 0
        self._notify_listeners()
        logger.info("UIBridgeServer stopped")

    def _accept_loop(self) -> None:
        while self._running and self._server_socket:
            try:
                client, addr = self._server_socket.accept()
                client.settimeout(RECV_TIMEOUT_S)
                with self._lock:
                    self._clients.append(client)
                    self._status.connected_clients = len(self._clients)
                self._notify_listeners()
                threading.Thread(
                    target=self._handle_client,
                    args=(client, addr),
                    name=f"ui-bridge-client-{addr[1]}",
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except Exception:
                if self._running:
                    logger.debug("UIBridgeServer accept error", exc_info=True)

    def _handle_client(self, client: socket.socket, addr: tuple[str, int]) -> None:
        buffer = ""
        try:
            while self._running:
                try:
                    data = client.recv(8192)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        response = self._dispatch(line)
                        client.sendall((json.dumps(response) + "\n").encode("utf-8"))
                except socket.timeout:
                    continue
                except Exception:
                    break
        finally:
            with self._lock:
                if client in self._clients:
                    self._clients.remove(client)
                self._status.connected_clients = len(self._clients)
            try:
                client.close()
            except Exception:
                pass
            self._notify_listeners()

    def _dispatch(self, line: str) -> dict[str, Any]:
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            return {"id": None, "error": f"invalid_json: {exc}"}

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        handler = self._handlers.get(method)
        if handler is None:
            return {
                "id": req_id,
                "error": f"unknown_method: {method}",
                "available_methods": sorted(self._handlers.keys()),
            }

        # Task 9: if shell is not ready, buffer send_message calls
        with self._ready_lock:
            shell_ready = self._shell_ready
        if not shell_ready and method == 'send_message':
            result = self.enqueue_pending_message(params if isinstance(params, dict) else {})
            if result:
                return {"id": req_id, "result": result}
            return {"id": req_id, "result": {"status": "queued_pending_shell_ready"}}

        try:
            result = handler(**params) if isinstance(params, dict) else handler(params)
            return {"id": req_id, "result": result}
        except Exception as exc:
            return {"id": req_id, "error": str(exc)[:500]}


class UIBridgeClient:
    """Cliente IPC que conecta al UIBridgeServer desde el MCP server.

    Envia comandos y recibe respuestas de forma sincrona.
    Thread-safe: cada llamada abre y cierra su propia conexion
    para evitar contention en el MCP multi-threaded.
    """

    def __init__(
        self,
        host: str = DEFAULT_BRIDGE_HOST,
        port: int = DEFAULT_BRIDGE_PORT,
    ) -> None:
        self._host = host
        self._port = port

    def is_ui_available(self) -> bool:
        """Verifica si la UI esta escuchando."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CONNECT_TIMEOUT_S)
            sock.connect((self._host, self._port))
            sock.close()
            return True
        except Exception:
            return False

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        """Envia un comando al UIBridgeServer y retorna la respuesta.

        Raises ConnectionError si la UI no esta disponible.
        """
        req_id = uuid.uuid4().hex[:12]
        request = {"id": req_id, "method": method, "params": params}
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(RECV_TIMEOUT_S)
            sock.connect((self._host, self._port))
        except Exception as exc:
            return {
                "id": req_id,
                "error": "ui_not_available",
                "detail": (
                    f"No se pudo conectar al UIBridgeServer en "
                    f"{self._host}:{self._port}. "
                    f"La UI PySide6 debe estar corriendo con el bridge activo. "
                    f"Error: {exc}"
                ),
            }
        try:
            payload = json.dumps(request) + "\n"
            sock.sendall(payload.encode("utf-8"))
            buffer = ""
            while "\n" not in buffer:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
            sock.close()
            if buffer.strip():
                return json.loads(buffer.strip())
            return {"id": req_id, "error": "empty_response"}
        except Exception as exc:
            try:
                sock.close()
            except Exception:
                pass
            return {"id": req_id, "error": f"communication_error: {exc}"}


def build_ui_bridge_server(
    control_center_viewmodel: Any = None,
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
) -> UIBridgeServer:
    """Construye un UIBridgeServer con handlers para la UI.

    Si ``control_center_viewmodel`` esta disponible, registra handlers
    que interactuan con el chat y la navegacion de la UI.
    """
    server = UIBridgeServer(host=host, port=port)

    # P0.71: mark whether a real ControlCenterViewModel is wired
    if control_center_viewmodel is not None:
        server.mark_control_vm_bound(True)

    # --- Chat messages buffer (in-memory, shared with UI handlers) ---
    _chat_buffer: list[dict[str, Any]] = []
    _chat_lock = threading.Lock()

    def _on_send_message(text: str = "") -> dict[str, Any]:
        """Envia un mensaje al chat de la UI.

        P0.71: fail-closed when no ControlCenterViewModel is bound.
        Returns status=unavailable with reason instead of silently buffering.
        """
        if not text:
            return {"status": "error", "detail": "text is required"}
        # --- Readiness gate: buffer if shell not interactive yet ---
        pending_result = server.enqueue_pending_message({'text': text})
        if pending_result:
            return pending_result
        if control_center_viewmodel is not None:
            try:
                result = control_center_viewmodel.send_message_from_bridge(text)
                if isinstance(result, dict):
                    return result
                return {"status": "queued", "text": text}
            except Exception as exc:
                return {"status": "error", "detail": str(exc)[:200]}
        # P0.71: fail-closed — no VM means message cannot reach chat
        return {
            "status": "unavailable",
            "reason": "control_center_vm_not_bound",
            "next_system_action": "wait_for_ui_bootstrap_to_wire_vm",
            "text": text,
        }

    def _on_read_messages(limit: int = 20) -> dict[str, Any]:
        """Lee los ultimos N mensajes del buffer del chat."""
        if control_center_viewmodel is not None:
            try:
                live_messages = list(control_center_viewmodel.get_chat_messages())
                if live_messages:
                    serialized = [
                        {
                            "role": str(message.get("role") or "unknown"),
                            "speaker": str(message.get("speaker") or ""),
                            "text": str(message.get("text") or ""),
                            "meta": str(message.get("meta") or ""),
                            "status": str(message.get("status") or "complete"),
                            "timestamp": str(message.get("timestamp") or ""),
                        }
                        for message in live_messages[-limit:]
                    ]
                    return {
                        "messages": serialized,
                        "total": len(live_messages),
                        "source": "viewmodel",
                    }
            except Exception:
                logger.debug("ui-bridge: fallback to buffer for read_messages", exc_info=True)
        with _chat_lock:
            messages = list(_chat_buffer[-limit:])
        return {"messages": messages, "total": len(_chat_buffer), "source": "buffer"}

    def _on_get_ui_state() -> dict[str, Any]:
        """Retorna el estado actual de la UI.

        P0.71: includes truth contract fields: ui_process_pid,
        bridge_owner_pid, control_vm_bound, navigation_controller_bound,
        current_page_verified, chat_ready.
        """
        state: dict[str, Any] = {
            "ui_running": True,
            "ui_process_pid": server.status.ui_process_pid or os.getpid(),
            "bridge_owner_pid": server.status.bridge_owner_pid or os.getpid(),
            "control_vm_bound": control_center_viewmodel is not None,
            "navigation_controller_bound": False,
            "current_page_verified": False,
            "chat_ready": server.status.chat_ready,
        }
        if control_center_viewmodel is not None:
            try:
                page: str = "unknown"
                nav = getattr(control_center_viewmodel, "navigation_controller", None)
                nav_bound = nav is not None
                state["navigation_controller_bound"] = nav_bound
                if nav is not None:
                    getter = getattr(nav, "get_current_route", None)
                    if callable(getter):
                        try:
                            page = str(getter() or "unknown")
                            state["current_page_verified"] = page != "unknown"
                        except Exception:
                            page = "unknown"
                    else:
                        page = str(getattr(nav, "_current_route", page) or page)
                if page == "unknown":
                    page = str(
                        getattr(control_center_viewmodel, "_current_page", "unknown")
                        or "unknown"
                    )
                state["current_page"] = page
                state["chat_session_id"] = getattr(
                    control_center_viewmodel, "_chat_session_id", ""
                )
                state["live_status"] = getattr(
                    control_center_viewmodel, "_live_status", "idle"
                )
            except Exception:
                pass
        return state

    def _on_navigate(page: str = "") -> dict[str, Any]:
        """Navega a una pagina/tab de la UI.

        P0.71: verifies the route actually changed after navigation.
        Returns status=failed if the route didn't change.
        """
        if not page:
            return {"status": "error", "detail": "page is required"}
        if control_center_viewmodel is not None:
            try:
                nav = getattr(control_center_viewmodel, "navigation_controller", None)
                if nav and hasattr(nav, "navigate_to"):
                    # P0.71: read route before and after to verify
                    getter = getattr(nav, "get_current_route", None)
                    before = ""
                    if callable(getter):
                        try:
                            before = str(getter() or "")
                        except Exception:
                            pass
                    nav.navigate_to(page)
                    # Short delay for navigation to settle
                    time.sleep(0.05)
                    after = ""
                    if callable(getter):
                        try:
                            after = str(getter() or "")
                        except Exception:
                            pass
                    if after and after != before:
                        return {"status": "navigated", "page": after, "verified": True}
                    if after == page or page.lower() in (after or "").lower():
                        return {"status": "navigated", "page": after, "verified": True}
                    return {
                        "status": "failed",
                        "detail": f"navigate_to({page}) called but route stayed '{after or before}'",
                        "requested_page": page,
                        "current_page": after or before,
                    }
            except Exception as exc:
                return {"status": "error", "detail": str(exc)[:200]}
        return {
            "status": "unavailable",
            "reason": "control_center_vm_not_bound",
            "detail": "navigation_controller not available",
        }

    def _on_capture_screenshot(region: str = "main") -> dict[str, Any]:
        """Captura screenshot de la ventana UI."""
        try:
            from iabv_v15.infra.ui import build_ui_screenshot_provider
            provider = build_ui_screenshot_provider()
            if provider is None:
                return {"status": "error", "detail": "ui_not_running"}
            screenshot_data = provider.capture(region)
            if screenshot_data:
                import base64
                return {
                    "status": "ok",
                    "format": "png",
                    "size_bytes": len(screenshot_data),
                    "data_b64": base64.b64encode(screenshot_data).decode("ascii"),
                }
            return {"status": "error", "detail": "capture returned empty"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)[:200]}

    def _on_push_chat_message(role: str = "user", text: str = "") -> dict[str, Any]:
        """Registra un mensaje en el buffer (llamado por la UI)."""
        with _chat_lock:
            _chat_buffer.append({
                "role": role,
                "text": text,
                "timestamp": time.time(),
            })
        return {"status": "recorded"}

    def _on_bridge_readiness() -> dict[str, Any]:
        """Returns the current readiness state of the bridge."""
        return server.readiness_snapshot()

    server.register_handler("send_message", _on_send_message)
    server.register_handler("read_messages", _on_read_messages)
    server.register_handler("get_ui_state", _on_get_ui_state)
    server.register_handler("navigate", _on_navigate)
    server.register_handler("capture_screenshot", _on_capture_screenshot)
    server.register_handler("push_chat_message", _on_push_chat_message)
    server.register_handler("bridge_readiness", _on_bridge_readiness)

    return server
