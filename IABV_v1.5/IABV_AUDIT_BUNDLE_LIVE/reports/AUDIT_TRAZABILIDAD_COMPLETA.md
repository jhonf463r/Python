# AUDITORÍA DE TRAZABILIDAD COMPLETA DEL ÓRGANO DE PERCEPCIÓN MULTIMODAL
**Fecha:** 2025-06-17
**Auditor:** Arquitecto Principal y Auditor Técnico de IABV

---

## 1. CADENA DE TRAZABILIDAD ESPERADA

```
INPUT (Usuario/Sistema)
↓
LISTENER (InputListenerService, OutputListenerService, FocusChangeListener, LifecycleListener)
↓
RUNTIME PERCEPTION (MultimodalPerceptionService.capture_action)
↓
SURFACE OBSERVATION (SurfaceObservation)
↓
EVIDENCE RECORD (EvidenceRecord)
↓
TRUTH ARBITRATOR (TruthArbitrator.arbitrate_truth)
↓
EVIDENCE RECORDER (EvidenceRecorder.persist_evidence)
↓
JSONL (evidence_records.jsonl)
```

---

## 2. ANÁLISIS DE CADA SALTO

### 2.1 INPUT → LISTENER

**Estado:** ✅ OPERATIVO

**Objeto generado:** InputEvent, OutputEvent, FocusChangeEvent, LifecycleEvent

**Timestamp:** Cada evento tiene su propio timestamp_utc

**Evidence_hash:** No aplica (los listeners no generan evidence_hash)

**Task_id:** No aplica (los listeners no generan task_id)

**Correlación:** Los listeners capturan eventos del sistema operativo y los almacenan en memoria para ser consumidos por MultimodalPerceptionService

**Evidencia:**
```python
# InputListenerService
class InputEvent:
    event_id: str
    timestamp_utc: str
    event_type: InputEventType
    source: InputSource
    metadata: dict[str, Any]

# OutputListenerService
class OutputEvent:
    event_id: str
    timestamp_utc: str
    event_type: OutputEventType
    source: OutputSource
    metadata: dict[str, Any]

# FocusChangeListener
class FocusChangeEvent:
    event_id: str
    timestamp_utc: str
    change_type: FocusChangeType
    trigger: FocusTrigger
    previous_surface_id: str
    current_surface_id: str
    metadata: dict[str, Any]

# LifecycleListener
class LifecycleEvent:
    event_id: str
    timestamp_utc: str
    event_type: LifecycleEventType
    trigger: LifecycleTrigger
    surface_id: str
    metadata: dict[str, Any]
```

**Conclusión:** El salto INPUT → LISTENER está operativo. Los listeners capturan eventos del sistema operativo con timestamps.

---

### 2.2 LISTENER → RUNTIME PERCEPTION

**Estado:** ⚠️ PARCIALMENTE OPERATIVO

**Objeto generado:** EventSignal

**Timestamp:** event_signal.timestamp_utc

**Evidence_hash:** No aplica (EventSignal no tiene evidence_hash)

**Task_id:** No aplica (EventSignal no tiene task_id)

**Correlación:** MultimodalPerceptionService.capture_action() consume eventos de los listeners y los fusiona en EventSignal

**Evidencia:**
```python
# MultimodalPerceptionService.capture_action()
def capture_action(
    self,
    *,
    task_id: str,
    action_type: str,
    target_surface: str,
    source: str,
) -> EvidenceRecord:
    # Capturar eventos de listeners
    input_events = self._input_listener_service.get_events() if self._input_listener_service else []
    output_events = self._output_listener_service.get_events() if self._output_listener_service else []
    focus_changes = self._focus_change_listener.get_events() if self._focus_change_listener else []
    lifecycle_events = self._lifecycle_listener.get_events() if self._lifecycle_listener else []
    
    # Crear EventSignal
    event_signal = EventSignal(
        input_events_count=len(input_events),
        output_events_count=len(output_events),
        focus_change=focus_changes[0] if focus_changes else None,
        lifecycle_events_count=len(lifecycle_events),
        task_state_events_count=0,
        timestamp_utc=datetime.utcnow().isoformat() + "+00:00",
    )
```

**Conclusión:** El salto LISTENER → RUNTIME PERCEPTION está parcialmente operativo. Los eventos de los listeners son consumidos y fusionados en EventSignal, pero no hay evidencia_hash ni task_id en este nivel.

---

### 2.3 RUNTIME PERCEPTION → SURFACE OBSERVATION

