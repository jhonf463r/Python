# KD-P0B-E1A-AUTHORITY: Knowledge Delta - P0-B E1a Authority / Provenance Reconstruction

## Contexto
Este documento registra la reconstrucción de la arquitectura real de approval para identificar el authority source canónico de P0-B.
Baseline: `4d5f65c9f40e856d916b1302359c5dffd2107f62`
Branch: `p0b-first-causal-break`
Parent: `bb3138fee2831be2227499e079d1b910f7bf1fd6`

## Objeto de E1a-AUTHORITY
Reconstruir el authority source real que produce una aprobación válida para una `ToolTask`, sin asumir que es HumanApprovalBroker.

## Previous Model (INCORRECTO)

### Hipótesis Anterior
```
HumanApprovalBroker → ApprovalDecision → ExternalActionAuthorization
```

### Afirmación Falsa Encontrada
En `src/iabv_v15/services/tools/tool_teach_service.py` línea 782:
```python
# This establishes the real connection: HumanApprovalBroker → session.checkpoints → task.approval_decision → authorization
```

**Esta afirmación es FALSA.** HumanApprovalBroker NO está conectado a ToolTask.

## Evidence

### 1. HumanApprovalBroker - REALIDAD

**Archivo:** `src/iabv_v15/services/security/human_approval_broker.py`

**Propósito:** Mediador thread-safe de aprobaciones humanas genéricas.

**Uso Actual:**
- `github_remote_service.py` - Aprobar PRs (línea 7)
- NO se usa en tool_teach_service.py para P0-B
- NO está conectado a ToolTask.approval_decision

**Conclusión:** HumanApprovalBroker existe pero NO es el authority source de P0-B.

### 2. ApprovalGateService - CHECKPOINT GENERATOR

**Archivo:** `src/iabv_v15/services/adaptive/approval_gate_service.py`

**Propósito:** Generar ApprovalCheckpoint con decision=PENDING.

**Línea Clave:**
```python
def evaluate(
    self,
    *,
    intent: TaskIntent,
    pack: StrategyPack,
    strategy_candidates: list[StrategyCandidate],
) -> list[ApprovalCheckpoint]:
    checkpoints: list[ApprovalCheckpoint] = []
    requires_strategy = pack.approval_policy != 'never' or any(item.requires_approval for item in strategy_candidates)
    if requires_strategy:
        checkpoints.append(
            ApprovalCheckpoint(
                title='Aprobar estrategia',
                detail=f'Se propone {strategy_candidates[0].title if strategy_candidates else pack.title} antes de pasar a la fase operativa.',
                phase_key='strategy',
                reason='El flujo requiere confirmacion humana antes de seguir.',
                risk_level=pack.risk_level,
            )
        )
    if intent.sensitive or intent.monetary:
        checkpoints.append(
            ApprovalCheckpoint(
                title='Aprobar fase critica',
                detail='La siguiente fase toca login sensible, dinero o una accion operativa delicada.',
                phase_key='execute_sensitive',
                reason='No se omiten checkpoints explicitos en acciones sensibles o monetarias.',
                risk_level=IssueSeverity.CRITICAL if intent.monetary else IssueSeverity.HIGH,
            )
        )
    return checkpoints
```

**Conclusión:** ApprovalGateService genera checkpoints PENDING, NO produce APPROVED.

### 3. ExecutionPlaybookService - APPROVAL RESOLVER

**Archivo:** `src/iabv_v15/services/adaptive/execution_playbook_service.py`

**Propósito:** Convertir PENDING → APPROVED (manual/vía UI).

**Líneas Clave:**
```python
def approve_next_phase(self, session: AdaptiveSession) -> AdaptiveSession:
    pending = next((item for item in session.approval_checkpoints if item.decision == ApprovalDecision.PENDING), None)
    if pending is None:
        return session
    pending.decision = ApprovalDecision.APPROVED
    pending.decided_at_utc = datetime.now(timezone.utc)
    return self._refresh_status(session)

def approve_strategy(self, session: AdaptiveSession) -> AdaptiveSession:
    return self._approve_matching(session, phase_key='strategy')
```

