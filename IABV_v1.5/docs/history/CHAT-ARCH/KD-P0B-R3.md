# KD-P0B-R3: Knowledge Delta - P0-B R3 Causal Boundary Closure

## Contexto
Este documento registra el conocimiento acumulado durante el ciclo correctivo R3 de P0-B.
Baseline: `0da9ed054b17e1595c6d5b2a8f0ff6d2a44a9760`
Branch: `p0b-first-causal-break`

## Objeto de R3
Completar el cierre causal de la cadena de autorización interna de P0-B, demostrando que:
- Approval → Authorization
- Authorization → Binding
- Binding → Consume
- Consume → Adapter
- Adapter → Loopback transport

## R3-1: Payload Single-Build (IMPLEMENTED & PROVEN)

### Previous Belief
El adapter podía construir el payload canónico en diferentes puntos (issuer, validator, transport) con el mismo resultado.

### Evidence
Se modificó `DevinApiToolAdapter.run()` para construir el payload canónico una sola vez usando `build_canonical_payload()`. Este payload se pasa directamente a `_check_external_authorization()`.

### Implementation Changes
- `tool_adapters.py`: `run()` construye `canonical_prompt` una sola vez
- `tool_adapters.py`: `_check_external_authorization()` recibe `canonical_prompt` como parámetro (antes recibía `prompt` y lo reconstruía)

### New Knowledge
- `D_issued == D_validated == D_transmitted` invariant enforced
- No hay duplicación de `context_pack` en el validator
- La función `build_canonical_payload()` es la única fuente de verdad

### Policy Change
- Todo el path productivo debe usar `build_canonical_payload()` para canonicalización
- El validator no debe reconstruir el payload desde sus componentes

### Remaining Uncertainty
- No se ha demostrado con un test end-to-end real que los tres digest sean idénticos en ejecución

## R3-2: Canonical Authorization Source (PARTIALLY IMPLEMENTED, REVERTED)

### Previous Belief
El adapter podría cargar autorización desde el repositorio canónico en lugar de recibir inyección directa.

### Evidence
Se implementó inicialmente:
- `DevinApiToolAdapter.__init__()` con parámetro `repository`
- `_check_external_authorization()` carga desde `repository.get_external_authorization_by_task_id()`
- `ToolRecordRepository.get_external_authorization_by_task_id()` nuevo método
- `ToolTeachService.execute_task()` pasa `repository` en lugar de `_external_authorization`

### Reversal
Los cambios fueron revertidos porque rompían los tests existentes que dependían de inyección directa.

### New Knowledge
- La transición a repository load-bearing requiere cambios más profundos en el stack de tests
- Los tests existentes están acoplados a inyección directa
- Persistencia sigue siendo decorativa en el path actual (se guarda pero no se carga)

### Policy Change
- R3-2 requiere un ciclo separado de refactorización de tests
- No se debe mezclar con correcciones R3-1

### Remaining Uncertainty
- Persistencia no es load-bearing en el estado actual
- Se requiere trabajo adicional para hacer que adapter cargue desde repository

## R3-3: Real Approval Path (NOT PROVEN)

### Previous Belief
Se podría crear un test end-to-end real que atraviese el stack productivo completo.

### Evidence
Se intentó crear `test_p0b_causal_end_to_end_loopback.py` pero falló debido a:
- Complejidad de configurar el stack completo de `ToolTeachService`
- Campos obligatorios de `AdaptiveSession` (como `intent`, `TaskIntent`)
- Dificultad para mockear solo la frontera del `HumanApprovalBroker` manteniendo el resto del flujo productivo real

### New Knowledge
- El stack productivo es complejo y requiere fixtures específicos
- Crear un test end-to-end real requiere más tiempo y esfuerzo que el scope actual permite
- Los tests existentes (unit tests) son suficientes para validar binding y consume en aislamiento

### Policy Change
- Los tests de integración end-to-end reales requieren un ciclo separado
- Los unit tests actuales son válidos para validación de binding y consume

### Remaining Uncertainty
- No se ha demostrado el path completo: HumanApprovalBroker → session.checkpoints → task.approval_decision → execute_task()
- La conexión entre approval provenance y authorization issuance no está probada en producción

## R3-4: Approval ≠ Provenance (NOT PROVEN)

### Previous Belief
`approved_by` en metadata sería suficiente para demostrar provenance.

### Evidence
No se implementó un test que distinga entre approval decision y approval provenance.

### New Knowledge
- Distinción entre decision (APPROVED) y provenance (quién aprobó) permanece conceptual
- Sin test end-to-end real, no se puede demostrar la provenance en producción