**Estado:** ⚠️ PARCIALMENTE OPERATIVO

**Objeto generado:** SurfaceObservation

**Timestamp:** surface_observation.timestamp_utc

**Evidence_hash:** surface_observation.metadata["evidence_hash"]

**Task_id:** surface_observation.metadata["task_id"]

**Correlación:** MultimodalPerceptionService._connect_to_runtime_perception_service() crea SurfaceObservation desde EvidenceRecord

**Evidencia:**
```python
# MultimodalPerceptionService._connect_to_runtime_perception_service()
def _connect_to_runtime_perception_service(self, record: EvidenceRecord) -> None:
    # Crear SurfaceObservation desde EvidenceRecord
    surface_observation = SurfaceObservation(
        timestamp_utc=record.timestamp_utc,
        surface_type=surface_type,
        surface_id=record.surface_id,
        surface_title=record.surface_title,
        app_name=record.process_signal.process_name if record.process_signal else "",
        process_id=record.process_signal.pid if record.process_signal else None,
        state=surface_state,
        focused=surface_state == SurfaceState.FOCUSED,
        visible=record.visual_truth_confidence >= 0.5,
        metadata={
            "evidence_hash": record.evidence_hash,
            "task_id": record.task_id,
            "action_type": record.action_type,
            "source": record.source,
            "truth_source": record.truth_source,
            "truth_confidence": record.truth_confidence,
            "connected_from": "multimodal_perception_service",
        }
    )
```

**Conclusión:** El salto RUNTIME PERCEPTION → SURFACE OBSERVATION está parcialmente operativo. SurfaceObservation se crea con evidence_hash y task_id de EvidenceRecord, pero la correlación en los datos persistidos no está funcionando correctamente.

---

### 2.4 SURFACE OBSERVATION → EVIDENCE RECORD

**Estado:** ❌ NO OPERATIVO

**Objeto generado:** No hay conexión directa

**Timestamp:** No aplica

**Evidence_hash:** No aplica

**Task_id:** No aplica

**Correlación:** No existe conexión directa entre SurfaceObservation y EvidenceRecord. La conexión es inversa: EvidenceRecord → SurfaceObservation

**Evidencia:**
```python
# No hay código que cree EvidenceRecord desde SurfaceObservation
# La conexión es unidireccional: EvidenceRecord → SurfaceObservation
```

**Conclusión:** El salto SURFACE OBSERVATION → EVIDENCE RECORD NO existe. La conexión es unidireccional: EvidenceRecord → SurfaceObservation.

---

### 2.5 EVIDENCE RECORD → TRUTH ARBITRATOR

**Estado:** ✅ OPERATIVO

**Objeto generado:** EvidenceRecord (modificado)

**Timestamp:** record.timestamp_utc

**Evidence_hash:** record.evidence_hash

**Task_id:** record.task_id

**Correlación:** MultimodalPerceptionService.capture_action() llama a TruthArbitrator.arbitrate_truth() para arbitrar la verdad

**Evidencia:**
```python
# MultimodalPerceptionService.capture_action()
def capture_action(
    self,
    *,
    task_id: str,
    action_type: str,
    target_surface: str,
    source: str,
) -> EvidenceRecord:
    # ... captura de señales ...
    
    # Arbitrar verdad
    truth_result = self._truth_arbitrator.arbitrate_truth(
        visual_signal=visual_signal,
        process_signal=process_signal,
        event_signal=event_signal,
        persistent_truth=None,
    )
    
    # Actualizar EvidenceRecord con resultado de arbitraje
    record.truth_source = truth_result["truth_source"]
    record.truth_confidence = truth_result["truth_confidence"]
    record.truth_type = truth_result["truth_type"]
    record.visual_truth_confidence = truth_result["visual_truth_confidence"]
    record.operational_truth_confidence = truth_result["operational_truth_confidence"]
    record.persistent_truth_confidence = truth_result["persistent_truth_confidence"]
    record.truth_explanation = truth_result["truth_explanation"]
    record.truth_conflicts = truth_result["truth_conflicts"]
```

**Conclusión:** El salto EVIDENCE RECORD → TRUTH ARBITRATOR está operativo. TruthArbitrator modifica EvidenceRecord con el resultado del arbitraje.

---

### 2.6 TRUTH ARBITRATOR → EVIDENCE RECORDER

**Estado:** ✅ OPERATIVO

**Objeto generado:** EvidenceRecord (persistido)

**Timestamp:** record.timestamp_utc

