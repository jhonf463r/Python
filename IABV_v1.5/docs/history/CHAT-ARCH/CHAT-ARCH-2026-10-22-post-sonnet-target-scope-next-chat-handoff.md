# IABV — continuidad para el nuevo chat tras el PASS de target_scope

- Episode ID: EP-20261022-SONNET-TARGET-SCOPE-CONTINUITY-01
- Fecha: 2026-10-22, America/Bogota.
- Tipo: handoff de continuidad; revisión estática recibida, estado remoto contrastado y ruta de trabajo reconciliada.
- North Star: GOVERNED_IABV_CODEX_BRIDGE
- Autoridad de routing: CURRENT-STATE.md. Este documento conserva contexto y evita repetición; no sustituye esa autoridad.
- Evidencia del dictamen: OWNER_SUPPLIED_INDEPENDENT_REVIEW. La rama, commit, blobs y comparación se consultaron directamente en GitHub en esta sesión.
- Estado global: DOCUMENTARY_HANDOFF_SAVED; M1 sigue bloqueada; no hubo ejecución local ni tests.

## 1. Resultado nuevo que sí cambia el estado

El Owner proporcionó el informe de Sonnet 4.6: REVIEW_VERDICT=PASS para la revisión estática del fragmento presentado. Esto cierra la objeción estática F-TS-1 del candidato; no cierra M1 ni habilita operaciones.

Hallazgos registrados:
- F-TS-1 queda cerrado en la rama candidata: desapareció la excepción abierta basada en block_target.startswith("consult_"). La ruta usa el conjunto explícito known_target_scopes.
- Caso A: consult_codex está registrado pero no aplica a la ruta audit; se omite sin bloquear la auditoría.
- Caso B: consult_unmapped_scope no está registrado; debe bloquear con governance_blocked=true y reason=operational_block_active.
- El informe aportado dice que cinco escenarios adversariales no abren bypass: alcance global "*", assistant_kind cruzados, doble "*", alcance registrado con rol diferente y consult-prefijo no registrado.
- La revisión fue estática sobre el fragmento suministrado. El informe explícitamente no sustituye la ejecución de las seis pruebas de aceptación ni valida un servidor en ejecución.

Interpretación correcta: PASS de la revisión documental/estática sobre el candidato remoto, no PASS de tests, runtime, servidor activo, ruta de lectura o puente.

## 2. Identidad remota exacta y divergencia del candidato

Snapshot consultado antes del commit documental de este handoff:
- main en ese momento: f93b513f7d12c321a65077335d677c998373c764
- rama candidata: fix/iabv-operational-block-target-scope-repair-20261022
- commit candidato: b7c3fffaec4ff3b78b1ca03ae64ead949236f504
- comparación capturada: status=diverged, ahead_by=1, behind_by=3
- merge-base: e61c5043bbdd8ea536ed5c9e642d80ff228ee897

La candidata nació desde e61c5043bbdd8ea536ed5c9e642d80ff228ee897. Después, main recibió tres commits documentales:
- 4f1584dea9b7e357f06b6946924216d152d34b05 — docs(iabv): record target scope review and restore current routing.
- 7ef7518d8f257a7788451808d89dc896a6fc1404 — docs(iabv): clarify candidate comparison after routing sync.
- f93b513f7d12c321a65077335d677c998373c764 — docs(iabv): make candidate divergence note durable.

El contraste confirmó que la candidata está divergente de main; los tres commits de la línea de main enumerados arriba modifican documentos de continuidad, no el código del candidato. La comparación de este apartado es una captura anterior al presente commit documental: volver a consultar compare antes de cualquier decisión futura sobre integración; no repetir ni congelar un ahead/behind viejo.

Los únicos archivos de código dentro del commit candidato son:
- IABV_v1.5/src/iabv_v15/infra/mcp/server.py — blob 1d3861dedd2734ca74e51d06647aa888d54ceed4.
- IABV_v1.5/tests/test_mcp_server.py — blob 943e05657a2b193d26806a5176a93957249b2d7f.

Comparación original base→candidato: server.py, 64 adiciones y 7 eliminaciones; test_mcp_server.py, 163 adiciones. No se fusionó, rebasó, desplegó ni adoptó la rama. No abrir una PR ni integrar por inferencia a partir de PASS estático.

Referencias:
- Rama: https://github.com/jhonf463r/Python/tree/fix/iabv-operational-block-target-scope-repair-20261022
- Commit: https://github.com/jhonf463r/Python/commit/b7c3fffaec4ff3b78b1ca03ae64ead949236f504
- Registro de la revisión: CHAT-ARCH-2026-10-22-candidate-target-scope-repaired-review.md

## 3. Qué se verificó en la candidata y qué no

Lectura pública de la rama confirmó:
- el chequeo abierto por prefijo consult_ ya no aparece;
- known_target_scopes sí existe como conjunto explícito;
- las ocho funciones enfocadas están presentes en test_mcp_server.py;
- las dos pruebas discriminantes nuevas se llaman test_audit_ignores_registered_consult_scope_for_other_route y test_unknown_consult_target_scope_fails_closed.

