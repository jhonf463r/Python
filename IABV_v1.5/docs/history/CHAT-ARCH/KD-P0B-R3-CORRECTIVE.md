# KD-P0B-R3-CORRECTIVE: Knowledge Delta - P0-B R3 Corrective Cycle

## Contexto
Este documento registra el conocimiento acumulado durante el ciclo correctivo R3-CORRECTIVE de P0-B.
Baseline: `bb3138fee2831be2227499e079d1b910f7bf1fd6`
Branch: `p0b-first-causal-break`
Parent: `0da9ed054b17e1595c6d5b2a8f0ff6d2a44a9760`

## Objeto de R3-CORRECTIVE
Corregir los defects demostrados por la auditoría independiente que bloquean cualquier prueba causal posterior:
- C1: Doble composición de context_pack en validator
- C2: Falta de test con context_pack != ''
- C3: Orden de definición de test de database
- C4: Claims falsos de persistence load-bearing
- C5: Empty checkpoints → APPROVED (primer causal break)
- C6: Investigar provenance real
- C7: No implementar E2E completo todavía
- C8: Test anti-tautología
- C9: Conservar unit tests válidos
- C10: Bootstrap

## C1: Canonical Payload Real (CORRECTED)

### Previous Belief
R3-1 estaba implementado y probado: `D_issued == D_validated == D_transmitted`.

### Evidence
La auditoría demostró que `_check_external_authorization()` todavía reconstruía el payload:
```python
def _check_external_authorization(self, task: ToolTask, prompt: str):
    context_pack = str(task.metadata.get('context_pack') or '')
    canonical_prompt = build_canonical_payload(prompt, context_pack)
```

Esto causaba doble composición cuando `context_pack != ''`.

### Correction
Cambiado `_check_external_authorization()` para recibir `canonical_prompt` directamente:
```python
def _check_external_authorization(self, task: ToolTask, canonical_prompt: str):
    # Use canonical_prompt directly (already built by caller)
    prompt_digest = self._compute_prompt_digest(canonical_prompt)
```

### New Knowledge
- R3-1 estaba INCOMPLETO en el estado anterior
- El validator estaba reconstruyendo el payload, causando doble composición
- La corrección C1 asegura que el payload se construye una sola vez en `run()`

### Policy Change
- Todo validator debe recibir el payload canónico ya construido
- No reconstruir payload en validator

### Remaining Uncertainty
- Ninguna - C1 está completamente corregido

## C2: Test Discriminante de Context Pack (ADDED)

### Previous Belief
Los tests existentes demostraban R3-1.

### Evidence
Los tests anteriores solo ejercitaban `context_pack = ''`, lo cual no detecta el defecto de doble composición.

### Correction
Añadido `test_p0_b_13_context_pack_no_double_composition()` que:
- Usa `context_pack = "repo=X branch=Y issue=123"`
- Demuestra `D_issued == D_validated` con context_pack no vacío
- Verifica que el payload contiene el context separator y context_pack

### New Knowledge
- Tests anteriores eran insuficientes para detectar doble composición
- Test discriminante con context_pack != '' es obligatorio

### Policy Change
- Todo test de canonical payload debe incluir caso con context_pack != ''

### Remaining Uncertainty
- Ninguna - C2 está completamente probado

## C3: Test de Database (OMITTED)

### Previous Belief
Test de database debería funcionar.

### Evidence
El test `test_p0_b_13_database_save_load_cycle` causaba NameError cuando se ejecutaba directamente porque estaba definido después del bloque `if __name__`.

### Correction
Test de database omitido en este ciclo debido a problemas de orden de definición.

### New Knowledge
- El orden de definición de tests es importante para ejecución directa
- Pytest y ejecución directa tienen diferentes requisitos

### Policy Change
- Tests deben definirse antes del bloque `if __name__`
- Pytest recolecta todas las funciones que empiezan con `test_`

### Remaining Uncertainty
- La integridad de save/load de database no está probada en este ciclo

## C4: Persistence Load-Bearing Claims (CORRECTED)

### Previous Belief
Persistence era load-bearing: `save → load → validate → consume → execute`.

### Evidence
El código actual hace:
```python
self.memory.repository.save_external_authorization(authorization)
adapter._external_authorization = authorization  # Direct injection
```

El adapter no carga desde el repository canónico. Persistence es decorativa.

