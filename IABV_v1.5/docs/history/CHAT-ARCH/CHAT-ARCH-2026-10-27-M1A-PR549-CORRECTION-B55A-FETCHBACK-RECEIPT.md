# M1A / PR #549 — recibo de seguimiento de pruebas fuente y fetch-back

- Fecha: 2026-10-27 (America/Bogota).
- Repositorio: `jhonf463r/Python`.
- PR: https://github.com/jhonf463r/Python/pull/549.
- Rama: `codex/m1a-g1-mcp130-entra-implementation-20261027`.
- HEAD previo: `8afee332e5e0f65715013effcee57b215413547c`.
- HEAD actual de la candidata: `b55a39322d04eff5fc501629c5f331d8ea22c291`.
- Main antes de este recibo documental: `3b6d2f7056777141ec3a04020654455e811697e1`.

## Cambios del último commit

Mensaje: `[skip ci] Isolate MCP test handlers and cover ID-token audience denial`.

Solo se modificaron:
- `IABV_v1.5/tests/test_mcp_server.py`: los handlers originales de las pruebas antiguas se capturan en un mapa de test y la monkeypatch se instala/restaura por cada prueba. Así se evita una mutación global de la clase durante toda la colección.
- `IABV_v1.5/tests/test_entra_token_verifier.py`: añade una prueba fuente para un token sintético con audiencia igual a un client ID permitido, sin marcadores `nonce`/`at_hash`, que debe ser rechazado por la comparación de audiencia de la API.

Los dos archivos se recuperaron de vuelta desde el HEAD exacto. No se ejecutó código ni se ejecutaron pruebas.

## Estado

```
PR=OPEN/DRAFT/UNMERGED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
CI=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
```

El dictamen independiente previo no cubre este HEAD. Revisión estática independiente nueva pendiente sobre `b55a39322d04eff5fc501629c5f331d8ea22c291`. La aprobación documental no equivale a autenticación operativa ni establece autoridad G1/G2/G3.



## Addendum — dictamen independiente posterior al fetch-back B55A (2026-10-27)

Este addendum actualiza el indicador de revisión pendiente sin sustituir ni borrar el recibo original de fetch-back que precede a esta sección.

- `REVIEWED_HEAD=b55a39322d04eff5fc501629c5f331d8ea22c291`
- `BASE_SHA=a8624c30744da7f593d6a1c829e48aa229c8efca`
- `MAIN_SHA_BEFORE_DOCUMENTATION_UPDATE=b8e18eb725a951209854e0b0756e88a7c7cbdc88`
- `PR=OPEN; DRAFT=TRUE; MERGED=FALSE`
- `P0=0_DEMONSTRATED_IN_REVIEWED_DELTA; P1=1; P2=3`
- `TESTS=NOT_RUN; BUILD=NOT_RUN; RUNTIME=NOT_RUN; CI=NOT_RUN`
- `G1/G2/G3=NOT_ESTABLISHED`
- `MCP_TOOL_ALLOWLIST=EMPTY`
- `PROTECTED_READS=FAIL_CLOSED; TUNNEL=DISABLED; BRIDGE=BRIDGE_NOT_READY`
- `MERGE=NOT_AUTHORIZED; PRODUCTION_ACTIVATION=NOT_AUTHORIZED`

### Dictamen

**P1 — bloqueo de aceptación:** el código mantiene denegadas las invocaciones ordinarias por la lista permitida vacía, pero no establece G1 (raíz/mandato independiente), G2 (política autorizada y revocable), G3 (resolución autoritativa de operación a destino) ni una fuente independiente conectada para revocar el mandato del Owner. No añadir herramientas a la lista para sortear este bloqueo.

**P2 — límites y evidencia:** (1) wrapper y sellos de configuración no constituyen aislamiento frente a código hostil que ya controla el mismo proceso Python; (2) los contratos añadidos y la compatibilidad con el SDK se revisaron solo estáticamente, sin ejecutar pruebas/build/runtime/CI; (3) la entrada previa que describía esta revisión como pendiente queda supersedida por este addendum. La revisión no demostró defectos P0 en el delta examinado, pero tampoco certifica componentes no examinados o comportamiento en ejecución.

La revisión confirmó estáticamente ausencia de `__iabv_original_handler__` y `__wrapped__` en los wrappers de producción, ausencia de captura directa de `handler` en la clausura, rechazo ordinario mediante el registrador común (incluidas `write_repo_file`, `apply_text_patch` y `git_commit_and_push`), y alcance por prueba de la fixture que captura handlers. Los tests de token sintético válido pero operación denegada y el test HTTP `403` por scope insuficiente son contratos diferentes; ninguno se ha ejecutado.

### Estado y siguiente frontera

Dictamen recibido el 2026-10-27 para el HEAD exacto B55A. La actualización canónica posterior se limita a estos tres documentos de continuidad. No altera código de producto, la candidata, su base ni configuración de Entra. Mantener la PR en borrador sin merge ni activación. Cualquier ejecución de pruebas requiere autorización separada y precondiciones verificadas; no inferir aprobación a partir de esta revisión documental.
