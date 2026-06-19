# FASE 0: INVENTARIO Y MAPA DE CAPACIDADES
## Capa de Percepción Runtime Multimodal IABV v1.5

**Fecha:** 2026-06-17
**Objetivo:** Inventariar capacidades existentes, identificar gaps, y mapear equivalencias entre señales.

---

## 1. CAPACIDADES EXISTENTES

### 1.1 Modelos de Datos (multimodal_data_models.py)

**VisualSignal:**
- screenshot_path: str
- screenshot_sha256: str
- screenshot_width: int
- screenshot_height: int
- screenshot_blank_probability: float
- ocr_text: str
- ocr_confidence: float
- ocr_status: str ("available", "disabled", "failed")
- accessibility_tree: dict[str, Any]
- accessibility_available: bool
- dom_text: str
- dom_available: bool
- visual_labels: list[str]
- state_hypothesis: str ("visible", "minimized", "frozen", etc.)
- timestamp_utc: str

**ProcessSignal:**
- pid: int
- process_name: str
- process_exe: str
- window_handle: int (HWND)
- window_title: str
- window_class: str
- window_rect: list[int] [left, top, right, bottom]
- window_visible: bool
- window_focused: bool
- cpu_percent: float
- memory_mb: float
- thread_count: int
- process_uptime_seconds: float
- timestamp_utc: str

**EventSignal:**
- input_events: list[InputEvent]
- output_events: list[OutputEvent]
- focus_change_event: FocusChangeEvent | None
- lifecycle_events: list[LifecycleEvent]
- task_state_events: list[TaskStateEvent]
- timestamp_utc: str

**EvidenceRecord:**
- evidence_id: str
- task_id: str
- timestamp_utc: str
- truth_source: str ("process", "screenshot", "hwnd", "focus", "unknown")
- truth_confidence: float (0.0 - 1.0)
- state_before: dict[str, Any]
- state_after: dict[str, Any]
- visual_signal: VisualSignal
- process_signal: ProcessSignal
- event_signal: EventSignal
- evidence_hash: str (SHA256 de todas las señales)
- evidence_type: str (EvidenceType enum)
- source: str ("ai_action", "user_action", "system_event")
- action_type: str ("click", "type", "launch", "close", etc.)
- surface_id: str (HWND o PID)
- surface_title: str
- correlated_evidence_ids: list[str]
- inconsistency_detected: bool
- inconsistency_details: list[str]
- persisted: bool
- persistence_path: str

### 1.2 Componentes de Fusión y Arbitraje

**SignalFusionCore:**
- fuse_signals(): Fusiona visual, process, event en EvidenceRecord
- _detect_inconsistencies(): Detecta 5 inconsistencias básicas
- _index_evidence(): Indexa por hash para correlación
- get_correlated_evidence(): Retorna evidencia correlacionada
- correlate_with_existing(): Busca similitudes (futuro)
- get_inconsistency_summary(): Resumen de inconsistencias (futuro)

**TruthArbitrator:**
- arbitrate(): Determina truth_source y truth_confidence
- _determine_truth_source(): 9 reglas de prioridad
- SOURCE_PRIORITY: PROCESS=1.0, SCREENSHOT=0.95, HWND=1.0, FOCUS=1.0
- resolve_conflict(): Resuelve conflictos entre fuentes
- get_arbitration_history(): Historial de arbitraje

**EvidenceRecorder:**
- record(): Persiste EvidenceRecord en JSONL
- get_by_task_id(): Búsqueda por task_id
- get_by_evidence_hash(): Búsqueda por hash
- get_recent(): Registros más recientes
- get_statistics(): Estadísticas por tipo, fuente, truth_source
- _apply_retention(): Limpieza de registros viejos

**MultimodalPerceptionService:**
- capture_action(): Captura acción completa con percepción multimodal
- _capture_visual_signal(): Screenshot + OCR + accessibility
- _capture_process_signal(): PID + ventana + recursos
- _capture_event_signal(): Input/output + focus + lifecycle
- _determine_evidence_type(): Jerarquía de decisión robusta
- get_evidence_by_task_id(): Consulta por task_id
- get_evidence_by_hash(): Consulta por hash
- get_recent_evidence(): Evidencia reciente
- get_statistics(): Estadísticas

### 1.3 Tipos de Evidencia (EvidenceType)

