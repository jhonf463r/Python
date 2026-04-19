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

Contratos que NO se rompen:
  - No decide rutas: sólo expone servicios existentes.
  - Respeta AutonomyGovernancePolicy: gates activos siguen bloqueando.
  - No crea otro cerebro; es un adaptador delgado sobre bootstrap.
  - No modifica datos de usuario; sólo lectura salvo chatgpt_web_capture y
    site_exploration_explore (ambos ya son servicios escritores legítimos).
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from typing import Any

from iabv_v15.infra.mcp import audit_tools

logger = logging.getLogger(__name__)


DEFAULT_SERVER_NAME = "iabv-v15"
SUPPORTED_TRANSPORTS = {"stdio", "sse", "streamable-http"}


def _to_jsonable(value: Any) -> Any:
    """Convierte dataclasses, pydantic models y contenedores anidados a JSON."""

    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
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
            mcp = FastMCP(name)
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
            return _to_jsonable(snapshot) or {}

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
            result = svc.explore(
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
            package = svc.current_package(refresh=bool(refresh), max_age_seconds=int(max_age_seconds))
            return _to_jsonable(package) or {}

        @mcp.tool()
        def self_examination_current(refresh: bool = False) -> dict[str, Any]:
            """Retorna el SelfExaminationSnapshot operativo actual.

            Incluye patrones repetidos, degradaciones detectadas y ajustes
            recomendados por `OperationalSelfExaminationService`.
            """
            svc = self._self_examination_service()
            review = svc.current_review(refresh=bool(refresh))
            summary = svc.review_summary(review)
            return {"review": _to_jsonable(review), "summary": _to_jsonable(summary)}

        @mcp.tool()
        def chatgpt_web_capture(
            prompt_text: str,
            launch_target: str = "https://chatgpt.com/",
            response_wait_seconds: float = 45.0,
            reingest_only: bool = False,
            browser_profile_dir: str | None = None,
            browser_headless: bool = False,
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
                browser_headless: si True, corre sin ventana visible.
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
            result = runner._capture_browser_dom_response(
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

    # ------------------------------------------------------------------
    # Ciclo de vida

    def run(self, transport: str = "stdio") -> None:
        if transport not in SUPPORTED_TRANSPORTS:
            raise ValueError(f"transport '{transport}' no soportado. Usa {sorted(SUPPORTED_TRANSPORTS)}")
        logger.info("IABV MCP server starting (transport=%s, name=%s)", transport, self.name)
        self.mcp.run(transport=transport)


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
    transport = os.environ.get("IABV_MCP_TRANSPORT", "stdio")
    name = os.environ.get("IABV_MCP_NAME", DEFAULT_SERVER_NAME)
    workspace_root = os.environ.get("IABV_WORKSPACE_ROOT")

    from iabv_v15.bootstrap import AppBootstrap
    container = AppBootstrap(workspace_root=workspace_root)
    server = IABVMCPServer(container, name=name)
    server.run(transport=transport)


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
