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
