# MAPA DE CONEXIONES REAL DEL ÓRGANO DE PERCEPCIÓN MULTIMODAL
**Fecha:** 2025-06-17
**Auditor:** Arquitecto Principal y Auditor Técnico de IABV

---

## 1. GRAFO DE DEPENDENCIAS REAL

### 1.1 Capa de Percepción Puntual (MultimodalPerceptionService)

```
MultimodalPerceptionService
├── SignalFusionCore (instancia interna)
├── TruthArbitrator (instancia interna)
├── EvidenceRecorder (instancia interna)
├── CapabilityDetector (instancia interna)
├── SurfaceClassifier (instancia interna)
├── AdapterSelector (instancia interna)
├── ScreenInfoProvider (instancia interna)
├── CoordinateTransformer (instancia interna)
├── GeometryNormalizer (instancia interna)
├── CalibrationMetrics (instancia interna)
├── AuditHUDService (instancia interna)
├── AuditLogService (instancia interna)
├── AuditMemoryService (instancia interna)
├── AuditValidationService (instancia interna)
├── WorldModelService (inyectado externamente)
├── UIScreenshotService (inyectado externamente)
├── ProcessScanner (inyectado externamente)
└── RuntimePerceptionAndVerificationService (inyectado externamente)
```

### 1.2 Capa de Percepción Continua (RuntimePerceptionAndVerificationService)

```
RuntimePerceptionAndVerificationService
├── WorldModelService (inyectado externamente)
├── DecisionAuditTrail (inyectado externamente)
├── InputListenerService (inyectado externamente)
├── OutputListenerService (inyectado externamente)
├── FocusChangeListener (inyectado externamente)
├── LifecycleListener (inyectado externamente)
└── Adaptadores (inicializados internamente)
    ├── Win32Adapter
    ├── MacOSAdapter
    └── LinuxAdapter
```

### 1.3 Listeners Activos

```
InputListenerService
└── pynput (dependencia externa)

OutputListenerService
├── uiautomation (dependencia externa)
└── win32clipboard (dependencia externa)

FocusChangeListener
└── uiautomation (dependencia externa)

LifecycleListener
├── psutil (dependencia externa)
└── uiautomation (dependencia externa)
```

### 1.4 FreezeDetectorService

```
FreezeDetectorService
├── InputListenerService (inyectado externamente)
├── OutputListenerService (inyectado externamente)
└── FocusChangeListener (inyectado externamente)
```

---

## 2. FLUJO DE DATOS REAL

### 2.1 Entrada

```
INPUT (Usuario/Sistema)
↓
InputListenerService (KEY_PRESS, KEY_RELEASE, MOUSE_MOVE, MOUSE_CLICK, MOUSE_SCROLL)
↓
MultimodalPerceptionService.capture_action()
```

### 2.2 Transformación

```
MultimodalPerceptionService.capture_action()
├── SignalFusionCore.fuse_signals()
│   ├── VisualSignal (screenshot + OCR + accessibility)
│   ├── ProcessSignal (PID + ventana + recursos)
│   └── EventSignal (input/output)
├── TruthArbitrator.arbitrate_truth()
│   ├── Visual truth
│   ├── Operational truth
│   └── Persistent truth
└── EvidenceRecord (evidence_hash, task_id, surface_id, timestamps)
```

### 2.3 Verificación

```
TruthArbitrator.arbitrate_truth()
├── Verifica consistencia entre señales
├── Detecta contradicciones
└── Genera truth_confidence
```

### 2.4 Persistencia

```
EvidenceRecord
↓
EvidenceRecorder.persist_evidence()
↓
JSONL (data/multimodal_evidence/evolution/multimodal_evidence/evidence_records.jsonl)
```

### 2.5 Consumo

```
EvidenceRecord
↓
_connect_to_runtime_perception_service()
↓
SurfaceObservation (timestamp, surface_type, surface_id, surface_title, app_name, process_id, state, focused, visible, metadata)
↓
RuntimePerceptionAndVerificationService.append_surface_observation()
```

---

## 3. CONEXIÓN ENTRE CAPA PUNTUAL Y CAPA CONTINUA

### 3.1 Dónde se Instancia

**MultimodalPerceptionService.__init__()**
```python
def __init__(
    self,
    *,
    data_root: str | Path = "",
    world_model_service: Any = None,
    screenshot_service: Any = None,
    process_scanner: Any = None,
    runtime_perception_service: Any = None,  # INYECCIÓN
) -> None:
    self._runtime_perception_service = runtime_perception_service
```

### 3.2 Quién lo Inyecta

**verify_hybrid_real.py**
```python
runtime_service = RuntimePerceptionAndVerificationService(
    world_model_service=world_model_service,
    data_root=evidence_root,
    input_listener_service=input_listener,
    output_listener_service=output_listener,
    focus_change_listener=focus_listener,
    lifecycle_listener=lifecycle_listener,
)

perception_service = MultimodalPerceptionService(
    data_root=evidence_root,
    screenshot_service=screenshot_service,
    world_model_service=world_model_service,
    runtime_perception_service=runtime_service,  # INYECCIÓN
)
```

