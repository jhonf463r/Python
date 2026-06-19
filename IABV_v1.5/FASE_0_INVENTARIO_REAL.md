# FASE 0: Inventario Real y Mapa de Equivalencias

**Fecha:** 2025-01-17  
**Objetivo:** Mapear entidades conceptuales a módulos reales en el repo IABV v1.5

---

## Confirmación de Repo Root

**Repo Root:** `C:\Python\IABV_v1.5` ✅ Confirmado

---

## Directorios Relevantes

### src/iabv_v15/services/perception/
Contiene los módulos de percepción multimodal:
- `adapter_selector.py` (13,280 bytes)
- `calibration_metrics.py` (12,238 bytes)
- `calibration_test_suite.py` (39,133 bytes)
- `capability_detector.py` (15,144 bytes)
- `coordinate_transformer.py` (9,765 bytes)
- `evidence_recorder.py` (16,853 bytes)
- `geometry_normalizer.py` (7,684 bytes)
- `multimodal_data_models.py` (18,306 bytes)
- `multimodal_perception_service.py` (22,104 bytes)
- `runtime_perception_and_verification_service.py` (36,884 bytes)
- `screen_info_provider.py` (10,263 bytes)
- `signal_fusion_core.py` (11,890 bytes)
- `surface_classifier.py` (5,502 bytes)
- `truth_arbitrator.py` (17,264 bytes)

### src/iabv_v15/services/evolution/
Contiene servicios de evolución y metacognición:
- `perception_cross_validator.py` (19,238 bytes) - Posible relevancia para verificación
- `runtime_signal_collector.py` (3,179 bytes) - Posible relevancia para captura de señales

---

## Mapa de Equivalencias: Entidades Conceptuales → Módulos Reales

| Entidad Conceptual | Módulo Real | Estado | Observaciones |
|-------------------|-------------|--------|---------------|
| MultimodalPerceptionService | `multimodal_perception_service.py` | ✅ EXISTE | Orquestador central de percepción multimodal |
| SignalFusionCore | `signal_fusion_core.py` | ✅ EXISTE | Fusión de señales con detección de inconsistencias |
| TruthArbitrator | `truth_arbitrator.py` | ✅ EXISTE | Arbitraje de verdad con separación visual/operativa/persistente |
| EvidenceRecorder | `evidence_recorder.py` | ✅ EXISTE | Persistencia de evidencia en JSONL |
| CapabilityRegistry | `capability_detector.py` | ⚠️ EQUIVALENTE | No existe como "CapabilityRegistry", pero `capability_detector.py` cumple la función de detección de capacidades |
| SurfaceClassifier | `surface_classifier.py` | ✅ EXISTE | Clasificación de superficie (desktop, browser, remote, mobile, mixed) |
| AdapterSelector | `adapter_selector.py` | ✅ EXISTE | Selección de adaptador con fallback automático |
| RuntimePerceptionAndVerificationService | `runtime_perception_and_verification_service.py` | ✅ EXISTE | Servicio de percepción y verificación runtime |
| ScreenGeometry | `screen_info_provider.py` + `multimodal_data_models.py` | ✅ EXISTE | ScreenGeometry como dataclass en multimodal_data_models.py, detección en screen_info_provider.py |
| CoordinateTransformer | `coordinate_transformer.py` | ✅ EXISTE | Transformación de coordenadas entre espacios |
| GeometryNormalizer | `geometry_normalizer.py` | ✅ EXISTE | Normalización de geometría para independencia de resolución |
| CalibrationMetrics | `calibration_metrics.py` | ✅ EXISTE | Colecta de 13 métricas de performance |

---

## Capacidades Detectadas por CapabilityDetector

El módulo `capability_detector.py` detecta las siguientes capacidades:

1. **window_focus_access** - Acceso a ventana/foco
2. **process_access** - Acceso a procesos
3. **screenshot_access** - Acceso a screenshot
4. **ocr_access** - Acceso a OCR
5. **accessibility_tree_access** - Acceso a accessibility tree
6. **keyboard_input_access** - Acceso a input de teclado
7. **clipboard_access** - Acceso a clipboard
8. **logs_access** - Acceso a logs
9. **persistence_access** - Acceso a persistencia
10. **geometry_access** - Acceso a geometría de pantalla

**FALTAN (según requerimiento del usuario):**
- **browser_access** - Acceso a navegador
- **native_app_access** - Acceso a app nativa
- **remote_access** - Acceso a remoto

---

## Estado de Componentes por Fase

### FASE 1: Arbitraje de Verdad
- **TruthArbitrator** ✅ EXISTE con separación visual/operativa/persistente
- **TruthType enum** ✅ EXISTE en multimodal_data_models.py
- **Confidence scores individuales** ✅ EXISTEN
- **Detección de conflictos** ✅ EXISTE (7 tipos)
- **Explicaciones de arbitraje** ✅ EXISTEN