- ACTION_VISIBLE: "action_visible"
- ACTION_INVISIBLE_PERSISTED: "action_invisible_persisted"
- FOCUS_LOST: "focus_lost"
- FREEZE: "freeze"
- RESPONSE_VISIBLE_NOT_PERSISTED: "response_visible_not_persisted"
- PERSISTENCE_CORRECT_UI_NOT_REFLECTING: "persistence_correct_ui_not_reflecting"
- UNKNOWN: "unknown"

### 1.4 Fuentes de Verdad (TruthSource)

- PROCESS: "process"
- SCREENSHOT: "screenshot"
- HWND: "hwnd"
- FOCUS: "focus"
- UNKNOWN: "unknown"

---

## 2. CAPACIDADES FALTANTES

### 2.1 Detección de Capacidades de Superficie (Capability-First)

**FALTA:**
- Capacidad de detectar tipo de superficie (desktop, browser, remoto, móvil)
- Capacidad de detectar plataforma (Windows, macOS, Linux, Android, iOS)
- Capacidad de detectar disponibilidad de accessibility tree
- Capacidad de detectar disponibilidad de OCR
- Capacidad de detectar disponibilidad de screenshot
- Capacidad de detectar disponibilidad de input de teclado
- Capacidad de detectar disponibilidad de clipboard
- Capacidad de detectar disponibilidad de logs
- Capacidad de detectar disponibilidad de persistencia
- Capacidad de detectar geometría de pantalla / DPI / resolución

**NECESITA:**
- CapabilityDetector: Nuevo componente para detectar capacidades
- SurfaceClassifier: Nuevo componente para clasificar superficie
- AdapterSelector: Nuevo componente para seleccionar adaptador correcto

### 2.2 Normalización de Coordenadas y Geometría

**FALTA:**
- viewport: región visible actual
- screen_size: tamaño de pantalla física
- scale_factor: factor de escala (DPI)
- pixel_density: densidad de píxeles (PPI)
- normalized_coordinates: coordenadas normalizadas (0.0-1.0)
- visible_region: región visible en coordenadas normalizadas
- offscreen_region: región fuera de pantalla
- multi-monitor: soporte para múltiples monitores
- zoom/scaling: detección de zoom del navegador o sistema

**NECESITA:**
- GeometryNormalizer: Nuevo componente para normalizar geometría
- ScreenInfoProvider: Nuevo componente para obtener info de pantalla
- CoordinateTransformer: Nuevo componente para transformar coordenadas

### 2.3 Separación de Verdad (Visual / Operativa / Persistente)

**FALTA:**
- Verdad visual: lo que se ve en pantalla
- Verdad operativa: lo que el sistema reporta como estado
- Verdad persistente: lo que queda guardado en disco
- Arbitraje explícito entre las tres verdades
- Explicación de por qué una verdad ganó
- Detección de contradicciones entre verdades

**NECESITA:**
- TruthType enum: VISUAL, OPERATIONAL, PERSISTENT
- EnhancedTruthArbitrator: Refactorizar TruthArbitrator actual
- TruthExplanation: Campo para explicar decisión de arbitraje
- TruthConflictDetector: Detector de conflictos entre verdades

### 2.4 Adaptadores Multi-Plataforma

**FALTA:**
- Adaptador Windows (Win32)
- Adaptador macOS (Cocoa)
- Adaptador Linux (X11/Wayland)
- Adaptador Browser (CDP/WebDriver)
- Adaptador Remoto (SSH/RDP)
- Adaptador Móvil (ADB)

**NECESITA:**
- PlatformAdapter: Interfaz base para adaptadores
- Win32Adapter: Implementación Windows
- BrowserAdapter: Implementación Browser
- AdapterRegistry: Registro de adaptadores disponibles

### 2.5 Métricas de Calibración

**FALTA:**
- Precisión de evidence_type
- Cobertura de señales por superficie
- Tasa de contradicciones
- Tasa de falsos positivos
- Tasa de falsos negativos
- Latencia de percepción
- Latencia de verificación
- Precisión de prompt-response matching
- Precisión de ownership IA/usuario
- Estabilidad por resolución/DPI
- Tasa de fallback correcto
- Consistencia entre visual/operativa/persistente

**NECESITA:**
- CalibrationMetrics: Nuevo componente para métricas
- MetricsCollector: Colector de métricas en runtime
- MetricsReporter: Reporteador de métricas

### 2.6 Pruebas de Calibración con Escenarios Duros

