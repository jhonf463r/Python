# UAAL-CFCP-001 — Protocolo de continuidad por evidencia y frontera causal (v1)

- Fecha: 2026-10-27 (America/Bogota).
- Repositorio: jhonf463r/Python.
- Tipo: aprendizaje metodológico versionado; no es un nuevo órgano de runtime.
- Autoridad canónica de estado: [CURRENT-STATE.md](./CURRENT-STATE.md).
- Handoff de ruta: [M1A / Entra G1 / MCP 1.30](./CHAT-ARCH-2026-10-27-M1A-CROSS-CHAT-HANDOFF-MCP130-20261027.md).

## 1. Motivo de la evolución

En la iteración PR #549, la ejecución combinada inicial reportó 194 aprobadas y 4 fallidas. Codex y el Owner localizaron discrepancias en el contrato de prueba/fixture: Host loopback aceptado por el middleware, objeto real exigido por el preflight sellado, atributo scan_stats consumido por la serialización y respuesta Streamable HTTP encuadrada como SSE. Se corrigió únicamente tests/test_mcp_server.py y luego se reportaron 198 aprobadas, una advertencia y código de salida 0 en las cuatro suites.

GitHub confirma que el commit 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28 tiene padre b55a39322d04eff5fc501629c5f331d8ea22c291 y cambia solo tests/test_mcp_server.py (+33/-7). El delta fue revisado estáticamente y no produjo nuevos hallazgos P0/P1/P2 confirmados. Los archivos locales de logs no fueron recuperados independientemente en esta sesión; los conteos siguen clasificados OWNER_CODEX_REPORTED, no reproducidos aquí.

Lección: progreso de validación, aceptación del órgano y funcionamiento E2E son estados distintos. No se debe minimizar el avance real ni convertir una prueba sintética exitosa en autoridad operativa.

## 2. Procedencia obligatoria por afirmación

| Clase | Significado | Ejemplo vigente |
|---|---|---|
| LIVE_VERIFIED | SHA, estado o blob obtenido en esta sesión desde GitHub | PR #549 HEAD 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28 y diff test-only |
| OWNER_CODEX_REPORTED | Salida de ejecución comunicada por Owner/Codex; artefacto local aún no inspeccionado aquí | 198 aprobadas, 1 advertencia, exit 0 |
| INDEPENDENTLY_REVIEWED | Fuente/diff exacto inspeccionado con alcance explícito | revisión estática del commit 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28 |
| INFERENCE | Conclusión razonada, no observación directa | los cuatro fallos eran contratos de fixture y no cambios de producto, conforme al informe recibido |
| HYPOTHESIS | Explicación por comprobar | que exista un artefacto de autoridad fuera de la evidencia inspeccionada |
| UNKNOWN / NOT_RUN | No demostrado, no consultado o no ejecutado | G1/G2/G3 reales, CI, Entra/JWKS real, Python 3.13.2 |

No convertir una salida comunicada en verificación directa sin recuperar el log u objeto original. No etiquetar un test escrito como test pasado, ni una revisión de delta como certificación de toda una PR.

## 3. Bucle de continuidad

1. Fijar identidad: leer CURRENT-STATE.md vivo, SHA de main, estado/base/HEAD de cada PR relevante y SHA exacto del objeto de la tarea.
2. Formular una sola pregunta discriminante: qué observación nueva puede mover un gate o distinguir causas plausibles. Si no cambió la evidencia ni una precondición, no repetir la misma operación.
3. Escoger una acción dentro del alcance autorizado: inspección estática acotada, ejecución aislada, validación de artefacto o cambio puntual. Separar lectura, código, ejecución, configuración y activación en fases distintas.
4. Etiquetar resultados por procedencia y conservar comandos, códigos de salida, fallos iniciales y logs. No borrar una ejecución fallida de la historia.
5. Corregir la capa causal demostrada. Si el test contradice el protocolo real, corregir la fixture/assertion; si falla producción, no ocultarlo editando solo el test.
6. Tras cambiar cualquier archivo, comprobar el diff y el SHA exactos. El dictamen anterior conserva validez solo para su SHA y ámbito; el nuevo delta requiere evaluación propia.
7. Hacer fetch-back de commit/blob y comprobar que la escritura documental es coherente con los refs vivos.
8. Elegir la siguiente frontera causal pendiente; no aumentar el volumen de pruebas ya resueltas como sustituto del requisito real.

## 4. Regla para ciclos de pruebas

- Guardar el fallo inicial, comando, SHA, retorno y log.
- Distinguir fallo de código, dependencia, configuración del test y precondición externa.
- Cambiar solo la capa que la evidencia demuestra defectuosa.
- Ejecutar primero las suites afectadas, después las suites independientes de aceptación y finalmente la combinación objetivo.
- Reportar la primera ejecución y la final separadamente.
- Diferenciar respuesta de error JSON-RPC sobre HTTP 200 del 403 HTTP emitido por el middleware; son contratos diferentes.
- Los tests sintéticos no prueban proveedor real de confianza, revocación de mandato, autorización de operaciones ni puente E2E.