**Conclusión:** ExecutionPlaybookService convierte PENDING → APPROVED, pero la provenance de quién llama a estos métodos es UNCLEAR.

### 4. AdaptiveTaskOrchestrator - SESSION BUILDER

**Archivo:** `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`

**Líneas Clave:**
```python
# Línea 1568
approvals = self.approval_gate_service.evaluate(intent=intent, pack=pack, strategy_candidates=strategy_candidates)

# Línea 1620
session.approval_checkpoints = approvals
```

**Conclusión:** AdaptiveTaskOrchestrator genera checkpoints y los asigna a session.approval_checkpoints.

### 5. ToolTeachService.build_task_for_session() - DECISION COPIER

**Archivo:** `src/iabv_v15/services/tools/tool_teach_service.py`

**Líneas Clave:**
```python
def build_task_for_session(self, session) -> ToolTask:
    # ... construcción del task ...

    # C5: Copy approval decision from session checkpoints to task
    rejected_checkpoints = [item for item in session.approval_checkpoints if item.decision == ApprovalDecision.REJECTED]
    if rejected_checkpoints:
        task.approval_decision = ApprovalDecision.REJECTED
    else:
        pending_checkpoints = [item for item in session.approval_checkpoints if item.decision == ApprovalDecision.PENDING]
        if pending_checkpoints:
            task.approval_decision = ApprovalDecision.PENDING
        elif session.approval_checkpoints:
            approved_checkpoints = [item for item in session.approval_checkpoints if item.decision == ApprovalDecision.APPROVED]
            if approved_checkpoints:
                task.approval_decision = ApprovalDecision.APPROVED
            else:
                task.approval_decision = ApprovalDecision.SKIPPED
        else:
            # C5: No checkpoints at all → SKIPPED (no approval evidence)
            task.approval_decision = ApprovalDecision.SKIPPED

    return task.model_copy(
        update={
            'session_id': session.session_id,
            'run_id': session.run_id,
            'pack_id': session.chosen_pack_id,
            'site_id': session.context.site_id or session.intent.site_hint,
            'approval_decision': task.approval_decision,
        }
    )
```

**Conclusión:** ToolTeachService copia la decisión de session.checkpoints a task.approval_decision, pero NO hay provenance de quién cambió el checkpoint de PENDING a APPROVED.

## Corrected Model

### Ruta Real de Approval
```
AdaptiveTaskOrchestrator
  ↓
ApprovalGateService.evaluate()
  ↓
ApprovalCheckpoint[] (decision=PENDING)
  ↓
session.approval_checkpoints
  ↓
ExecutionPlaybookService.approve_next_phase() / approve_strategy()
  ↓
ApprovalCheckpoint (decision=APPROVED)
  ↓
ToolTeachService.build_task_for_session()
  ↓
ToolTask.approval_decision = APPROVED
  ↓
ToolTeachService.execute_task()
  ↓
ExternalActionAuthorization issuance
```

### Authority Source Real
**ExecutionPlaybookService** es el authority source que convierte PENDING → APPROVED.

**Provenance:** UNCLEAR. No está claro quién llama a ExecutionPlaybookService.approve_next_phase() desde la UI o quién es el actor que inicia la aprobación.

### Brecha de Provenance
1. ApprovalGateService genera checkpoints PENDING automáticamente.
2. ExecutionPlaybookService convierte PENDING → APPROVED manualmente.
3. NO hay registro de quién/qué inició la conversión.
4. NO hay conexión con HumanApprovalBroker.
5. NO hay campo de provenance explícito en ApprovalCheckpoint.

## Causal Graph

### Edge A1: ApprovalGateService → ApprovalCheckpoint

**Producer:** AdaptiveTaskOrchestrator
**Consumer:** AdaptiveSession
**Data:** ApprovalCheckpoint[] (decision=PENDING)
**Evidence:** Línea 1568 en adaptive_task_orchestrator.py
**Status:** PROVEN

