# IABV v1.5 — Log de Decisiones

**Actualizado:** 2026-05-03

---

## Decisiones de esta sesión (2026-05-03, Devin)

### D-2026-05-03-001: Crear capa de trazabilidad interna como docs/governance/
- **Razón:** El repositorio carecía de una fuente de verdad viva que permitiera a cualquier IA entrar, leer el estado actual y seguir trabajando sin depender del historial completo del chat.
- **Módulos afectados:** docs/ (nuevo directorio)
- **Estado:** Implementado
- **Riesgo:** Ninguno — es documentación, no toca código ejecutable

### D-2026-05-03-002: No implementar AutonomyCycleService todavía
- **Razón:** El archivo no existe en el source tree (UNRESOLVED U1). Antes de crearlo hay que confirmar si fue descartado intencionalmente o si fue mergeado en otra rama. El código disperso en OSES y TOR sigue funcionando con fallback inline.
- **Módulos afectados:** Ninguno (decisión de no-cambio)
- **Estado:** Aceptado
- **Riesgo:** Bajo — el código disperso funciona, solo es deuda de organización

### D-2026-05-03-003: Implementar ControlCenterVM lazy init (Fase 1)
- **Razón:** `__init__` bloqueaba el main thread ~3733ms. Heavy I/O (PBT load, goal context, repo bridge, local stack) movido a `_bg_pool.submit(_bg_initial_refresh)`. Resultado aplicado en main thread via `taskResolved` signal con task name `_initial_refresh`. `QTimer.singleShot(0)` reemplaza `QTimer.singleShot(250)` para deferred inmediato. Refresh de UI (progress cards, evolution snapshot, agent cards, provider health) encadenado en `_apply_task_result`.
- **Módulos afectados:** `control_center_viewmodel.py` (3 edits: __init__ deferred, new methods, _apply_task_result handler)
- **Estado:** Implementado y verificado (2391 passed / 29 failed / 25 skipped — 0 regresiones)
- **Riesgo:** Bajo — cambio local al VM, no afecta servicios ni contratos

### D-2026-05-03-006: Documentar evidencia exhaustiva de búsqueda para U1
- **Razón:** Usuario pidió trazabilidad exacta de qué se buscó y dónde para AutonomyCycleService. Se documentó: grep en src/, tests/, bootstrap, domain/models, git history. Todo arrojó 0 resultados.
- **Módulos afectados:** `docs/governance/UNRESOLVED_REGISTRY.md`
- **Estado:** Implementado
- **Riesgo:** Ninguno

### D-2026-05-03-007: Crear nota de reconciliación de inventario
- **Razón:** Usuario reportó que los conteos entre reportes no coincidían. Se aclaró que miden dimensiones distintas (tests vs archivos vs backlog vs UNRESOLVED). No hubo lectura parcial ni snapshot distinto.
- **Módulos afectados:** `docs/governance/INVENTORY_RECONCILIATION.md` (nuevo)
- **Estado:** Implementado
- **Riesgo:** Ninguno

### D-2026-05-03-008: Fase 2 — Quota tracker wiring en ATO
- **Razón:** `record_message_sent(tool, email)` existía en `account_resource_scanner.py` pero nunca era invocado. Sin esto, el quota tracker no aprende y el selector sigue usando workers agotados.
- **Cambio:** Agregados `_record_quota_usage()` y `_record_quota_usage_for_candidate()` en `AdaptiveTaskOrchestrator`. Se llaman antes de cada `plan_or_execute()` (govern_adaptive_payload y parallel comparison). Extraen `tool` de `governance.assistant_kind` y `email` de `worker_gate.top_worker`. Envueltos en try/except.
- **Módulos afectados:** `adaptive_task_orchestrator.py`
- **Estado:** Implementado y verificado (0 regresiones)
- **Riesgo:** Bajo — try/except impide que fallo de I/O rompa la sesión

### D-2026-05-03-009: Fase 3 — worker_pool_snapshot en WorldModelSnapshot
- **Razón:** Sin el pool de workers en el snapshot, `AutonomyGovernancePolicy` no puede tomar decisiones de ruta basadas en cuota disponible sin consultar el scanner ad-hoc desde el Orchestrator.
- **Cambio:** Campo `worker_pool_snapshot: dict = {}` agregado a `WorldModelSnapshot` en `domain/models.py`. Método `_estimate_worker_pool(timeout_s=2.0)` en `world_model_service.py` usa `ThreadPoolExecutor` con timeout para no bloquear el ciclo de monitoreo. Solo se ejecuta en scans `full`.
- **Módulos afectados:** `domain/models.py`, `world_model_service.py`
- **Estado:** Implementado y verificado (0 regresiones)
- **Riesgo:** Medio — agrega I/O al ciclo full, pero con timeout de 2s

### D-2026-05-03-010: Prompt de auditoría real para laptop
- **Razón:** El usuario necesita un prompt listo para que Windsurf/Codex audite los cambios en el entorno Windows real donde corre el programa.
- **Módulos afectados:** `docs/governance/AUDIT_PROMPT_LAPTOP.md` (nuevo)
- **Estado:** Implementado
- **Riesgo:** Ninguno

