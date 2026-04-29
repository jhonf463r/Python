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

## UNRESOLVED / honestos
1. La medicion en Linux offscreen no reproduce el bloqueo Windows-specifico (pythonw + miniconda + red lenta). Necesita evidencia real del usuario.
2. Las 13 pruebas pre-existentes rojas en `test_control_center_viewmodel.py` y derivados no son objetivo de este slice; quedan documentadas. Algunas indican `sqlite3.OperationalError: unable to open database file` cuando varios tests comparten state.
3. Aun queda por revisar si `WorldModelService.bootstrap_scan` (que hace probes propios) deberia tambien diferirse en el camino UI (linea 514 de `bootstrap.py`). UNRESOLVED hasta cruzar el timeline real.
4. `auto_install_bg: aider_coder queued for background install (aider-chat)` ya esta en background, asi que no es bloqueante; el unico install sincronico era `mcp_client` y hoy esta diferido.