Las ocho funciones enfocadas son seis casos previos de aceptación más dos pruebas discriminantes nuevas:
1. test_audit_route_ignores_ram_block_scoped_to_heavy_local_model
2. test_heavy_local_model_route_still_respects_ram_block
3. test_ui_focus_block_only_applies_to_ui_scoped_audit_operation
4. test_fully_unspecified_active_block_remains_global
5. test_unknown_operational_target_scope_fails_closed
6. test_explicit_audit_block_still_blocks_audit_route
7. test_audit_ignores_registered_consult_scope_for_other_route
8. test_unknown_consult_target_scope_fails_closed

TESTS=NOT_RUN. No afirmar que esas funciones pasan. El código de prueba crea servicios falsos y llama al helper de gate; la lectura estática no demuestra ausencia de efectos secundarios en toda la cadena de importación. No se hizo validación transitive-import completa. Por eso, el riesgo de que algún entorno de ejecución arranque Ollama u otro proceso no se puede declarar descartado sin la autorización, aislamiento y recibo correspondientes.

No se leyó checkout local, no se identificó la revisión del servidor MCP activo, y no se lanzó IABV, MCP, Codex CLI/App Server ni Ollama.

## 4. Explicación causal sin sobreafirmaciones

La evidencia previa mostraba un intento de list_repo_directory rechazado por el gate MCP con governance_blocked=true y reason=operational_block_active, con el detalle «Hay bloqueos activos en WorldModelSnapshot para esta ruta». En la versión pública de main examinada antes del arreglo, el gate podía tratar assistant_kind vacío como global sin aplicar bien target_scope. El bloqueo reportado era de RAM, target_scope=heavy_local_model, assistant_kind vacío.

La corrección candidata pretende que un bloqueo específico para heavy_local_model siga bloqueando la operación de benchmark/modelo pesado, sin convertirse en bloqueo de una lectura audit no relacionada. Los alcances reconocidos quedan cerrados: que un string empiece por consult_ ya no basta para considerarlo válido; cualquier alcance desconocido continúa fail-closed.

La hipótesis de incompatibilidad del gate en el código público es una explicación estática plausible de aquel rechazo, pero:
- LIVE_SERVER_CAUSALITY=UNVERIFIED;
- LIVE_SERVER_IDENTITY=UNVERIFIED;
- GLOBAL_ROUTE_EXISTENCE=UNRESOLVED;
- el arreglo de la rama candidata no altera el servidor que ya está en ejecución;
- cambiar el alcance de un bloqueo no concede autoridad ni libera por sí solo el bloqueo.

No confundir tres afirmaciones distintas: (1) el candidato corrige el patrón de código público revisado; (2) el servidor activo utiliza esa revisión; (3) existe una ruta gobernada autorizada y disponible. Solo la primera tiene respaldo estático en este checkpoint.

## 5. La tarea primaria no se mueve: M1

PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK_ID=M1
ACTIVE_TASK=IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
CURRENT_STATUS=BLOCKED_WAITING_FOR_SUPPORTED_AUTHORITY_OR_ROUTE

M1 sigue siendo la única tarea técnica activa. La revisión de target_scope es un subtrabajo documental acotado; no desplaza M1 ni demuestra que la ruta local de lectura ya exista.

Situación al último inventario acotado:
- SESSION_EXPOSED_SUPPORTED_ADMIN_READ_TOOL=NOT_FOUND
- GLOBAL_ROUTE_EXISTENCE=UNRESOLVED
- LIVE_SERVER_AND_CHECKOUT_IDENTITY=UNVERIFIED
- autoridad capaz de emitir una decisión de lectura y, separadamente, resolver el bloqueo aplicable: no identificada en esta sesión.

La falta de un tool visible en la sesión solo significa NOT_FOUND en la superficie inspeccionada; no demuestra que no haya interfaz u operador en otros entornos. No inventar una herramienta, persona, autorización o recibo.

Criterio de aceptación de M1: identificar y verificar una interfaz/operador legítimo, el principal emisor de confianza, la identidad del servidor y raíz/checkout reales, el alcance explícito de solo lectura y las rutas permitidas, caducidad/revocación, condiciones de bloqueo/liberación decididas por autoridad independiente y un recibo de lectura correlacionado. La propia lectura no debe poder auto-liberar el bloqueo.

La autorización limitada previamente concedida para inspección estática no necesita re-preguntarse; falló porque el gate denegó la operación. Si aparece la ruta válida, esa autorización cubre únicamente el mapeo estático permitido (registro/llamada/consumidor del executor y campos efectivos de política no secretos incluidos en la whitelist). Excluye data/, SQLite, secretos, credenciales, .env, cambios de archivos, pruebas, builds, runtime, lanzamientos, reload de modelos, merge/adopción y transporte real.

Siguiente acción única: continuar solo por la superficie administrativa/gobernanza legítima o con el operador responsable del servidor y checkout reales. Si la sesión no expone ninguna ruta nueva y no hay autoridad identificada, conservar NOT_FOUND para la superficie de esa sesión y GLOBAL_ROUTE_EXISTENCE=UNRESOLVED; no realizar otro escaneo amplio ni usar un lector alternativo para saltar el gate.

