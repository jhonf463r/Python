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

---

## Decisiones históricas relevantes

| Fecha | Decisión | Agente |
|---|---|---|
| 2026-04-19 | Sembrar 37 reglas desde AGENTS.md al Control Master | Codex |
| 2026-04-19 | Crear 4 objetivos de super sincronía | Codex |
| 2026-04-22 | Capa 2: LocalCliToolAdapter + ToolCards | Devin |
| 2026-04-22 | Capa 2.1: inject $HOME/.iabv/tools/* into MCP bridge PATH | Devin |
| 2026-04-22 | Capa 2.2: proactive token rotation detector | Devin |
| 2026-04-30 | PR #307: Architecture Report V5, propuesta de AutonomyCycleService | Devin/Windsurf |