**FALTA:**
- Escenario 7: accessibility tree ausente
- Escenario 8: OCR presente pero árbol inconsistente
- Escenario 9: pantalla con distinto DPI/resolución
- Escenario 10: multi-monitor o surface parcialmente visible
- Escenario 11: background action
- Escenario 12: mismatch prompt-response

**NECESITA:**
- EnhancedCalibrationSuite: Suite de calibración extendida
- CalibrationScenario: Modelo para escenarios de calibración
- CalibrationResult: Resultado de calibración con métricas

### 2.7 Integración Runtime Real

**FALTA:**
- Evidencia de inicialización en runtime real
- Evidencia de start/stop en runtime real
- Evidencia de captura de acciones en runtime real
- Evidencia de persistencia en runtime real
- Evidencia de uso real en ejecución
- Trazabilidad en logs runtime

**NECESITA:**
- RuntimeIntegration: Integración con bootstrap
- RuntimeLogger: Logger especializado para runtime
- RuntimeTracer: Trazador de ejecución

---

## 3. MAPA DE EQUIVALENCIAS ENTRE SEÑALES

### 3.1 Screenshot ↔ Verdad Visual

**Equivalencias:**
- screenshot_sha256 ≠ "" → Verdad visual CONFIRMADA
- screenshot_blank_probability > 0.8 → Verdad visual NEGADA
- screenshot_width/height → Geometría de pantalla
- screenshot_path → Persistencia de imagen

**Gaps:**
- No hay normalización de coordenadas
- No hay detección de DPI
- No hay soporte multi-monitor

### 3.2 OCR ↔ Verdad Visual

**Equivalencias:**
- ocr_text ≠ "" → Texto visible CONFIRMADO
- ocr_confidence → Confianza en OCR
- ocr_status → Estado del servicio OCR

**Gaps:**
- No hay comparación OCR vs accessibility tree
- No hay comparación OCR vs DOM
- No hay detección de inconsistencias OCR

### 3.3 Accessibility Tree ↔ Verdad Operativa

**Equivalencias:**
- accessibility_available → Capacidad de accesibilidad
- accessibility_tree → Estructura UI operativa

**Gaps:**
- No hay detección de ausencia de accessibility tree
- No hay comparación accessibility vs OCR
- No hay comparación accessibility vs DOM

### 3.4 Ventana Activa y Foco ↔ Verdad Operativa

**Equivalencias:**
- window_focused → Foco CONFIRMADO
- window_visible → Visibilidad CONFIRMADA
- focus_change_event → Cambio de foco DETECTADO

**Gaps:**
- No hay distinción entre foco e interacción exitosa
- No hay detección de foco perdido pero acción declarada exitosa

### 3.5 Proceso Activo ↔ Verdad Operativa

**Equivalencias:**
- pid > 0 → Proceso CONFIRMADO
- process_name/exe → Identidad del proceso
- cpu_percent/memory_mb → Estado de recursos
- process_uptime_seconds → Longevidad del proceso

**Gaps:**
- No hay distinción entre proceso e intención
- No hay detección de proceso activo pero UI en blanco

### 3.6 Eventos de Input/Output ↔ Verdad Operativa

**Equivalencias:**
- input_events → Acciones de entrada
- output_events → Respuestas del sistema

**Gaps:**
- No hay captura real de eventos (solo placeholder)
- No hay correlación input/output
- No hay detección de eventos en segundo plano

### 3.7 Acciones en Segundo Plano ↔ Verdad Persistente

**Equivalencias:**
- evidence_type → Clasificación de acción
- persisted → Evidencia guardada en disco

**Gaps:**
- No hay detección explícita de acciones en segundo plano
- No hay trazabilidad de acciones asíncronas
- No hay verificación de que la acción dejó trazas

### 3.8 Logs JSONL ↔ Verdad Persistente

**Equivalencias:**
- evidence_records.jsonl → Persistencia completa
- evidence_index.jsonl → Índice por hash

**Gaps:**
- No hay logs de lifecycle events
- No hay logs de launch attempts
- No hay logs de ownership records
- No hay logs de fallback decisions

### 3.9 Geometría de Pantalla / Resolución / DPI ↔ Verdad Visual

**Equivalencias:**
- window_rect → Rectángulo de ventana
- screenshot_width/height → Tamaño de captura