## 6. Gates permanentes

GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
LOCAL_SOURCE_READ=NOT_RUN
TESTS=NOT_RUN
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED

No iniciar, modificar o reinstalar Ollama/modelos; no cambiar GPU/CUDA, variables de entorno o alias; no lanzar IABV/MCP/Codex CLI/App Server; no pruebas, builds, probes ni transporte real; no acceder a M0A/data/SQLite/secretos; no leer, limpiar, resetear, hacer checkout, stash, pull ni revertir el checkout local sucio. La nota de continuidad jamás se convierte en autorización de ejecución.

Las pruebas específicas del candidato son un carril secundario pendiente. Solo proponer/ejecutar pruebas focalizadas en entorno aislado cuando exista la autorización explícita aplicable; no asumir que el PASS de Sonnet las autoriza. Verificar también el plan para impedir lanzamientos involuntarios de modelos antes de ejecutar.

## 7. Errores y rutas que no se deben repetir

- No repetir la revisión de OpenCode del builder-grant successor v0.2: ya se recibió y quedó documentada; es histórica y no es la siguiente acción.
- No volver a depender de intentos 404 a enlaces de documentos ni a reabrir el catálogo genérico de herramientas por costumbre.
- No enviar otra petición genérica por la misma ruta de IABV general-chat que respondió con un broad auto-scan fuera de alcance.
- No hacer escaneo general de cientos de archivos, no forzar la lectura local, no buscar lectores alternativos para evadir la gobernanza.
- No tratar OWNER_REPORTED, un informe conversacional, un spinner, un test count o un dictamen estático como recibo de ejecución.
- No repetir el antiguo compare ahead_by=1 / behind_by=0; la base de la rama y main ya divergieron con commits documentales.
- No reabrir F-TS-1 sin evidencia contradictoria. Si aparece una objeción nueva, relacionarla con el commit/blob exacto y distinguirla de las ya cerradas.

## 8. Ollama/RAM: hipótesis preservada en la bandeja, no tarea activa

El Owner ha expresado que algunas pruebas/consultas de Codex parecen activar Ollama y consumir mucha RAM, sin estar claro si el razonamiento de IABV realmente lo requiere. Esto sigue siendo una hipótesis legítima, no una causa demostrada. Los registros anteriores identifican cobertura incompleta del monitor y falta de métricas correlacionadas de Ollama; no se debe afirmar causalidad ni ausencia continua del proceso. También debe distinguirse inferencia local requerida, warm-up/ready, fallback, loop en segundo plano y arranque incidental.

Clasificación: PARK_FOR_LATER salvo que nueva evidencia haga este riesgo una dependencia directa del trabajo activo o un riesgo inmediato. No ejecutar la prueba para “mirar qué pasa”, no recargar modelos ni extender monitorización sin autorización. Cuando se autorice un diagnóstico futuro, exigir request/attempt IDs, marcas de tiempo, estado del proceso, métricas RAM, estado Ollama y resultado correlacionados; preservar el entorno local.

## 9. Continuidad y comportamiento del coordinador

Mantener el método documentado en CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md:
- un North Star y una sola tarea activa;
- las ideas se registran en bandeja con clasificación (dependencia directa, después, duplicada/resuelta, fuera de alcance), sin desplazar automáticamente M1;
- progreso expresado como artefactos, dependencias y recibos, sin porcentajes inventados;
- separar dato de fuente, informe del Owner, inferencia y propuesta;
- al inicio del nuevo chat, recuperar CURRENT-STATE.md y este handoff; no pedir que el Owner repita decisiones ya registradas;
- no declarar que el coordinador tiene ejecución/runtime o reutilización causal demostrados. COORDINATOR_RUNTIME=NOT_PROVEN y CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN hasta observar un ciclo posterior real de recuperación, aplicación, verificación y persistencia.

## 10. Arranque exacto del próximo chat

1. Leer la cabecera más reciente de CURRENT-STATE.md como única autoridad de routing y después este handoff junto con CHAT-ARCH-2026-10-22-candidate-target-scope-repaired-review.md.
2. Revalidar en GitHub el SHA de main y la comparación actual de la rama candidata antes de cualquier decisión sobre integración; el compare aquí registrado es una fotografía anterior a este commit documental.
3. Conservar M1 como tarea activa. No iniciar por tests de la candidata, por investigación de Ollama ni por una auditoría general.
4. Comprobar solo si hay una superficie administrativa/de gobernanza específica realmente disponible para solicitar la lectura acotada. Si no existe en la superficie actual, registrar el límite de la búsqueda sin generalizarlo y detener la ruta; no sondear lectores alternativos.
5. No tocar el checkout local ni ejecutar comandos, procesos, pruebas, builds o transporte.
6. La siguiente salida debe identificar: avance verificable, frontera aún abierta, precondición exacta, una sola acción siguiente y el actor correcto. No volver a pedir al Owner que elija entre tareas ya ordenadas.

END_STATE=PASS_STATIC_REVIEW_ONLY; M1_BLOCKED; KEEP_BLOCKED; LOCAL_WORKTREE_UNTOUCHED
