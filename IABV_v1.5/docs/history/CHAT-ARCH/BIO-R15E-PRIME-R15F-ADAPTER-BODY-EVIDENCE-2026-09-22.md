# BIO-R15E′ + R15F — evidencia y resultado

## 1. PROVENANCE

- Repository: `jhonf463r/Python`; ejecución bajo `IABV_v1.5/`.
- Base exacta: `23f17bd2a1895fe12412f20884951cc0b5ccebfa`.
- Fuente histórica R15E: branch `codex/bio-r15e-toolfcard-adapter-runtime-2026-09-22`, commit `7093802c141e46cecba2cebbb44d6ab966538d7d`, parent igual a la base; tree `1dc1b26aa996e9cb01447441f137739e067a68b3`.
- Harness R15E comprobado en esa revisión: `IABV_v1.5/tests/experiments/test_bio_r15e_learned_preference_to_toolcard_adapter.py`, blob `463c8b0b9bf00488948d4d3cf4ef8e2b9bf9e6e1`.
- R15E′ implementation: `IABV_v1.5/tests/experiments/test_bio_r15e_prime_to_r15f_adapter_body_runtime.py`, SHA-256 `9f9ecc423cd1bb3c4aea4df610a73152841ab8e3f9b7e8c83d8ff3a29683e729`.
- Artefactos fuente R15E verificados: evidence `IABV_v1.5/docs/history/CHAT-ARCH/BIO-R15E-TOOLCARD-ADAPTER-EVIDENCE-2026-09-22.md` (blob `dc9b4f6ad5ca163737d078b3da0b3f2972637c1c`); stdout (blob `5b860c788da9d05706f60678f39a6f68556587bd`); manifest (blob `1ac73dfd33752015adc1e2844a9eb9525ac8bf2b`).
- R15E′/R15F worktree/branch: `C:\Users\faber\.codex\worktrees\bio-r15e-prime-r15f-adapter-body-runtime\Python`, `codex/bio-r15e-prime-r15f-adapter-body-runtime-2026-09-22`, iniciado en la base indicada.

## 2. R15E′ FIXTURE

La ruta real de R15E′ se ejecutó una vez para la condición control: recomendación `chatgpt` (score `0.964`), preferencia y governance `chatgpt`, `ToolTask.tool_id=chatgpt_web_assisted`, `ToolCard.tool_id=chatgpt_web_assisted`, adapter key `external_assistant`, y predicado real de disponibilidad observado `true`. El predicado no prueba capacidad externa efectiva.

- Fixture root: `IABV_v1.5/docs/history/CHAT-ARCH/BIO-R15E-PRIME-RUNTIME-2026-09-22/control/`.
- SQLite: `control/app.sqlite`; final closed-file SHA-256 `9555ea72813766644d1f25b0d7c0fb64c0ce1a15edc2d2d7e6d6cf42e9ba653a`. The in-process pre-close digest in initial `fixture.json` was superseded after SQLite closed; this final digest is from the preserved file.
- Task JSON recuperado por el repository: `control/tool_teaching/tasks/8c1413f6-e3ce-46dc-9cd1-4da2ae4a94d3.json`; SHA-256 `aa4d924a2bd891be1dc3ce73a73e3cf894a29cf228801308bc42e411110f628c`.
- Identidad: task `8c1413f6-e3ce-46dc-9cd1-4da2ae4a94d3`; tool `chatgpt_web_assisted`; `execution_scope=read_only`; `sandbox_first=true`; `approval_decision=pending`; `ToolTask.status=pending`.
- La serialización JSON completa (`model_dump(mode='json')`), todos los actions/rollback_actions/metadata, tarjeta completa con metadata, configuracion del adapter, rutas de artifacts y huellas están en `control/fixture.json`; la tarjeta persistida completa también está en `control/tool_teaching/cards/chatgpt_web_assisted.json`.
- El directorio conserva `app.sqlite`, cards, task, results, logs, interaction results y artefactos de persistencia producidos por la ruta. El digest anterior corresponde al SQLite cerrado; no se eliminó el runtime.

## 3. R15F RUNTIME OBSERVATION

R15E′ produjo `ToolResult.execution_state.state=waiting_approval`, `approval_required=true` y `approval_decision=pending`. Sin embargo, el objeto recuperado mediante `ToolRecordRepository.get_task(task_id)` tiene `ToolTask.status=pending`, no `waiting_approval`. Son campos/objetos distintos: no se promovió el estado del resultado a estado del task.

El cuerpo real de `ExternalAssistantToolAdapter.run()` fue observado durante la fase R15E′ con `sandbox=true` (call y return monotónicos/UTC), como parte de la sandbox de producción. No se observó invocación con `sandbox=false`. Debido al incumplimiento de la precondición literal de fase A, no se llamó a `execute_task(task, approved=True, launch_dry_run=False)`; no se cambió manualmente aprobación/status. El runner seguro recibió cero llamadas.

## 4. FIRST BROKEN EDGE

`sandbox completion → persisted ToolTask.status=waiting_approval` está abierto: el resultado queda `waiting_approval` pero el task persistido queda `pending`. Es la primera condición exigida que no se cumplió; R15F se detuvo aquí sin diagnosticar bordes posteriores.

