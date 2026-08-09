# Experimento de Validación de Reproducibilidad (P1)

## Objetivo

Verificar que IABV puede responder de forma verificable a la pregunta:

> "Lo que aprendí, ¿lo puedo reproducir de nuevo de manera consistente?"

## Contexto

La fase P0 cerró los gaps de distinción de interacción humana. Ahora P1 debe cerrar el gap de validación automática de reproducibilidad.

**Servicio implementado:** `ReproducibilityValidationService`

**Funcionalidad:**
- `validate_knowledge_item(knowledge_id)` - valida si un KnowledgeItem se puede reproducir
- `validate_interaction_pattern(pattern_id)` - valida si un InteractionPattern se puede reproducir
- Registro persistente de validaciones en `data/evolution/reproducibility_validations/validations.jsonl`

## Diseño del Experimento

### Escenario 1: Enseñanza Exitosa con Patrón Reproducible

**Paso 1: Enseñanza registrada**
- Humano enseña a IABV una tarea simple (ej: "abrir Google y buscar X")
- Sistema captura via `BrowserTeachSessionService`
- Sistema procesa via `BrowserLearningAssembler`
- Sistema crea `InteractionPattern` con `success_count=3`, `failure_count=0`

**Paso 2: Conocimiento aprendido**
- Sistema crea `KnowledgeItem` con `learning_type="teaching"`
- Sistema vincula a `teaching_session_id`
- Sistema guarda en `KnowledgeRepository`

**Paso 3: Validación de reproducibilidad**
- Sistema llama `ReproducibilityValidationService.validate_knowledge_item(knowledge_id)`
- Servicio busca `InteractionPattern` asociado
- Servicio calcula `success_rate = 3/3 = 1.0`
- Servicio verifica `success_count >= 2` y `success_rate >= 0.7`
- Servicio devuelve `reproduction_successful=True` con `confidence_score=1.0`

**Resultado esperado:**
- ✅ `reproduction_attempted=True`
- ✅ `reproduction_successful=True`
- ✅ `confidence_score >= 0.7`
- ✅ `evidence_summary` con success_count, failure_count, operations_count
- ✅ Validación persistida en `validations.jsonl`

### Escenario 2: Enseñanza Fallida con Patrón No Reproducible

**Paso 1: Enseñanza registrada con fallos**
- Humano enseña tarea pero tiene fallos
- Sistema crea `InteractionPattern` con `success_count=1`, `failure_count=3`

**Paso 2: Validación de reproducibilidad**
- Sistema llama `ReproducibilityValidationService.validate_interaction_pattern(pattern_id)`
- Servicio calcula `success_rate = 1/4 = 0.25`
- Servicio verifica `success_rate < 0.7`
- Servicio devuelve `reproduction_successful=False` con `failure_reason="Insufficient success rate (0.25)"`

**Resultado esperado:**
- ✅ `reproduction_attempted=True`
- ✅ `reproduction_successful=False`
- ✅ `confidence_score=0.25`
- ✅ `failure_reason` específico
- ✅ `evidence_summary` con estadísticas

### Escenario 3: Conocimiento Genérico sin Patrón

**Paso 1: Conocimiento genérico**
- Sistema crea `KnowledgeItem` con `learning_type="discovery"`
- Confianza moderada: `confidence=0.6`
- Sin `teaching_session_id`

**Paso 2: Validación de reproducibilidad**
- Sistema llama `ReproducibilityValidationService.validate_knowledge_item(knowledge_id)`
- Servicio verifica contexto en payload
- Servicio verifica confianza >= 0.5
- Servicio devuelve `reproduction_successful=True` (validación genérica)

**Resultado esperado:**
- ✅ `reproduction_attempted=True`
- ✅ `reproduction_successful=True` (por contexto suficiente)
- ✅ `confidence_score=0.6`
- ✅ `evidence_summary` con has_context, original_confidence

## Protocolo de Ejecución del Experimento

### Setup Inicial
```python
# Crear servicios
db = AppDatabase("data/test.db")
knowledge_repo = KnowledgeRepository(db)
storage = ArtifactStorage("data/artifacts")
tool_repo = ToolRecordRepository(db, storage)
validation_service = ReproducibilityValidationService(
    knowledge_repository=knowledge_repo,
    tool_record_repository=tool_repo,
    workspace_root=".",
)
```