### Edge A2: ExecutionPlaybookService → APPROVED

**Producer:** UNCLEAR (UI/Usuario?)
**Consumer:** AdaptiveSession.approval_checkpoints
**Data:** ApprovalCheckpoint (decision=APPROVED)
**Evidence:** Líneas 89-95 en execution_playbook_service.py
**Status:** PARTIAL (método existe, caller desconocido)

### Edge A3: ToolTeachService → ToolTask.approval_decision

**Producer:** ToolTeachService.build_task_for_session()
**Consumer:** ToolTask
**Data:** ApprovalDecision
**Evidence:** Líneas 688-707 en tool_teach_service.py
**Status:** PROVEN

### Edge A4: ToolTask.approval_decision → ExternalActionAuthorization

**Producer:** ToolTeachService.execute_task()
**Consumer:** ExternalActionAuthorization
**Data:** task.approval_decision
**Evidence:** Línea 779-782 en tool_teach_service.py
**Status:** PARTIAL (emisión condicional en execute_task)

## Authority Source Classification

| Candidato | Existe | Participa en approval | Puede producir APPROVED | Tiene provenance | Conectado a ToolTask | Conectado a authorization issuance |
|-----------|--------|----------------------|------------------------|------------------|----------------------|-----------------------------------|
| HumanApprovalBroker | YES | NO (solo para PRs) | YES | YES | NO | NO |
| ApprovalGateService | YES | YES (genera PENDING) | NO | NO | NO | NO |
| ExecutionPlaybookService | YES | YES (convierte PENDING→APPROVED) | YES | NO | NO | NO |
| ToolApprovalPolicy | ? | ? | ? | ? | ? | ? |

## Empty Approval Behavior

### No Checkpoints
**Resultado:** `task.approval_decision = SKIPPED`
**Authorization emitted:** NO
**Evidence:** Líneas 704-707 en tool_teach_service.py (C5 corregido)

### Checkpoints PENDING
**Resultado:** `task.approval_decision = PENDING`
**Authorization emitted:** NO
**Evidence:** Líneas 692-694 en tool_teach_service.py

### Checkpoints APPROVED
**Resultado:** `task.approval_decision = APPROVED`
**Authorization emitted:** YES (condicional)
**Evidence:** Líneas 698-700 en tool_teach_service.py

## Pseudo-Integration Test

**Archivo:** `tests/test_p0b_real_discriminating_integration.py`

**Estado:** NO EXISTE (no se encontró en el código actual)

**Nota:** La auditoría anterior mencionó este archivo con lógica reimplementada y approval fabricado, pero actualmente no existe en el repositorio.

## E1b Preview

### APPROVED → Authorization

**Condición:** `approval_required and task.approval_decision == ApprovalDecision.APPROVED`

**Producer:** ToolTeachService.execute_task()

**Consumer:** ExternalActionAuthorization

**Data copiado:**
- task_id
- tool_id
- adapter_key
- prompt_digest
- approval_decision

**Provenance copiada:** NO (no hay campo de provenance en ExternalActionAuthorization)

**Status:** PARTIAL (emisión condicional implementada, pero sin provenance)

## Existing Observability

**Mecanismos existentes:**
- ToolMemory.audit_event(...)
- LiveAuditSupervisor
- approval_checkpoint_repository (persiste checkpoints)
- TaskOutcomeRecorder (persiste session con checkpoints)

**Limitaciones:**
- NO hay registro de quién cambió PENDING → APPROVED
- NO hay timestamp de acción de aprobación explícito
- NO hay campo de actor/role en ApprovalCheckpoint

## Causal Matrix P0-B Actualizada

### E1a: Authority → ApprovalDecision

**Anterior:** HumanApprovalBroker → ApprovalDecision
**Actual:** ExecutionPlaybookService → ApprovalDecision
**Estado:** PARTIAL (método existe, caller/provenance desconocido)

### E1b: ApprovalDecision → Authorization

**Estado:** PARTIAL (emisión condicional implementada, sin provenance)

### E2: Authorization → Binding

