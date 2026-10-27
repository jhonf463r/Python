# Handoff entre chats — IABV / Entra G1 / MCP 1.30 (2026-10-27)

## Continuity checkpoint for a new chat — current verified route (2026-10-27)

Canonical authority: [CURRENT-STATE.md](./CURRENT-STATE.md). Read it first, then [UAAL-CFCP-001](./CHAT-ARCH-2026-10-27-UAAL-EVIDENCE-TO-CAUSAL-FRONTIER-CONTINUITY-PROTOCOL-v1.md). New headed sections supersede older status lines where they conflict; keep historical receipts intact.

Live references verified for this checkpoint:
- main before this documentation update: 1b8906057e0ae19f4a79b451f5e4ec476a0442c3.
- PR #549: OPEN/DRAFT/UNMERGED; HEAD 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28; base a8624c30744da7f593d6a1c829e48aa229c8efca. Four local suites are Owner/Codex-reported as passing (198 combined, 1 warning, exit 0) on Python 3.14.4; the exact test-only delta has a bounded static review with no new P0/P1/confirmed P2. The local logs were not independently inspected here; Python 3.13.2 and GitHub Actions CI were not validated.
- PR #531: OPEN/DRAFT/UNMERGED; HEAD bc2baf525a70d66628809360a197f25a069aa328; base 7ddfe285b1a3267f9ef6f57f862cca78bc8438c2. Its branch is on an older base; do not rebase or merge automatically.
- Gates: G1/G2/G3=NOT_ESTABLISHED; AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED; OWNER_ROOT_SELECTION=NOT_PROVIDED; MCP_TOOL_ALLOWLIST=EMPTY; PROTECTED_READS=FAIL_CLOSED; TUNNEL=DISABLED; BRIDGE=BRIDGE_NOT_READY; MERGE=NOT_AUTHORIZED; PRODUCTION_ACTIVATION=NOT_AUTHORIZED.

## Next task — one discriminating read-only review, not another broad inventory

Inspect only the exact live PR #531 HEAD bc2baf525a70d66628809360a197f25a069aa328. Follow bootstrap.py composition into ReadAuthorizationCoordinator and trace concrete wired provider instances for G1/G2/G3. First question: does already-present, independently verifiable evidence establish an Owner trust root/mandate plus an independent verification/revocation channel, or are the paths only Protocol contracts, unconfigured None providers, synthetic tests or bounded GitHub merge evidence? Report exact path/line/blob evidence, separate observation from inference, and stop if no real G1 artifact is present. Do not repeat the broad inventory.

Do not change code, rebase/merge, configure production Entra, run live runtime, enable protected reads or tools, start a tunnel, or activate the bridge during this read-only discrimination. If G1 has no real source/evidence, specify the exact missing producer and the one new input that could change the decision.

## Process learning

The first failed test run is evidence, not noise: preserve it, classify root cause, fix only the layer shown to be wrong, rerun the affected suites and the full set, and report both initial and final outcomes. A new commit always gets a SHA-bound delta review; no review inherits automatically to a new HEAD. A test pass is not live authority or E2E readiness. These rules now live in UAAL-CFCP-001.

---
## Static review of PR #549 test-only delta completed — HEAD 519c55a5 (2026-10-27)

Read-only review of exact commit `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28` confirms parent `b55a39322d04eff5fc501629c5f331d8ea22c291` and only one changed path, `tests/test_mcp_server.py`. The test fixture corrections are statically coherent; no new finding was identified in this delta (`NEW_P0=0; NEW_P1=0; NEW_CONFIRMED_P2=0`). This is not a full security certification.

The four local suites are reported by Codex as passing (198 combined, one warning, exit 0), in Python 3.14.4; logs were not independently retrieved here, Python 3.13.2 was unavailable, and GitHub Actions CI was not run. PR #549 remains open/draft/unmerged at `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28`, base `a8624c30744da7f593d6a1c829e48aa229c8efca`.

The acceptance blocker is unchanged. The next route is to reconcile this Entra transport/authentication candidate with the pre-existing integrated G1/G2/G3 source-organ candidate in PR #531, after a narrow evidence check on real authority artifacts. Do not rebase, merge, fabricate a root or enable protected reads.

