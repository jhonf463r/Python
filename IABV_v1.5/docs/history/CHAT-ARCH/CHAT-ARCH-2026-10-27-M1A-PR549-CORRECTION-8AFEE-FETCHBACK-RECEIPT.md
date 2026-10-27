# M1A / PR #549 — recibo de corrección estática y fetch-back

- Fecha: 2026-10-27 (America/Bogota).
- Repositorio: `jhonf463r/Python`.
- PR: https://github.com/jhonf463r/Python/pull/549.
- Rama: `codex/m1a-g1-mcp130-entra-implementation-20261027`.
- HEAD previo: `05d007965ea7efda6f528657e20103ea82bcb6b5`.
- Nuevo HEAD candidato: `8afee332e5e0f65715013effcee57b215413547c`.
- Main canónico antes del follow-up documental: `6d69e87d63131a99ee4748c0f6a2a0b8b2cbe82d`.

## Cambios del commit candidato

Mensaje: `[skip ci] Harden fail-closed tool guard and auth binding`.

- `server.py`: los wrappers de herramientas MCP ya no incorporan referencias al handler original ni `functools.wraps`/ `__wrapped__`. Conservan nombre, documentación, anotaciones y firma para el esquema de herramienta, pero niegan toda invocación porque todavía no existe un dispatcher G1/G2/G3 y la lista permitida está vacía. El objeto de preflight también rechaza la eliminación ordinaria de campos.
- `entra_token_verifier.py`: los campos que fijan la confianza (`_config`, `_issuer_url`, `_metadata_url`, `_jwks_cache_seconds`) rechazan reasignación/eliminación ordinarias tras inicializarse.
- `test_mcp_server.py`: las pruebas de comportamiento usan un registro de handlers separado que vive solo en el módulo de tests, no en las herramientas registradas en producción. Se añaden contratos para token sintético válido que sigue bloqueado por falta de autoridad de operación y para HTTP 403 por alcance insuficiente.
- `test_entra_token_verifier.py`: se añaden contratos fuente de no reasignación/no eliminación de los campos de confianza.

Se verificó por lectura de vuelta el HEAD exacto y se comprobaron los anchors estáticos. No es un resultado de ejecución.

## Estado y límites

```
PR=OPEN/DRAFT/UNMERGED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
CI=NOT_RUN
WORKFLOW_RUNS_FOR_HEAD=NONE_FOUND
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
```

El dictamen independiente anterior cubría `05d007965ea7efda6f528657e20103ea82bcb6b5`. Hace falta una revisión estática separada del HEAD exacto `8afee332e5e0f65715013effcee57b215413547c`. No se ejecutaron pruebas, CI, instalaciones, llamadas a Entra/JWKS, túneles ni lecturas protegidas; no hubo merge ni despliegue.
