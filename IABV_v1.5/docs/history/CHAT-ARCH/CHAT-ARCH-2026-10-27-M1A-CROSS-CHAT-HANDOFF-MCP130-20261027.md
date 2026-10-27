# Handoff entre chats — IABV / Entra G1 / MCP 1.30 (2026-10-27)

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