### D-2026-05-03-004: Actualizar Control Master con estado de tests y sesión actual
- **Razón:** El Control Master estaba desactualizado desde 2026-04-19 (2 semanas). Los objetivos, tests y decisiones no reflejaban el trabajo reciente.
- **Módulos afectados:** data/evolution/control_master/
- **Estado:** Implementado
- **Riesgo:** Ninguno — es actualización de estado, no de código

### D-2026-05-03-005: Integrar IABV_MASTER_DOC_v1.md al repo
- **Razón:** Documento valioso que consolida estado, visión, backlog y plan. Sin él, futuras sesiones perderían contexto. Debe vivir versionado dentro del repo.
- **Módulos afectados:** docs/
- **Estado:** Implementado
- **Riesgo:** Ninguno

## Decisiones de continuacion (2026-05-04, Devin)

### D-2026-05-04-011: DashboardVM lazy init
- **Razon:** Windsurf audit (PR #307) identifico que `DashboardViewModel.refresh()` bloqueaba el main thread ~51s post-arranque. El patron es identico al ya corregido en ControlCenterVM (Fase 1).
- **Cambio:** `refresh()` ahora submit a `_bg_pool` (ThreadPoolExecutor). I/O (`list_recent()`, `describe_index()`) corre en background. Resultado aplicado via `refreshResolved` signal + `_apply_refresh()` en main thread. Signal `refreshResolved = Signal(object)` agregado.
- **Modulos afectados:** `dashboard_viewmodel.py`
- **Estado:** Implementado y verificado (2489 passed / 24 failed / 23 skipped — 0 regresiones)
- **Riesgo:** Bajo — cambio local al VM

### D-2026-05-04-012: Crear ui_visibility_audit.py
- **Razon:** Usuario pidio modulo de auditoria de experiencia visible: captura de popups, dialogs, errores FileNotFound, notificaciones y eventos inesperados de Windows. Windsurf lo creo localmente pero no lo versionno.
- **Cambio:** Modulo nuevo en `src/iabv_v15/infra/ui_visibility_audit.py`. Incluye VisibilityAuditLog (singleton, JSONL append-only), Win32PopupWatcher (daemon thread), SplashAuditAdapter, SubprocessAuditWrapper. Distingue CAT_INTENTIONAL / CAT_UNEXPECTED / CAT_BACKGROUND.
- **Modulos afectados:** `infra/ui_visibility_audit.py` (nuevo), `tests/test_ui_visibility_audit.py` (nuevo)
- **Estado:** Implementado, 9 tests pasan. Integracion en bootstrap pendiente para Windows.
- **Riesgo:** Bajo — es modulo pasivo, no interfiere con runtime

### D-2026-05-04-013: Reescribir AUDIT_PROMPT_LAPTOP.md con prompts segmentados
- **Razon:** Auditoria anterior de Windsurf se hizo con un solo prompt largo. Segmentar en 5 prompts independientes (arranque, quota, world model, ui audit, tests) permite re-auditar piezas individuales sin repetir todo.
- **Modulos afectados:** `docs/governance/AUDIT_PROMPT_LAPTOP.md`
- **Estado:** Implementado
- **Riesgo:** Ninguno

## Decisiones de continuacion (2026-04-23, Devin)

### D-2026-04-23-014: Win32PopupWatcher categorization fix
- **Razon:** Windsurf detecto en validacion que todas las ventanas no-IABV se categorizaban como CAT_UNEXPECTED, incluyendo Shell_TrayWnd, Progman, DummyDWMListenerWindow. La logica ignoraba la lista de clases benignas.
- **Cambio:** Agregados `_KNOWN_BENIGN_CLASSES` (14 clases), `_is_suspicious()` (patrones de titulo sospechoso), y logica de categorizacion: benigna → CAT_BACKGROUND; sospechosa → CAT_UNEXPECTED + unresolved; desconocida → CAT_UNEXPECTED sin unresolved.
- **Modulos afectados:** `infra/ui_visibility_audit.py`
- **Estado:** Implementado, 2 tests nuevos
- **Riesgo:** Bajo — logica solo afecta clasificacion de eventos

### D-2026-04-23-015: QmlDialogAuditBridge
- **Razon:** Los dialogs QML (CredentialPromptDialog, ClarificationDialog, MissingDependencyDialog) se abrian sin dejar registro en ui_visibility_audit. La cadena era: Python VM emite signal → QML Connections abre dialog → usuario ve dialog → pero auditoria no lo sabe.
- **Cambio:** `QmlDialogAuditBridge` conecta a los signals de los ViewModels y registra `dialog_shown` con nombre, VM origen, y payload (passwords redactadas via `_safe_serialize()`). `record_dialog_closed()` disponible para cierre. `_DIALOG_SIGNAL_MAP` mapea signal names a dialog info.
- **Modulos afectados:** `infra/ui_visibility_audit.py` (nuevo bridge), `tests/test_ui_visibility_audit.py`
- **Estado:** Implementado, 7 tests nuevos. Wiring en bootstrap pendiente.
- **Riesgo:** Bajo — solo observa signals, no los modifica

### D-2026-04-23-016: ToastAuditAdapter
- **Razon:** `WinToastBridge.notify()` enviaba toasts sin registrar en auditoria visible. El usuario ve un toast pero la auditoria no lo sabe.
- **Cambio:** `ToastAuditAdapter` monkey-patches `_notify_winotify()` y `_notify_balloon()` para registrar `toast_shown` automaticamente. Idempotente (double-install safe). Registra backend, icon, success.
- **Modulos afectados:** `infra/ui_visibility_audit.py` (nuevo adapter), `tests/test_ui_visibility_audit.py`
- **Estado:** Implementado, 5 tests nuevos. Wiring en bootstrap pendiente.
- **Riesgo:** Bajo — monkey-patch preserva original en closure

### D-2026-04-23-017: GAP C — ui_visibility_audit → WorldModel.detected_blocks
- **Razon:** Los eventos de auditoria visible (popups inesperados, FileNotFoundError, dialogs sin resolver) no influian en la lista canonica de bloqueos operativos del WorldModel. El orquestador tomaba decisiones sin saber que habia un popup bloqueante o un archivo faltante.
- **Cambio:** Nuevo parametro `ui_visibility_audit_log` en `WorldModelService.__init__()`. Nuevo metodo `_ui_audit_blocks()` que extrae bloques de `audit.summary()['unresolved']`, `['file_not_found']` y popups unexpected. Se insertan antes del corte de 18 items en `_detected_blocks()`.
- **Modulos afectados:** `services/evolution/world_model_service.py`, `tests/test_ui_visibility_audit.py`
- **Estado:** Implementado, 5 tests nuevos
- **Riesgo:** Bajo — inyeccion aditiva, no modifica bloques existentes

### D-2026-04-23-018: GAP D — audit snapshot → ATO perception context
- **Razon:** El contexto de percepcion del ATO (PerceptionSnapshot.live_audit) no incluia la auditoria visible. El orquestador no sabia que el usuario estaba viendo un popup, un toast o un error de archivo.
- **Cambio:** Nuevo parametro `ui_visibility_audit_log` en `TaskContextAssembler.__init__()`. Nuevo metodo `_ui_visibility_snapshot()` que genera resumen compacto (total_events, by_category, unresolved_count, has_unexpected). Se inyecta en `live_audit['ui_visibility']` dentro de `build_perception_snapshot()`.
- **Modulos afectados:** `services/adaptive/task_context_assembler.py`, `tests/test_ui_visibility_audit.py`
- **Estado:** Implementado, 3 tests nuevos
- **Riesgo:** Bajo — enriquece live_audit sin modificar campos existentes

### D-2026-04-23-019: SLICE 1+2 — Runtime wiring en bootstrap.py
- **Razon:** GAP C y GAP D estaban implementados como logica pero sin wiring real. `WorldModelService` y `TaskContextAssembler` no recibian la instancia de `VisibilityAuditLog`, y los bridges QML/toast no estaban instalados en runtime.
- **Cambio:** (1) `bootstrap.py` importa `get_audit_log()` y pasa el singleton a ambos servicios. (2) Nuevo metodo `_wire_ui_audit_bridges()` instala `QmlDialogAuditBridge` en ambos VMs y `ToastAuditAdapter` en WinToastBridge, con fallback seguro (try/except + logger). El singleton es el mismo en todos los consumers.
- **Modulos afectados:** `bootstrap.py`, `tests/test_ui_visibility_audit.py`
- **Estado:** Implementado, 5 tests nuevos de runtime wiring
- **Riesgo:** Bajo — fallback seguro, no rompe bootstrap si audit no disponible

### D-2026-04-23-020: Dialog close tracking — UNRESOLVED U2
- **Razon:** `record_dialog_closed()` existe en `QmlDialogAuditBridge` pero no hay Python-side @Slot que QML pueda llamar al cerrar un dialog. Los dialogs se abren via Python signal (credentialPromptRequested, etc.) pero se cierran en QML (InlineCredentialPrompt.qml credentialSubmitted signal) sin callback Python.
- **Cambio:** Ninguno — marcado como UNRESOLVED U2. Requiere agregar @Slot en ControlCenterVM.
- **Modulos afectados:** Ninguno (decision de no-cambio)
- **Estado:** UNRESOLVED U2
- **Riesgo:** Bajo — los dialog open events SI se capturan; solo falta el close event

---

## Decisiones historicas relevantes

| Fecha | Decisión | Agente |
|---|---|---|
| 2026-04-19 | Sembrar 37 reglas desde AGENTS.md al Control Master | Codex |
| 2026-04-19 | Crear 4 objetivos de super sincronía | Codex |
| 2026-04-22 | Capa 2: LocalCliToolAdapter + ToolCards | Devin |
| 2026-04-22 | Capa 2.1: inject $HOME/.iabv/tools/* into MCP bridge PATH | Devin |
| 2026-04-22 | Capa 2.2: proactive token rotation detector | Devin |
| 2026-04-30 | PR #307: Architecture Report V5, propuesta de AutonomyCycleService | Devin/Windsurf |