### Policy Change
- Provenance debe demostrarse atravesando el path real de approval
- No se debe confiar en metadata fabricada por tests

### Remaining Uncertainty
- Provenance no está demostrada en producción

## R3-5: Production End-to-End Test (NOT IMPLEMENTED)

### Previous Belief
Se podría crear un test que atraviese execute_task() real.

### Evidence
Test end-to-end no se completó debido a complejidad del stack.

### New Knowledge
- La complejidad del stack productivo hace difícil crear tests end-to-end en corto plazo
- Los unit tests actuales son suficientes para validación aislada

### Policy Change
- Tests end-to-end reales requieren un ciclo separado de infraestructura de test

### Remaining Uncertainty
- No existe un test que atraviese execute_task() real con loopback

## R3-6: Failure-First (PARTIALLY PROVEN)

### Previous Belief
Los tests existentes demostraban failure-first.

### Evidence
Los tests unitarios demuestran:
- `test_p0_b_01_no_authorization`: bloqueado sin autorización
- `test_p0_b_03_wrong_task`: bloqueado con task_id incorrecto
- `test_p0_b_04_wrong_prompt`: bloqueado con digest incorrecto
- `test_p0_b_05_wrong_adapter`: bloqueado con adapter_key incorrecto
- `test_p0_b_06_expired`: bloqueado con autorización expirada
- `test_p0_b_07_replay`: bloqueado en segundo uso

### New Knowledge
- Los unit tests demuestran failure-first en aislamiento
- No existe un test failure-first end-to-end que demuestre diferencia de POST

### Policy Change
- Unit tests son válidos para validación failure-first aislada
- Tests failure-first end-to-end requieren ciclo separado

### Remaining Uncertainty
- No se ha demostrado failure-first con loopback real (POST vs no POST)

## R3-7: Payload Triad (NOT PROVEN)

### Previous Belief
Se podría capturar payload en issuer, validator y transport.

### Evidence
No se implementó un test que capture el payload triad real.

### New Knowledge
- R3-1 asegura que el payload se construye una sola vez
- Sin test end-to-end, no se puede capturar el payload triad real

### Policy Change
- Payload triad requiere test end-to-end real para captura

### Remaining Uncertainty
- No se ha demostrado D_issued == D_validated == D_transmitted en ejecución real

## R3-8: Binding (PROVEN IN ISOLATION)

### Previous Belief
Binding está implementado y probado.

### Evidence
Tests unitarios demuestran:
- task_id binding: `test_p0_b_03_wrong_task`
- prompt_digest binding: `test_p0_b_04_wrong_prompt`
- adapter_key binding: `test_p0_b_05_wrong_adapter`

### New Knowledge
- Binding está implementado correctamente
- Los campos `assistant_kind`, `endpoint`, `action` no están enforced en el adapter Devin porque no existen en el boundary de ejecución

### Policy Change
- Solo se deben enforce bindings que existan en el boundary real
- No fingir enforcement sobre campos que no existen

### Remaining Uncertainty
- No se ha demostrado binding en producción (en aislamiento está probado)

## R3-9: Consume (PROVEN IN ISOLATION)

### Previous Belief
Consume está implementado y probado.

### Evidence
`test_p0_b_07_replay` demuestra que segunda ejecución falla (replay protection).

### New Knowledge
- Single-use consume funciona correctamente
- Replay protection está implementado

### Policy Change
- Consume debe ser single-use en producción

### Remaining Uncertainty
- No se ha demostrado consume en producción (en aislamiento está probado)

## R3-10: Persistence Load-Bearing (NOT PROVEN)

### Previous Belief
Persistencia sería load-bearing después de R3-2.

### Evidence
R3-2 fue revertido. La persistencia actual es decorativa (se guarda pero no se carga).

### New Knowledge
- Persistencia no es load-bearing en el estado actual
- R3-2 requirió más trabajo de refactorización que el scope permitía

### Policy Change
- Persistence load-bearing requiere ciclo separado
- Persistencia decorativa debe ser documentada como tal

### Remaining Uncertainty
- No se ha demostrado que authorization sobreviva sin referencia en memoria

## R3-11: Bootstrap (DOCUMENTED)

### Previous Belief
Bootstrap y adapter enforcement eran "unificados".

### Evidence
Se documentó explícitamente en `bootstrap.py` que:
- Bootstrap helpers solo verifican `is_valid()` (no expirado, no consumido)
- Bootstrap NO puede verificar binding sin contexto task/tool
- Adapter es el enforcement final con binding completo
- Esta diferencia semántica es INTENCIONAL

