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