### FASE 2: Signal Fusion
- **SignalFusionCore** ✅ EXISTE con detección de inconsistencias
- **InconsistencyType enum** ✅ EXISTE (7 tipos)
- **Historial de inconsistencias** ✅ EXISTE
- **Resumen de inconsistencias** ✅ EXISTE

### FASE 3: Capability-First
- **CapabilityDetector** ✅ EXISTE (detecta 10 capacidades)
- **SurfaceClassifier** ✅ EXISTE (5 tipos de superficie)
- **AdapterSelector** ✅ EXISTE (mapa de adaptadores por plataforma/superficie)
- **CapabilityProfile** ✅ EXISTE en multimodal_data_models.py

### FASE 4: Adaptación a Dimensión y Dispositivo
- **ScreenInfoProvider** ✅ EXISTE (Windows, macOS, Linux)
- **CoordinateTransformer** ✅ EXISTE (transformación entre espacios)
- **GeometryNormalizer** ✅ EXISTE (normalización de coordenadas)
- **ScreenGeometry** ✅ EXISTE en multimodal_data_models.py
- **NormalizedCoordinates** ✅ EXISTE en multimodal_data_models.py

### FASE 5: Calibración Real
- **CalibrationTestSuite** ✅ EXISTE (12 escenarios: 6 básicos + 6 duros)
- **Escenarios duros implementados:**
  - Escenario 7: accessibility tree ausente ✅
  - Escenario 8: OCR presente pero árbol inconsistente ✅
  - Escenario 9: pantalla con distinto DPI/resolución ✅
  - Escenario 10: multi-monitor / surface parcialmente visible ✅
  - Escenario 11: background action ✅
  - Escenario 12: mismatch prompt-response ✅

### FASE 6: Métricas de Calibración
- **CalibrationMetrics** ✅ EXISTE (13 métricas)
  - evidence_type_accuracy ✅
  - signal_coverage ✅
  - contradiction_rate ✅
  - false_positive_rate ✅
  - false_negative_rate ✅
  - avg_perception_latency ✅
  - avg_verification_latency ✅
  - prompt_response_accuracy ✅
  - ownership_accuracy ✅
  - resolution_stability ✅
  - fallback_rate ✅
  - fallback_accuracy ✅
  - truth_consistency ✅

### FASE 7: Verificación Runtime Real
- **verify_runtime_integration.py** ✅ EXISTE (script de verificación)
- **bootstrap.py** ✅ EXISTE con integración de MultimodalPerceptionService
- **Integración en runtime** ✅ VERIFICADA en bootstrap.py

### FASE 8: Prompt/Response, Ownership y Secuencia
- **Campos en EvidenceRecord** ✅ EXISTEN:
  - prompt_sent ✅
  - response_received ✅
  - prompt_response_match ✅
  - ownership_record ✅
  - launch_attempt ✅
  - freeze_detection ✅
- **RuntimePerceptionAndVerificationService** ✅ EXISTE (36,884 bytes)

### FASE 9: Salida Obligatoria
- **DIAGNOSTICO_FINAL_CALIBRACION.md** ✅ EXISTE (diagnóstico completo)

---

## Gaps Identificados

### Capacidades Faltantes en CapabilityDetector
1. **browser_access** - No detectado actualmente
2. **native_app_access** - No detectado actualmente
3. **remote_access** - No detectado actualmente

### Verificación Runtime Real
- **verify_runtime_integration.py** existe pero usa simulación si no hay servicios reales
- **No hay evidencia de captura real de Accessibility Tree en producción**
- **No hay evidencia de eventos reales de input/output en producción**
- **No hay logs runtime de producción verificados**

### Tests con TemporaryDirectory
- Los tests actuales pueden usar TemporaryDirectory (necesita verificación)
- El usuario explícitamente NO quiere tests que oculten la realidad con TemporaryDirectory

---

## Conclusión del Inventario

**Estado General:** La mayoría de los componentes conceptuales existen como módulos reales. La arquitectura capability-first está implementada. Los 12 escenarios de calibración existen. Las 13 métricas de calibración existen.

**Gaps Críticos:**
1. Faltan 3 capacidades en CapabilityDetector (browser, native_app, remote)
2. Falta verificación real de captura de Accessibility Tree en producción
3. Falta verificación real de eventos de input/output en producción
4. Falta verificación de logs runtime de producción
5. Posible uso de TemporaryDirectory en tests (necesita verificación)

**Próxima Acción:** Comenzar FASE 1 para mejorar el arbitraje de verdad con enfoque en verificación real, no simulación.