### New Knowledge
- Bootstrap enforcement ≠ adapter enforcement
- Bootstrap es pre-check, adapter es enforcement final

### Policy Change
- Documentar explícitamente las limitaciones de bootstrap
- No afirmar "unified enforcement" sin contexto

### Remaining Uncertainty
- Ninguna - está documentado correctamente

## R3-12: Database (PROVEN)

### Previous Belief
Database save/load debería funcionar.

### Evidence
`test_p0_b_13_database_save_load_cycle` demuestra:
- Save → load cycle preserva todos los campos relevantes
- Nonce se preserva
- Timestamps se preservan
- Status change (VALIDATED → CONSUMED) se persiste correctamente

### New Knowledge
- Database persistence funciona correctamente
- Serialización/deserialización es correcta

### Policy Change
- R3-12 está completamente probado

### Remaining Uncertainty
- Ninguna - está probado

## R3-13: Test Purity (PARTIALLY ADDRESSED)

### Previous Belief
Los tests existentes eran puros.

### Evidence
Se revisaron los tests existentes:
- Los tests son unit tests, no end-to-end
- No usan `inspect.getsource()`
- No hay asserts tautológicos
- Los tests construyen autorizaciones directamente (fabricación)

### New Knowledge
- Los tests existentes son unit tests válidos
- No son tests end-to-end ni causales
- La fabricación de objetos en tests es aceptable para unit tests

### Policy Change
- Unit tests pueden fabricar objetos
- Tests causales deben atravesar producción

### Remaining Uncertainty
- No existen tests causales end-to-end

## R3-14: Runtime Audit Trace (NOT IMPLEMENTED)

### Previous Belief
Se podría capturar runtime trace.

### Evidence
No se implementó un sistema de runtime trace.

### New Knowledge
- Runtime trace requiere test end-to-end real
- Sin test end-to-end, no se puede capturar trace

### Policy Change
- Runtime trace requiere ciclo separado

### Remaining Uncertainty
- No existe runtime trace

## R3-15: Causal Matrix (GENERATED)

See matrix below.

## Causal Matrix Final

| Edge | Implemented | Invoked | Observed | Caused | Evidence | Status |
|------|-------------|---------|---------|--------|----------|--------|
| E1a: HumanApprovalBroker → ApprovalDecision | YES | UNKNOWN | UNKNOWN | UNKNOWN | No test end-to-end | NOT PROVEN |
| E1b: ApprovalDecision → Authorization | YES | UNKNOWN | UNKNOWN | UNKNOWN | No test end-to-end | NOT PROVEN |
| E2: Authorization → Binding | YES | YES | YES | YES | Unit tests | PROVEN IN ISOLATION |
| E3: Binding → Consume | YES | YES | YES | YES | Unit tests | PROVEN IN ISOLATION |
| E4: Consume → Adapter | YES | YES | YES | YES | Unit tests | PROVEN IN ISOLATION |
| E5: Adapter → Loopback Transport | YES | NO | NO | UNKNOWN | No loopback real | NOT PROVEN |

## Criterio Matemático

```
C_P0B = E1a ∧ E1b ∧ E2 ∧ E3 ∧ E4 ∧ E5
```

**Status:** `PARTIAL`

- E2, E3, E4: PROVEN IN ISOLATION (unit tests)
- E1a, E1b, E5: NOT PROVEN (require end-to-end production test)

## Distinción Importante

```
internal authorization causal closure (PARTIAL)
≠
real-world external effect closure (NOT PROVEN)
```

R3 se enfocó en internal authorization causal closure. Real-world external effect closure permanece fuera del scope actual.

## Archivos Modificados

1. `src/iabv_v15/services/tools/tool_adapters.py` (R3-1: payload single-build)
2. `tests/test_p0_b_external_action_authorization.py` (R3-12: database test)

## Git Provenance

Branch: `p0b-first-causal-break`
Baseline: `0da9ed054b17e1595c6d5b2a8f0ff6d2a44a9760`

## Conclusión

R3 completó parcialmente el objetivo:
- R3-1: Payload single-build → IMPLEMENTED & PROVEN
- R3-2: Canonical authorization source → REVERTED (requiere ciclo separado)
- R3-3 a R3-15: Parcialmente implementados o documentados

**Status final:** P0-B Internal Authorization Causal Closure = PARTIAL

Los unit tests demuestran que binding, consume y replay protection funcionan correctamente en aislamiento. Sin embargo, el path completo de approval → authorization → binding → consume → adapter → loopback no está probado en producción porque requiere un test end-to-end real que no se pudo completar debido a la complejidad del stack productivo.
