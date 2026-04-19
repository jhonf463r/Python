# Auditoria humana / IA - 2026-04-19

> Este archivo es parte del **area de pendientes maestra**. Codex, ChatGPT, Devin,
> Claude o cualquier IA que tome una sesion de IABV v1.5 debe leer esto despues
> de `AGENTS.md`, `self_examination/latest.md` y `portable_context/latest.md`.
> La version viva siempre es la del ultimo archivo `human-audit-YYYY-MM-DD.md`
> de este directorio.

**Sesion:** Devin (devin-24c8eff425584b9498bbb008b18cd3aa)
**VM:** Linux (ubuntu-22.04) | **App real:** Windows
**Alcance cubierto:** backend Python + servicios reales ejercitados en REPL
**Alcance no cubierto:** UI PySide6/QML en Windows (requiere la maquina real del usuario)

---

## Servicios ejercitados con evidencia real

| Servicio | Contrato observado | Estado | Evidencia |
|---|---|---|---|
| `CredentialBroker` | `needs`, `request`, `accept`, `get` | OK | `needs('chatgpt.com')=True -> request -> accept(user=..., secret=...) -> needs=False -> get() devuelve `CredentialRecord`` |
| `SecretVault` (como deps del broker) | `__init__(path)` | OK | Construido como `secret_vault=SecretVault(tmp)` sin error |
| `ClarificationRequestService` | `register_prompt_handler(cb)`, `ask(question, options, context, timeout_s)`, `resolve(request_id, response)`, `pending_ids()`, `cancel()` | OK | Handler recibe payload `{id,question,options,context}`. `ask()` bloquea hasta `resolve()`. Timeout emite `ClarificationTimeoutError`. Probado con approve ("Autorizo") y con timeout |
| `WorldModelService` | `current_model()`, `scan_now()`, `request_refresh()`, `grant_observation_permission()`, `permission_snapshot()` | OK en Linux (parcial) | Snapshot construido, `observation_sources=['environment_self_model','network_probe']`. `active_windows=0` y `tool_live_status=[]` porque no hay ventanas Windows -> `unresolved_fields=['UNRESOLVED:focused_window']` | 
| `SiteExplorationService.explore` | `is_available`, `explore(start_url, max_pages, priority_keywords)` | OK | Real crawl contra `https://www.python.org/` con `max_pages=4` devolvio 4 paginas con titles, headings, 21 links internos cada una, 1 form. `execution_ms=1538`. Priority keywords `['downloads','doc']` reordenaron correctamente (primero `/doc/av`, `/doc/`, `/downloads/android/`) |
| `SiteManualRepository.save` | `save(manual) -> (json_path, md_path)` | OK | Persiste `<hostname>.json` y `<hostname>.md` en el root. Verificado contra `www.python.org` |
| Reingest+clipboard de `UIExecutionRunner` | bug de PR #13 | FIX + TESTS | Ver PR #21 |

Unit tests ejercitados en la VM Linux:

```
PYTHONPATH=src python -m pytest tests/test_ui_execution_runner.py tests/test_tool_adapters.py tests/test_adaptive_task_orchestrator.py -q
# 56 passed, 1 pre-existing fail (test_external_assistant_adapter_resolves_wildcard_candidate_path,
# glob Windows-only, identico en main)
```

---

## Hallazgos nuevos

### 1. BUG (RESUELTO por PR #21) - `ui_execution_runner.py:186` no respetaba `reingest_only` en el path clipboard

- **Donde:** `src/iabv_v15/services/tools/ui_execution_runner.py` linea 186 (pre-fix).
- **Sintoma:** cuando `browser_dom_capture_pending` obligaba a caer al fallback clipboard y la orquestacion pedia `reingest_only=True` (retry tras `SESSION_EXPIRED`), `capture_response_from_app` igual pegaba el prompt sobre la ventana enfocada. El `Ctrl+A/Ctrl+C` posterior leia el prompt y no la respuesta del asistente. El modo reingest quedaba inutil en ese branch.
- **Causa raiz:** el guard `and not reingest_only` existia en el path `browser_dom` (linea 777) pero no en el path clipboard.
- **Fix:** PR #21 (https://github.com/jhonf463r/Python/pull/21) agrega el guard + 2 regresiones (`test_ui_execution_runner_skips_paste_in_clipboard_reingest_only`, `test_ui_execution_runner_still_pastes_prompt_when_not_reingesting`).
- **Status pending_issue:** resolviendose en PR abierto.

### 2. CONTEXT (NO ES BUG) - En Linux el WorldModel no observa ventanas/asistentes