## 5. Validez de la revisión por SHA

Toda revisión registra REVIEWED_HEAD, PARENT_SHA, SCOPE y CHANGED_PATHS. Cuando cambia HEAD, la revisión anterior sigue siendo histórica para ese commit, pero no se convierte en revisión del nuevo. Un delta test-only puede declarar NEW_FINDINGS=0 sin certificar la PR completa, la seguridad global ni el runtime.

## 6. Aprendizaje persistente del sistema que construye

El aprendizaje aquí significa un delta metodológico versionado, reutilizable y vinculado a observaciones, no consciencia ni un runtime de memoria compartido automáticamente entre ChatGPT, Codex e IABV. Para que una experiencia cuente como aprendizaje de proceso, guardar: observación/contexto, hipótesis descartadas y razones, cambio mínimo realizado, resultados antes/después, regla general, límite de validez y siguiente acción que podría refutar o ampliar la conclusión.

No añadir otro servicio de memoria u orquestador por esta observación: la regla es fortalecer el bucle ya existente de captura, clasificación, causalidad, verificación, escritura canónica y comprobación de reutilización. CURRENT-STATE.md sigue siendo la autoridad de ruta.

## 7. Próxima frontera M1A

- PR #549: OPEN/DRAFT/UNMERGED; HEAD 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28; base a8624c30744da7f593d6a1c829e48aa229c8efca. Cuatro suites reportadas como aprobadas por Owner/Codex; el delta test-only fue revisado estáticamente. Python 3.13.2 y CI de GitHub Actions no validados.
- PR #531: OPEN/DRAFT/UNMERGED; HEAD bc2baf525a70d66628809360a197f25a069aa328; base 7ddfe285b1a3267f9ef6f57f862cca78bc8438c2. No rebasear ni fusionar.
- Estado: G1/G2/G3=NOT_ESTABLISHED; AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED; OWNER_ROOT_SELECTION=NOT_PROVIDED; MCP_TOOL_ALLOWLIST=EMPTY; lecturas protegidas fail-closed; puente no listo.

Próxima acción discriminante: revisión estática de solo lectura, acotada al candidato vivo de PR #531. Seguir bootstrap.py hasta ReadAuthorizationCoordinator y los proveedores concretos que se inyectan para G1/G2/G3. Determinar si la evidencia existente incluye una raíz/mandato verificable e independiente del Owner y un canal independiente de verificación/revocación, o si solo existen Protocols, proveedores unconfigured/None, tests sintéticos y evidencia acotada de merge en GitHub.

No repetir el inventario general. No crear raíces, mandatos, políticas, resolutores o revocadores sintéticos. No usar PR #549 para habilitar operaciones. Si no existe un artefacto de G1 en la evidencia autorizada disponible, documentar el proveedor exacto faltante y pedir solo el nuevo dato que podría cambiar esa conclusión.

## 8. Puertas preservadas

```text
G1/G2/G3=NOT_ESTABLISHED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
OWNER_ROOT_SELECTION=NOT_PROVIDED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
PYTHON_3_13_2=NOT_AVAILABLE_IN_REPORTED_RUN
GITHUB_ACTIONS_CI=NOT_RUN
LOCAL_TESTS=OWNER_CODEX_REPORTED_PASS; 198_PASSED; 1_WARNING; EXIT=0
```


## 9. Automation-first operation and OS-consent boundary — 2026-10-27

### Normative rule

The Owner is the decision/consent authority, not the default shell operator. When a bounded operation is authorized and a supported local agent can execute it, the agent MUST attempt the safe automated route first. Do not assign the Owner manual shell commands, console navigation, screenshots or copying of diagnostic values merely because the first process lacks a capability.

### Elevation decision

1. Determine whether elevation is actually required for the narrow operation; do not infer it from one access-denied result unless the API's documented contract supports that inference.
2. If elevation is necessary and the operation is already explicitly authorized, ask the local agent to invoke the standard OS consent UI (on Windows, a separate bounded process using a supported `RunAs`/UAC flow). The prompt is the human interruption; it replaces manual operation.
3. After consent, execute only the pre-authorized read-only command set. Capture exit codes and sanitized outputs in a temporary artifact readable by the parent process. Never log secrets, raw SID, credentials, private keys or unrelated device details. Clean up temporary artifacts created by the task.
4. If consent is denied, no eligible admin account exists, a policy blocks elevation, or the agent cannot invoke the UI, stop that attempt and report a precise blocker. Do not circumvent UAC, suppress prompts, change policy, self-elevate invisibly or retry an unchanged action.
5. Never extrapolate read-only elevation consent to provisioning, key creation, service installation, ACL changes, Entra configuration, protected reads, tunnel/runtime activation or merge. Those remain separate gates.
6. Ask the Owner only for a human-owned choice or unavoidable OS/account consent. Do not ask the Owner to carry out diagnostic steps that the supported local agent can perform. If this ChatGPT session lacks local-desktop execution, state that limitation and use Codex as the local execution bridge rather than claiming the popup was launched here.