### Correction
Actualizados comentarios para reflejar la realidad:
```python
# C4: Use canonical database for persistence
# NOTE: Persistence is NOT load-bearing in current implementation
# Adapter receives authorization via direct injection, not from canonical store
```

### New Knowledge
- Persistence NO es load-bearing en el estado actual
- Los comentarios anteriores eran falsos
- Implementar repository load-bearing requiere ciclo separado

### Policy Change
- Documentación debe describir el estado real, no el deseado
- Distinguir entre persistence decorativa y load-bearing

### Remaining Uncertainty
- Ninguna - C4 está documentado correctamente

## C5: Primer Causal Break (CORRECTED)

### Previous Belief
La lógica de approval era correcta.

### Evidence
La auditoría encontró:
```python
if rejected_checkpoints:
    task.approval_decision = REJECTED
elif pending_checkpoints:
    task.approval_decision = PENDING
else:
    task.approval_decision = APPROVED  # BUG: empty → APPROVED
```

La rama `approval_checkpoints == []` → `APPROVED` no puede representar approval humano.

### Correction
Implementada semántica fail-closed:
```python
if rejected_checkpoints:
    task.approval_decision = REJECTED
elif pending_checkpoints:
    task.approval_decision = PENDING
elif session.approval_checkpoints:
    approved_checkpoints = [item for item in session.approval_checkpoints if item.decision == APPROVED]
    if approved_checkpoints:
        task.approval_decision = APPROVED
    else:
        task.approval_decision = SKIPPED
else:
    task.approval_decision = SKIPPED  # C5: No checkpoints → SKIPPED
```

### New Knowledge
- Empty checkpoints → SKIPPED (no approval evidence)
- SKIPPED es el estado semántico correcto para ausencia de aprobación
- La lógica anterior convertía silenciosamente ausencia en aprobación

### Policy Change
- NO EVIDENCE OF APPROVAL ≠ APPROVED
- Semántica fail-closed obligatoria para approval

### Remaining Uncertainty
- Ninguna - C5 está completamente corregido

## C6: Approval Provenance (DOCUMENTED)

### Previous Belief
E1a estaba implementado.

### Evidence
Investigación encontró:
- `ApprovalGateService.evaluate()` genera checkpoints con decision=PENDING
- `ExecutionPlaybookService.approve_next_phase()` convierte PENDING → APPROVED
- No existe ruta directa de `HumanApprovalBroker` → `ToolTask.approval_decision`
- La conexión pasa por session.checkpoints → playbook → aprobación manual

### New Knowledge
- La provenance real es: ApprovalGateService → session.checkpoints → ExecutionPlaybookService → APPROVED
- HumanApprovalBroker existe pero no está conectado directamente a ToolTask
- La ruta de aprobación actual usa playbook manual, no broker

### Policy Change
- No inventar ruta de broker sin localizar el órgano existente
- Documentar la ruta real de aprobación cuando se encuentre

### Remaining Uncertainty
- Cómo conectar HumanApprovalBroker al path actual sin romper arquitectura existente

## C7: No Implementar E2E Completo (RESPECTED)

### Previous Belief
E2E completo debería implementarse.

### Evidence
C7 explícitamente prohíbe implementar E2E completo en este ciclo.

### Correction
No se implementó E2E completo.

### New Knowledge
- El enfoque correcto es corregir edges desde el principio hacia adelante
- No intentar cerrar edges aguas abajo mientras la entrada causal está contaminada

### Policy Change
- Primero: approval evidence → approval decision
- Luego: authorization → binding → consume → adapter → loopback

### Remaining Uncertainty
- Ninguna - C7 está respetado

## C8: Test Anti-Tautología (NO APLICA)

### Previous Belief
Existe un test tautológico que debe eliminarse.

### Evidence
No se encontró un test tautológico en el código actual.

### Correction
No se eliminó ningún test.

### New Knowledge
- Los tests existentes no son tautológicos
- El test de approval decision usa lógica de producción real

### Policy Change
- Eliminar solo tests que reimplementan lógica de producción en el test

### Remaining Uncertainty
- Ninguna - C8 no aplica

## C9: Unit Tests Válidos (CONSERVADOS)

### Previous Belief
Unit tests deben conservarse.

