"""MCP server que expone los servicios core de IABV v1.5.

Tools expuestas:
  - world_model_snapshot: snapshot operativo (ventanas, foco, red, tools, bloqueos)
  - orchestrator_preview: previsualiza la decisión del AdaptiveTaskOrchestrator
                          para un goal sin ejecutarla (lectura; no altera estado)
  - site_exploration_explore: crawl BFS same-domain con persistencia de manual
  - portable_context_get: paquete portable condensado para sesiones nuevas
  - self_examination_current: review operativo actual + patrones detectados
  - chatgpt_web_capture: flujo chatgpt_web_assisted (browser_dom_capture) con
                         soporte de reingest_only (PR #13 / PR #21)
  - run_self_audit: ejecuta `SelfAuditService` (read-only) y devuelve snapshot
                    serializado; pasa por governance gate `assistant_kind='audit'`

Audit tools (capa humana para que Devin observe la laptop del usuario):
  - run_pytest: ejecuta la batería oficial (o una suite whitelisted) read-only
  - read_repo_file: lee archivos dentro del workspace, respetando blacklist
                    de secrets y tope de tamaño
  - list_repo_directory: lista entries con {name, type, size, mtime}
  - capture_ui_screenshot: captura ventana IABV vía provider del container
                           (degrada explícito a `ui_not_running` si no hay)
  - git_status_and_log: read-only `git status --porcelain -b` + `git log`
  - probe_assistant_login: comprueba si el usuario está logueado en un
                           asistente externo (ChatGPT/Claude/Codex/Gemini)
                           abriendo la URL declarada con Playwright; primer
                           gate con `requires_network=True`

Contratos que NO se rompen:
  - No decide rutas: sólo expone servicios existentes.
  - Respeta AutonomyGovernancePolicy: gates activos siguen bloqueando.
  - No crea otro cerebro; es un adaptador delgado sobre bootstrap.
  - No modifica datos de usuario; sólo lectura salvo chatgpt_web_capture y
    site_exploration_explore (ambos ya son servicios escritores legítimos).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, TypeVar

from iabv_v15.infra.mcp import audit_tools, audit_tools_observation

logger = logging.getLogger(__name__)

_R = TypeVar("_R")


def _run_sync_off_event_loop(
    func: Callable[..., _R],
    /,
    *args: Any,
    **kwargs: Any,
) -> _R:
    """Ejecuta ``func`` fuera del event loop activo, si hay uno.

    FastMCP invoca tools sync directamente sobre el hilo del event loop de
    uvicorn. Librerías como ``playwright.sync_api`` detectan ese loop y
    refusan arrancar con ``Please use the Async API instead``. Este helper
    despacha ``func`` a un ``ThreadPoolExecutor`` de un solo worker cuando
    detecta un loop corriendo (ningún loop en el hilo worker → Playwright
    sync OK), y la corre directo si no hay loop (tests y CLI).
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return func(*args, **kwargs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(func, *args, **kwargs).result()


DEFAULT_SERVER_NAME = "iabv-v15"
SUPPORTED_TRANSPORTS = {"stdio", "sse", "streamable-http"}


def _to_jsonable(value: Any) -> Any:
    """Convierte dataclasses, pydantic models y contenedores anidados a JSON."""

    from datetime import date, datetime

    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if isinstance(value, datetime):
        # ISO 8601 con separador 'T' (asdict sobre dataclasses frozen deja los
        # datetime sin serializar; `str(dt)` usa espacio en vez de 'T').
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return str(value)
    except Exception:
        return None


class IABVMCPServer:
    """Adaptador delgado que expone servicios de IABV vía MCP.

    Recibe un `container` ya construido (normalmente `AppBootstrap`) y registra
    las tools sobre una instancia de `FastMCP`. No instancia servicios nuevos
    ni duplica contratos: reutiliza lo que ya existe.
    """

    def __init__(
        self,
        container: Any,
        *,
        name: str = DEFAULT_SERVER_NAME,
        mcp: Any | None = None,
    ) -> None:
        if container is None:
            raise ValueError("container no puede ser None")
        self.container = container
        self.name = name
        if mcp is None:
            from mcp.server.fastmcp import FastMCP  # lazy import

            fastmcp_kwargs: dict[str, Any] = {
                'log_level': 'WARNING',
            }
            # MCP Python SDK >= 1.x introdujo DNS rebinding protection en
            # ``streamable-http`` que rechaza cualquier Host distinto a
            # localhost con ``HTTP/2 421 Invalid Host header`` (issue
            # modelcontextprotocol/python-sdk#1798). En nuestro flujo de
            # audit live el MCP se expone detras de un quick-tunnel de
            # cloudflared, asi que el Host llega como
            # ``*.trycloudflare.com`` y el server devolveria 421. Para
            # permitir el audit real desde afuera, inyectamos
            # ``TransportSecuritySettings`` con hosts/origenes abiertos
            # cuando la proteccion esta disponible en la version
            # instalada. Si la dependencia no expone el simbolo (versiones
            # viejas) seguimos con el constructor por defecto.
            try:
                from mcp.server.transport_security import TransportSecuritySettings

                fastmcp_kwargs["transport_security"] = TransportSecuritySettings(
                    enable_dns_rebinding_protection=False,
                    allowed_hosts=["*"],
                    allowed_origins=["*"],
                )
            except Exception:
                # Compatibilidad hacia atras: versiones sin
                # ``TransportSecuritySettings`` tampoco aplican la
                # proteccion, asi que no hace falta configurar nada.
                pass

            mcp = FastMCP(name, **fastmcp_kwargs)
        self.mcp = mcp
        self._register_tools()

    # ------------------------------------------------------------------
    # Helpers de acceso a servicios del container

    def _world_model_service(self) -> Any:
        svc = getattr(self.container, "world_model_service", None)
        if svc is None:
            raise RuntimeError("world_model_service no está disponible en el container")
        return svc

    def _portable_context_service(self) -> Any:
        svc = getattr(self.container, "portable_context_service", None)
        if svc is None:
            raise RuntimeError("portable_context_service no está disponible en el container")
        return svc

    def _self_examination_service(self) -> Any:
        svc = getattr(self.container, "operational_self_examination_service", None)
        if svc is None:
            raise RuntimeError("operational_self_examination_service no está disponible en el container")
        return svc

    def _site_exploration_service(self) -> Any:
        svc = getattr(self.container, "site_exploration_service", None)
        if svc is None:
            raise RuntimeError("site_exploration_service no está disponible en el container")
        return svc

    def _adaptive_orchestrator(self) -> Any:
        svc = getattr(self.container, "adaptive_task_orchestrator", None)
        if svc is None:
            raise RuntimeError("adaptive_task_orchestrator no está disponible en el container")
        return svc

    def _autonomy_cycle_service(self) -> Any:
        svc = getattr(self.container, "autonomy_cycle_service", None)
        if svc is None:
            raise RuntimeError("autonomy_cycle_service no está disponible en el container")
        return svc

    def _freeze_incident_reporter(self) -> Any:
        svc = getattr(self.container, "freeze_incident_reporter", None)
        if svc is None:
            raise RuntimeError("freeze_incident_reporter no está disponible en el container")
        return svc

    def _resource_orchestrator(self) -> Any:
        return getattr(self.container, "adaptive_resource_orchestrator", None)

    def _startup_timeline(self) -> Any:
        try:
            from iabv_v15.infra.startup_timeline import get_global_timeline
            return get_global_timeline()
        except Exception:
            return None

    def _environment_self_model(self) -> Any:
        svc = getattr(self.container, "environment_self_awareness_service", None)
        if svc is None:
            return None
        try:
            return svc.current_model()
        except Exception:
            return None

    def _pending_queue(self) -> Any:
        return getattr(self.container, "platform_pending_queue", None)

    def _oses(self) -> Any:
        return getattr(self.container, "operational_self_examination_service", None)

    def _ui_execution_runner(self) -> Any:
        svc = getattr(self.container, "ui_execution_runner", None)
        if svc is None:
            # bootstrap.py no siempre expone el runner como atributo estable;
            # lo construimos bajo demanda con el workspace_root del config.
            from iabv_v15.services.tools.ui_execution_runner import UIExecutionRunner
            config = getattr(self.container, "config", None)
            workspace_root = getattr(config, "workspace_root", None) if config else None
            if workspace_root is None:
                workspace_root = os.getcwd()
            return UIExecutionRunner(workspace_root=str(workspace_root))
        return svc

    def _code_audit_trail(self) -> Any:
        svc = getattr(self.container, "code_audit_trail", None)
        if svc is None:
            raise RuntimeError("code_audit_trail no está disponible en el container")
        return svc

    def _workspace_root(self) -> str:
        """Resuelve el `workspace_root` que usan las audit tools.

        Prioriza `container.config.workspace_root` (bootstrap normal); si no
        está, cae a `container.workspace_root` y como último recurso al
        `cwd()`. Las audit tools rechazarán rutas fuera de este root.
        """

        config = getattr(self.container, "config", None)
        root = getattr(config, "workspace_root", None) if config else None
        if root is None:
            root = getattr(self.container, "workspace_root", None)
        if root is None:
            root = os.getcwd()
        return str(root)

    def _ui_screenshot_provider(self) -> Any:
        """Devuelve el provider registrado para capturar la ventana IABV.

        El container puede exponer `ui_screenshot_provider` en Windows real
        (QScreen.grabWindow / mss). En Linux CI normalmente no existe y la
        tool degrada a `ui_not_running` sin fallar.
        """

        return getattr(self.container, "ui_screenshot_provider", None)

    def _pytest_python_executable(self) -> str | None:
        """Resuelve el intérprete Python para ``run_pytest`` server-side.

        Los MCP clients no eligen binario (sería RCE); la elección es del
        host. Jerarquía:

        1. ``container.config.pytest_python_executable`` si existe;
        2. ``container.environment_self_model.runtime_profile.python_executable``
           (lo que ya registra `EnvironmentSelfAwarenessService`);
        3. env var ``IABV_PYTEST_PYTHON`` (override operativo en Windows);
        4. ``None`` → `audit_tools.run_pytest` cae a `sys.executable`.

        Cualquier valor que falle la validación estricta de
        ``validate_pytest_executable`` (basename python* / existe / sin
        metachars de shell) se descarta silenciosamente en favor del
        siguiente nivel.
        """

        candidates: list[str] = []
        config = getattr(self.container, "config", None)
        if config is not None:
            cfg_value = getattr(config, "pytest_python_executable", None)
            if cfg_value:
                candidates.append(str(cfg_value))
        env_self_model = getattr(self.container, "environment_self_model", None)
        if env_self_model is not None:
            runtime = getattr(env_self_model, "runtime_profile", None)
            if isinstance(runtime, dict):
                rt_value = runtime.get("python_executable")
                if rt_value:
                    candidates.append(str(rt_value))
            elif runtime is not None:
                rt_value = getattr(runtime, "python_executable", None)
                if rt_value:
                    candidates.append(str(rt_value))
        env_value = os.environ.get("IABV_PYTEST_PYTHON")
        if env_value:
            candidates.append(env_value)

        for candidate in candidates:
            try:
                normalized = audit_tools.validate_pytest_executable(candidate)
            except audit_tools.AuditToolError:
                continue
            if normalized:
                return normalized
        return None

    # ------------------------------------------------------------------
    # Gate de governance / world_model antes de rutas externas
    #
    # Política (AGENTS.md "Política Operativa Actual"):
    #   1) consultar WorldModelSnapshot antes de una herramienta externa
    #   2) verificar red, foco, hilo, cuota, permiso y bloqueo activo
    #   3) si falta permiso o evidencia, bloquear la ruta y explicarlo
    #
    # Este helper implementa 1 y 2: lee el snapshot vivo del container,
    # revisa bloqueos activos, red y gates de permiso relevantes. Si algo
    # impide la ruta devuelve un payload `{"governance_blocked": True, ...}`
    # para que la tool lo propague al cliente MCP SIN ejecutar el servicio.

    def _load_candidate_traces_for_scope(self, scope_key: str) -> list[Any]:
        """Best-effort: pide al ExperimentLab wireado los traces del scope.

        El contrato de `ExperimentLab` wireado en este bootstrap no
        garantiza un selector nativo por ``comparison_scope_key``; para
        mantener esta tool puramente read-only y fail-observable,
        intentamos un set acotado de nombres conocidos sin inventar
        contratos nuevos. Si ninguno está disponible, devolvemos lista
        vacía para que la tool reporte ``no_candidates``.

        Usamos ``getattr`` sólo para el discovery del método opcional en
        `ExperimentLab`; la decisión es explícita: si el resultado no es
        iterable devolvemos ``[]``.
        """

        lab = getattr(self.container, "experiment_lab", None)
        if lab is None or not scope_key:
            return []
        for method_name in (
            "list_candidate_traces_for_scope",
            "list_ia_traces_for_scope",
            "traces_for_scope",
        ):
            candidate = getattr(lab, method_name, None)
            if candidate is None:
                continue
            try:
                maybe_traces = candidate(scope_key)
            except Exception:  # pragma: no cover - defensive
                continue
            if isinstance(maybe_traces, list):
                return maybe_traces
        return []

    def _governance_block_for_route(
        self,
        *,
        assistant_kind: str,
        requires_network: bool,
        allow_offline_refresh: bool = False,
    ) -> dict[str, Any] | None:
        """Devuelve dict de bloqueo si la ruta no es viable, o None si lo es.

        Args:
            assistant_kind: etiqueta de ruta (`chatgpt_web`, `site_crawler`, etc.).
                Se usa para filtrar gates/bloqueos específicos.
            requires_network: si True, exige `network_status.connected`.
            allow_offline_refresh: si True y no hay snapshot, intenta refresh.
        """

        wm_service = getattr(self.container, "world_model_service", None)
        if wm_service is None:
            # Sin world_model no podemos validar; fail-closed por seguridad.
            return {
                "governance_blocked": True,
                "reason": "world_model_service_unavailable",
                "detail": (
                    "No se pudo consultar WorldModelSnapshot antes de usar una "
                    "herramienta externa; la ruta queda bloqueada por defecto."
                ),
            }

        snapshot = None
        try:
            snapshot = wm_service.current_model()
        except Exception as exc:  # pragma: no cover - defensa
            return {
                "governance_blocked": True,
                "reason": "world_model_read_failed",
                "detail": str(exc),
            }

        if snapshot is None and allow_offline_refresh:
            try:
                snapshot = wm_service.request_refresh(reason="mcp_gate", full=False)
            except Exception:  # pragma: no cover - defensa
                snapshot = None

        if snapshot is None:
            return {
                "governance_blocked": True,
                "reason": "world_model_snapshot_missing",
                "detail": "No hay WorldModelSnapshot disponible para decidir la ruta.",
            }

        # 1) red: si la ruta requiere red, bloquear si no hay conexión.
        network = getattr(snapshot, "network_status", None)
        if requires_network and network is not None and not getattr(network, "connected", False):
            return {
                "governance_blocked": True,
                "reason": "network_unavailable",
                "detail": (
                    f"network_status.connected=False "
                    f"(status={getattr(network, 'status', 'desconocido')!r}); "
                    "no es seguro ejecutar la ruta externa."
                ),
                "network_status": _to_jsonable(network),
            }

        # 2) bloqueos operativos activos que apliquen a este assistant_kind
        #    o sean globales ("*" / vacío).
        blockers: list[dict[str, Any]] = []
        for record in getattr(snapshot, "block_records", []) or []:
            if getattr(record, "status", "active") != "active":
                continue
            scope = getattr(record, "assistant_kind", "") or ""
            if scope in ("", "*", assistant_kind):
                payload = _to_jsonable(record)
                if isinstance(payload, dict):
                    blockers.append(payload)
        if blockers:
            return {
                "governance_blocked": True,
                "reason": "operational_block_active",
                "detail": "Hay bloqueos activos en WorldModelSnapshot para esta ruta.",
                "blocks": blockers,
            }

        # 3) permission gates requeridos y no concedidos para este kind.
        pending_gates: list[dict[str, Any]] = []
        for gate in getattr(snapshot, "permission_gates", []) or []:
            if getattr(gate, "status", "no_requerido") != "requerido":
                continue
            if getattr(gate, "granted", False):
                continue
            scope = getattr(gate, "assistant_kind", "") or ""
            if scope in ("", "*", assistant_kind):
                payload = _to_jsonable(gate)
                if isinstance(payload, dict):
                    pending_gates.append(payload)
        if pending_gates:
            return {
                "governance_blocked": True,
                "reason": "permission_gate_required",
                "detail": (
                    "Hay permission gates `requerido` sin conceder; "
                    "aprueba el popup de clarificación antes de reintentar."
                ),
                "permission_gates": pending_gates,
            }

        return None

    # ------------------------------------------------------------------
    # Registro de tools

    def _register_tools(self) -> None:
        mcp = self.mcp

        @mcp.tool()
        def world_model_snapshot(refresh: bool = False, full: bool = False) -> dict[str, Any]:
            """Retorna el WorldModelSnapshot actual (ventanas, foco, red, tools, bloqueos).

            Args:
                refresh: si True, fuerza un refresh antes de leer.
                full: si True con refresh=True, pide un escaneo completo (más caro).
            """
            svc = self._world_model_service()
            if refresh:
                snapshot = svc.request_refresh(reason="mcp_refresh", full=bool(full))
            else:
                snapshot = svc.current_model()
            result = _to_jsonable(snapshot) or {}
            result['scan_stats'] = getattr(svc, 'scan_stats', {}) or {}
            return result

        @mcp.tool()
        def autonomy_status() -> dict[str, Any]:
            """Estado de autonomía: tareas pendientes, checkpoints de reanudación y capacidades.

            Expone lo que el programa sabe que puede hacer, lo que no puede,
            y lo que quedó interrumpido.  Útil para que el siguiente agente
            o sesión sepa exactamente dónde retomar.
            """
            acs = self._autonomy_cycle_service()
            summary = acs.startup_summary()
            queue = acs.queue
            summary['queue_summary'] = queue.summary()
            summary['all_tasks'] = [
                _to_jsonable(t) for t in queue.list_all()
            ]
            return summary

        @mcp.tool()
        def autonomy_update_task(
            task_id: str,
            status: str = "",
            next_action: str = "",
            resume_hint: str = "",
        ) -> dict[str, Any]:
            """Actualiza una tarea pendiente en la cola de autonomía.

            Args:
                task_id: ID de la tarea a actualizar.
                status: nuevo estado (PENDING, BLOCKED, COMPLETED, UNRESOLVED, READY_FOR_NEXT_SLICE).
                next_action: próxima acción sugerida.
                resume_hint: hint para reanudación.
            """
            from iabv_v15.domain.models import PendingTaskStatus
            acs = self._autonomy_cycle_service()
            queue = acs.queue
            task = queue.get(task_id)
            if task is None:
                return {'error': f'task {task_id} not found'}
            updates: dict[str, Any] = {}
            if status:
                try:
                    updates['status'] = PendingTaskStatus(status)
                except ValueError:
                    return {'error': f'invalid status: {status}'}
            if next_action:
                updates['next_action'] = next_action
            if resume_hint:
                updates['resume_hint'] = resume_hint
            if updates:
                task = task.model_copy(update=updates)
                queue.upsert(task)
            return _to_jsonable(task) or {}

        @mcp.tool()
        def report_freeze(
            description: str = "",
            trigger: str = "user",
        ) -> dict[str, Any]:
            """Captura un reporte completo de incidente/congelamiento.

            Genera un JSON estructurado con recursos, hilos, SQLite,
            timeline, hallazgos OSES y estado de la cola — todo lo que
            una IA necesita para diagnosticar qué pasó.

            Args:
                description: descripción del usuario (ej: "se congeló al abrir evolución").
                trigger: quién disparó el reporte: 'user', 'auto', 'startup'.
            """
            reporter = self._freeze_incident_reporter()
            path = reporter.capture_incident(
                trigger=trigger,
                user_description=description,
                resource_orchestrator=self._resource_orchestrator(),
                startup_timeline=self._startup_timeline(),
                environment_self_model=self._environment_self_model(),
                pending_queue=self._pending_queue(),
                oses=self._oses(),
            )
            report = reporter.get_report(path.name)
            return {
                'status': 'ok',
                'report_file': str(path),
                'report': report,
            }

        @mcp.tool()
        def list_freeze_reports(limit: int = 10) -> list[dict[str, Any]]:
            """Lista los reportes de incidentes/congelamientos recientes.

            Args:
                limit: máximo de reportes a devolver (default 10).
            """
            reporter = self._freeze_incident_reporter()
            return reporter.list_reports(limit=limit)

        @mcp.tool()
        def runtime_trace_summary() -> dict[str, Any]:
            """Resumen del trace de auditoría continua desde el arranque.

            Devuelve: total de eventos, desglose por tipo, errores,
            uptime, y si el tracing está habilitado.
            """
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            return get_runtime_tracer().summary()

        @mcp.tool()
        def runtime_trace_events(
            kind: str = "",
            limit: int = 50,
        ) -> list[dict[str, Any]]:
            """Lee eventos recientes del trace de auditoría continua.

            Cada evento tiene: ts, elapsed_ms, kind, data.
            Kinds comunes: service_init, decision, external_query,
            permission, error, ui_event, resource_snapshot.

            Args:
                kind: filtrar por tipo (vacío = todos).
                limit: máximo de eventos a devolver (default 50).
            """
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            return get_runtime_tracer().events(kind=kind or None, limit=limit)

        @mcp.tool()
        def runtime_boot_report() -> dict[str, Any]:
            """Reporte estructurado del arranque para diagnóstico por IA.

            Incluye: servicios inicializados, servicios fallidos,
            servicios lentos, queries externas, permisos denegados,
            errores durante boot. Diseñado para que cualquier IA
            pueda leer y diagnosticar problemas de arranque.
            """
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            return get_runtime_tracer().export_boot_report()

        @mcp.tool()
        def orchestrator_preview(
            user_goal: str,
            goal_parameters: dict[str, Any] | None = None,
            offline_only: bool = False,
            task_role: str | None = None,
        ) -> dict[str, Any]:
            """Previsualiza la decisión del orquestador adaptativo SIN ejecutarla.

            Útil para que el cliente MCP sepa qué proveedor/ruta recomendaría
            IABV para un goal dado (y por qué), respetando governance y world_model.

            Args:
                user_goal: texto del objetivo del usuario.
                goal_parameters: parámetros auxiliares (opcional).
                offline_only: fuerza ruta local sin consulta externa.
                task_role: hint de rol (training/chat/etc.), opcional.
            """
            from iabv_v15.domain.models import InferenceRequest, TaskRole

            orchestrator = self._adaptive_orchestrator()
            kwargs: dict[str, Any] = {
                "user_goal": user_goal,
                "goal_parameters": goal_parameters or {},
                "offline_only": bool(offline_only),
            }
            if task_role:
                try:
                    kwargs["task_role"] = TaskRole(task_role)
                except ValueError:
                    pass
            request = InferenceRequest(**kwargs)
            decision = orchestrator.build_decision_context_preview(request)
            return _to_jsonable(decision) or {}

        @mcp.tool()
        def site_exploration_explore(
            start_url: str,
            max_pages: int = 4,
            priority_keywords: list[str] | None = None,
        ) -> dict[str, Any]:
            """Crawl BFS same-domain con persistencia de manual.

            Guarda `<hostname>.json` + `.md` en `data/evolution/site_manuals/`.

            Args:
                start_url: URL raíz del crawl.
                max_pages: presupuesto de páginas a visitar (default 4).
                priority_keywords: tokens que reordenan la cola BFS.
            """
            block = self._governance_block_for_route(
                assistant_kind="site_crawler",
                requires_network=True,
            )
            if block is not None:
                return block
            svc = self._site_exploration_service()
            # `SiteExplorationService.explore` usa `BrowserSessionController`
            # (Playwright sync). Si corre sobre el event loop de uvicorn,
            # `sync_playwright()` explota con `Please use the Async API`.
            # Mismo patrón que PR #59/#60: despachar al thread pool sin loop.
            result = _run_sync_off_event_loop(
                svc.explore,
                start_url=start_url,
                max_pages=max_pages,
                priority_keywords=priority_keywords or [],
            )
            payload = _to_jsonable(result) or {}
            # persistencia opcional vía repositorio del container (si existe)
            repo = getattr(self.container, "site_manual_repository", None)
            if repo is not None and getattr(result, "success", False):
                try:
                    repo.save(result)
                    payload["manual_persisted"] = True
                except Exception as exc:  # pragma: no cover - defensa
                    payload["manual_persisted"] = False
                    payload["persist_error"] = str(exc)
            return payload

        @mcp.tool()
        def portable_context_get(refresh: bool = False, max_age_seconds: int = 300) -> dict[str, Any]:
            """Retorna el PortableContextPackage vigente (o lo reconstruye).

            Args:
                refresh: si True, fuerza rebuild aún si el cache está fresco.
                max_age_seconds: ventana de frescura aceptable cuando refresh=False.
            """
            svc = self._portable_context_service()
            # When the caller does NOT request a refresh, prefer the
            # persisted package on disk even if it is older than
            # max_age_seconds.  The persisted file (latest.json) is the
            # authoritative rich snapshot; rebuilding without an active
            # task_context produces empty sections because there is no
            # live orchestration cycle feeding the builder.
            effective_max_age = int(max_age_seconds)
            if not refresh:
                effective_max_age = max(effective_max_age, 86400)
            package = svc.current_package(
                refresh=bool(refresh),
                max_age_seconds=effective_max_age,
            )
            result = _to_jsonable(package) or {}
            # Fallback: if the returned package has empty sections but a
            # richer version exists on disk, load and return that instead.
            sections = result.get("sections") or []
            total_chars = sum(
                len(str(s.get("plain_text") or s.get("items") or ""))
                for s in sections
            )
            if sections and total_chars == 0:
                loaded = svc._load_latest_package()
                if loaded is not None:
                    loaded_dump = _to_jsonable(loaded) or {}
                    loaded_sections = loaded_dump.get("sections") or []
                    loaded_chars = sum(
                        len(str(s.get("plain_text") or s.get("items") or ""))
                        for s in loaded_sections
                    )
                    if loaded_chars > total_chars:
                        result = loaded_dump
            return result

        @mcp.tool()
        def self_examination_current(refresh: bool = False) -> dict[str, Any]:
            """Retorna el SelfExaminationSnapshot operativo actual.

            Incluye patrones repetidos, degradaciones detectadas y ajustes
            recomendados por `OperationalSelfExaminationService`.
            """
            svc = self._self_examination_service()
            review = svc.current_review(refresh=bool(refresh))
            summary = svc.review_summary(review)
            result = {"review": _to_jsonable(review), "summary": _to_jsonable(summary)}

            # Enrich recurring_issues and recommended_adjustments with
            # consumer-expected field aliases so that MCP clients
            # looking for ``pattern``, ``count``, ``recommendation``
            # (recurring_issues) and ``status``, ``adjustment``,
            # ``evidence_count`` (recommended_adjustments) find real
            # values instead of None.
            summary_dict = result.get("summary")
            if isinstance(summary_dict, dict):
                for issue in summary_dict.get("recurring_issues") or []:
                    if isinstance(issue, dict):
                        if "pattern" not in issue:
                            issue["pattern"] = issue.get("title") or ""
                        if "count" not in issue:
                            refs = issue.get("evidence_refs") or []
                            issue["count"] = len(refs) if refs else 1
                        if "recommendation" not in issue:
                            issue["recommendation"] = issue.get("summary") or ""
                for adj in summary_dict.get("recommended_adjustments") or []:
                    if isinstance(adj, dict):
                        if "adjustment" not in adj:
                            adj["adjustment"] = adj.get("recommended_change") or ""
                        if "status" not in adj:
                            adj["status"] = adj.get("severity") or "pending"
                        if "evidence_count" not in adj:
                            refs = adj.get("evidence_refs") or []
                            adj["evidence_count"] = len(refs)

            return result

        @mcp.tool()
        def gpu_model_benchmark(models: list[str] | None = None) -> dict[str, Any]:
            """Ejecuta benchmark de modelos Ollama locales y registra en ExperimentLab.

            Descubre los modelos instalados, ejecuta prompts estandarizados,
            mide tokens/segundo y calidad, y devuelve un ranking con la
            recomendacion del ExperimentLab sobre cual modelo rinde mejor
            en el hardware actual.

            Si ``models`` se omite, benchmarkea todos los modelos instalados.
            """
            block = self._governance_block_for_route(
                assistant_kind="gpu_benchmark",
                requires_network=False,
            )
            if block is not None:
                return block
            svc = getattr(self.container, "gpu_model_benchmark_service", None)
            if svc is None:
                return {"error": "gpu_model_benchmark_service no disponible en el container"}
            return _run_sync_off_event_loop(svc.run_full_benchmark, models=models)

        @mcp.tool()
        def chatgpt_web_capture(
            prompt_text: str,
            launch_target: str = "https://chatgpt.com/",
            response_wait_seconds: float = 45.0,
            reingest_only: bool = False,
            browser_profile_dir: str | None = None,
            browser_headless: bool = True,
            input_selectors: list[str] | None = None,
            response_selectors: list[str] | None = None,
            submit_selectors: list[str] | None = None,
        ) -> dict[str, Any]:
            """Ejecuta el flujo chatgpt_web_assisted con el UIExecutionRunner.

            Si `reingest_only=True` NO pega el prompt: relee la respuesta
            ya presente en el hilo (caso retry tras SESSION_EXPIRED).

            Args:
                prompt_text: texto del prompt a pegar (ignorado si reingest_only).
                launch_target: URL del asistente (default chatgpt.com).
                response_wait_seconds: tope de espera de respuesta estable.
                reingest_only: si True, sólo relee DOM sin pegar prompt.
                browser_profile_dir: ruta del perfil persistente (opcional).
                browser_headless: si True, corre sin ventana visible (default).
                input_selectors / response_selectors / submit_selectors:
                    selectores del card (defaults = oficiales del ToolCard).
            """
            block = self._governance_block_for_route(
                assistant_kind="chatgpt_web",
                requires_network=True,
            )
            if block is not None:
                return block
            runner = self._ui_execution_runner()
            defaults_input = ["textarea", 'div[contenteditable="true"]']
            defaults_response = ['[data-message-author-role="assistant"]', "main article"]
            defaults_submit = ['button[data-testid="send-button"]']
            profile_dir = browser_profile_dir or ""
            # `UIExecutionRunner._capture_browser_dom_response` usa Playwright
            # sync vía `BrowserSessionController`. Si corre sobre el event
            # loop de uvicorn (caso FastMCP streamable-http), explota con
            # `Please use the Async API`. Mismo patrón que PR #59/#60.
            result = _run_sync_off_event_loop(
                runner._capture_browser_dom_response,
                launch_target=launch_target,
                prompt_text=prompt_text,
                response_wait_seconds=float(response_wait_seconds),
                browser_profile_dir=profile_dir,
                browser_headless=bool(browser_headless),
                input_selectors=input_selectors or defaults_input,
                response_selectors=response_selectors or defaults_response,
                submit_selectors=submit_selectors or defaults_submit,
                reingest_only=bool(reingest_only),
            )
            return _to_jsonable(result) or {}

        # ----------------------------------------------------------------
        # Audit tools (Frente 1 del plan Devin ↔ IABV).
        #
        # Todas pasan por `_governance_block_for_route(assistant_kind="audit",
        # requires_network=False)` así un `OperationalBlockRecord` global o
        # específico de `audit` puede freezar la auditoría humana sin tener
        # que desactivar el bridge entero.

        @mcp.tool()
        def run_pytest(
            suite: str | None = None,
            keyword: str | None = None,
        ) -> dict[str, Any]:
            """Ejecuta la batería oficial (o una suite whitelisted) read-only.

            Args:
                suite: ruta relativa al workspace (default ``tests/``).
                    Debe matchear ``tests/`` o ``tests/subdir/test_*.py``;
                    cualquier otra cosa se rechaza para evitar ejecución
                    arbitraria fuera del árbol de pruebas.
                keyword: valor opcional de ``-k`` (alphanum + ``_.:[]-``).

            El intérprete Python se resuelve server-side (desde
            ``container.config`` / ``EnvironmentSelfModel`` o la env var
            ``IABV_PYTEST_PYTHON`` en Windows; si nada aplica, cae a
            ``sys.executable``). Los MCP clients NO pueden elegir binario.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            try:
                return audit_tools.run_pytest(
                    self._workspace_root(),
                    suite=suite,
                    keyword=keyword,
                    python_executable=self._pytest_python_executable(),
                )
            except audit_tools.AuditToolError as exc:
                return exc.to_payload()

        @mcp.tool()
        def read_repo_file(relative_path: str) -> dict[str, Any]:
            """Lee un archivo dentro del workspace como texto UTF-8.

            Rechaza paths absolutos, ``..``, archivos fuera del workspace,
            archivos sensibles (``.env*``, ``credentials*.json``, ``*.key``,
            ``*.pem``, ...) y archivos > 1 MiB.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            try:
                return audit_tools.read_repo_file(self._workspace_root(), relative_path)
            except audit_tools.AuditToolError as exc:
                return exc.to_payload()

        @mcp.tool()
        def list_repo_directory(
            relative_path: str = "",
            max_entries: int = audit_tools.DEFAULT_LIST_MAX,
        ) -> dict[str, Any]:
            """Lista entries de un directorio dentro del workspace.

            Devuelve ``{name, type, size, mtime, sensitive}`` por entry.
            ``max_entries`` se capea a ``MAX_LIST_ENTRIES`` (200).
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            try:
                return audit_tools.list_repo_directory(
                    self._workspace_root(),
                    relative_path,
                    max_entries=int(max_entries),
                )
            except audit_tools.AuditToolError as exc:
                return exc.to_payload()

        @mcp.tool()
        def capture_ui_screenshot(region: str = "control_center") -> dict[str, Any]:
            """Captura un screenshot de la ventana IABV si la UI está mapeada.

            Si el container no registró `ui_screenshot_provider` (caso Linux
            CI o la UI sin arrancar), devuelve ``{error: 'ui_not_running'}``
            en vez de tirar excepción.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            provider = self._ui_screenshot_provider()
            return audit_tools.capture_ui_screenshot(provider, region=region)

        @mcp.tool()
        def git_status_and_log(limit: int = audit_tools.DEFAULT_GIT_LOG_LIMIT) -> dict[str, Any]:
            """Lee ``git status --porcelain -b`` + ``git log -n <limit>``.

            Read-only. Devuelve ``{branch, ahead, behind, dirty_files,
            dirty_count, last_commits}`` o ``{error}`` si algo falla (ej.
            el workspace no es repo).
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            try:
                return audit_tools.git_status_and_log(
                    self._workspace_root(),
                    limit=int(limit),
                )
            except audit_tools.AuditToolError as exc:
                return exc.to_payload()

        # ------------------------------------------------------------
        # === F1.3 observation tools ===
        #
        # Read-only, cross-platform cuando es posible, degradan explícito a
        # payloads `{error, detail}` si la dependencia nativa falta. Todas
        # pasan por governance gate `assistant_kind='audit'`, sin red.

        @mcp.tool()
        def list_open_windows() -> dict[str, Any]:
            """Lista ventanas top-level visibles (Windows, pywin32).

            Fuera de Windows o sin pywin32 devuelve
            ``{error: 'not_supported_platform' | 'dependency_missing'}``.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            return audit_tools_observation.list_open_windows()

        @mcp.tool()
        def list_running_processes(limit: int = audit_tools_observation.MAX_PROCESSES_DEFAULT) -> dict[str, Any]:
            """Lista procesos del sistema vía psutil (cross-platform).

            `cmdline` viene sanitizado (redacta flags con tokens/secrets).
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            return audit_tools_observation.list_running_processes(limit=int(limit))

        @mcp.tool()
        def read_clipboard() -> dict[str, Any]:
            """Lee texto del portapapeles (pyperclip con fallback tkinter)."""

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            return audit_tools_observation.read_clipboard()

        @mcp.tool()
        def dump_qml_tree(max_nodes: int = audit_tools_observation.MAX_QML_NODES) -> dict[str, Any]:
            """Dumpa el árbol QObject/QQuickItem de la UI IABV si corre en este proceso."""

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            return audit_tools_observation.dump_qml_tree(max_nodes=int(max_nodes))

        # ------------------------------------------------------------
        # Frente 3 — probe_assistant_login
        #
        # Primera tool de audit que requiere red: abre la URL declarada
        # del asistente externo (chatgpt/claude/codex/gemini) y evalúa
        # si el usuario está logueado. Pasa por `assistant_kind='audit'`
        # + `requires_network=True` (fail-closed si la red no está
        # disponible o hay un bloqueo activo).

        @mcp.tool()
        def probe_assistant_login(
            assistant_kind: str,
            use_browser_session: bool = True,
            timeout_seconds: float = 10.0,
            include_screenshot: bool = False,
        ) -> dict[str, Any]:
            """Verifica si el usuario está logueado en un asistente externo.

            Abre la URL del provider (ChatGPT/Claude/Codex/Gemini) con
            Playwright (contexto aislado ``program_chat`` si
            ``use_browser_session=True``; CDP contra el Chrome del usuario si
            ``False``) y evalúa una heurística de logueo por provider.

            Args:
                assistant_kind: uno de ``chatgpt``, ``claude``, ``codex``,
                    ``gemini``.
                use_browser_session: si True (default), usa un contexto
                    aislado; si False, se conecta al Chrome del usuario vía
                    CDP (``IABV_SHARED_CDP_URL``, default
                    ``http://localhost:29229``).
                timeout_seconds: tope duro de navegación + heurística.
                include_screenshot: si True, incluye un PNG en base64 como
                    evidencia adicional (default False para payloads
                    chicos).

            Returns:
                ``{assistant_kind, logged_in, reason, evidence,
                checked_at_iso, duration_ms}`` en happy path, o
                ``{error, detail, assistant_kind, ...}`` ante fallo.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=True,
            )
            if block is not None:
                return block
            from iabv_v15.infra.mcp.audit_tools.probe_assistant_login import (
                probe_assistant_login as _probe,
            )

            # `_probe` usa Playwright sync API internamente. Si FastMCP nos
            # ejecuta sobre el event loop de uvicorn, `sync_playwright().start()`
            # falla con `Please use the Async API`. Despachamos a un worker
            # thread sin loop para mantener el contrato sync de `_probe`
            # (ejercitado por tests) y destrabar la invocación real desde MCP.
            return _run_sync_off_event_loop(
                _probe,
                assistant_kind,
                use_browser_session=bool(use_browser_session),
                timeout_seconds=float(timeout_seconds),
                include_screenshot=bool(include_screenshot),
            )

        # ------------------------------------------------------------
        # Frente 3.2 — audit_capability
        #
        # Ejecuta el runner asociado a una capacidad (ver
        # ``CapabilityAuditHarness``) y devuelve ``{executed, success,
        # latency_ms, output_preview, error, evidence, policy}``. El gate
        # de network se decide por capacidad: ``llm_external_*`` y
        # ``browser_capture`` requieren red; ``llm_local_ollama`` y
        # ``ui_execution`` no. En ``dry_run=True`` sólo se valida que
        # haya runner registrado (no dispara el gate de red).

        @mcp.tool()
        def audit_capability(
            capability_id: str,
            dry_run: bool = False,
        ) -> dict[str, Any]:
            """Audita end-to-end una capacidad declarada (sonda sintética).

            Pasa por ``assistant_kind='audit'``. ``requires_network`` se
            determina dinámicamente desde la policy de la capacidad (ej.
            ``llm_external_chatgpt`` → True; ``llm_local_ollama`` → False).

            Args:
                capability_id: uno de ``llm_local_ollama``,
                    ``llm_external_chatgpt``, ``llm_external_claude``,
                    ``browser_capture``, ``ui_execution`` (o cualquier otro
                    registrado en ``CapabilityAuditHarness``).
                dry_run: si True, solo valida que el runner exista sin
                    ejecutarlo; útil para revisar cobertura sin consumir
                    cuota externa.
            """

            from iabv_v15.infra.mcp.audit_tools.audit_capability import (
                audit_capability as _audit_capability,
                policy_for_capability as _policy_for_capability,
            )

            policy = _policy_for_capability(str(capability_id or "").strip())
            # En dry_run no tocamos red, así que no exigimos el gate de red
            # (pero sí el gate de audit). En modo real, respetamos
            # policy.requires_network.
            block = self._governance_block_for_route(
                assistant_kind=str(policy.assistant_kind or "audit"),
                requires_network=(False if bool(dry_run) else bool(policy.requires_network)),
            )
            if block is not None:
                return block

            harness = getattr(self.container, "capability_audit_harness", None)
            # Los runners de `audit_capability` (en particular
            # `browser_capture` y los que usan `probe_assistant_login`)
            # pueden invocar Playwright sync internamente. FastMCP nos
            # ejecuta sobre el event loop de uvicorn → `sync_playwright()`
            # explota con `Please use the Async API`. Mismo tratamiento
            # que `probe_assistant_login` (PR #59): despachar al thread
            # pool sin loop. Para runners puros (ollama httpx, ui_execution)
            # el overhead es mínimo y mantiene el contrato sync del harness.
            return _run_sync_off_event_loop(
                _audit_capability,
                capability_id,
                dry_run=bool(dry_run),
                harness=harness,
            )

        # ------------------------------------------------------------
        # Frente 3.3 — compare_perception_vs_ground_truth
        #
        # Contrasta lo que ``UniversalPerceptionService`` "ve" para una
        # ventana objetivo contra el ``WorldModelSnapshot`` real. Pasa
        # por ``assistant_kind='audit'`` (fail-closed ante bloqueos) y
        # NO requiere red: todo el cotejo es local (perception local +
        # WorldModel local).

        @mcp.tool()
        def compare_perception_vs_ground_truth(
            window_title: str,
            tool_id: str = "",
            assistant_kind: str = "",
            site_id: str = "",
        ) -> dict[str, Any]:
            """Compara la perception de IABV vs ground truth local.

            Args:
                window_title: título (o substring) de la ventana
                    objetivo; obligatorio. Se matchea case-insensitive
                    contra ``active_windows`` y ``focused_window`` del
                    ``WorldModelSnapshot``.
                tool_id, assistant_kind, site_id: pistas opcionales que
                    se propagan a ``UniversalPerceptionService.build_signal``.

            Returns:
                ``{tool_id, window_title, perception_json, ground_truth_json,
                mismatches, mismatch_count, severity_counts, evidence, error,
                detail, duration_ms, checked_at_iso}`` en happy path, o
                ``{error, detail, ...}`` ante fallo o bloqueo.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            from iabv_v15.infra.mcp.audit_tools.compare_perception_vs_ground_truth import (
                compare_perception_vs_ground_truth as _compare,
            )

            comparator = getattr(
                self.container, "perception_ground_truth_comparator", None
            )
            return _compare(
                window_title,
                tool_id=str(tool_id or ""),
                assistant_kind=str(assistant_kind or ""),
                site_id=str(site_id or ""),
                comparator=comparator,
            )

        # ------------------------------------------------------------
        # PCS v1 — cognitive_frame_translate + assistant_capabilities_list
        #
        # Traduce determinísticamente un ``PerceptionSnapshot`` al frame
        # cognitivo óptimo del asistente objetivo. Consume el
        # ``CognitiveFrameTranslator`` y el ``UniversalPerceptionService``
        # ya wireados en el bootstrap; no muta estado ni consume red.
        #
        # No pasa por governance gate: es read-only sobre perception vivo
        # + registry declarativo. Si falta el translator o el perception
        # service, degrada a ``{error: 'translator_unavailable', ...}`` o
        # ``{error: 'perception_unavailable', ...}`` (fail-observable).

        @mcp.tool()
        def cognitive_frame_translate(
            target_assistant_kind: str,
            user_goal: str = "",
            snapshot_hint: str = "",
        ) -> dict[str, Any]:
            """Renderiza el perception actual al frame óptimo del asistente.

            Args:
                target_assistant_kind: ``"codex"``, ``"claude_web"``,
                    ``"devin"``, etc. Si es desconocido, cae a
                    ``structured_qa`` (invariante del registry).
                user_goal: objetivo del usuario en lenguaje natural.
                    Si se omite, se usa ``snapshot_hint`` como fallback.
                snapshot_hint: etiqueta libre que queda en ``metadata``
                    para que otra sesión pueda correlacionar el render.

            Returns:
                ``CognitiveFramePayload`` serializado como dict, o un
                payload ``{error: ..., detail: ...}`` si falta alguna
                dependencia del container.
            """

            translator = getattr(self.container, "cognitive_frame_translator", None)
            if translator is None:
                return {
                    "error": "translator_unavailable",
                    "detail": (
                        "AssistantCapabilityRegistry/CognitiveFrameTranslator no "
                        "está wireado en el bootstrap."
                    ),
                    "target_assistant_kind": str(target_assistant_kind or ""),
                }
            context_assembler = getattr(
                self.container, "task_context_assembler", None
            )
            if context_assembler is None or not hasattr(
                context_assembler, "build_perception_snapshot"
            ):
                return {
                    "error": "perception_unavailable",
                    "detail": (
                        "TaskContextAssembler.build_perception_snapshot no está "
                        "wireado; no se puede producir PerceptionSnapshot."
                    ),
                    "target_assistant_kind": str(target_assistant_kind or ""),
                }
            try:
                from iabv_v15.domain.models import (
                    InferenceRequest,
                    RuntimeSignal,
                    SessionHealthSnapshot,
                    TaskIntent,
                )

                # -- Gather runtime_signals from WorldModelService ----------
                runtime_signals: list[RuntimeSignal] = []
                try:
                    wm_svc = getattr(self.container, "world_model_service", None)
                    if wm_svc is not None:
                        wm_snap = wm_svc.current_model()
                        if wm_snap is not None:
                            net = getattr(wm_snap, "network_status", None)
                            if net is not None:
                                runtime_signals.append(
                                    RuntimeSignal(
                                        signal_kind="network_status",
                                        summary=(
                                            f"connected={getattr(net, 'connected', False)}, "
                                            f"latency_ms={getattr(net, 'latency_ms', -1)}"
                                        ),
                                        metadata=_to_jsonable(net) or {},
                                    )
                                )
                            tool_count = len(wm_snap.tool_live_status or [])
                            if tool_count:
                                runtime_signals.append(
                                    RuntimeSignal(
                                        signal_kind="tool_live_count",
                                        summary=f"{tool_count} tools con live status",
                                    )
                                )
                except Exception:
                    pass

                # -- Build session_health from OSES -------------------------
                session_health: SessionHealthSnapshot | None = None
                try:
                    oses = getattr(
                        self.container,
                        "operational_self_examination_service",
                        None,
                    )
                    if oses is not None:
                        review = oses.current_review(refresh=False)
                        if review is not None:
                            session_health = SessionHealthSnapshot(
                                health_label=review.status or "unknown",
                                health_flags=[
                                    f.title
                                    for f in (review.findings or [])[:3]
                                    if f.title
                                ],
                                status=review.status or "idle",
                            )
                except Exception:
                    pass

                effective_goal = str(user_goal or snapshot_hint or "cognitive_frame_translation")
                request = InferenceRequest(
                    user_goal=effective_goal,
                    metadata={"source": "cognitive_frame_translate"},
                )
                intent = TaskIntent(
                    intent_key="pcs_v1.cognitive_frame_translate",
                    title="PCS v1 cognitive frame translation",
                    summary=effective_goal,
                )
                perception = context_assembler.build_perception_snapshot(
                    request=request,
                    intent=intent,
                    runtime_signals=runtime_signals or None,
                    session_health=session_health,
                )
            except Exception as exc:  # pragma: no cover - defensive
                return {
                    "error": "perception_error",
                    "detail": str(exc),
                    "target_assistant_kind": str(target_assistant_kind or ""),
                }
            if perception is None:
                return {
                    "error": "perception_unavailable",
                    "detail": "build_perception_snapshot() devolvió None.",
                    "target_assistant_kind": str(target_assistant_kind or ""),
                }
            payload = translator.translate(
                perception=perception,
                target_assistant_kind=str(target_assistant_kind or ""),
            )
            dumped = payload.model_dump(mode="json")
            if snapshot_hint:
                metadata = dumped.get("metadata") or {}
                metadata["snapshot_hint"] = str(snapshot_hint)
                dumped["metadata"] = metadata
            return dumped

        @mcp.tool()
        def assistant_capabilities_list() -> dict[str, Any]:
            """Devuelve los `AssistantCapabilityProfile` declarados (PCS v1).

            Es read-only: cada perfil se serializa como dict y se incluye
            el listado de ``known_kinds``. Si el registry no está wireado,
            devuelve ``{error: 'registry_unavailable'}``.
            """

            registry = getattr(self.container, "assistant_capability_registry", None)
            if registry is None:
                return {
                    "error": "registry_unavailable",
                    "detail": "AssistantCapabilityRegistry no está wireado.",
                    "profiles": [],
                    "known_kinds": [],
                }
            profiles = registry.all_profiles()
            return {
                "known_kinds": registry.known_kinds(),
                "profiles": [p.model_dump(mode="json") for p in profiles],
            }

        # ------------------------------------------------------------
        # PCS v1 — synaptic_route + consensus_fuse (Piezas 4 y 5)
        #
        # Ambas son read-only, sin governance gate y fail-observable:
        # si falta la dependencia wireada en el bootstrap devolvemos
        # ``{error: '*_unavailable', detail: ...}`` en vez de crashear.
        #
        # ``synaptic_route`` devuelve un `SynapticRoutingDecision` con
        # scoring (fit, weight, availability) sin ejecutar la ruta.
        # Respeta el feature flag ``SYNAPTIC_ROUTING`` (default off):
        # con flag off la decisión viene con ``routing_enabled=False``
        # y ``selected_assistant_kind=''``.
        #
        # ``consensus_fuse`` fusiona candidate_traces del `ExperimentLab`
        # para un ``comparison_scope_key`` dado; si no hay mecanismo para
        # leer traces por scope en el lab wireado (o la lista resulta
        # vacía), retorna fail-observable con ``no_candidates``. No
        # muta los traces de entrada.

        @mcp.tool()
        def synaptic_route(
            task_kind: str,
            candidate_assistant_kinds: str = "",
            user_goal: str = "",
        ) -> dict[str, Any]:
            """Calcula la preferencia sináptica (PCS v1) para un task_kind.

            Read-only, sin governance gate. No ejecuta la ruta: sólo
            devuelve una `SynapticRoutingDecision` con scoring (fit,
            weight, availability) para el task_kind y los candidatos
            dados. ``LocalRoleRouter`` sigue siendo el decisor
            operativo; esta tool es un adaptador informativo.

            Args:
                task_kind: clasificación libre de la tarea (e.g.
                    ``"code_generation"``, ``"long_context_synthesis"``).
                    Si no mapea a un `AssistantStrength`, el fit_score es
                    ``0.0`` y ``unresolved_fields`` incluye
                    ``"task_kind_unknown"``.
                candidate_assistant_kinds: kinds separados por coma; si
                    está vacío se usan todos los kinds del registry.
                user_goal: texto libre del objetivo del usuario. Si
                    menciona un proveedor explícito (e.g. "gemini",
                    "claude"), ese candidato recibe un bonus de scoring.

            Returns:
                ``SynapticRoutingDecision`` serializado como dict, o
                ``{error: 'router_unavailable', ...}`` si el router no
                está wireado. Si el feature flag ``SYNAPTIC_ROUTING`` no
                está activo, la decisión viene con
                ``routing_enabled=False`` y ``selected_assistant_kind=''``.
            """

            router = getattr(self.container, "synaptic_router", None)
            if router is None:
                return {
                    "error": "router_unavailable",
                    "detail": (
                        "SynapticRouter no está wireado en el bootstrap. "
                        "Revisa el wiring de PCS v1 (Pieza 4)."
                    ),
                    "selected_assistant_kind": "",
                    "routing_enabled": False,
                }
            kinds = [
                s.strip()
                for s in str(candidate_assistant_kinds or "").split(",")
                if s.strip()
            ] or None
            decision = router.decide(
                task_kind=str(task_kind or ""),
                candidate_assistant_kinds=kinds,
                user_goal=str(user_goal or ""),
            )
            return decision.model_dump(mode="json")

        @mcp.tool()
        def consensus_fuse(
            scope_key: str = "",
            strategy: str = "weighted_vote",
        ) -> dict[str, Any]:
            """Fusiona candidate_traces del ExperimentLab por scope_key.

            Read-only, sin governance gate. No muta los traces de
            entrada. Estrategias soportadas: ``"weighted_vote"``
            (default), ``"highest_confidence"``, ``"first_success"``.

            La lectura de traces del `ExperimentLab` es best-effort: si
            el lab no expone un selector por ``comparison_scope_key``
            (o devuelve lista vacía), la tool devuelve
            ``{error: 'no_candidates', ...}`` — fail-observable.

            Args:
                scope_key: ``comparison_scope_key`` a consultar.
                strategy: estrategia de fusión (ver arriba). Valor
                    desconocido degrada a unresolved con
                    ``unknown_strategy``.

            Returns:
                ``ConsensusResult`` serializado como dict, o un
                ``{error: 'consensus_unavailable' | 'no_candidates', ...}``
                fail-observable.
            """

            service = getattr(self.container, "consensus_fusion_service", None)
            if service is None:
                return {
                    "error": "consensus_unavailable",
                    "detail": (
                        "ConsensusFusionService no está wireado en el "
                        "bootstrap. Revisa el wiring de PCS v1 (Pieza 5)."
                    ),
                    "strategy_used": str(strategy or ""),
                }
            scope_key_clean = str(scope_key or "").strip()
            candidate_traces = self._load_candidate_traces_for_scope(scope_key_clean)
            if not candidate_traces:
                return {
                    "error": "no_candidates",
                    "detail": (
                        "No hay candidate_traces accesibles para el "
                        "comparison_scope_key indicado. El ExperimentLab "
                        "wireado no expone selector por scope_key o la "
                        "lista está vacía."
                    ),
                    "comparison_scope_key": scope_key_clean,
                    "strategy_used": str(strategy or ""),
                }
            result = service.fuse(
                candidate_traces=candidate_traces,
                strategy=str(strategy or "weighted_vote"),
            )
            return result.model_dump(mode="json")

        # ------------------------------------------------------------
        # PCS v1 — embodiment_manifest
        #
        # Contrato declarativo que IABV expone a cada IA externa que se
        # conecte vía MCP. Una IA "encarnada" debe preferir las tools del
        # cuerpo (world_model_snapshot, self_examination_current,
        # run_pytest, read_repo_file, etc.) antes que las suyas cuando la
        # pregunta cae en un sensor ya cubierto por IABV.
        #
        # En v1 es puramente declarativo (``handshake_required=False``):
        # no bloquea a las IAs que lo ignoren; sólo las orienta. La
        # detección de violaciones vive aparte en
        # ``EmbodimentViolationDetector``. Esta tool NO requiere red, no
        # consume estado y no pasa por governance gate (es un manifest
        # fijo que describe la integración).

        @mcp.tool()
        def embodiment_manifest() -> dict[str, Any]:
            """Devuelve el contrato de encarnamiento PCS para IAs externas.

            Principio: si IABV tiene un sensor propio para esta pregunta,
            usalo antes de recurrir a tools externas al cuerpo. El JSON
            devuelto es estable y versionado por ``protocol``.
            """

            return {
                "protocol": "PCS-v1",
                "embodiment_principle": (
                    "Si IABV tiene un sensor propio para esta pregunta, "
                    "usalo antes de recurrir a tools externas al cuerpo."
                ),
                "sensor_before_question": [
                    {"question": "¿estado de ventanas/foco?", "tool": "world_model_snapshot"},
                    {"question": "¿salud del sistema?", "tool": "self_examination_current"},
                    {"question": "¿tests pasan?", "tool": "run_pytest"},
                    {"question": "¿contenido de archivo?", "tool": "read_repo_file"},
                    {"question": "¿listar directorio?", "tool": "list_repo_directory"},
                    {"question": "¿clipboard usuario?", "tool": "read_clipboard"},
                    {"question": "¿ventanas abiertas?", "tool": "list_open_windows"},
                    {"question": "¿procesos corriendo?", "tool": "list_running_processes"},
                    {"question": "¿árbol QML UI?", "tool": "dump_qml_tree"},
                    {"question": "¿login de asistente?", "tool": "probe_assistant_login"},
                    {"question": "¿captura DOM de ChatGPT?", "tool": "chatgpt_web_capture"},
                    {"question": "¿auditoría global?", "tool": "run_self_audit"},
                    {"question": "¿contexto portable?", "tool": "portable_context_get"},
                    {"question": "¿historia de git?", "tool": "git_status_and_log"},
                ],
                "violations_tracked": True,
                "violation_reporting_channel": "operational_self_examination_service",
                "session_scope_header": "X-IABV-Embodiment-Session",
                "handshake_required": False,
                "frame_translation_endpoint": "cognitive_frame_translate",
                "capability_profiles_endpoint": "assistant_capabilities_list",
            }

        # ------------------------------------------------------------
        # PCS v1 — embodiment_violations_current
        #
        # Devuelve las violaciones de encarnamiento acumuladas por el
        # ``EmbodimentViolationDetector``. En v1 el detector NO bloquea
        # (``handshake_required=False`` en el manifest); esta tool es
        # puramente read-only y fail-observable: si el container no
        # expone el detector, devuelve ``{'error': 'detector_unavailable'}``
        # en vez de crashear.

        @mcp.tool()
        def embodiment_violations_current(session_id: str = "") -> dict[str, Any]:
            """Lista violaciones detectadas para una sesión o globalmente.

            Args:
                session_id: si se pasa, filtra al buffer de esa sesión;
                    si queda vacío, devuelve el agregado global.
            """

            detector = getattr(self.container, "embodiment_violation_detector", None)
            if detector is None or not hasattr(detector, "snapshot"):
                return {
                    "error": "detector_unavailable",
                    "detail": (
                        "container.embodiment_violation_detector no está disponible. "
                        "Asegurate de construir el bootstrap completo."
                    ),
                    "session_id": session_id,
                    "violations": [],
                    "count": 0,
                }
            records = detector.snapshot(session_id=session_id or None)
            violations = [_to_jsonable(record) for record in records]
            return {
                "session_id": session_id,
                "violations": violations,
                "count": len(violations),
            }

        # ------------------------------------------------------------
        # Frente 2 — Self audit tool
        #
        # `run_self_audit` ejecuta el `SelfAuditService` y devuelve el
        # snapshot serializado. Pasa por el gate de governance con
        # `assistant_kind='audit'` (fail-closed). No requiere red.
        # Si el container no expone el service (bootstrap degradado),
        # devuelve un payload `{'error': 'self_audit_unavailable', ...}`
        # en vez de crashear: la ruta debe ser siempre observable.

        @mcp.tool()
        def run_self_audit(reason: str | None = None) -> dict[str, Any]:
            """Ejecuta el SelfAuditService (read-only) y devuelve el snapshot.

            Pasa por el governance gate `assistant_kind='audit'` (fail-closed).
            No toca red ni sistema vivo; sólo lee estado ya observado por los
            services de evolution. El snapshot queda persistido en
            `data/evolution/self_audit/{latest.json, latest.md, history/*}`.

            Args:
                reason: etiqueta humana opcional que se guarda con el snapshot
                    para trazabilidad (por ejemplo, `"pre_release_check"`).
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            service = getattr(self.container, "self_audit_service", None)
            if service is None:
                return {
                    "error": "self_audit_unavailable",
                    "detail": (
                        "container.self_audit_service no está disponible. "
                        "Revisa bootstrap.py: el wiring de SelfAuditService "
                        "puede haber degradado."
                    ),
                }
            snapshot = service.run(reason=reason)
            return _to_jsonable(snapshot) or {}

        # ------------------------------------------------------------
        # F1.7 — PerceptionCrossValidator expuesto como MCP tool
        #
        # Cruza datos de multiples fuentes de percepcion (procesos vs
        # tool availability, WorldModel vs ToolRegistry, ventanas vs
        # focused_window) para detectar inconsistencias que sensores
        # individuales no ven.  Read-only; no modifica estado.

        @mcp.tool()
        def cross_validate_perception() -> dict[str, Any]:
            """Cruza datos de multiples fuentes de percepcion para detectar inconsistencias.

            Compara:
            - Procesos corriendo vs tool availability (detecta tools instalados
              pero reportados como missing)
            - ToolRegistry vs WorldModel tool_live_status (detecta tools
              invisibles para el WorldModel)
            - Ventanas activas vs focused_window (detecta anomalias de foco)

            Pasa por governance gate ``assistant_kind='audit'`` (fail-closed).
            No requiere red: todo el cotejo es local.
            """
            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=False,
            )
            if block is not None:
                return block
            validator = getattr(self.container, "perception_cross_validator", None)
            if validator is None:
                return {
                    "error": "cross_validator_unavailable",
                    "detail": (
                        "container.perception_cross_validator no está disponible. "
                        "Revisa bootstrap.py: el wiring de PerceptionCrossValidator "
                        "puede haber degradado."
                    ),
                }
            return validator.run_cross_validation()

        # ------------------------------------------------------------
        # F2.1 — GitHubRemoteService expuesto como MCP tool
        #
        # Permite que el chat (via tool_calling_bridge) o un cliente MCP
        # (audit live en laptop) pida a IABV abrir un PR desde una rama
        # local. Pasa por ``AutonomyGovernancePolicy.allow_github_pr_open``
        # y por ``HumanApprovalBroker`` cuando la policy lo exige. La
        # evidencia JSON se persiste en ``data/evolution/pr_history/``.

        @mcp.tool()
        def github_remote_publish_branch_as_pr(
            branch: str,
            title: str,
            body: str = "",
            base: str = "main",
            diff_lines: int | None = None,
            draft: bool = False,
            remote: str = "origin",
        ) -> dict[str, Any]:
            """Empuja ``branch`` a ``remote`` y abre un PR hacia ``base``.

            Orquesta policy -> aprobacion humana (si aplica) -> git push ->
            GitHub API ``create_pr`` -> evidencia en disco.

            Args:
                branch: rama local a publicar. Debe existir en el checkout.
                title: titulo del PR (obligatorio).
                body: cuerpo del PR en Markdown.
                base: rama base (default ``main``).
                diff_lines: numero total de lineas agregadas+eliminadas.
                    Requerido para auto-aprobar ramas ``iabv-auto/*`` por la
                    policy. Si no se pasa, la policy exige humano.
                draft: si True, crea el PR en modo draft.
                remote: nombre del remote para el push (default ``origin``).
            """

            service = getattr(self.container, "github_remote_service", None)
            if service is None:
                return {
                    "error": "github_remote_unavailable",
                    "detail": (
                        "container.github_remote_service no esta disponible. "
                        "Revisa bootstrap.py (necesita GITHUB_TOKEN + "
                        "GitHubApiToolAdapter operativo)."
                    ),
                }
            result = service.publish_branch_as_pr(
                branch=branch,
                title=title,
                body=body,
                base=base,
                diff_lines=diff_lines,
                draft=bool(draft),
                remote=remote,
            )
            return {
                "success": result.success,
                "branch": result.branch,
                "base": result.base,
                "pushed": result.pushed,
                "pr_number": result.pr_number,
                "pr_url": result.pr_url,
                "http_status": result.http_status,
                "blocked_by_policy": result.blocked_by_policy,
                "required_approval": result.required_approval,
                "approval_granted": result.approval_granted,
                "error": result.error,
                "evidence_path": result.evidence_path,
            }

        # ------------------------------------------------------------
        # gpu_metacognition_check — verificación real de GPU
        #
        # Metacognición: el programa verifica qué GPU está usando
        # realmente cruzando nvidia-smi, ollama ps y wmic.
        # ------------------------------------------------------------

        @mcp.tool()
        def gpu_metacognition_check() -> dict[str, Any]:
            """Verificación metacognitiva de GPU (cross-validation).

            Cruza nvidia-smi, ollama ps, y detección de hardware para
            verificar que Ollama realmente usa la GPU correcta y que
            los modelos caben 100% en VRAM.

            Returns:
                dict con gpus_detected, ollama_state, issues, recommendations.
            """
            from iabv_v15.services.gpu_metacognition import gpu_metacognition_report
            return _to_jsonable(_run_sync_off_event_loop(gpu_metacognition_report))

        # ------------------------------------------------------------
        # full_system_metacognition_scan — inventario completo del sistema
        # ------------------------------------------------------------

        @mcp.tool()
        def full_system_metacognition_scan() -> dict[str, Any]:
            """Escaneo COMPLETO del sistema: navegadores, programas, modelos IA, configuraciones optimas."""
            from iabv_v15.services.full_system_metacognition import full_system_metacognition_report
            return _to_jsonable(_run_sync_off_event_loop(full_system_metacognition_report))

        # ------------------------------------------------------------
        # Code audit trail — registro y consulta de auditorías de código
        # ------------------------------------------------------------

        @mcp.tool()
        def register_audit_finding(
            module_path: str = '',
            title: str = '',
            description: str = '',
            impact: str = '',
            severity: str = 'medium',
            status: str = 'found',
            fix_description: str = '',
            pr_url: str = '',
            pattern_tag: str = '',
            category: str = '',
            bug_id: str = '',
            round_number: int = 0,
            auditor_name: str = '',
            source: str = 'external_agent',
            environment: str = 'unknown',
            needs_windows_verification: bool = False,
            needs_linux_verification: bool = False,
            confidence: float = 0.9,
        ) -> dict[str, Any]:
            """Registra un hallazgo de auditoría de código.

            Cualquier agente (Devin, Codex, IABV self-examination, humano)
            puede registrar hallazgos para que el sistema aprenda y
            cruce información entre auditorías.

            Args:
                module_path: ruta del módulo auditado (ej: services/auto_correction_engine.py)
                title: título corto del hallazgo
                description: descripción detallada del bug o hallazgo
                impact: impacto en el sistema
                severity: low, medium, high, critical
                status: found, fixed, unresolved, wont_fix, needs_cross_verification
                fix_description: cómo se fixeó (si aplica)
                pr_url: URL del PR que contiene el fix
                pattern_tag: etiqueta de patrón (ej: jsonl_resilience, constructor_mismatch)
                category: categoría general (ej: wiring, persistence, security)
                bug_id: identificador del bug (ej: R18-1)
                round_number: número de ronda de auditoría
                auditor_name: nombre del auditor (ej: devin, codex, human)
                source: external_agent, self_examination, human
                environment: linux_vm, windows_native, unknown
                needs_windows_verification: True si necesita verificación en Windows
                needs_linux_verification: True si necesita verificación en Linux
                confidence: nivel de confianza del hallazgo (0.0-1.0)
            """
            trail = self._code_audit_trail()
            return trail.record_finding(
                module_path=module_path,
                title=title,
                description=description,
                impact=impact,
                severity=severity,
                status=status,
                fix_description=fix_description,
                pr_url=pr_url,
                pattern_tag=pattern_tag,
                category=category,
                bug_id=bug_id,
                round_number=round_number,
                auditor_name=auditor_name,
                source=source,
                environment=environment,
                needs_windows_verification=needs_windows_verification,
                needs_linux_verification=needs_linux_verification,
                confidence=confidence,
            )

        @mcp.tool()
        def register_audit_round(
            auditor_name: str = '',
            source: str = 'external_agent',
            environment: str = 'unknown',
            round_number: int = 0,
            modules_audited: list[str] | None = None,
            total_loc_audited: int = 0,
            pr_url: str = '',
            ci_status: str = '',
            unresolved_items: list[str] | None = None,
            findings: list[dict[str, Any]] | None = None,
            tests_added: int = 0,
            tests_passed: int = 0,
            tests_failed: int = 0,
            auditor_session_url: str = '',
        ) -> dict[str, Any]:
            """Registra una ronda completa de auditoría con N hallazgos en un solo batch.

            A diferencia de register_audit_finding (que crea una mini-ronda
            por hallazgo), este tool registra UNA ronda coherente con todos
            los findings de una sesión de auditoría.

            Args:
                auditor_name: nombre del auditor (ej: devin, codex, human)
                source: external_agent, self_examination, human
                environment: linux_vm, windows_native, unknown
                round_number: número de ronda de auditoría
                modules_audited: lista de módulos auditados
                total_loc_audited: líneas de código revisadas
                pr_url: URL del PR asociado a la ronda
                ci_status: estado de CI (passed, failed, pending)
                unresolved_items: lista de items sin resolver
                findings: lista de dicts, cada uno con campos de AuditFinding
                    (module_path, title, description, impact, severity,
                     status, fix_description, pr_url, pattern_tag, category,
                     bug_id, line_range, needs_windows_verification,
                     needs_linux_verification, confidence)
                tests_added: tests nuevos agregados en esta ronda
                tests_passed: tests que pasaron
                tests_failed: tests que fallaron
                auditor_session_url: URL de la sesión del auditor
            """
            from iabv_v15.services.evolution.code_audit_trail import (
                AuditEnvironment,
                AuditFinding,
                AuditRound,
                AuditSource,
                FindingSeverity,
                FindingStatus,
                _safe_enum,
            )

            parsed_findings: list[AuditFinding] = []
            for fd in (findings or []):
                parsed_findings.append(AuditFinding(
                    round_id='',
                    bug_id=fd.get('bug_id', ''),
                    module_path=fd.get('module_path', ''),
                    line_range=fd.get('line_range', ''),
                    category=fd.get('category', ''),
                    title=fd.get('title', ''),
                    description=fd.get('description', ''),
                    impact=fd.get('impact', ''),
                    severity=_safe_enum(FindingSeverity, fd.get('severity', 'medium'), FindingSeverity.MEDIUM),
                    status=_safe_enum(FindingStatus, fd.get('status', 'found'), FindingStatus.FOUND),
                    fix_description=fd.get('fix_description', ''),
                    pr_url=fd.get('pr_url', ''),
                    pattern_tag=fd.get('pattern_tag', ''),
                    needs_windows_verification=bool(fd.get('needs_windows_verification', False)),
                    needs_linux_verification=bool(fd.get('needs_linux_verification', False)),
                    confidence=float(fd.get('confidence', 0.9)),
                ))

            audit_round = AuditRound(
                round_number=round_number,
                auditor_name=auditor_name,
                auditor_session_url=auditor_session_url,
                source=_safe_enum(AuditSource, source, AuditSource.EXTERNAL_AGENT),
                environment=_safe_enum(AuditEnvironment, environment, AuditEnvironment.UNKNOWN),
                modules_audited=modules_audited or [],
                total_loc_audited=total_loc_audited,
                findings=parsed_findings,
                tests_added=tests_added,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                pr_url=pr_url,
                ci_status=ci_status,
                unresolved_items=unresolved_items or [],
            )

            trail = self._code_audit_trail()
            trail.record_round(audit_round)

            return {
                'round_id': audit_round.round_id,
                'round_number': audit_round.round_number,
                'auditor_name': audit_round.auditor_name,
                'source': audit_round.source.value,
                'environment': audit_round.environment.value,
                'findings_count': len(parsed_findings),
                'modules_audited': audit_round.modules_audited,
                'total_loc_audited': audit_round.total_loc_audited,
                'tests_added': audit_round.tests_added,
                'unresolved_items': audit_round.unresolved_items,
                'pr_url': audit_round.pr_url,
                'timestamp_utc': audit_round.timestamp_utc,
            }

        @mcp.tool()
        def code_audit_summary() -> dict[str, Any]:
            """Resumen completo de las auditorías de código registradas.

            Incluye: cobertura, patrones recurrentes, rondas recientes,
            verificaciones cruzadas pendientes.

            Útil para que un agente nuevo sepa qué ya se auditó, qué
            patrones de bugs se repiten, y qué necesita verificación
            en otro entorno (Linux vs Windows).
            """
            trail = self._code_audit_trail()
            return trail.summary_for_portable_context()

        @mcp.tool()
        def auditor_comparison() -> dict[str, Any]:
            """Comparación de rendimiento entre auditores (Devin, Codex, IABV, humano).

            Muestra por cada auditor:
            - Rondas realizadas, bugs encontrados, LOC auditados
            - Detection rate (bugs/módulos), coverage depth (tests/bugs)
            - Especialidades por patrón de bugs
            - Entornos cubiertos (Linux, Windows)

            Usa esto para saber quién es mejor en qué tipo de auditoría
            y alimentar la decisión de a quién asignar la siguiente.
            """
            trail = self._code_audit_trail()
            return trail.auditor_performance_summary()

        # ------------------------------------------------------------
        # self_audit — IABV tests itself by running a goal through
        # its own pipeline and verifying the full chain works.
        # ------------------------------------------------------------

        @mcp.tool()
        def self_audit(
            test_goal: str = "explica brevemente que eres y que puedes hacer",
        ) -> dict[str, Any]:
            """IABV se auto-audita: envía un objetivo de prueba por su
            propio pipeline y verifica que orquestación, routing, contexto
            portable, world model y OSES funcionan correctamente.

            Esto implementa la auto-auditoría: el sistema se mete en sus
            propios zapatos y verifica que todo funciona de punta a punta.

            Args:
                test_goal: objetivo de prueba a enviar por el pipeline.

            Returns:
                Reporte con resultados de cada subsistema auditado.
            """
            import time as _time
            from datetime import datetime as _dt, timezone as _tz
            from iabv_v15.domain.models import InferenceRequest

            report: dict[str, Any] = {
                'test_goal': test_goal,
                'timestamp_utc': _dt.now(_tz.utc).isoformat(),
                'subsystems': {},
            }
            t0 = _time.monotonic()

            # 1. Orchestrator preview — does intent classification work?
            try:
                orch = self._adaptive_orchestrator()
                request = InferenceRequest(user_goal=test_goal)
                preview = orch.build_decision_context_preview(request)
                preview_data = _to_jsonable(preview) or {}
                report['subsystems']['orchestrator'] = {
                    'status': 'ok',
                    'intent': preview_data.get('intent_schema', {}).get('primary_intent', ''),
                    'route': preview_data.get('route_decision', ''),
                    'confidence': preview_data.get('confidence', 0),
                }
            except Exception as exc:
                report['subsystems']['orchestrator'] = {'status': 'error', 'detail': str(exc)[:200]}

            # 2. Synaptic routing — does provider selection work?
            try:
                router = getattr(self.container, 'synaptic_router', None)
                if router:
                    decision = router.decide(
                        task_kind='code_generation',
                        user_goal=test_goal,
                    )
                    report['subsystems']['synaptic_router'] = {
                        'status': 'ok',
                        'selected': decision.selected_assistant_kind,
                        'score': decision.total_score,
                        'provider_hint': (decision.metadata or {}).get('provider_hint', ''),
                        'candidates': len(decision.alternatives or []),
                    }
                else:
                    report['subsystems']['synaptic_router'] = {'status': 'not_wired'}
            except Exception as exc:
                report['subsystems']['synaptic_router'] = {'status': 'error', 'detail': str(exc)[:200]}

            # 3. World Model — is it alive?
            try:
                svc = self._world_model_service()
                wm_obj = svc.current_model()
                wm = _to_jsonable(wm_obj) or {}
                report['subsystems']['world_model'] = {
                    'status': 'ok',
                    'windows_count': len(wm.get('open_windows', [])) if isinstance(wm, dict) else 0,
                    'tools_count': len(wm.get('tool_live_status', [])) if isinstance(wm, dict) else 0,
                }
            except Exception as exc:
                report['subsystems']['world_model'] = {'status': 'error', 'detail': str(exc)[:200]}

            # 4. OSES — self-examination working?
            try:
                oses = getattr(self.container, 'operational_self_examination_service', None)
                if oses:
                    review = oses.current_review(refresh=False, max_age_seconds=600)
                    report['subsystems']['oses'] = {
                        'status': 'ok',
                        'review_status': review.status,
                        'findings_count': len(review.findings),
                        'top_finding': review.findings[0].title if review.findings else 'none',
                        'has_auto_probes': bool((review.metadata or {}).get('pending_auto_probes')),
                    }
                else:
                    report['subsystems']['oses'] = {'status': 'not_wired'}
            except Exception as exc:
                report['subsystems']['oses'] = {'status': 'error', 'detail': str(exc)[:200]}

            # 5. Portable context — can it build a package?
            try:
                pcs = getattr(self.container, 'portable_context_service', None)
                if pcs:
                    pkg = pcs.build_package()
                    sections = list((pkg.sections or {}).keys()) if hasattr(pkg, 'sections') else []
                    report['subsystems']['portable_context'] = {
                        'status': 'ok',
                        'sections': sections[:10],
                        'section_count': len(sections),
                    }
                else:
                    report['subsystems']['portable_context'] = {'status': 'not_wired'}
            except Exception as exc:
                report['subsystems']['portable_context'] = {'status': 'error', 'detail': str(exc)[:200]}

            # 6. CommonSense — can it extract facts?
            try:
                from iabv_v15.services.common_sense_engine import extract_environment_facts
                facts = extract_environment_facts()
                report['subsystems']['common_sense'] = {
                    'status': 'ok',
                    'facts_count': len(facts) if isinstance(facts, (set, list)) else 0,
                    'sample_facts': sorted(list(facts))[:8] if isinstance(facts, set) else [],
                }
            except Exception as exc:
                report['subsystems']['common_sense'] = {'status': 'error', 'detail': str(exc)[:200]}

            # 7. UI state — is the UI running?
            try:
                provider = self._ui_screenshot_provider()
                from iabv_v15.infra.mcp import audit_tools
                ui_result = audit_tools.capture_ui_screenshot(provider, region='control_center')
                report['subsystems']['ui'] = {
                    'status': 'ok' if not ui_result.get('error') else 'not_running',
                    'detail': ui_result.get('error', 'screenshot_captured'),
                }
            except Exception as exc:
                report['subsystems']['ui'] = {'status': 'not_running', 'detail': str(exc)[:200]}

            elapsed = _time.monotonic() - t0
            report['elapsed_ms'] = round(elapsed * 1000)

            # Verdict
            statuses = [s.get('status', 'error') for s in report['subsystems'].values()]
            ok_count = sum(1 for s in statuses if s == 'ok')
            report['verdict'] = {
                'ok': ok_count,
                'total': len(statuses),
                'healthy': ok_count >= len(statuses) - 1,
                'summary': f'{ok_count}/{len(statuses)} subsystems operational',
            }

            return report

        # ------------------------------------------------------------
        # self_audit_incremental — version incremental que reporta
        # subsistema por subsistema para evitar timeout de tunnel
        # ------------------------------------------------------------

        @mcp.tool()
        def self_audit_incremental(
            subsystems: list[str] | None = None,
        ) -> dict[str, Any]:
            """Auto-auditoria incremental: audita subsistemas individuales.

            A diferencia de ``self_audit`` que audita los 7 subsistemas
            de una vez (y puede superar el timeout de ~100s del tunnel),
            esta version permite seleccionar que subsistemas auditar.

            Llamar sin ``subsystems`` audita solo los 3 mas rapidos
            (orchestrator, world_model, common_sense). Para una auditoria
            completa, hacer multiples llamadas con diferentes subsistemas.

            Subsistemas disponibles: orchestrator, synaptic_router,
            world_model, oses, portable_context, common_sense, ui.

            Args:
                subsystems: lista de subsistemas a auditar. Si None,
                    audita orchestrator + world_model + common_sense.

            Returns:
                Reporte parcial con resultados de los subsistemas pedidos.
            """
            import time as _time
            from datetime import datetime as _dt, timezone as _tz
            from iabv_v15.domain.models import InferenceRequest

            available = {
                'orchestrator', 'synaptic_router', 'world_model',
                'oses', 'portable_context', 'common_sense', 'ui',
            }
            if subsystems is None:
                subsystems = ['orchestrator', 'world_model', 'common_sense']
            else:
                subsystems = [s for s in subsystems if s in available]
                if not subsystems:
                    return {
                        'error': 'no_valid_subsystems',
                        'available': sorted(available),
                    }

            report: dict[str, Any] = {
                'mode': 'incremental',
                'requested': subsystems,
                'timestamp_utc': _dt.now(_tz.utc).isoformat(),
                'subsystems': {},
            }
            t0 = _time.monotonic()

            test_goal = "explica brevemente que eres y que puedes hacer"

            for sub in subsystems:
                sub_t0 = _time.monotonic()
                try:
                    if sub == 'orchestrator':
                        orch = self._adaptive_orchestrator()
                        request = InferenceRequest(user_goal=test_goal)
                        preview = orch.build_decision_context_preview(request)
                        preview_data = _to_jsonable(preview) or {}
                        report['subsystems']['orchestrator'] = {
                            'status': 'ok',
                            'intent': preview_data.get('intent_schema', {}).get('primary_intent', ''),
                            'route': preview_data.get('route_decision', ''),
                            'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                        }
                    elif sub == 'synaptic_router':
                        router = getattr(self.container, 'synaptic_router', None)
                        if router:
                            decision = router.decide(task_kind='code_generation', user_goal=test_goal)
                            report['subsystems']['synaptic_router'] = {
                                'status': 'ok',
                                'selected': decision.selected_assistant_kind,
                                'score': decision.total_score,
                                'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                            }
                        else:
                            report['subsystems']['synaptic_router'] = {'status': 'not_wired'}
                    elif sub == 'world_model':
                        svc = self._world_model_service()
                        wm_obj = svc.current_model()
                        wm = _to_jsonable(wm_obj) or {}
                        report['subsystems']['world_model'] = {
                            'status': 'ok',
                            'windows_count': len(wm.get('open_windows', [])) if isinstance(wm, dict) else 0,
                            'tools_count': len(wm.get('tool_live_status', [])) if isinstance(wm, dict) else 0,
                            'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                        }
                    elif sub == 'oses':
                        oses = getattr(self.container, 'operational_self_examination_service', None)
                        if oses:
                            review = oses.current_review(refresh=False, max_age_seconds=600)
                            report['subsystems']['oses'] = {
                                'status': 'ok',
                                'findings_count': len(review.findings),
                                'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                            }
                        else:
                            report['subsystems']['oses'] = {'status': 'not_wired'}
                    elif sub == 'portable_context':
                        pcs = getattr(self.container, 'portable_context_service', None)
                        if pcs:
                            pkg = pcs.build_package()
                            sections = list((pkg.sections or {}).keys()) if hasattr(pkg, 'sections') else []
                            report['subsystems']['portable_context'] = {
                                'status': 'ok',
                                'section_count': len(sections),
                                'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                            }
                        else:
                            report['subsystems']['portable_context'] = {'status': 'not_wired'}
                    elif sub == 'common_sense':
                        from iabv_v15.services.common_sense_engine import extract_environment_facts
                        facts = extract_environment_facts()
                        report['subsystems']['common_sense'] = {
                            'status': 'ok',
                            'facts_count': len(facts) if isinstance(facts, (set, list)) else 0,
                            'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                        }
                    elif sub == 'ui':
                        provider = self._ui_screenshot_provider()
                        ui_result = audit_tools.capture_ui_screenshot(provider, region='control_center')
                        report['subsystems']['ui'] = {
                            'status': 'ok' if not ui_result.get('error') else 'not_running',
                            'detail': ui_result.get('error', 'screenshot_captured'),
                            'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                        }
                except Exception as exc:
                    report['subsystems'][sub] = {
                        'status': 'error',
                        'detail': str(exc)[:200],
                        'elapsed_ms': round((_time.monotonic() - sub_t0) * 1000),
                    }

            elapsed = _time.monotonic() - t0
            report['elapsed_ms'] = round(elapsed * 1000)

            statuses = [s.get('status', 'error') for s in report['subsystems'].values()]
            ok_count = sum(1 for s in statuses if s == 'ok')
            report['verdict'] = {
                'ok': ok_count,
                'total': len(statuses),
                'healthy': ok_count == len(statuses),
                'summary': f'{ok_count}/{len(statuses)} subsystems operational',
            }

            return report

        # ------------------------------------------------------------
        # ui_bridge — interaccion con la UI PySide6 via IPC
        # ------------------------------------------------------------

        @mcp.tool()
        def ui_bridge_send_message(text: str) -> dict[str, Any]:
            """Envia un mensaje al chat de la UI PySide6 via UIBridgeService.

            El MCP server se conecta al UIBridgeServer (TCP localhost:18921)
            que corre en el proceso de la UI y despacha el mensaje al chat.

            Args:
                text: texto a enviar al chat.

            Returns:
                Estado del envio o error si la UI no esta disponible.
            """
            from iabv_v15.services.ui_bridge_service import UIBridgeClient
            client = UIBridgeClient()
            return client.call("send_message", text=text)

        @mcp.tool()
        def ui_bridge_read_messages(limit: int = 20) -> dict[str, Any]:
            """Lee los ultimos N mensajes del chat de la UI via UIBridgeService.

            Args:
                limit: cantidad maxima de mensajes a retornar.

            Returns:
                Lista de mensajes o error si la UI no esta disponible.
            """
            from iabv_v15.services.ui_bridge_service import UIBridgeClient
            client = UIBridgeClient()
            return client.call("read_messages", limit=limit)

        @mcp.tool()
        def ui_bridge_get_state() -> dict[str, Any]:
            """Obtiene el estado actual de la UI PySide6 (pagina activa, etc.).

            Returns:
                Estado de la UI o error si no esta disponible.
            """
            from iabv_v15.services.ui_bridge_service import UIBridgeClient
            client = UIBridgeClient()
            return client.call("get_ui_state")

        @mcp.tool()
        def ui_bridge_navigate(page: str) -> dict[str, Any]:
            """Navega a una pagina/tab de la UI PySide6.

            Args:
                page: nombre de la pagina (ej: 'control_center',
                    'evolution_center', 'capture_studio').

            Returns:
                Estado de la navegacion o error.
            """
            from iabv_v15.services.ui_bridge_service import UIBridgeClient
            client = UIBridgeClient()
            return client.call("navigate", page=page)

        # ------------------------------------------------------------
        # performance_profile — bottleneck detection for bootstrap/runtime
        # ------------------------------------------------------------

        @mcp.tool()
        def performance_profile(
            include_object_sizes: bool = False,
        ) -> dict[str, Any]:
            """Profila el rendimiento y uso de memoria de IABV en runtime.

            Mide tiempo y memoria de cada servicio/componente instanciado
            en el container (AppBootstrap). Identifica cuellos de botella
            y sugiere optimizaciones.

            Args:
                include_object_sizes: si True, estima el tamano en memoria
                    de cada atributo del container (mas lento pero mas detallado).

            Returns:
                Diccionario con:
                - process_memory_mb: memoria total del proceso
                - service_count: cantidad de servicios instanciados
                - heavy_services: servicios que consumen mas memoria
                - active_threads: hilos activos y su estado
                - background_timers: timers/polling activos
                - recommendations: lista de optimizaciones sugeridas
                - bottlenecks: cuellos de botella detectados
            """
            import sys as _sys
            import threading as _threading
            import time as _time

            result: dict[str, Any] = {
                'timestamp': _time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            }

            # --- Process memory ---
            try:
                import psutil
                proc = psutil.Process()
                mem_info = proc.memory_info()
                result['process_memory_mb'] = round(mem_info.rss / (1024 * 1024), 1)
                result['process_memory_vms_mb'] = round(mem_info.vms / (1024 * 1024), 1)
                result['cpu_percent'] = proc.cpu_percent(interval=0.5)
                result['open_files'] = len(proc.open_files())
                result['num_fds'] = getattr(proc, 'num_fds', lambda: -1)()
                children = proc.children(recursive=True)
                result['child_processes'] = [
                    {'pid': c.pid, 'name': c.name(), 'memory_mb': round(c.memory_info().rss / (1024 * 1024), 1)}
                    for c in children
                ]
            except ImportError:
                # psutil not available — fallback to /proc on Linux
                try:
                    with open('/proc/self/status') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                result['process_memory_mb'] = round(int(line.split()[1]) / 1024, 1)
                            elif line.startswith('VmSize:'):
                                result['process_memory_vms_mb'] = round(int(line.split()[1]) / 1024, 1)
                except Exception:
                    result['process_memory_mb'] = -1
                result['child_processes'] = []
            except Exception as exc:
                result['process_memory_error'] = str(exc)

            # --- Active threads ---
            threads = _threading.enumerate()
            result['active_thread_count'] = len(threads)
            thread_details = []
            for t in threads:
                thread_details.append({
                    'name': t.name,
                    'daemon': t.daemon,
                    'alive': t.is_alive(),
                })
            result['active_threads'] = thread_details

            # --- Container service inventory ---
            container = self.container
            service_attrs: list[dict[str, Any]] = []
            total_attrs = 0
            for attr_name in sorted(dir(container)):
                if attr_name.startswith('_'):
                    continue
                try:
                    obj = getattr(container, attr_name)
                except Exception:
                    continue
                if callable(obj) and not hasattr(obj, '__dict__'):
                    continue
                entry: dict[str, Any] = {
                    'name': attr_name,
                    'type': type(obj).__name__,
                }
                if include_object_sizes:
                    try:
                        entry['shallow_size_bytes'] = _sys.getsizeof(obj)
                    except Exception:
                        entry['shallow_size_bytes'] = -1
                service_attrs.append(entry)
                total_attrs += 1
            result['service_count'] = total_attrs

            # --- Detect polling/timer threads (bottlenecks) ---
            polling_threads = [
                t for t in thread_details
                if any(kw in t['name'].lower() for kw in
                       ('scan', 'poll', 'monitor', 'timer', 'refresh',
                        'world_model', 'health', 'bridge', 'bg-install'))
            ]
            result['background_polling_threads'] = polling_threads

            # --- WorldModel scan config ---
            wms = getattr(container, 'world_model_service', None)
            if wms is not None:
                result['world_model_config'] = {
                    'scan_interval_s': getattr(wms, '_scan_interval', None),
                    'full_scan_interval_s': getattr(wms, '_full_scan_interval', None),
                    'network_timeout_s': getattr(wms, '_NETWORK_TIMEOUT_SECONDS', None),
                }

            # --- Heavy services (by object dict size) ---
            if include_object_sizes:
                sized = [s for s in service_attrs if s.get('shallow_size_bytes', 0) > 0]
                sized.sort(key=lambda x: x['shallow_size_bytes'], reverse=True)
                result['heavy_services_by_size'] = sized[:15]

            # --- Recommendations ---
            recommendations = []
            bottlenecks = []

            mem_mb = result.get('process_memory_mb', 0)
            if isinstance(mem_mb, (int, float)) and mem_mb > 500:
                bottlenecks.append({
                    'area': 'memory',
                    'severity': 'high',
                    'detail': f'Proceso consume {mem_mb}MB RSS — considerar lazy loading de servicios no criticos',
                })
                recommendations.append(
                    'Implementar lazy loading: no instanciar todos los servicios en __init__. '
                    'Usar @property con cache para servicios pesados como EmbeddingIndexService, '
                    'SiteExplorationService, BrowserSessionController.'
                )

            if len(polling_threads) > 3:
                bottlenecks.append({
                    'area': 'threads',
                    'severity': 'medium',
                    'detail': f'{len(polling_threads)} hilos de polling activos — cada uno consume CPU y memoria',
                })
                recommendations.append(
                    'Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y '
                    'HealthRouter podrian compartir un unico hilo de scan con diferentes intervalos.'
                )

            thread_count = result.get('active_thread_count', 0)
            if thread_count > 15:
                bottlenecks.append({
                    'area': 'threads',
                    'severity': 'medium',
                    'detail': f'{thread_count} hilos activos total — overhead de context switching',
                })

            children = result.get('child_processes', [])
            if len(children) > 3:
                bottlenecks.append({
                    'area': 'subprocesses',
                    'severity': 'medium',
                    'detail': f'{len(children)} subprocesos hijos (MCP, tunnel, pip, etc.)',
                })
                recommendations.append(
                    'Reducir subprocesos: considerar ejecutar MCP in-process en vez de subprocess.'
                )

            if total_attrs > 50:
                recommendations.append(
                    f'{total_attrs} objetos instanciados en bootstrap. Considerar agrupar servicios '
                    'relacionados en modulos lazy-loaded y solo instanciar bajo demanda.'
                )

            recommendations.append(
                'Network probe: si el firewall bloquea port 53, los 3 fallbacks '
                'agregan hasta 7s de latencia al WorldModel scan. Considerar cache '
                'del resultado de conectividad por 60s.'
            )

            result['recommendations'] = recommendations
            result['bottlenecks'] = bottlenecks
            result['services'] = service_attrs

            return result

        # ------------------------------------------------------------
        # model_selection_status — adaptive provider selection
        # ------------------------------------------------------------

        @mcp.tool()
        def model_selection_status(
            task_type: str = 'general',
        ) -> dict[str, Any]:
            """Estado de seleccion adaptativa de modelos/proveedores.

            Muestra que proveedor (cloud o local) es el mejor para el
            tipo de tarea actual, con scores, latencias, tasas de exito
            y cooldowns activos por cuota agotada.

            Args:
                task_type: tipo de tarea (general, coding, planning, etc.)

            Returns:
                Diccionario con:
                - selected: proveedor seleccionado
                - fallback_chain: orden de proveedores
                - scores: puntuacion de cada proveedor
                - performance_summary: resumen de rendimiento historico
                - local_model_recommendation: modelo Ollama recomendado
                - degradation_findings: problemas detectados
            """
            from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector as _AMS
            from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService as _CRP

            selector = _CRP._model_selector
            if selector is None:
                selector = _AMS()

            selection = selector.select_best_provider(task_type=task_type)
            summary = selector.performance_summary()
            degradation = selector.detect_degradation()
            local_rec = selector.recommend_local_model(task_type=task_type)

            return _to_jsonable({
                'selected': selection.get('provider_id'),
                'reason': selection.get('reason'),
                'fallback_chain': selection.get('fallback_chain'),
                'scores': selection.get('scores'),
                'performance_summary': summary,
                'local_model_recommendation': local_rec,
                'degradation_findings': degradation,
            })

        # ------------------------------------------------------------
        # deep_environment_scan — periféricos, BIOS, seguridad, red
        # ------------------------------------------------------------

        @mcp.tool()
        def deep_environment_scan() -> dict[str, Any]:
            """Escaneo PROFUNDO del entorno: BIOS, USB, impresoras, audio, bluetooth, monitores, red, seguridad, servicios.

            Cubre los blind spots que EnvironmentSelfAwarenessService no cubre.
            """
            from iabv_v15.services.deep_environment_scanner import deep_environment_scan as _scan
            return _to_jsonable(_run_sync_off_event_loop(_scan))

        # ------------------------------------------------------------
        # evolution_backlog — tareas pendientes priorizadas
        # ------------------------------------------------------------

        @mcp.tool()
        def evolution_backlog_read() -> dict[str, Any]:
            """Leer el backlog de evolución — tareas pendientes que el programa debe resolver.

            Muestra todas las tareas pendientes priorizadas por severidad.
            """
            from iabv_v15.services.evolution_backlog import get_pending_tasks, load_backlog
            ws = self._workspace_root()
            pending = get_pending_tasks(workspace=ws)
            all_tasks = load_backlog(workspace=ws)
            return _to_jsonable({
                'pending': pending,
                'total_pending': len(pending),
                'total_all': len(all_tasks),
                'completed': len([t for t in all_tasks if t.get('status') == 'completed']),
            })

        @mcp.tool()
        def evolution_backlog_add(
            title: str,
            area: str,
            priority: str = 'medium',
            evidence: str = '',
        ) -> dict[str, Any]:
            """Agregar una tarea al backlog de evolución.

            Args:
                title: descripción corta de la tarea
                area: categoría (metacognition, hardware, gpu_routing, learning_persistence, etc.)
                priority: critical / high / medium / low
                evidence: por qué es necesaria
            """
            from iabv_v15.services.evolution_backlog import add_task
            ws = self._workspace_root()
            return _to_jsonable(add_task(
                title=title, area=area, priority=priority,
                source='mcp_tool', evidence=evidence, workspace=ws,
            ))

        @mcp.tool()
        def evolution_backlog_complete(task_id: str) -> dict[str, Any]:
            """Marcar una tarea del backlog como completada.

            Args:
                task_id: UUID de la tarea a completar
            """
            from iabv_v15.services.evolution_backlog import complete_task
            ws = self._workspace_root()
            ok = complete_task(task_id, workspace=ws)
            return _to_jsonable({'ok': ok, 'task_id': task_id})

        # ------------------------------------------------------------
        # account_resource_scan — cuentas, APIs, secretos, recursos
        # ------------------------------------------------------------

        @mcp.tool()
        def account_resource_scan_tool() -> dict[str, Any]:
            """Escanear cuentas, APIs, secretos y recursos disponibles.

            Detecta qué APIs están configuradas (GitHub, Devin, Ollama),
            qué cuentas de navegador existen, qué secretos están configurados,
            y el estado de Cloudflare Tunnel.
            """
            from iabv_v15.services.account_resource_scanner import account_resource_scan
            return _to_jsonable(_run_sync_off_event_loop(account_resource_scan))

        # ------------------------------------------------------------
        # regression_cycle_scan — detector de ciclos hacer-deshacer
        # ------------------------------------------------------------

        @mcp.tool()
        def regression_cycle_scan_tool() -> dict[str, Any]:
            """Detector de ciclos y regresiones — hacer-deshacer.

            Analiza el historial de git para detectar reverts, archivos
            con churn cíclico, tareas del backlog que oscilan, y funciones
            que se eliminan y reaparecen.
            """
            from iabv_v15.services.regression_cycle_detector import regression_cycle_scan
            ws = self._workspace_root()
            return _to_jsonable(regression_cycle_scan(workspace=ws))

        # ------------------------------------------------------------
        # limits_awareness — metacognición de límites y blind spots
        # ------------------------------------------------------------

        @mcp.tool()
        def limits_awareness_scan_tool() -> dict[str, Any]:
            """Metacognición profunda de límites y blind spots.

            Identifica qué NO puede ver o hacer el programa: hardware sin
            acceso, software no instalado, percepciones limitadas, gaps de
            conocimiento, y restricciones de autonomía.
            """
            from iabv_v15.services.limits_awareness import limits_awareness_scan
            ws = self._workspace_root()
            return _to_jsonable(limits_awareness_scan(workspace=ws))

        # ------------------------------------------------------------
        # gpu_routing — verificar y corregir GPU usada por Ollama
        # ------------------------------------------------------------

        @mcp.tool()
        def verify_gpu_routing_tool() -> dict[str, Any]:
            """Verificar y corregir qué GPU está usando Ollama.

            Cross-valida nvidia-smi vs ollama ps para determinar si Ollama
            está en la NVIDIA (correcto) o en Intel/CPU (incorrecto).
            Si está mal, reconfigura CUDA_VISIBLE_DEVICES y recarga el modelo.
            """
            from iabv_v15.services.gpu_metacognition import verify_ollama_gpu_usage
            return _to_jsonable(verify_ollama_gpu_usage())

        # ------------------------------------------------------------
        # common_sense — razonamiento autónomo por sentido común
        # ------------------------------------------------------------

        @mcp.tool()
        def common_sense_reasoning_tool(dry_run: bool = False) -> dict[str, Any]:
            """Ejecutar motor de razonamiento autónomo (sentido común).

            Observa el entorno, deduce conclusiones por cadena causal,
            y ejecuta acciones seguras automáticamente. Si dry_run=True,
            solo reporta lo que haría sin ejecutar.
            """
            from iabv_v15.services.common_sense_engine import run_common_sense_reasoning
            from iabv_v15.services.gpu_metacognition import gpu_metacognition_report
            from iabv_v15.services.account_resource_scanner import account_resource_scan
            ws = self._workspace_root()
            gpu = gpu_metacognition_report()
            acc = _run_sync_off_event_loop(account_resource_scan)
            return _to_jsonable(run_common_sense_reasoning(
                gpu_scan=gpu, account_scan=acc, dry_run=dry_run,
            ))

        # ------------------------------------------------------------
        # auto_correction — correcciones autónomas + deducción de herramientas
        # ------------------------------------------------------------

        @mcp.tool()
        def auto_correction_scan_tool() -> dict[str, Any]:
            """Ejecutar motor de auto-corrección y deducción de herramientas.

            Toma las deducciones del holistic scan, detecta qué herramientas
            faltan, aplica correcciones automáticas seguras, y genera una
            lista de lo que necesita acción del usuario.
            """
            from iabv_v15.services.auto_correction_engine import execute_auto_corrections
            from iabv_v15.services.account_resource_scanner import account_resource_scan
            from iabv_v15.services.limits_awareness import limits_awareness_scan
            from iabv_v15.services.gpu_metacognition import gpu_metacognition_report
            from iabv_v15.services.regression_cycle_detector import regression_cycle_scan
            from iabv_v15.services.self_code_analysis import holistic_metacognition_scan
            ws = self._workspace_root()
            acc = _run_sync_off_event_loop(account_resource_scan)
            lim = limits_awareness_scan(workspace=ws)
            gpu = gpu_metacognition_report()
            reg = regression_cycle_scan(workspace=ws)
            hol = holistic_metacognition_scan(
                account_state=acc, gpu_state=gpu,
                regression_state=reg, workspace=ws,
            )
            result = execute_auto_corrections(
                holistic_scan=hol, account_scan=acc,
                limits_scan=lim, gpu_scan=gpu,
                regression_scan=reg, workspace=ws,
            )
            return _to_jsonable(result)

        @mcp.tool()
        def deduce_missing_tools_tool() -> dict[str, Any]:
            """Deducir qué herramientas, APIs y recursos le faltan a IABV.

            Analiza los gaps detectados por los scanners y genera un plan
            de qué instalar, qué secretos pedir, y qué requiere acción
            del usuario vs qué puede resolverse automáticamente.
            """
            from iabv_v15.services.auto_correction_engine import deduce_missing_tools
            from iabv_v15.services.account_resource_scanner import account_resource_scan
            from iabv_v15.services.limits_awareness import limits_awareness_scan
            from iabv_v15.services.gpu_metacognition import gpu_metacognition_report
            ws = self._workspace_root()
            acc = _run_sync_off_event_loop(account_resource_scan)
            lim = limits_awareness_scan(workspace=ws)
            gpu = gpu_metacognition_report()
            return _to_jsonable(deduce_missing_tools(
                account_scan=acc, limits_scan=lim, gpu_scan=gpu,
            ))

        # ------------------------------------------------------------
        # self_code_analysis — el programa analiza su propio código
        # ------------------------------------------------------------

        @mcp.tool()
        def self_code_analysis() -> dict[str, Any]:
            """Auto-análisis COMPLETO del código: sintaxis, ramas pendientes, MCP tools, rendimiento, threading.

            Metacognición: el programa examina su propio código fuente para
            detectar errores de sintaxis, ramas sin mergear, problemas de
            indentación en tools MCP, llamadas bloqueantes en UI, y otros
            patrones que degradan rendimiento o funcionalidad.
            """
            from iabv_v15.services.self_code_analysis import full_self_analysis_report
            ws = self._workspace_root()
            return _to_jsonable(full_self_analysis_report(ws))

        @mcp.tool()
        def self_merge_branch(
            branch: str,
        ) -> dict[str, Any]:
            """Mergear una rama pendiente a la rama actual.

            Metacognición: el programa detecta ramas con mejoras no integradas
            y puede auto-mergearlas para mantener su código actualizado.

            Args:
                branch: nombre de la rama a mergear (ej: 'origin/iabv-auto/...')
            """
            gate = self._governance_block_for_route(
                assistant_kind='self_modify',
                requires_network=False,
            )
            if gate:
                return _to_jsonable(gate)

            import re as _re
            import subprocess as _sp
            if branch.startswith('-'):
                return _to_jsonable({'ok': False, 'error': 'branch name cannot start with "-" (git flag injection)'})
            if _re.search(r'[;&|`$\n]|--force|\.\.', branch):
                return _to_jsonable({'ok': False, 'error': 'branch name rejected (unsafe chars)'})
            # AGENTS.md: only devin/* and iabv-auto/* branches can be auto-merged
            safe_prefixes = ('devin/', 'iabv-auto/', 'origin/devin/', 'origin/iabv-auto/')
            if not any(branch.startswith(p) for p in safe_prefixes):
                return _to_jsonable({'ok': False, 'error': f'branch {branch!r} not in safe prefixes {safe_prefixes} — requires explicit human approval per AGENTS.md'})

            ws = self._workspace_root()
            try:
                merge_result = _sp.run(
                    ['git', '-C', ws, 'merge', '--no-edit', branch],
                    capture_output=True, text=True, timeout=60,
                )
                if merge_result.returncode != 0:
                    # Abort the merge on conflict
                    _sp.run(['git', '-C', ws, 'merge', '--abort'],
                                   capture_output=True, timeout=10)
                    return _to_jsonable({
                        'ok': False,
                        'error': 'merge conflict — aborted',
                        'details': merge_result.stderr.strip()[:500],
                    })
                return _to_jsonable({
                    'ok': True,
                    'merged': branch,
                    'output': merge_result.stdout.strip()[:500],
                })
            except Exception as exc:
                return _to_jsonable({'ok': False, 'error': str(exc)})

        # ------------------------------------------------------------
        # self_update — el programa se actualiza a sí mismo (git pull)
        #
        # Metacognición: el programa puede aplicar sus propias mejoras
        # sin requerir intervención manual del usuario.
        # ------------------------------------------------------------

        @mcp.tool()
        def self_update(
            branch: str | None = None,
        ) -> dict[str, Any]:
            """El programa se actualiza a sí mismo haciendo git pull.

            Metacognición aplicada: el programa reconoce que tiene una
            versión nueva disponible y se auto-actualiza sin intervención
            del usuario.

            Args:
                branch: rama específica (default: rama actual).

            Returns:
                dict con status, branch, output del git pull.
            """
            import re as _re
            import subprocess as _sp

            block = self._governance_block_for_route(
                assistant_kind="self_update",
                requires_network=True,
            )
            if block is not None:
                return block

            # Sanitize branch name — reject git flags (--force),
            # directory traversal (..), and shell metacharacters.
            if branch:
                if branch.startswith('-'):
                    return {"status": "error", "detail": "branch name cannot start with '-' (git flag injection)"}
                if '..' in branch:
                    return {"status": "error", "detail": "branch name cannot contain '..' (directory traversal)"}
                if not _re.match(r'^[a-zA-Z0-9][\w./-]*$', branch):
                    return {"status": "error", "detail": "invalid branch name"}

            ws = self._workspace_root()
            try:
                # Get current branch
                cur = _sp.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, timeout=10,
                    cwd=ws, check=False,
                )
                current_branch = cur.stdout.strip() or "unknown"

                if branch and branch != current_branch:
                    co = _sp.run(
                        ["git", "checkout", branch],
                        capture_output=True, text=True, timeout=30,
                        cwd=ws, check=False,
                    )
                    if co.returncode != 0:
                        return {
                            "status": "error",
                            "detail": f"checkout failed: {co.stderr.strip()}",
                        }
                    current_branch = branch

                # --rebase=false tolerates diverging branches
                # (e.g. local auto-merge commits that diverge from remote).
                # --ff-only would fail with "Diverging branches can't".
                result = _sp.run(
                    ["git", "pull", "--rebase=false"],
                    capture_output=True, text=True, timeout=60,
                    cwd=ws, check=False,
                )
                return {
                    "status": "ok" if result.returncode == 0 else "error",
                    "branch": current_branch,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.returncode != 0 else None,
                }
            except Exception as exc:
                return {"status": "error", "detail": str(exc)}

        # ------------------------------------------------------------
        # self_run_benchmark — el programa corre su propio benchmark
        #
        # Metacognición: el programa se auto-evalúa ejecutando el
        # script de benchmark y reportando los resultados.
        # ------------------------------------------------------------

        @mcp.tool()
        def self_run_benchmark() -> dict[str, Any]:
            """El programa ejecuta su propio GPU benchmark (gpu_auto_benchmark.py).

            Metacognición aplicada: el programa se auto-evalúa corriendo
            el benchmark completo (FASE 0-5) y reportando los resultados.

            Returns:
                dict con status, output (últimas 200 líneas), report_path.
            """
            import subprocess as _sp

            block = self._governance_block_for_route(
                assistant_kind="gpu_benchmark",
                requires_network=False,
            )
            if block is not None:
                return block

            ws = self._workspace_root()
            script = os.path.join(ws, "scripts", "gpu_auto_benchmark.py")
            if not os.path.isfile(script):
                return {"status": "error", "detail": f"script not found: {script}"}

            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = os.path.join(ws, "src")
                result = _sp.run(
                    ["python", script],
                    capture_output=True, text=True, timeout=600,
                    cwd=ws, env=env, check=False,
                )
                lines = result.stdout.strip().splitlines()
                # Return last 200 lines to avoid huge responses
                output_tail = "\n".join(lines[-200:]) if len(lines) > 200 else result.stdout.strip()
                return {
                    "status": "ok" if result.returncode == 0 else "error",
                    "output": output_tail,
                    "error": result.stderr.strip()[-500:] if result.returncode != 0 else None,
                    "report_path": os.path.join(ws, "data", "gpu_benchmark_report.json"),
                    "total_lines": len(lines),
                }
            except _sp.TimeoutExpired:
                return {"status": "timeout", "detail": "benchmark exceeded 10 min limit"}
            except Exception as exc:
                return {"status": "error", "detail": str(exc)}

        # ------------------------------------------------------------
        # self_auto_merge — el programa mergea sus propios PRs devin/*
        #
        # Motivacion: el usuario pidio dejar de hacer click en "Merge" en
        # GitHub cada vez que una IA cierra una mejora. Esta tool reusa la
        # misma logica que ``scripts/auto_merge_devin_pr.py`` con las
        # mismas salvaguardas (rama devin/*|iabv-auto/*, mergeable_state
        # no bloqueado, checks verdes). El gate de governance usa
        # ``assistant_kind="self_auto_merge"`` y ``requires_network=True``
        # para que el usuario pueda bloquearla globalmente sin tocar
        # codigo (``OperationalBlockRecord`` o ``permission_gate``).

        @mcp.tool()
        def self_auto_merge(
            pr_number: int,
            repo: str | None = None,
            method: str = "squash",
        ) -> dict[str, Any]:
            """Auto-mergea un PR ``devin/*`` / ``iabv-auto/*`` desde el programa.

            Usa el mismo criterio que el CLI ``scripts/auto_merge_devin_pr.py``:
            solo mergea ramas seguras, ``mergeable_state`` fuera de
            ``blocked/dirty/behind`` y checks verdes. ``force`` NO esta
            expuesto aqui: si hace falta saltear salvaguardas, usar el CLI
            con justificacion explicita del humano.

            Args:
                pr_number: numero del PR a mergear.
                repo: ``owner/repo`` (default ``jhonf463r/Python``).
                method: ``squash`` / ``merge`` / ``rebase``.

            Returns:
                ``MergeResult.to_dict()``. Campos clave: ``status``
                (``merged``/``already_merged``/``closed``/``blocked``/
                ``missing_token``/``http_error``), ``reason``, ``detail``,
                ``merge_sha``, ``branch_safe``.
            """

            block = self._governance_block_for_route(
                assistant_kind="self_auto_merge",
                requires_network=True,
            )
            if block is not None:
                return block

            from iabv_v15.infra.mcp.self_auto_merge import auto_merge as _auto_merge

            target_repo = (repo or "jhonf463r/Python").strip() or "jhonf463r/Python"
            result = _auto_merge(
                target_repo,
                int(pr_number),
                method=method,
                force=False,
            )
            return result.to_dict()

        @mcp.tool()
        def tool_version_scan() -> dict[str, Any]:
            """Escanea versiones de todas las herramientas que IABV usa.

            Retorna version instalada, disponibilidad y estado de cada
            tool (Ollama, git, gh, cloudflared, APIs). Persiste el log
            en data/metacognition/tool_versions_log.jsonl.
            """

            block = self._governance_block_for_route(
                assistant_kind="audit",
                requires_network=True,
            )
            if block is not None:
                return block

            from iabv_v15.services.tools.tool_version_monitor import (
                full_version_scan, persist_version_log,
            )
            scan = full_version_scan()
            ws = self._workspace_root() or ''
            if ws:
                persist_version_log(ws, scan)
            return _to_jsonable(scan)

    # ------------------------------------------------------------------
    # Ciclo de vida

    def run(self, transport: str = "stdio") -> None:
        if transport not in SUPPORTED_TRANSPORTS:
            raise ValueError(f"transport '{transport}' no soportado. Usa {sorted(SUPPORTED_TRANSPORTS)}")
        
        # Register self-update (write) tools for autonomous self-modification
        try:
            from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools
            _n_write_tools = register_self_update_tools(
                mcp=self.mcp,
                workspace_root_fn=self._workspace_root,
                governance_fn=self._governance_block_for_route,
                to_jsonable_fn=_to_jsonable,
            )
            logger.info("self_update_tools: %d write tools registered", _n_write_tools)
        except Exception as _sut_exc:
            logger.warning("self_update_tools: failed to register: %s", _sut_exc)

        # Suppress noisy per-session transport logs from the MCP SDK
        # and uvicorn access lines.
        for noisy in ('mcp', 'mcp.server', 'mcp.server.streamable_http',
                       'fastmcp', 'uvicorn', 'uvicorn.access', 'uvicorn.error'):
            logging.getLogger(noisy).setLevel(logging.WARNING)
        # httpx/httpcore handled by shared suppress_noisy_http_loggers().
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        suppress_noisy_http_loggers()

        logger.info("IABV MCP server starting (transport=%s, name=%s)", transport, self.name)
        self._log_github_api_adapter_status()
        self._log_devin_api_adapter_status()
        self.mcp.run(transport=transport)

    def _log_devin_api_adapter_status(self) -> None:
        """Diagnostica si ``devin_api`` esta listo para delegar a Devin.

        Mismo patron que ``_log_github_api_adapter_status``: si no hay API
        key resuelto, avisamos al arrancar con la lista exacta de env vars
        aceptados, asi el usuario no se entera solo cuando ya trato de
        delegar una tarea a Devin y vio ``devin_api [missing]`` en el
        audit.
        """

        adapters = getattr(self.container, "tool_adapters", None) or {}
        adapter = adapters.get("devin_api") if isinstance(adapters, dict) else None
        api_key = getattr(adapter, "api_key", "") if adapter is not None else ""
        if adapter is None:
            logger.warning(
                "devin_api adapter no esta wired; el chat cross-IA "
                "con Devin no podra delegar sesiones."
            )
            return
        if not api_key:
            logger.warning(
                "devin_api sin token. Exporta uno de: "
                "DEVIN_API_KEY_IABV (preferido), IABV_DEVIN_API_KEY, "
                "DEVIN_API_KEY. Sin token, devin_api aparece como "
                "'missing' en run_self_audit y la delegacion a Devin "
                "falla en is_available."
            )
            return
        logger.info(
            "devin_api adapter listo (api_key_len=%s).",
            len(api_key),
        )

    def _log_github_api_adapter_status(self) -> None:
        """Diagnostica si ``github_api`` esta listo para ``github_remote_*``.

        Si falta el token de GitHub, ``GitHubRemoteService`` puede pushear
        la rama pero ``create_pr`` falla. Emitimos un log explicito al
        arrancar asi el usuario no se entera solo cuando ya intento abrir
        un PR autonomo y vio un 401.
        """

        adapters = getattr(self.container, "tool_adapters", None) or {}
        adapter = adapters.get("github_api") if isinstance(adapters, dict) else None
        token = getattr(adapter, "token", "") if adapter is not None else ""
        repo = getattr(adapter, "repo", "") if adapter is not None else ""
        if adapter is None:
            logger.warning(
                "github_api adapter no esta wired; github_remote_publish_branch_as_pr "
                "solo podra pushear, no crear el PR."
            )
            return
        if not token:
            logger.warning(
                "github_api sin token. Exporta uno de: "
                "GITHUB_TOKEN_IABV (preferido), IABV_GITHUB_TOKEN, "
                "GITHUB_TOKEN, GH_TOKEN. Sin token, github_api aparece "
                "como 'missing' en run_self_audit y los PRs autonomos "
                "fallan en create_pr."
            )
            return
        logger.info(
            "github_api adapter listo (repo=%s, token_len=%s).",
            repo or "<no-repo>",
            len(token),
        )


def create_server(container: Any | None = None, *, name: str = DEFAULT_SERVER_NAME) -> IABVMCPServer:
    """Fabrica un IABVMCPServer. Si container es None, construye AppBootstrap."""

    if container is None:
        from iabv_v15.bootstrap import AppBootstrap
        container = AppBootstrap()
    return IABVMCPServer(container, name=name)


def main() -> None:
    """Entry point CLI: `python -m iabv_v15.infra.mcp.server`.

    Configurable vía variables de entorno:
      - IABV_MCP_TRANSPORT: stdio (default) | sse | streamable-http
      - IABV_MCP_NAME: nombre visible del server
      - IABV_WORKSPACE_ROOT: raíz del workspace para AppBootstrap
    """
    logging.basicConfig(
        level=os.environ.get("IABV_MCP_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    # Suppress noisy transport/access messages from the MCP SDK and uvicorn
    # in the subprocess — the main UI process already logs these.
    for noisy_logger in ('mcp', 'mcp.server', 'mcp.server.streamable_http',
                         'fastmcp', 'uvicorn', 'uvicorn.access', 'uvicorn.error'):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    # httpx/httpcore handled by shared suppress_noisy_http_loggers().
    from iabv_v15.infra.logging import suppress_noisy_http_loggers
    suppress_noisy_http_loggers()
    transport = os.environ.get("IABV_MCP_TRANSPORT", "stdio")
    name = os.environ.get("IABV_MCP_NAME", DEFAULT_SERVER_NAME)
    workspace_root = os.environ.get("IABV_WORKSPACE_ROOT")

    from iabv_v15.bootstrap import AppBootstrap
    container = AppBootstrap(workspace_root=workspace_root)
    server = IABVMCPServer(container, name=name)
    server.run(transport=transport)


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