- `WorldModelService` en Linux VM produce `active_windows=0`, `tool_live_status=[]`, `permission_gates=[]`. Esto es correcto: `_load_user32()` solo carga Win32 y las tools instaladas (ChatGPT.exe / Codex.exe) no existen en Linux.
- `grant_observation_permission` persiste correctamente en `self._observation_permissions` (verificado via `permission_snapshot()`), pero el gate solo aparece en `snapshot.permission_gates` si hay un `tool_live_status` con `permission_state != 'no_requerido'`. En Linux no lo hay.
- **No requiere fix.** Documentado aqui para que futuras IAs no lo confundan con regresion.

### 3. PENDIENTE - Flujo `chatgpt_web_assisted` contra chatgpt.com real

- **Estado:** no ejercitado en esta sesion. Requiere credenciales de una cuenta ChatGPT web.
- **Proximo paso:** el usuario fue consultado con 3-option secret request (temporal / permanente / skip). Si provee, se ejecutara `ExternalAssistantToolAdapter` con `browser_dom_capture` (Playwright + Chromium ya instalados en la VM Linux).
- **UNRESOLVED hasta entonces.**

### 4. PENDIENTE - Validacion Windows real de PRs #12, #13, #15, #16, #18, #21

Todos los PRs mergeados + el PR #21 abierto tienen checklists explicitas que solo el usuario puede validar en su Windows real. La lista consolidada:

- PR #12: popup de credenciales aparece cuando ChatGPT/Codex pide login.
- PR #13: retry tras 5min re-ingesta el DOM ya existente sin re-pegar el prompt.
- PR #15: governance con `permission_gate=requerido` emite popup de clarificacion y respuesta "No, autorizo" queda negado.
- PR #16: chat local `"explora https://python.org max_pages=3"` genera `data/evolution/site_manuals/www.python.org.md`. (Verificado en Linux con Playwright headless - la integracion funciona; falta solo el trigger via ToolCallingBridge).
- PR #18: "No, autorizo" NO autoriza (verificado por unit test). `http://localhost:8080/` conserva el port al normalizar (verificado por unit test).
- PR #21: este. reingest_only ya no contamina el clipboard capture.

### 5. DEUDA DE RENDIMIENTO DE PRUEBAS (no regresion)

`AGENTS.md` ya lo documenta: "Varias suites de UI siguen siendo lentas en Windows; no es una falla funcional, pero si una deuda de rendimiento de pruebas." Mantengo la nota para continuidad.

---

## Infraestructura instalada en la VM Linux (reproducible en futuras sesiones Devin)

- `ollama` (install oficial `curl -fsSL https://ollama.com/install.sh | sh`; requiere `sudo apt-get install zstd` en Ubuntu 22.04). Modelo `qwen2.5:3b` descargado (~1.9GB). Listo para ejercitar chat local via `LocalRoleRouter`.
- `playwright` + Chromium headless (`pip install playwright && python -m playwright install chromium`). Verificado: `SiteExplorationService.is_available()=True`, crawl real OK.
- `pytest pydantic httpx Pillow` via `pip install --quiet`. Agregado a `env.maintenance` en env-config propuesto.

---

## Master control - que falta para cerrar la auditoria humana end-to-end

- [ ] **User:** revisar y aprobar PR #21 (fix reingest_only+clipboard).
- [ ] **User:** decidir 3-option secret para ChatGPT web (temporal / permanente / skip). Sin esto no puedo validar el chatgpt_web_assisted real.
- [ ] **Devin** (al recibir credenciales): ejecutar `ExternalAssistantToolAdapter` contra chatgpt.com con Playwright, capturar DOM real, actualizar este audit.
- [ ] **User** en Windows: validar los checklists de PRs #12, #13, #15, #16, #18, #21 (solo ahi se puede; en Linux esta hecho todo lo backend).
- [ ] **User** en Windows: correr `C:\Users\faber\miniconda3\python.exe -m pytest -p no:cacheprovider tests/ -q` con `PYTHONPATH=C:\Python\IABV_v1.5\src` una vez los 5 PRs esten en `main` para confirmar la bateria completa.

---

## Como consumir este archivo

- **Codex / ChatGPT / Claude / Devin** que tomen una sesion nueva: leer este archivo despues de `AGENTS.md`. Es complemento de `self_examination/latest.md`, no reemplazo.
- Si se genera una auditoria humana posterior, agregar un nuevo archivo `human-audit-YYYY-MM-DD.md` al mismo folder y dejar este archivo como historial.
- Si se cierra un pendiente de la seccion "Master control", **marcarlo** aqui en vez de borrarlo, para preservar trazabilidad.