## 5. CAUSAL CLASSIFICATION

Global: `OPEN`. R15E′ source → fixture fue causado por la ejecución del harness; la lectura del task/card/result persistidos fue observada. Approval → approved, approved → execute_task, `execute_task` → `ExternalAssistantToolAdapter.run(sandbox=False)` y adapter → runner no fueron invocados.

| Edge | State | Evidence |
|---|---|---|
| R15E′ source → fixture | CAUSED | Una ejecución creó el workspace persistente aislado. |
| fixture → persisted ToolTask | OBSERVED | `tasks/<task_id>.json`, SQLite y `fixture.json`; serialización íntegra. |
| persisted ToolTask → repository read | OBSERVED | `get_task(task_id)` devuelve el task persistido; status `pending`. |
| pending approval → approved | DEFINED | Rama real `execute_task(approved=True)` presente; no invocada. |
| approved → execute_task | DEFINED | Continuación real está definida; precondición de fase A no satisfecha. |
| execute_task → resolved ToolCard | OBSERVED | La ejecución R15E′ resolvió la tarjeta ChatGPT real. |
| execute_task → ExternalAssistantToolAdapter.run(sandbox=False) | DEFINED | Rama estática; invocación non-sandbox no observada. |
| adapter body → runner | DEFINED | Inyección segura configurada; runner calls = 0. |

## 6. WHAT IS PROVEN

Solo para esta corrida aislada: la ruta R15E′ real seleccionó la recomendación ChatGPT, construyó y persistió el task/card, ejecutó la rama sandbox del cuerpo real del adapter y generó un `ToolResult` cuyo execution state es `waiting_approval`. También se demostró que el Task persistido no recibe ese status.

## 7. WHAT IS NOT PROVEN

No se probó approval transition, `execute_task(... approved=True)`, llamada `ExternalAssistantToolAdapter.run(sandbox=False)`, runner handoff, lanzamiento, entrega del prompt, respuesta, captura, verificación, aprendizaje, efecto externo, development ni evolution. El test de disponibilidad solo observó el booleano del predicado.

## 8. NEGATIVE KNOWLEDGE

Se conserva: adapter non-sandbox ≠ lanzamiento externo; runner invocation ≠ entrega de prompt; entrega ≠ respuesta; captura ≠ respuesta verificada; respuesta verificada ≠ aprendizaje causal; aprendizaje ≠ nueva capacidad; capacidad ≠ development; development ≠ evolution. Todos: `NOT_PROVEN`. ΔK: evidencia nueva de discrepancia `ToolResult.execution_state` vs `ToolTask.status`. Δπ: ninguno. ΔB: ninguno (sin cambio productivo). ΔY: ningún resultado externo.

## 9. ARTIFACTS

- Harness R15E′/R15F: `IABV_v1.5/tests/experiments/test_bio_r15e_prime_to_r15f_adapter_body_runtime.py`.
- Fixture runtime completo: `IABV_v1.5/docs/history/CHAT-ARCH/BIO-R15E-PRIME-RUNTIME-2026-09-22/control/`.
- stdout de lectura de evidencia (report-only), no stdout original íntegro de la corrida R15E′: `BIO-R15E-PRIME-R15F-ADAPTER-BODY-STDOUT-2026-09-22.txt`.
- El stdout inicial de R15E′ no se redirigió a archivo durante esa ejecución. No se puede afirmar preservación byte-a-byte de ese stdout; el registro completo del fixture sí está preservado en JSON/SQLite/archivos listados arriba.
- Manifest SHA-256: `BIO-R15E-PRIME-R15F-ADAPTER-BODY-SHA256-2026-09-22.txt`.

## 10. NEXT MINIMAL DISCRIMINATING EXPERIMENT

Objetivo: determinar si el contrato esperado está en `ToolTask.status` o en `ToolResult.execution_state` y quién debe persistir la transición. Incertidumbre restante: por qué el resultado de `execute_task` se marca `waiting_approval` mientras el task almacenado conserva `pending`. Capability-fit: inspección estrecha de `ToolTeachService.execute_task`, `ToolRecordRepository` y consumidores del estado de aprobación, sin mutar el task/producción. Actor fit: un agente con acceso local de lectura y conocimiento de ese contrato; la implementación, si luego se autoriza, corresponde al propietario del lifecycle `ToolTeachService`/persistence, no al experimento. Después de cerrar esa precondición, una única continuación puede recuperar este mismo fixture y probar R15F; no reconstruir otra tarea ni repetir R15D.

## Environment and command

Windows 11 build `10.0.26200.0`; Python `3.13.2` (64-bit AMD64). R15E′ command: `$env:PYTHONPATH=(Join-Path (Get-Location) 'IABV_v1.5\src'); & 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider 'IABV_v1.5\tests\experiments\test_bio_r15e_prime_to_r15f_adapter_body_runtime.py' -q -s`. Exit code `0`, duration `4.61s`, one test passed. The later fixture read-back was a separate report-only pytest invocation (exit 0, `0.70s`); it did not rerun R15E′.