**Evidence_hash:** record.evidence_hash

**Task_id:** record.task_id

**Correlación:** MultimodalPerceptionService.capture_action() llama a EvidenceRecorder.persist_evidence() para persistir EvidenceRecord

**Evidencia:**
```python
# MultimodalPerceptionService.capture_action()
def capture_action(
    self,
    *,
    task_id: str,
    action_type: str,
    target_surface: str,
    source: str,
) -> EvidenceRecord:
    # ... captura de señales ...
    # ... arbitraje de verdad ...
    
    # Persistir evidencia
    self._evidence_recorder.persist_evidence(record)
    
    return record
```

**Conclusión:** El salto TRUTH ARBITRATOR → EVIDENCE RECORDER está operativo. EvidenceRecorder persiste EvidenceRecord en JSONL.

---

### 2.7 EVIDENCE RECORDER → JSONL

**Estado:** ✅ OPERATIVO

**Objeto generado:** Archivo JSONL

**Timestamp:** Cada registro tiene su propio timestamp_utc

**Evidence_hash:** Cada registro tiene su propio evidence_hash

**Task_id:** Cada registro tiene su propio task_id

**Correlación:** EvidenceRecorder.persist_evidence() escribe EvidenceRecord en evidence_records.jsonl

**Evidencia:**
```python
# EvidenceRecorder.persist_evidence()
def persist_evidence(self, record: EvidenceRecord) -> None:
    # Convertir EvidenceRecord a dict
    record_dict = asdict(record)
    
    # Escribir en JSONL
    with open(self._evidence_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record_dict, default=str) + "\n")
```

**Conclusión:** El salto EVIDENCE RECORDER → JSONL está operativo. EvidenceRecorder escribe EvidenceRecord en evidence_records.jsonl.

---

## 3. CORRELACIÓN DE DATOS EN PERSISTENCIA

### 3.1 EvidenceRecord

**Archivo:** `data/multimodal_evidence/evolution/multimodal_evidence/evidence_records.jsonl`

**Campos de correlación:**
- evidence_id: "e072700e2e264f29bca5179b6e80aaaa"
- task_id: "runtime_real_verification"
- timestamp_utc: "2026-06-17T19:48:17.738956+00:00"
- evidence_hash: "4f4ab048eea6cf7195b7cdb85e69acc4f564afdeebda61a5c7cba657cb05e435"
- surface_id: ""

**Conclusión:** EvidenceRecord tiene todos los campos necesarios para correlación.

### 3.2 SurfaceObservation

**Archivo:** `data/multimodal_evidence/evolution/runtime_perception/surface_observations.jsonl`

**Campos de correlación:**
- observation_id: "dee1c0f0-e728-48f9-afda-ade23f71a1a0"
- timestamp_utc: "2026-06-18T02:12:22.782146+00:00"
- surface_id: ""
- metadata.evidence_hash: "cd6e1f22ad6149d57d49a0a8efa5ea9fbf1e1e174fc300821847cf2707a5ce12"
- metadata.task_id: "hybrid_verification"

**Conclusión:** SurfaceObservation tiene campos de correlación en metadata, pero los valores no coinciden con EvidenceRecord.

### 3.3 Problema de Correlación

**EvidenceRecord:**
- evidence_hash: "4f4ab048eea6cf7195b7cdb85e69acc4f564afdeebda61a5c7cba657cb05e435"
- task_id: "runtime_real_verification"
- surface_id: ""

**SurfaceObservation:**
- metadata.evidence_hash: "cd6e1f22ad6149d57d49a0a8efa5ea9fbf1e1e174fc300821847cf2707a5ce12"
- metadata.task_id: "hybrid_verification"
- surface_id: ""

**Observaciones:**
- Los evidence_hash son diferentes
- Los task_id son diferentes
- Los surface_id están vacíos en ambos

**Conclusión:** ❌ La correlación entre EvidenceRecord y SurfaceObservation no está funcionando correctamente.

---

## 4. ANÁLISIS DEL PROBLEMA

### 4.1 Causa Raíz

El problema es que `_connect_to_runtime_perception_service()` se llama DESPUÉS de que EvidenceRecord ya ha sido persistido por EvidenceRecorder. Esto significa que:

1. EvidenceRecord se crea con un evidence_hash y task_id específicos
2. EvidenceRecord se persiste en JSONL
3. `_connect_to_runtime_perception_service()` se llama y crea SurfaceObservation con evidence_hash y task_id de EvidenceRecord
4. SurfaceObservation se persiste en JSONL