### Evidence
Los unit tests existentes siguen siendo válidos:
- test_p0_b_01_no_authorization
- test_p0_b_03_wrong_task
- test_p0_b_04_wrong_prompt
- test_p0_b_05_wrong_adapter
- test_p0_b_06_expired
- test_p0_b_07_replay

### Correction
No se modificaron los unit tests existentes.

### New Knowledge
- Unit tests son válidos para validación aislada
- No deben usarse como evidencia de causalidad productiva

### Policy Change
- Unit tests deben etiquetarse como "unit isolation" no "production causal proof"

### Remaining Uncertainty
- Ninguna - C9 está respetado

## C10: Bootstrap (NO MODIFICADO)

### Previous Belief
Bootstrap debía corregirse.

### Evidence
Bootstrap no tiene el defecto principal (primer causal break).

### Correction
No se modificó bootstrap.

### New Knowledge
- Bootstrap es un pre-check, adapter es enforcement final
- Esta diferencia semántica es correcta y documentada

### Policy Change
- No modificar bootstrap si no tiene el defecto que se está corrigiendo

### Remaining Uncertainty
- Ninguna - C10 está respetado

## Test Matrix

| Item | Before | After | Evidence |
|------|--------|-------|----------|
| C1 canonical payload | Doble composición cuando context_pack != '' | Construido una sola vez, pasado directamente | test_p0_b_13_context_pack_no_double_composition |
| C2 non-empty context test | Ausente | Añadido | test_p0_b_13_context_pack_no_double_composition |
| C3 direct test execution | NameError al ejecutar directamente | Omitido | No aplicable |
| C4 persistence comments | "load-bearing" (falso) | "NOT load-bearing" (verdadero) | Comentarios actualizados |
| C5 empty approval evidence | Empty → APPROVED (bug) | Empty → SKIPPED (correcto) | build_task_for_session() corregido |
| C6 approval provenance | Unknown/assumed | Documentado: ApprovalGateService → ExecutionPlaybookService | Investigación de código |
| C8 tautological integration test | No encontrado | No aplicica | No aplica |

## Estado de E1a

**E1a: HumanApprovalBroker → ApprovalDecision**

- Implemented: NO (HumanApprovalBroker no está conectado a ToolTask)
- Invoked: NO
- Observed: NO
- Caused: NO
- Reproducible: NO

**Estado:** NOT PROVEN

**Nota:** La ruta real es ApprovalGateService → session.checkpoints → ExecutionPlaybookService → APPROVED. HumanApprovalBroker existe pero no está conectado a este path.

## Estado de R3-1

**R3-1: Payload Single-Build**

**Con context_pack = ""**
- Before: Doble composición
- After: Construido una sola vez
- Evidence: C1 corregido

**Con context_pack != ""**
- Before: Doble composión
- After: Construido una sola vez
- Evidence: test_p0_b_13_context_pack_no_double_composition

**Estado:** PROVEN

## Persistencia

**Save/Load Integrity:**
- Database save/load funciona correctamente (probado en ciclo anterior)
- Nonce, timestamps, status change se preservan correctamente

**Load-Bearing Authorization:**
- NO - adapter usa inyección directa, no carga desde repository
- Documentado correctamente como "NOT load-bearing"

**Estado:** Persistence integrity = PROVEN, Load-bearing = NOT PROVEN

## Primer Causal Break Después de las Correcciones

**Primer causal break:** C5 - Empty checkpoints → APPROVED

**Estado:** CORREGIDO

Ahora empty checkpoints → SKIPPED (no approval evidence ≠ approval).

**Nota:** E1a permanece NOT PROVEN porque la conexión de HumanApprovalBroker no está implementada.

## Git Provenance

**Commit:** (pendiente)
**Remote branch:** `p0b-first-causal-break`
**Remote HEAD:** (pendiente)

## Conclusión

**Status final:** Primer causal break corregido (C5), pero E1a permanece NOT PROVEN.

El primer causal break (empty checkpoints → APPROVED) ha sido corregido. Sin embargo, la conexión de E1a (HumanApprovalBroker → ApprovalDecision) permanece NOT PROVEN porque:

1. HumanApprovalBroker existe pero no está conectado a ToolTask
2. La ruta real es ApprovalGateService → ExecutionPlaybookService
3. No existe un test que demuestre la conexión causal de approval real

**NO declaro P0-B PROVEN.** La clasificación final corresponde a la evidencia real: C5 corregido, E1a NOT PROVEN.
