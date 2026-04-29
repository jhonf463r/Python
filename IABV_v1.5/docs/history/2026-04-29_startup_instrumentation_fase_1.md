# 2026-04-29 — Fase 1 / Fase 3: instrumentacion del startup + diferimiento del probe pesado

## Contexto
Handoff `2026-04-28_codex_live_audit_handoff.md`: la transicion **splash → shell** se queda 45–75s y a veces mas. MCP y bridge pueden estar vivos antes del shell, asi que `send_message` puede encolarse sin respuesta. Hay que medir por etapas reales antes de cualquier rediseño y, si hay evidencia, sacar peso del camino critico.

## Que cambio en este slice (PR de Fase 1 + minimo Fase 3)

### Fase 1 — instrumentacion sin cambios funcionales
- `src/iabv_v15/infra/startup_timeline.py`: nueva clase `StartupTimeline`, cheap y crash-safe. Cada `mark()` registra `phase`, `t_ms_from_start` (perf_counter), `rss_mb` y un `extra` opcional, en memoria + opcionalmente en `data/logs/startup_timeline.jsonl` (una linea JSON por hito). Se desactiva con `IABV_STARTUP_TIMELINE=0`.
- `bootstrap.py` enchufa la timeline global apenas se conoce `logs_dir` y emite hitos en cada transicion del camino real:
  - `bootstrap_init_start` (primera linea de `__init__`)
  - `bootstrap_init_done` (ultima linea de `__init__`, con `tool_availability_deferred=True/False`)
  - `run_start`
  - `splash_visible` (despues de `splash_app.processEvents()`)
  - `engine_load_main_qml_start` / `engine_load_main_qml_done`
  - `populate_ui_start` / `populate_ui_done` (dentro del `QTimer.singleShot(0, _populate_ui)`)
  - `main_window_shown`
  - `splash_set_ready`
  - `app_exec_about_to_start`
  - `deferred_post_window_setup_start` / `deferred_post_window_setup_done`

### Fase 3 — sacar peso del camino critico (cambio minimo)
La unica cosa que esta sesion movio del camino critico es `_log_tool_availability()`, que en `__init__`:
- corre probes HTTP (Devin / GitHub / Ollama) en paralelo (8 workers) y bloquea con `as_completed`,
- llama `auto_fix_missing_tools(...)`, que hace `pip install mcp_client` sincronicamente,
- corre `_startup_self_examination()` (no-op aqui porque `perception_cross_validator` aun no existe).

Mediciones pre-cambio en Linux frio (offscreen, `.venv` con PySide6 reciente):
- `IMPORT bootstrap`: ~1750 ms
- `AppBootstrap.__init__`: ~2170 ms
- de los cuales `_log_tool_availability()` ~700 ms en Linux con cache pip caliente

En Windows con miniconda + red lenta + pip frio el costo del probe es **mayor** (los logs vivos del usuario muestran `auto_install: mcp_client installed via pip (mcp)` en arranque y picos de RAM hasta ~8.4 GB cuando se anida con inferencia).

Cambio: el probe se programa via `QTimer.singleShot(2000, self._run_deferred_post_window_setup)` justo despues de `main_win.show()` + `splash.set_ready()`. La ventana renderiza primero y el probe corre 2 s despues, con la GUI ya interactiva.

Salvaguarda de retro-compat: `IABV_DEFER_TOOL_PROBE=0` restaura el camino sincronico viejo (lo usan tests que dependen del side-effect).

## Pruebas focalizadas
- `tests/test_startup_timeline.py` (8 tests): mark/JSONL/env-disable/singleton/log_dir-broken/reset/unicode.
- `tests/test_bootstrap_defer_tool_probe.py` (5 tests): probe diferido por defecto, sincronico con `IABV_DEFER_TOOL_PROBE=0`, idempotencia del deferred setup, hitos `bootstrap_init_start`/`done` registrados, JSONL persistido bajo `data/logs`.

`PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider tests/test_startup_timeline.py tests/test_bootstrap_defer_tool_probe.py -q` → **13 passed**.

Regresion en archivos del slice (mcp_bridge_toggle, specific_apikey_routing, cloud_quick_reply, startup_evolution, general_chat_llm_routing): mismas 13 fallas en main que con el cambio aplicado (verificado con `git stash`). Son **pre-existentes** y se documentan como UNRESOLVED, no introducidas por esta serie.

## Que NO toca este PR
- Fase 2 (handshake soberano shell/bridge/chat): pendiente, requiere primero la evidencia que produzca este JSONL en Windows.
- Fase 3 completa (provider scans, refresh UI no critico, auto-correction): solo movimos `_log_tool_availability`. El resto sigue UNRESOLVED hasta cruzar timeline + logs reales.
- Fase 4 (RAM en chat ligero): UNRESOLVED.
- Fase 5 (selector soberano unificado): planning-only, no se toca.

## Que tiene que correr el usuario en Windows para cerrar Fase 1
```powershell
cd C:\Python\IABV_v1.5
git pull --ff-only
scripts\start_iabv.ps1 -StartUI
```
Y despues mandar:
- `data/logs/startup_timeline.jsonl` (un line-JSON por hito)
- video o capturas de en que hito se ve el splash, en que hito ya esta el shell, y en que hito el primer chat respondio

Con eso se cruza contra los hitos del timeline y se identifica con precision cual etapa retiene el hilo principal. Solo entonces se cierra Fase 1 y se abre Fase 2 con el cambio correcto.

## Cable A (PR #258) — startup_timeline.jsonl → PortableContext + OSES

PR #258 cierra el cable A del marco de simbiosis: el JSONL deja de ser un log suelto.