Sin embargo, los datos persistidos muestran que los evidence_hash y task_id no coinciden. Esto sugiere que:

1. O bien `_connect_to_runtime_perception_service()` no se está llamando
2. O bien se está llamando con un EvidenceRecord diferente
3. O bien hay un problema en la lógica de copia de evidence_hash y task_id

### 4.2 Verificación del Código

El código de `_connect_to_runtime_perception_service()` muestra que debería copiar evidence_hash y task_id:

```python
surface_observation = SurfaceObservation(
    ...
    metadata={
        "evidence_hash": record.evidence_hash,
        "task_id": record.task_id,
        ...
    }
)
```

Esto sugiere que el problema está en cuándo se llama `_connect_to_runtime_perception_service()` o con qué EvidenceRecord.

### 4.3 Verificación de Llamada

**Línea de código:** `capture_action()` línea 375

**Secuencia de ejecución:**
1. Línea 362: `record = self._evidence_recorder.record(record)` - EvidenceRecord se persiste en JSONL
2. Línea 375: `self._connect_to_runtime_perception_service(record)` - SurfaceObservation se crea y persiste

**Problema identificado:**
- `_connect_to_runtime_perception_service()` se llama DESPUÉS de que EvidenceRecord ha sido persistido
- Esto significa que el EvidenceRecord persistido en JSONL y el SurfaceObservation persistido en JSONL deberían tener los mismos evidence_hash y task_id
- Sin embargo, los datos persistidos muestran que los evidence_hash y task_id son diferentes

**Hipótesis:**
- O bien `_connect_to_runtime_perception_service()` no se está llamando en todos los casos
- O bien se está llamando con un EvidenceRecord diferente al que se persistió
- O bien hay un problema en la lógica de persistencia de SurfaceObservation

**Conclusión:** ❌ La correlación entre EvidenceRecord y SurfaceObservation no está funcionando correctamente debido a un problema en la secuencia de ejecución o en la lógica de persistencia.

---

## 5. CONCLUSIÓN DE FASE 4

### 5.1 Estado General

**Estado:** ⚠️ PARCIALMENTE OPERATIVO

### 5.2 Saltos Operativos

- ✅ INPUT → LISTENER: Operativo
- ⚠️ LISTENER → RUNTIME PERCEPTION: Parcialmente operativo (sin evidence_hash ni task_id)
- ⚠️ RUNTIME PERCEPTION → SURFACE OBSERVATION: Parcialmente operativo (correlación no funciona)
- ❌ SURFACE OBSERVATION → EVIDENCE RECORD: No operativo (conexión inversa)
- ✅ EVIDENCE RECORD → TRUTH ARBITRATOR: Operativo
- ✅ TRUTH ARBITRATOR → EVIDENCE RECORDER: Operativo
- ✅ EVIDENCE RECORDER → JSONL: Operativo

### 5.3 Problemas Identificados

1. **Correlación EvidenceRecord ↔ SurfaceObservation:** No funciona correctamente
   - EvidenceHash: Diferente entre EvidenceRecord y SurfaceObservation
   - TaskId: Diferente entre EvidenceRecord y SurfaceObservation
   - SurfaceId: Vacío en ambos

2. **Conexión unidireccional:** No existe conexión directa de SurfaceObservation a EvidenceRecord
   - La conexión es unidireccional: EvidenceRecord → SurfaceObservation
   - Esto impide la trazabilidad completa en ambas direcciones

3. **Correlación en EventSignal:** EventSignal no tiene evidence_hash ni task_id
   - Esto impide la correlación entre eventos de listeners y EvidenceRecord

### 5.4 Recomendaciones

1. **Corregir correlación:** Investigar por qué los evidence_hash y task_id son diferentes entre EvidenceRecord y SurfaceObservation
2. **Mejorar surface_id:** Usar window_handle o process_id como surface_id para mejor correlación
3. **Agregar correlación a EventSignal:** Agregar evidence_hash y task_id a EventSignal para mejor trazabilidad
4. **Implementar conexión bidireccional:** Implementar conexión de SurfaceObservation a EvidenceRecord para trazabilidad completa

### 5.5 Próxima Fase

Continuar con FASE 5: VALIDACIÓN DE NO VERIFICADOS<tool_call>read_file<arg_key>file_path</arg_key><arg_value>C:\Python\IABV_v1.5\src\iabv_v15\services\perception\multimodal_perception_service.py