**Estado:** PROVEN IN ISOLATION (unit tests)

### E3: Binding → Consume

**Estado:** PROVEN IN ISOLATION (unit tests)

### E4: Consume → Adapter

**Estado:** PROVEN IN ISOLATION (unit tests)

### E5: Adapter → Loopback

**Estado:** NOT PROVEN (no loopback real)

## Key Discoveries

1. **HumanApprovalBroker NO es el authority source de P0-B.** Esta hipótesis era incorrecta.
2. **ExecutionPlaybookService es el authority source real** que convierte PENDING → APPROVED.
3. **No hay provenance de approval.** No está claro quién llama a ExecutionPlaybookService.approve_next_phase().
4. **ApprovalGateService es solo un generador de checkpoints PENDING**, no un authority source.
5. **La afirmación en tool_teach_service.py línea 782 es FALSA.** Debe corregirse.
6. **Empty checkpoints → SKIPPED** (C5 corregido) funciona correctamente.
7. **ExternalActionAuthorization NO tiene campo de provenance.** No registra quién aprobó.

## Corrected Model

### Authority Source Canónico
**ExecutionPlaybookService** (vía llamada desde UI/usuario) es el authority source que convierte PENDING → APPROVED.

### Ruta Causal Real
```
ApprovalGateService (auto)
  ↓ generates PENDING checkpoints
session.approval_checkpoints
  ↓
ExecutionPlaybookService (manual/vía UI)
  ↓ converts PENDING → APPROVED
session.approval_checkpoints
  ↓
ToolTeachService.build_task_for_session()
  ↓ copies decision to task
ToolTask.approval_decision
  ↓
ToolTeachService.execute_task()
  ↓ if APPROVED, emits authorization
ExternalActionAuthorization
```

### Brecha Principal
**Provenance de Approval:** NO EXISTE. No hay registro de quién/qué inició la conversión PENDING → APPROVED.

## Policy Changes

1. **Eliminar la afirmación falsa** en tool_teach_service.py línea 782 sobre HumanApprovalBroker.
2. **Documentar ExecutionPlaybookService** como el authority source real.
3. **Agregar provenance** a ApprovalCheckpoint (actor, role, timestamp de acción).
4. **Distinguir entre approval automático (PENDING) y approval manual (APPROVED).**
5. **Conectar UI → ExecutionPlaybookService** con provenance explícita.

## Testing Implications

### Futuro E1a Test
Debe demostrar:
1. ApprovalGateService genera checkpoints PENDING automáticamente.
2. ExecutionPlaybookService convierte PENDING → APPROVED manualmente.
3. ToolTeachService copia la decisión a task.approval_decision.
4. La provenance de quién convirtió PENDING → APPROVED está registrada.

### Futuro E1b Test
Debe demostrar:
1. task.approval_decision == APPROVED causa emisión de ExternalActionAuthorization.
2. task.approval_decision != APPROVED NO causa emisión.
3. La provenance de approval se propaga a ExternalActionAuthorization.

## Remaining Uncertainty

1. **Quién llama a ExecutionPlaybookService.approve_next_phase()?** (UI? Usuario? Sistema?)
2. **Dónde está la conexión UI → ExecutionPlaybookService?**
3. **Por qué HumanApprovalBroker no está conectado a P0-B?**
4. **Por qué ExternalActionAuthorization no tiene campo de provenance?**
5. **Cómo registrar provenance de approval sin romper arquitectura existente?**

## Git Provenance

**Commit:** (pendiente)
**Remote branch:** `p0b-first-causal-break`
**Remote HEAD:** (pendiente)

## Conclusión

**Status final:** E1a = PARTIAL

El authority source real es ExecutionPlaybookService, no HumanApprovalBroker. Sin embargo, la provenance de approval NO está registrada. La afirmación en tool_teach_service.py línea 782 es FALSA y debe corregirse.

**NO declaro E1a PROVEN.** La clasificación final corresponde a la evidencia real: ExecutionPlaybookService es el authority source, pero la provenance de approval es UNKNOWN.