Receipt: [PR #549 519c static delta review](./CHAT-ARCH-2026-10-27-M1A-PR549-519C-STATIC-DELTA-REVIEW.md).

---

## Latest candidate validation — PR #549 HEAD 519c55a5 (2026-10-27)

The Owner supplied Codex's isolated test-execution report for candidate `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28`. GitHub independently confirms that commit's parent is `b55a39322d04eff5fc501629c5f331d8ea22c291` and its diff changes only `IABV_v1.5/tests/test_mcp_server.py` (+33/-7). PR #549 stays `OPEN/DRAFT/UNMERGED`, based on `a8624c30744da7f593d6a1c829e48aa229c8efca`; `main` before this documentation update was `7780db1b33304923c17a0247403cb789c7907e01`.

Reported results (logs are local temporary files and were not independently inspected in this session): Python 3.14.4 in a fresh venv; `mcp==1.30.0`, `pytest==9.2.0`; four suites passed: verifier 36, MCP server 90, audit tools 56, bridge service 16; combined 198 passed, one warning, exit 0. The earlier combined run was 194 passed / 4 failed. Only test fixtures/requests were corrected. Python 3.13.2 was unavailable, so that target remains unverified. No live Entra/JWKS, server, tunnel or GitHub Actions execution occurred; this commit carries `[skip ci]`.

The previous independent static review was for `b55a39322d04eff5fc501629c5f331d8ea22c291`; independent review of the exact current HEAD `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28` remains pending. Continue to preserve `G1/G2/G3=NOT_ESTABLISHED`, `MCP_TOOL_ALLOWLIST=EMPTY`, `PROTECTED_READS=FAIL_CLOSED`, `TUNNEL=DISABLED`, `BRIDGE=BRIDGE_NOT_READY`, `MERGE=NOT_AUTHORIZED`. Passing local synthetic tests is real progress, but not proof of live authorization or bridge readiness.

Receipt: [M1A PR #549 isolated test execution — 519c55a5](./CHAT-ARCH-2026-10-27-M1A-PR549-TEST-RUN-519C-RECEIPT.md).

---

## Dictamen independiente completado — PR #549 HEAD b55a3932 (2026-10-27)

Se recibió y contrastó el dictamen estático de solo lectura para el HEAD exacto `b55a39322d04eff5fc501629c5f331d8ea22c291`. PR #549 permanece `OPEN/DRAFT/UNMERGED`, con base `a8624c30744da7f593d6a1c829e48aa229c8efca`; `main` antes de esta actualización era `b8e18eb725a951209854e0b0756e88a7c7cbdc88`.

- Resultado: `P0=0` demostrados en el delta examinado; `P1=1` bloqueo de aceptación; `P2=3` riesgos/vacíos. No es certificación de seguridad.
- Bloqueo: `G1/G2/G3=NOT_ESTABLISHED`; falta autoridad independiente, política G2 revocable, resolver G3 y fuente independiente de revocación del mandato del Owner. `MCP_TOOL_ALLOWLIST=EMPTY`; llamadas normales siguen denegadas.
- Confirmación estática: wrappers de producción no exponen `__iabv_original_handler__` ni `__wrapped__`, ni capturan directamente el handler; las tres herramientas tardías de autoactualización usan el mismo registrador.
- Límites: los sellos Python no son una frontera contra código hostil dentro del mismo proceso; los nuevos contratos de tests y la compatibilidad SDK solo se han revisado estáticamente.
- La revisión «pendiente» indicada en la sección siguiente queda supersedida por este resultado. La sección y sus referencias históricas permanecen intactas.
- Sin ejecución: `TESTS/BUILD/RUNTIME/CI=NOT_RUN`. Se mantienen `PROTECTED_READS=FAIL_CLOSED`, `TUNNEL=DISABLED`, `BRIDGE=BRIDGE_NOT_READY`, `MERGE=NOT_AUTHORIZED` y `PRODUCTION_ACTIVATION=NOT_AUTHORIZED`.

La candidata y su base no se modificaron. Mantener PR #549 en borrador; una puerta de tests requiere autorización separada y precondiciones verificadas.

---

## Latest candidate update — PR #549 HEAD b55a3932 (2026-10-27)

This note supersedes earlier candidate HEAD references only. It does not relax the no-tests/no-runtime/no-merge boundaries.

- PR: https://github.com/jhonf463r/Python/pull/549 — OPEN/DRAFT/UNMERGED.
- Current main before this note: `3b6d2f7056777141ec3a04020654455e811697e1`. PR base remains its earlier recorded SHA `a8624c30744da7f593d6a1c829e48aa229c8efca`. Do not rebase or merge automatically.
- Previous candidate HEAD: `8afee332e5e0f65715013effcee57b215413547c`.
- Current candidate HEAD: `b55a39322d04eff5fc501629c5f331d8ea22c291`.
- Latest commit changes two test files only: per-test scoped capture of original handlers in test-only state, and a negative ID-token-like audience contract without relying on `nonce`/`at_hash` markers.
- The prior static correction removed original-handler references from production MCP tool wrappers, kept the allowlist empty and tightened ordinary mutability of trust-binding fields. Latest source files were fetched back from the exact candidate HEAD.
- Tests/build/runtime/CI have not been run. The prior independent report does not review this new HEAD. Request the second static review against `b55a39322d04eff5fc501629c5f331d8ea22c291` exactly.
- Preserve `G1/G2/G3=NOT_ESTABLISHED`, `PROTECTED_READS=FAIL_CLOSED`, `MCP_TOOL_ALLOWLIST=EMPTY`, `TUNNEL=DISABLED`, `BRIDGE=BRIDGE_NOT_READY`, `MERGE=NOT_AUTHORIZED`.

Receipt: [CHAT-ARCH-2026-10-27-M1A-PR549-CORRECTION-B55A-FETCHBACK-RECEIPT.md](./CHAT-ARCH-2026-10-27-M1A-PR549-CORRECTION-B55A-FETCHBACK-RECEIPT.md).

---


## Latest candidate update — PR #549 HEAD 8afee332 (2026-10-27)

This note supersedes the candidate SHA only; it does not supersede the no-runtime/no-merge boundaries recorded below.

- PR #549: OPEN/DRAFT/UNMERGED — https://github.com/jhonf463r/Python/pull/549
- Base initially verified: `a8624c30744da7f593d6a1c829e48aa229c8efca`; current canonical main was `6d69e87d63131a99ee4748c0f6a2a0b8b2cbe82d` before this note. Do not rebase or merge automatically.
- Previous candidate HEAD: `05d007965ea7efda6f528657e20103ea82bcb6b5`.
- Current candidate HEAD: `8afee332e5e0f65715013effcee57b215413547c`.
- Corrections: remove original-handler references from production tool objects while keeping the allowlist empty; prevent ordinary deletion of preflight fields and reassignment/deletion of verifier trust-binding fields; add test contracts for valid synthetic auth still blocked by the operation gate and missing scope -> 403. Four files changed in the latest commit.
- Source was fetched back and static anchors verified. No tests/build/runtime/CI were run; no workflow runs were found for this HEAD.
- The previous independent report targets HEAD `05d007965ea7efda6f528657e20103ea82bcb6b5`, not this new SHA. Independent review of `8afee332e5e0f65715013effcee57b215413547c` is now the next action.
- Preserve: `G1/G2/G3=NOT_ESTABLISHED`; `MCP_TOOL_ALLOWLIST=EMPTY`; `PROTECTED_READS=FAIL_CLOSED`; `TUNNEL=DISABLED`; `BRIDGE=BRIDGE_NOT_READY`; `MERGE=NOT_AUTHORIZED`; no local checkout changes.

Review follow-up receipt: [CHAT-ARCH-2026-10-27-M1A-PR549-CORRECTION-8AFEE-FETCHBACK-RECEIPT.md](./CHAT-ARCH-2026-10-27-M1A-PR549-CORRECTION-8AFEE-FETCHBACK-RECEIPT.md).

---


## Addendum vigente — autorización limitada de candidata PR #549 (2026-10-27)

Leer primero `CURRENT-STATE.md`; su nueva entrada de reconciliación prevalece cuando una sección histórica del presente handoff aún diga que nunca se autorizó preparar código. La respuesta original «ok procede» sigue describiendo correctamente la ratificación inicial del objetivo/plan, pero posteriormente se aceptó y ejecutó un prompt con alcance explícito para preparar una candidata code-only aislada.

- PR: https://github.com/jhonf463r/Python/pull/549
- Base inicial: `a8624c30744da7f593d6a1c829e48aa229c8efca`
- HEAD verificado: `05d007965ea7efda6f528657e20103ea82bcb6b5`
- Procedencia: consentimiento de alcance en esta conversación evidenciado por el prompt acotado usado por el Owner y el resultado de Codex aportado después; no es autenticación independiente del runtime.
- Autorizado: cambios de código y pruebas fuente únicamente en la rama candidata de PR #549.
- No autorizado: instalación, resolución de dependencias, ejecución de pruebas/build/runtime/CI, portal o configuración real de Entra, túnel, lecturas protegidas, merge, despliegue o activación; no tocar el checkout `C:\Python`.
- Estado: `PR=OPEN/DRAFT/UNMERGED`; `TESTS/BUILD/RUNTIME=NOT_RUN`; `G1/G2/G3=NOT_ESTABLISHED`; `PROTECTED_READS=FAIL_CLOSED`; `TUNNEL=DISABLED`; `BRIDGE=BRIDGE_NOT_READY`; `MERGE=NOT_AUTHORIZED`.

El recibo de procedencia está en [CHAT-ARCH-2026-10-27-M1A-CODE-ONLY-PR549-AUTHORIZATION-RECONCILIATION-RECEIPT.md](./CHAT-ARCH-2026-10-27-M1A-CODE-ONLY-PR549-AUTHORIZATION-RECONCILIATION-RECEIPT.md). La revisión independiente del HEAD actual encontró 0 P0 demostrados, 2 bloqueos P1 y 3 riesgos/vacíos P2; los informes de pruebas fuente no cuentan como pruebas ejecutadas.

---


- Zona horaria: America/Bogota.
- Propósito: permitir que un nuevo chat continúe sin perder las decisiones, evidencia, límites de autorización, fallos previos ni reglas anti-repetición.
- Autoridad operativa única: [CURRENT-STATE.md](./CURRENT-STATE.md). Un resumen o handoff no puede sobrescribir su estado vivo.
- Plan de integración actual: [M1A G1 — objetivo MCP fijado y plan de integración Entra, sin código](./CHAT-ARCH-2026-10-27-M1A-G1-MCP130-IMPLEMENTATION-PLAN-NO-CODE.md).
- Diseño Entra revisado: [M1A G1 — diseño y revisión técnica](./CHAT-ARCH-2026-10-27-M1A-G1-ENTRA-BOOTSTRAP-DESIGN-ONLY.md).

## 1. Estado breve y autoritativo

El Owner ratificó el objetivo de planificación con «ok procede». Esa ratificación cubre **objetivo y plan documental**, no implementación.

- Objetivo ratificado para una futura fase aislada: Miniconda Python 3.13.2, distribución MCP SDK mcp==1.30.0, Streamable HTTP, bind 127.0.0.1:8000, túnel desactivado.
- El preflight local reportado por Codex encontró Miniconda Python 3.13.2 con mcp 1.27.0 y un entorno Python 3.14.4 con mcp 1.30.0; por tanto, el entorno objetivo aún no tiene la versión elegida según el informe aportado.
- El checkout local informado como C:\Python estaba en HEAD 8425f03eb45abd11951938f6e3234459c1585b55, detached, con estado extremadamente sucio (13.833 entradas reportadas, 0 staged, 13.833 unstaged y 13.313 untracked). Esa es evidencia local comunicada por el informe de Codex y no se revalidó por el asistente; tratarla como condición de preservación. No limpiar, sincronizar, cambiar de rama ni editar ese checkout.
- El main vivo consultado para el plan era a283424e5ec1e489a4cbef0e19b2ab68da825b2c; después se registraron la planificación y las actualizaciones de continuidad. Antes de cualquier acción nueva, volver a leer CURRENT-STATE.md desde main y obtener los SHAs vivos.
- En el main inspeccionado, pyproject.toml no declara directamente mcp, uvicorn ni PyJWT; el servidor permite stdio/sse/streamable-http pero el default es stdio; el lanzador predetermina Miniconda, Streamable HTTP y puerto 8000 y contiene ruta de túnel; la documentación del puente refleja puerto 8765 y reconoce que no hay autenticación HTTP por token. No iniciar el lanzador actual ni túnel como modo de prueba.
- No se ha conectado un TokenVerifier Entra en main. El SDK revisado expone TokenVerifier y AuthSettings; esto no significa que la autoridad, el bootstrap o el runtime estén listos.
- G1, G2 y G3 permanecen NOT_ESTABLISHED; ocho prerrequisitos de implementación siguen abiertos; las lecturas protegidas permanecen FAIL_CLOSED; el puente continúa BRIDGE_NOT_READY.

## 2. Decisiones de Owner: no preguntar de nuevo

1. La decisión previa Option D — no crear una nueva raíz de confianza y mantener fail-closed — ya está ratificada y no debe volver a preguntarse.
2. «Sí» autorizó el diseño documental de Entra, no la configuración del portal, ni registro de aplicaciones, ni credenciales, ni permisos, ni código.
3. «Ok procede» ratificó el objetivo MCP y permitió documentar el plan sin código. **No es una autorización para implementar, instalar/actualizar paquetes, ejecutar el servidor, probar, abrir un túnel, desplegar ni habilitar lecturas protegidas.**
4. No se necesita repetir la configuración de Entra/Authenticator ni la evaluación general OIDC.

## 3. Diseño de autenticación y corrección crítica

En tokens v2 de Entra, no confundir:
- la URL canónica HTTPS del recurso MCP;
- el Application ID URI registrado;
- el parámetro OAuth resource del cliente; y
- el claim aud del token.

En el flujo previsto, resource y Application ID URI deben coincidir exactamente en el contexto indicado por la guía de Microsoft. El aud esperado del access token v2 es normalmente el Application (client) ID GUID de la API. El verificador debe validar el recurso y aud de forma separada y no desactivar ninguno para sortear un desajuste.

La URL canónica HTTPS todavía no está aprobada; por eso el objetivo de loopback es solo una meta local de transporte, no un E2E real con Entra. No inventar URL, no crear una app registration y no abrir Cloudflare Tunnel. La protección OAuth de HTTP no protege automáticamente stdio; stdio requiere un contrato independiente de proceso, usuario y mandato local. La ceremonia local propuesta sigue siendo una hipótesis, no una prueba del canal G1 independiente.

Fuentes:
- https://learn.microsoft.com/en-us/entra/agent-id/secure-mcp-server-with-entra-id
- https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- https://py.sdk.modelcontextprotocol.io/v1/run/authorization/
- https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

## 4. Protocolos operativos obligatorios

- Leer CURRENT-STATE.md de main al inicio de cualquier tarea sustantiva y después los archivos exactos vinculados a la tarea.
- Diferenciar MAIN_EVIDENCE, LOCAL_CODEX_REPORT, OWNER_REPORTED, INFERENCE, HYPOTHESIS, UNKNOWN y NOT_RUN. La observación local no prueba el contenido de main ni el runtime de producción.
- Preservar la procedencia: no convertir una interfaz o un protocolo en evidencia de proveedor productivo; no declarar runtime, test, build, transporte o autorización si no se observó.
- Aplicar UAAL-D019 anti-loop: fingerprint por objetivo/revisión, operación/entradas, actor/ruta, autorización/precondiciones, entorno y observación esperada. Repetir prompt/chat no crea una experiencia nueva. Solo elegir una acción discriminante con evidencia nueva o detenerse.
- Una acción autorizada debe tener alcance exacto y una sola frontera de finalización. Verificar el resultado con fetch-back cuando se editen documentos.
- Preservar ideas y evidencia no destructivamente: registrar procedencia, vincular versiones y contradicciones, diferir antes de descartar, y no llamar “aprendizaje reutilizable” a un resumen almacenado si todavía no se verificó su uso efectivo en una tarea no idéntica.
- Nunca limpiar el checkout sucio, descartar trabajo, sincronizar/rebasear el checkout local, modificar main directamente, iniciar servidores, ejecutar pruebas, instalar paquetes o abrir túneles como consecuencia automática.
- No crear raíz sintética, proveedor fake, identidad asumida ni permisos permisivos. Si faltan autoridad, configuración, metadata o claves, denegar por defecto.
- No repetir el análisis general de OIDC, el preflight local recién informado, los chequeos de facturación de GitHub ya concluidos ni intentos de leer la huella privada de GitHub App. Para el último asunto, la ruta de lectura local segura seguía sin demostrarse; mantener MATCH=NOT_VERIFIED y PROTECTED_READS=FAIL_CLOSED salvo nueva evidencia de ruta aprobada.
- Los resultados de cambios en documentación se deben verificar por lectura de vuelta; mantener CURRENT-STATE.md como ruta única de autoridad y sincronizar las cuatro puertas de entrada cuando se cierre un cambio terminal de continuidad.

## 5. Estado de la tarea separada de clave GitHub App

No mezclar este subproblema con la integración Entra. PR #548 sigue siendo la ruta de handoff para recuperación/comparación de clave GitHub App, con trabajo anterior no resuelto. Nunca volver a leer la huella del nodo en el navegador, usar clipboard history, producir screenshots/dumps ni volcar valores crudos. El último diagnóstico aportado decía:
- LOCAL_EXECUTION=YES
- IABV_BROWSER_ROUTE=UNAVAILABLE
- BROWSER_OBSERVER_REGISTERED=YES
- LOCAL_DOM_ACCESS=UNKNOWN
- ACCESSIBILITY_ACCESS=AVAILABLE
- UIA_CAPABILITY_SCOPE=UNKNOWN
- EXECUTION_BOUNDARY=LOCAL
- RAW_VALUE_CAN_REACH_MODEL_OR_TRANSCRIPT=YES
- BLOCKER_CLASS=DATA_BOUNDARY_UNPROVEN
- NEXT_ACTION=STOP_UNTIL_ROUTE_EVIDENCE

PR #548: https://github.com/jhonf463r/Python/pull/548. Mantener MATCH=NOT_VERIFIED, no reutilizar el TXT de 40 caracteres previamente rechazado, no inspeccionar clipboard history, no alegar que la comparación de fingerprint se completó.

## 6. Estado de PRs y rutas paralelas

Conservar los estados canónicos vivos en CURRENT-STATE.md y refrescarlos antes de actuar. El último snapshot conocido de antes de este handoff registraba:
- PR #531 OPEN/DRAFT/UNMERGED, candidato bc2baf525a70d66628809360a197f25a069aa328.
- PR #546 OPEN/DRAFT/UNMERGED, no actuar.
- PR #547 OPEN/DRAFT/UNMERGED, HEAD 9b60d787528a5199c36b59a6c172f860c4bd6a86, revisión independiente pendiente.
- Actions billing-lock observado; causa raíz UNKNOWN; no repetir un intento sin cambio material.

Estos hashes se deben revalidar en el estado canónico vivo antes de usarlos en una operación, no tratar como actuales por ser un handoff.

## 7. Siguiente paso y autorización exacta que falta

El diseño y el plan están documentados. El siguiente paso no es instalar nada ni cambiar código automáticamente: hace falta una autorización explícita para iniciar la implementación en una worktree/branch/PR aislada, derivada de la revisión viva de main, dejando C:\Python intacto.

Esa autorización debe limitar claramente si incluye:
- solo edición de código/documentación de implementación;
- creación de branch/PR draft;
- cambios de entorno o instalación (recomendado excluirlos al principio);
- pruebas locales (recomendado excluirlas hasta una revisión independiente);
- cualquier portal Entra, registro/roles o credenciales (excluir);
- túnel, deployment y lectura protegida (excluir).

Recomendación: dividir la implementación en una primera fase de código en branch/PR aislada, sin instalar paquetes en el entorno de uso del Owner, sin portal Entra, sin test/runtime y sin túnel. Solo preparar la implementación deny-by-default y los tests en el PR; antes de ejecutar o instalar, pedir otra autorización. No editar main ni tocar el checkout dirty. La URL canónica HTTPS y el rol/mandato Entra siguen bloqueados para el E2E real.

## 8. Prompt para empezar el nuevo chat

Copia el siguiente prompt en el nuevo chat. No uses un resumen de memoria como sustituto de revalidar el estado vivo:

“Continúa IABV / puente Codex desde GitHub, siguiendo todos los protocolos ya registrados. Empieza leyendo desde main IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md, después este handoff CHAT-ARCH-2026-10-27-M1A-CROSS-CHAT-HANDOFF-MCP130-20261027.md y el plan CHAT-ARCH-2026-10-27-M1A-G1-MCP130-IMPLEMENTATION-PLAN-NO-CODE.md. Revalida SHA de main, enlaces, estado del plan y las PR antes de hacer cualquier cosa.

La ratificación del Owner ya está hecha: objetivo Miniconda Python 3.13.2, mcp 1.30.0, Streamable HTTP, 127.0.0.1:8000, sin túnel. No preguntes de nuevo por este objetivo ni por Option D. Esa ratificación autoriza la planificación documental solamente, no la implementación, instalación, portal Entra, credenciales, permisos, runtime, tests, túnel ni lecturas protegidas.

Preserva completamente C:\\Python; el checkout local fue reportado como detached y extremadamente sucio. No sincronices, limpies ni modifiques ese directorio. Usa evidencia viva de main y distingue los informes locales de Codex de la evidencia remota. No repitas el preflight ya realizado, el análisis general OIDC ni rutas fallidas idénticas. Aplica UAAL-D019 anti-loop y registra toda observación como VERIFIED, OWNER_REPORTED, INFERENCE, HYPOTHESIS, UNKNOWN o NOT_RUN.

El paso siguiente es solicitar autorización específica para una implementación inicial en worktree/branch/PR draft aislada, sin instalar paquetes, sin acceder al portal Entra, sin ejecutar tests/runtime, sin túnel y sin habilitar lecturas protegidas. Si se autoriza, limita el trabajo a preparar código con fail-closed y tests en el PR, y verifica cada cambio. No ejecutes cambios fuera de ese alcance. Mantén G1/G2/G3 NOT_ESTABLISHED y BRIDGE_NOT_READY hasta evidencia independiente y aceptación verificable.”

## 9. Estado terminal del handoff

- HANDOFF=CONSOLIDATED_FOR_NEW_CHAT
- CANONICAL_ROUTE=CURRENT-STATE.md
- OWNER_TARGET_RATIFIED=MINICONDA_PYTHON_3_13_2; MCP_1_30_0; STREAMABLE_HTTP; LOOPBACK_8000; NO_TUNNEL
- OWNER_AUTHORIZATION_SCOPE=TARGET_AND_DOCUMENTATION_PLAN_ONLY
- DIRTY_LOCAL_CHECKOUT=PRESERVE; DO_NOT_EDIT
- SOURCE_IMPLEMENTATION=NOT_AUTHORIZED
- ENVIRONMENT_INSTALL=NOT_AUTHORIZED
- ENTRA_PORTAL=NOT_AUTHORIZED
- TESTS=NOT_RUN
- BUILD=NOT_RUN
- RUNTIME=NOT_RUN
- PROTECTED_READS=FAIL_CLOSED
- OPTION_D=UNCHANGED
- G1=NOT_ESTABLISHED
- G2=NOT_ESTABLISHED
- G3=NOT_ESTABLISHED
- BRIDGE=BRIDGE_NOT_READY
- NEXT_ACTION=OWNER_EXPLICIT_AUTHORIZATION_FOR_ISOLATED_CODE_IMPLEMENTATION
- AUTOMATIC_FOLLOW_ON=FALSE