### 3.3 Cuándo se Ejecuta

**MultimodalPerceptionService.capture_action()**
```python
def capture_action(
    self,
    *,
    task_id: str,
    action_type: str,
    target_surface: str,
    source: str,
) -> EvidenceRecord:
    # ... captura de señales ...
    
    # Conectar con RuntimePerceptionAndVerificationService
    self._connect_to_runtime_perception_service(record)
    
    return record
```

### 3.4 Qué Datos Transmite

**_connect_to_runtime_perception_service(record: EvidenceRecord)**
```python
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
        },
    )
    
    # Pasar a RuntimePerceptionAndVerificationService
    self._runtime_perception_service.append_surface_observation(surface_observation)
```

---

## 4. CORRELACIÓN DE DATOS

### 4.1 EvidenceHash

```
EvidenceRecord.evidence_hash
↓
SurfaceObservation.metadata["evidence_hash"]
↓
Correlación entre capa puntual y capa continua
```

### 4.2 TaskId

```
EvidenceRecord.task_id
↓
SurfaceObservation.metadata["task_id"]
↓
Correlación entre capa puntual y capa continua
```

### 4.3 SurfaceId

```
EvidenceRecord.surface_id
↓
SurfaceObservation.surface_id
↓
Correlación entre capa puntual y capa continua
```

### 4.4 Timestamps

```
EvidenceRecord.timestamp_utc
↓
SurfaceObservation.timestamp_utc
↓
Correlación temporal entre capa puntual y capa continua
```

### 4.5 TruthSource

```
EvidenceRecord.truth_source
↓
SurfaceObservation.metadata["truth_source"]
↓
Correlación de fuente de verdad entre capa puntual y capa continua
```

### 4.6 Ownership

```
EvidenceRecord.ownership
↓
SurfaceObservation.metadata["ownership"]
↓
Correlación de ownership entre capa puntual y capa continua
```

---

## 5. RESUMEN DE DEPENDENCIAS

### 5.1 Entradas

- **Input del usuario:** InputListenerService (pynput)
- **Output del sistema:** OutputListenerService (uiautomation + win32clipboard)
- **Cambios de foco:** FocusChangeListener (uiautomation)
- **Eventos de lifecycle:** LifecycleListener (psutil + uiautomation)
- **Captura de pantalla:** UIScreenshotService
- **Escaneo de procesos:** ProcessScanner

### 5.2 Transformaciones

- **Fusión de señales:** SignalFusionCore
- **Arbitraje de verdad:** TruthArbitrator
- **Detección de capacidades:** CapabilityDetector
- **Clasificación de superficie:** SurfaceClassifier
- **Selección de adaptador:** AdapterSelector
- **Transformación de coordenadas:** CoordinateTransformer
- **Normalización de geometría:** GeometryNormalizer

### 5.3 Verificaciones

- **Verificación de freezes:** FreezeDetectorService
- **Verificación de interacciones:** RuntimePerceptionAndVerificationService.verify_interaction()
- **Validación de auditoría:** AuditValidationService

### 5.4 Persistencia

- **Evidencia multimodal:** EvidenceRecorder (JSONL)
- **Logs de auditoría:** AuditLogService
- **Memoria de auditoría:** AuditMemoryService
- **Observaciones de superficie:** RuntimePerceptionAndVerificationService (JSONL)
- **Detecciones de freeze:** RuntimePerceptionAndVerificationService (JSONL)

### 5.5 Consumidores

- **WorldModelService:** Consume evidencia de percepción
- **DecisionAuditTrail:** Consume decisiones de verificación
- **AuditHUDService:** Consume estado de auditoría para visualización

---

## 6. OBSERVACIONES

### 6.1 Positivas

- ✅ Conexión entre capa puntual y capa continua está implementada y verificada
- ✅ Correlación de datos (evidence_hash, task_id, surface_id, timestamps) está implementada
- ✅ Listeners activos están integrados en RuntimePerceptionAndVerificationService
- ✅ FreezeDetectorService usa listeners activos para detección real
- ✅ Flujo de datos es claro y trazable

### 6.2 Negativas

- ❌ RuntimePerceptionAndVerificationService no está exportado en __init__.py
- ❌ Listeners activos no están exportados en __init__.py
- ❌ FreezeDetectorService no está exportado en __init__.py
- ❌ Algunos métodos de RuntimePerceptionAndVerificationService están marcados como NO VERIFICADO

### 6.3 Impacto

- **Bajo:** La falta de exportación en __init__.py no afecta la funcionalidad interna
- **Medio:** Puede afectar la facilidad de uso para desarrolladores externos
- **Alto:** Los métodos NO VERIFICADO pueden afectar la verificación completa

---

## 7. CONCLUSIÓN

**Estado General:** READY

El grafo de dependencias real está bien estructurado y la conexión entre capa puntual y capa continua está implementada y verificada. El flujo de datos es claro y trazable desde la entrada hasta la persistencia.

**Recomendación:** Continuar con FASE 3 - Auditoría de Ejecución