### Que cambio
- `PortableContextService._startup_health_snapshot()` lee `data/logs/startup_timeline.jsonl`, detecta la **ultima corrida contigua** (boundary por `t_ms_from_start` no monotonico) y expone `init_ms`, `run_to_window_ms`, `deferred_ms`, `rss_mb_max`, `recent_blockers`, `last_started_at_utc`.
- `PortableContextService._startup_health_section()` agrega seccion `startup_health` al package portable. Sin JSONL → `confidence=0.0` + `UNRESOLVED:startup_timeline_missing`. Sin datos parseables → `UNRESOLVED:startup_timeline_empty`. **No inventa.**
- `OperationalSelfExaminationService._startup_health_findings()` emite `SelfExaminationFinding(category='startup_degradation')` por umbral cruzado. Hook en `_findings_loop` tras `_cloud_reasoning_findings`.
- Thresholds **publicos al tope del modulo** (greppables, sin entrar al metodo):
  ```python
  STARTUP_INIT_MS_DEGRADED = 4000.0
  STARTUP_RUN_TO_WINDOW_MS_DEGRADED = 8000.0
  STARTUP_DEFERRED_MS_DEGRADED = 5000.0
  ```
  `init_ms > 2*threshold` → severity HIGH; resto MEDIUM. Las constantes son los unicos puntos a tunear si la realidad Windows muestra otros umbrales.

### Reglas que respeta
- **Sin servicio nuevo** (lectura directa del JSONL en metodos privados de servicios existentes).
- **Sin memoria paralela** (la fuente es el JSONL ya producido por la instrumentacion).
- **Respeta P3** (PortableContext sigue siendo el unico generador del paquete portable).
- **Respeta P4** (OSES sigue siendo el unico emisor de findings).

### Pruebas
`tests/test_startup_health_cable.py` (11 tests, 11/11 verde) cubre:
- Snapshot: `no_log` / `no_data` / `analyzed`, fallback a `bootstrap_init_done` cuando falta `run_start`, blockers detectados.
- Section: confidence + items + UNRESOLVED.
- OSES: no log, healthy (sin findings), tres umbrales cruzados (3 findings), umbral parcial (1 finding).
- Verifica que los thresholds son constantes de modulo importables.

Regresion `tests/test_portable_context_service.py` + `tests/test_operational_self_examination_service.py`: 29/29 verde.

## D1-D7 — gaps reales abiertos del marco de simbiosis

Estos cables NO se tocaron en este slice. Siguen pendientes para Fase 5. **No abrir hasta que el arranque visible este estable.**

| # | Gap | Cable concreto |
|---|---|---|
| D1 | chat ligero → `DecisionAuditTrail` | en `control_center_viewmodel.sendChat`, despues de elegir ruta y obtener respuesta, llamar `decision_audit_trail.record(DecisionRecord(phase=PROVIDER_SELECTION, provider_id=..., outcome=..., latency_ms=..., user_goal=msg))`. Sin servicio nuevo. |
| D2 | chat ligero → `ExperimentLab` via `TaskOutcomeRecorder` | cada respuesta del chat alimenta un `RunRecord` minimal. Reusar el contrato existente. Asi `composite_recommendation` cubre la ruta del chat. |
| D3 | `LocalRoleRouter` consulta worker_pool antes de rutear | una linea: si `account_resource_scanner.estimate_available_workers().total_remaining_messages > 0`, considerar shadow paralelo cloud/web. Sin crear nada. |
| D4 | shadow learning formal | cuando el chat elige local, lanzar tambien una ruta web/api gratis y mandar ambas a `experiment_lab.run_experiment()` como candidatos del mismo `subject_key`. **BLOQUEADO** mientras el arranque siga inestable (decision del usuario). |
| D5 | `PortableContext.account_inventory` | `_account_inventory_snapshot()` llamando `estimate_available_workers()`. Cable A cierra el otro half (`startup_health`); este queda pendiente. |
| D6 | rotacion gobernada cruzando trends | `best_account_for_tool` ya rota por mensajes restantes; sumar tie-break por `decision_audit_trail.analyze_provider_trends()` (degradacion). 3 lineas. |
| D7 | OSES findings de startup_timeline | **CERRADO en PR #258.** |

Reglas duras al avanzar Fase 5:
- No crear servicio "simbiosis" nuevo. Todo va sobre las 8 piezas: ExperimentLab + StrategySelector + AdaptiveWeightLayer + TaskOutcomeRecorder + DecisionAuditTrail + PortableContext + account_resource_scanner + OSES.
- No memoria paralela. Persistir en repos existentes (`ExperimentLabRepository`, `decision_audit/decisions.jsonl`, `quota_tracker.json`, `portable_context/latest.json`).
- `WorldModelSnapshot` sigue como fuente viva; `account_inventory` se compone desde scanner, no se duplica.

## UNRESOLVED / honestos
1. La medicion en Linux offscreen no reproduce el bloqueo Windows-specifico (pythonw + miniconda + red lenta). Necesita evidencia real del usuario.
2. Las 13 pruebas pre-existentes rojas en `test_control_center_viewmodel.py` y derivados no son objetivo de este slice; quedan documentadas. Algunas indican `sqlite3.OperationalError: unable to open database file` cuando varios tests comparten state.
3. Aun queda por revisar si `WorldModelService.bootstrap_scan` (que hace probes propios) deberia tambien diferirse en el camino UI (linea 514 de `bootstrap.py`). UNRESOLVED hasta cruzar el timeline real.
4. `auto_install_bg: aider_coder queued for background install (aider-chat)` ya esta en background, asi que no es bloqueante; el unico install sincronico era `mcp_client` y hoy esta diferido.
