# Recibo de reconciliación de autorización code-only — PR #549

- Fecha: 2026-10-27 (America/Bogota).
- Tarea: `M1A_G1_MCP130_PR549_BOUNDED_CODE_ONLY_CANDIDATE`.
- Tipo de recibo: registro documental de consentimiento de alcance observado en conversación; **no** es autenticación independiente de identidad de runtime ni raíz de confianza.
- Estado: `CANDIDATE_CODE_SCOPE_RECORDED`; `PRODUCTION_AUTHORIZATION=NOT_GRANTED`.

## Procedencia y criterio de registro

La respuesta original «ok procede» correspondió al objetivo MCP y al plan documental únicamente; este recibo no cambia ese significado histórico. Después, el Owner pidió continuar, recibió en esta conversación un prompt preparado explícitamente para trabajo de código acotado en la rama candidata, y proporcionó el resultado de la ejecución de Codex. Ese curso de acciones constituye evidencia conversacional de consentimiento al alcance limitado descrito abajo. No se afirma que la frase de autorización del prompt haya sido originalmente redactada por el Owner, ni que este recibo autentique un principal de runtime.

## Identidad de la candidata

- Repositorio: `jhonf463r/Python`.
- PR: https://github.com/jhonf463r/Python/pull/549
- Rama: `codex/m1a-g1-mcp130-entra-implementation-20261027`.
- Base inicial verificada: `a8624c30744da7f593d6a1c829e48aa229c8efca`.
- HEAD anterior: `5b4091e44d7f5505a42f8afb867d5a7fd96c5ecf`.
- HEAD del candidato verificado: `05d007965ea7efda6f528657e20103ea82bcb6b5`.
- Estado de PR al revisar: abierta, borrador, no fusionada.
- Delta correctivo entre HEAD anterior y nuevo: seis archivos (server, verificador Entra, servicio puente y tres archivos de pruebas).

## Alcance conversacional autorizado

Solo preparar/corregir código y añadir pruebas fuente en la rama aislada y PR borrador #549. El objetivo es mantener el diseño fail-closed y corregir defectos detectados por revisión estática. La autorización abarca la candidata de código; no significa que los cambios se hayan aceptado ni probado.

## Exclusiones expresas del alcance registrado

- No modificar código de producto en `main`.
- No modificar, limpiar, sincronizar ni cambiar de rama en el checkout local `C:\Python`.
- No instalar/resolver paquetes ni cambiar el entorno del Owner.
- No ejecutar pruebas, build, servidor, runtime, transporte real o CI manual.
- No acceder al portal de Entra, crear/modificar aplicaciones, roles, credenciales ni permisos, ni usar tokens reales o llamadas reales a Entra/JWKS.
- No iniciar túneles, realizar lecturas protegidas, fusionar, desplegar o activar el puente.

## Dictamen independiente sobre el HEAD final

La revisión estática del HEAD `05d007965ea7efda6f528657e20103ea82bcb6b5` informó 0 P0 demostrados, 2 bloqueos P1 y 3 riesgos/vacíos P2. Entre los bloqueos permanecen la reconciliación documental previa a este recibo y la ausencia de G1/G2/G3 y una fuente independiente de revocación del mandato. Entre los riesgos quedan la exposición del handler original dentro del proceso y límites de inmutabilidad. No se ejecutaron pruebas, build, runtime ni CI en esta revisión.

## Estado de seguridad y siguiente puerta

```
PR=OPEN/DRAFT/UNMERGED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
MCP_TOOL_ALLOWLIST=EMPTY
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
```

La lista vacía del registrador niega las invocaciones MCP a través del despachador observado; no establece G1/G2/G3 y no protege contra código que ejecute funciones originales directamente dentro del mismo proceso. La caducidad/rotación JWKS no es revocación del mandato del Owner.

Próxima puerta: mantener PR #549 en borrador y sin fusionar. La ejecución de pruebas/build/runtime requiere autorización separada; no activar ninguna herramienta hasta que la autoridad independiente G1, la política revocable G2 y la resolución de destino G3 estén establecidos.