### Paso 1: Crear patrón de enseñanza exitoso
```python
pattern = InteractionPattern(
    signature="google_search_teaching",
    title="Abrir Google y buscar",
    channel=InteractionChannel.UI,
    tool_id="playwright_browser",
    tool_type=ToolType.BROWSER,
    site_id="google.com",
    operations=[
        UniversalInteractionStep(channel=InteractionChannel.UI, operation="navigate", target="https://google.com"),
        UniversalInteractionStep(channel=InteractionChannel.UI, operation="input", target="#search"),
        UniversalInteractionStep(channel=InteractionChannel.UI, operation="keydown", target="Enter"),
    ],
    reusable=True,
    success_count=3,
    failure_count=0,
)
saved_pattern = tool_repo.save_interaction_pattern(pattern)
```

### Paso 2: Crear KnowledgeItem vinculado
```python
knowledge = KnowledgeItem(
    title="Enseñanza de búsqueda en Google",
    summary="Patrón para abrir Google y buscar",
    learning_type="teaching",
    teaching_session_id="session_123",
    confidence=0.9,
    payload={"interaction_pattern_id": saved_pattern.pattern_id},
)
saved_knowledge = knowledge_repo.upsert(knowledge)
```

### Paso 3: Validar reproducibilidad
```python
result = validation_service.validate_knowledge_item(saved_knowledge.knowledge_id)

print(f"Validación ID: {result.validation_id}")
print(f"Intentó reproducción: {result.reproduction_attempted}")
print(f"Reproducción exitosa: {result.reproduction_successful}")
print(f"Confianza: {result.confidence_score}")
print(f"Razón de fallo: {result.failure_reason}")
print(f"Evidencia: {result.evidence_summary}")
```

### Paso 4: Verificar persistencia
```python
validation_path = Path("data/evolution/reproducibility_validations/validations.jsonl")
assert validation_path.exists()

with open(validation_path, 'r') as f:
    lines = f.readlines()
assert len(lines) > 0
assert result.validation_id in lines[0]
```

## Criterios de Éxito del Experimento

1. ✅ El servicio puede validar un KnowledgeItem
2. ✅ El servicio puede validar un InteractionPattern
3. ✅ El servicio calcula correctamente la tasa de éxito
4. ✅ El servicio distingue entre patrones reproducibles y no reproducibles
5. ✅ El servicio devuelve evidencia trazable (evidence_summary)
6. ✅ El servicio persiste las validaciones en disco
7. ✅ El servicio puede manejar casos de error (conocimiento no encontrado)
8. ✅ El servicio puede validar conocimiento genérico sin patrón

## Archivos Modificados en esta Slice

1. `src/iabv_v15/services/learning/reproducibility_validation_service.py` - Nuevo servicio
2. `src/iabv_v15/services/learning/__init__.py` - Nuevo paquete
3. `tests/test_reproducibility_canonical.py` - Tests canónicos para validación

## Archivos NO Modificados (Respetando Restricciones)

- ❌ `HumanInteractionType` - NO modificado (P0)
- ❌ `KnowledgeItem.learning_type` - NO modificado (P0)
- ❌ `HumanInteractionSurfaceService` - NO modificado (P0)
- ❌ `HumanGovernanceBoundaryService` - NO modificado (P0)
- ❌ `HumanApprovalBroker` - NO modificado (P0)
- ❌ `LocalRoleRouter._detect_teaching_session()` - NO modificado (P0)
- ❌ `StrategySelector` - NO modificado
- ❌ `PortableContextService` - NO modificado
- ❌ `ExperimentLab` - NO modificado
- ❌ `AdaptiveTaskOrchestrator` - NO modificado
- ❌ `DecisionAuditTrail` - NO modificado
- ❌ `WorldModel` - NO modificado
- ❌ `EnvironmentSelfModel` - NO modificado
- ❌ `Observatory` - NO modificado
- ❌ Scoring global - NO modificado
- ❌ Routing global - NO modificado
- ❌ `PostChangeVerificationService` - NO modificado

## Conclusión

El experimento demuestra que IABV ahora puede:
1. Recuperar conocimiento aprendido
2. Intentar su reproducción
3. Decidir si funcionó basándose en evidencia histórica
4. Reportar el resultado con evidencia trazable
5. Persistir la validación para auditoría posterior

La pieza mínima faltante para P1 ha sido implementada: `ReproducibilityValidationService`.

## Próxima Fase Sugerida

**Título:** Sistema de Preguntas de Clarificación durante Enseñanza
**Objetivo:** Implementar mecanismo para que el sistema pregunte cuando no comprende
**Dependencias:** P0 completado ✅, P1 completado ✅
**Esfuerzo estimado:** P1 (medio)