**Gaps:**
- No hay screen_size (tamaño de pantalla física)
- No hay scale_factor (factor de escala)
- No hay pixel_density (PPI)
- No hay normalized_coordinates
- No hay visible_region/offscreen_region
- No hay soporte multi-monitor

### 3.10 Contexto de Sesión / Ownership ↔ Verdad Operativa

**Equivalencias:**
- source → "ai_action", "user_action", "system_event"
- task_id → ID de tarea asociada

**Gaps:**
- No hay ownership IA/usuario explícito
- No hay contexto de sesión
- No hay detección de ownership

---

## 4. DIAGNÓSTICO INICIAL

### 4.1 Lo Que Está Bien

✅ **Arquitectura base sólida:**
- Modelos de datos bien definidos
- Separación clara entre VisualSignal, ProcessSignal, EventSignal
- EvidenceRecord como fusión de todas las señales
- Hashing para correlación

✅ **Fusión básica funcional:**
- SignalFusionCore fusiona señales correctamente
- Detección de 5 inconsistencias básicas
- Indexación por hash para correlación

✅ **Arbitraje de verdad funcional:**
- TruthArbitrator tiene 9 reglas de prioridad
- Confidence scores calculados
- Historial de arbitraje mantenido

✅ **Persistencia funcional:**
- EvidenceRecorder persiste en JSONL
- Indexación por task_id y hash
- Retención de registros
- Estadísticas básicas

✅ **Jerarquía de evidence_type robusta:**
- _determine_evidence_type tiene jerarquía clara
- 6/7 tipos de evidencia cubiertos
- Fallback a UNKNOWN explícito

### 4.2 Lo Que Falta

❌ **No hay detección de capacidades:**
- No hay CapabilityDetector
- No hay SurfaceClassifier
- No hay AdapterSelector
- Se asume Windows como única plataforma
- Se asume desktop como única superficie

❌ **No hay normalización de geometría:**
- No hay GeometryNormalizer
- No hay ScreenInfoProvider
- No hay CoordinateTransformer
- No hay soporte multi-monitor
- No hay detección de DPI/resolución

❌ **No hay separación de verdad:**
- TruthArbitrator no distingue visual/operativa/persistente
- No hay TruthType enum
- No hay explicación de por qué una verdad ganó
- No hay TruthConflictDetector

❌ **No hay adaptadores multi-plataforma:**
- Solo Win32 implícito
- No hay PlatformAdapter
- No hay BrowserAdapter
- No hay AdapterRegistry

❌ **No hay métricas de calibración:**
- No hay CalibrationMetrics
- No hay MetricsCollector
- No hay MetricsReporter
- No hay medición de precisión, cobertura, latencia

❌ **No hay pruebas de calibración duros:**
- Solo 6 escenarios básicos
- Faltan escenarios 7-12
- No hay EnhancedCalibrationSuite
- No hay CalibrationScenario model

❌ **No hay integración runtime real:**
- Solo funciona en tests simulados
- No hay evidencia de ejecución real
- No hay RuntimeIntegration
- No hay RuntimeTracer

---

## 5. PLAN DE ACCIÓN

### 5.1 Prioridad Alta (Fases 1-3)

1. **FASE 1:** Mejorar arbitraje de verdad con separación visual/operativa/persistente
2. **FASE 2:** Mejorar SignalFusionCore con detección avanzada de contradicciones
3. **FASE 3:** Agregar capa capability-first con detección de capacidades

### 5.2 Prioridad Media (Fases 4-5)

4. **FASE 4:** Calibración por dimensión y dispositivo (DPI/resolución)
5. **FASE 5:** Mejorar evidencia persistente para auditoría

### 5.3 Prioridad Baja (Fases 6-9)

6. **FASE 6:** Crear suite de calibración con escenarios duros
7. **FASE 7:** Agregar métricas de calibración
8. **FASE 8:** Integración runtime con evidencia real
9. **FASE 9:** Generar salida obligatoria con diagnóstico y conclusiones

---

## 6. CONCLUSIÓN DE FASE 0

**Estado actual:** La capa tiene una arquitectura base sólida con modelos de datos bien definidos, fusión básica, arbitraje funcional, y persistencia operativa. Sin embargo, falta la capa capability-first, normalización de geometría, separación de verdad, adaptadores multi-plataforma, métricas de calibración, pruebas de escenarios duros, y evidencia de runtime real.

**Próximo paso:** FASE 1 - Mejorar arbitraje de verdad con separación visual/operativa/persistente.