### Evidence and anti-loop requirements

Record the exact scope, whether the UAC prompt was invoked (not merely planned), whether it was accepted/denied/unavailable, exit code, output provenance, cleanup, and the next discriminating question. The first non-elevated denial remains historical evidence; a second attempt is justified only because the authorization context changed. If the elevated attempt is still denied, do not repeat it without a changed precondition.

### Applied to the current M1A task

The local Codex report says `ADMIN_CONTEXT=False` and correctly stopped before TPM/Secure Boot queries. Next action is one automated, user-consented, read-only elevation attempt for the exact prior query set. No manual console opening is required if the local agent can display the normal UAC prompt. If no interactive local execution channel exists, record `UAC_UI_UNAVAILABLE_IN_AGENT` and stop; do not claim a hardware result.

This rule changes workflow ergonomics only. It does not establish G1/G2/G3 or authorize any product operation.


## 10. UAC invocation blocked before UI — no manual fallback or retry loop (2026-10-27)

### Evidence

The approved local Codex attempt to launch a bounded PowerShell child using `Start-Process -Verb RunAs` returned `exec_command failed: Rejected … blocked by policy`. The process did not start; no UAC window appeared; no TPM/Secure Boot query ran; no temporary script or output artifact was created. No machine/repository change occurred.

Classify this precisely as:

```text
UAC_REQUEST=BLOCKED_BY_EXECUTION_TOOL_POLICY
UAC_UI=NOT_SHOWN
ELEVATED_CHILD=NOT_STARTED
TPM=UNKNOWN
SECURE_BOOT=UNKNOWN
OWNER_CONSENT=NOT_REQUESTED_BY_OS
```

This is **not** an Owner denial, not an OS/UAC rejection, and not evidence about hardware.

### Required response

- Do not repeat the same invocation or try an alternate elevation route after the execution policy explicitly blocked it.
- Do not ask the Owner to open consoles or navigate Windows Settings. The Owner explicitly prefers local-agent execution; preserve that preference.
- Do not claim a normal UAC prompt can be shown when the tool policy rejected the process before launch.
- Continue work that does not depend on this observation: static analysis, provider-composition tracing, threat-model/contract design, and draft implementation planning within existing authorization.
- Keep any hardware-dependent choice unresolved. A UI result can be obtained only if a supported local execution route later becomes available or policy changes; the Owner should not be made the operator by default.
- Do not treat this obstacle as authorization to provision a software key, weaken trust requirements, enable protected reads, or promote any acceptance gate.

### Next discriminating route

The immediate next operation is not another hardware probe. Prepare a source-derived authority/bootstrap contract from the existing G1/G2/G3 code, identifying mandatory interfaces, trust binding, revocation and rollback requirements, and fail-closed composition tests. It must remain backend-agnostic between a future verified hardware-backed provider and any separately approved alternative, without selecting or provisioning either one. Then perform an exact-HEAD review and identify the first non-hardware decision that genuinely requires Owner consent.

This is a workflow lesson: an agent-side tool policy blocker is a boundary of the execution channel, not an Owner task. Record the blocked action once and advance on the independent safe frontier.

## 11. ToolTask-scoped human approval and same-task continuation (2026-10-27)

1. Keep static source evidence separate from execution: visible UI, a prompt, a broker result, dispatch, external effect, returned result and captured evidence are distinct claims. Record provenance and do not promote a report to verified runtime fact.
2. Do not retry the failed local UI/kernel initialization or the partial clone checkout that reported Filename too long unless a materially new precondition supports a different attempt. Preserve existing directories. Do not create a new task merely to reach an approval screen.
3. A task approval must be immutably correlated to request_id, the existing task_id, server-resolved destination, operation/scope and a cryptographic digest of the exact authorized content. Any change invalidates that approval.
4. An approved boolean, approved_by string, learned policy, VALIDATED state, or auto_resolved result is not proof of interactive human consent. Require a verifiable human actor and authority; auto-approval cannot satisfy a human-required gate.
5. Prefer asynchronous durable suspension/resumption over blocking the execution/UI thread. The current in-memory synchronous broker wait does not establish safe UI scheduling or restart recovery.
6. Define monotonic transitions, atomic claim/CAS, idempotent duplicate resolution, and explicit rejection of conflicting decisions. Specify expiry, cancellation races, errors, process restart, recovery of the same task_id and treatment of unknown external outcomes. Never infer approval from timeout or retry an uncertain non-idempotent effect.
7. Distinguish sandbox success, actual dispatch, external acceptance/effect, returned result and capture. Each needs its own observable evidence and correlation to task_id; one stage does not prove the next.
8. After any documentation write, verify fetch-back of every changed blob and the exact commit/ref. A successful local/API write request alone does not establish canonical adoption.
9. Keep G1/G2/G3 unestablished, MCP allowlist empty, protected reads fail-closed, tunnel disabled and bridge not ready until independent evidence and separate authorization change those gates.

This section records process/design requirements only; it does not authorize implementation or runtime activation.
