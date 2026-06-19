# CAPA DE PERCEPCIÓN RUNTIME MULTIMODAL - IABV v1.5
**Fecha**: 2026-06-17  
**Objetivo**: Capturar y correlacionar en tiempo real múltiples señales para construir la verdad del sistema

---

## 1. ARQUITECTURA PROPUESTA

### 1.1 Principio de Diseño: Fusión de Señales

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTIMODAL PERCEPTION LAYER                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  VISUAL      │  │  PROCESS     │  │  EVENT       │          │
│  │  SENSOR      │  │  SENSOR      │  │  SENSOR      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Screenshot   │  │ Active PID   │  │ Input/Output │          │
│  │ OCR Text     │  │ Window List  │  │ Focus Change │          │
│  │ Acc. Tree    │  │ Memory/CPU   │  │ Task Events  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                           ▼                                     │
│              ┌──────────────────────┐                          │
│              │  SIGNAL FUSION CORE  │                          │
│              │  (Evidence Hashing)  │                          │
│              └──────────┬───────────┘                          │
│                         │                                       │
│                         ▼                                       │
│              ┌──────────────────────┐                          │
│              │  TRUTH ARBITRATOR    │                          │
│              │  (Source Priority)   │                          │
│              └──────────┬───────────┘                          │
│                         │                                       │
│                         ▼                                       │
│              ┌──────────────────────┐                          │
│              │  EVIDENCE RECORD     │                          │
│              │  (task_id, timestamp,│                          │
│              │   state_before/after) │                          │
│              └──────────────────────┘                          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Componentes Principales

**1. MultimodalPerceptionService** (Nuevo)
- Orquestador central de todos los sensores
- Coordina captura simultánea de múltiples señales
- Genera evidence hashes para correlación

**2. SignalFusionCore** (Nuevo)
- Fusiona señales visuales, de proceso y de eventos
- Aplica hashing para deduplicación y correlación
- Detecta inconsistencias entre fuentes

**3. TruthArbitrator** (Nuevo)
- Define prioridad de fuentes de verdad
- Resuelve conflictos entre señales contradictorias
- Emite veredicto con confidence score

**4. EvidenceRecorder** (Nuevo)
- Registra acciones en segundo plano con metadatos completos
- Persiste evidencia con task_id, timestamp, source, state_before, state_after
- Indexa por evidence hash para recuperación rápida

**5. CalibrationTestSuite** (Nuevo)
- Batería de pruebas para validar percepción
- Simula escenarios edge case
- Genera reportes de calibración

### 1.3 Flujo de Datos

```
Evento Trigger → Captura Multimodal → Fusión de Señales → Arbitraje de Verdad → Registro de Evidencia
     ↓                  ↓                    ↓                    ↓                      ↓
  Task Start      Screenshot +         Evidence Hash      Source Priority      task_id: uuid
  User Action     Process List          Correlation       Conflict Resolution   timestamp: ISO
  System Event    Focus State          Inconsistency      Confidence Score     state_before: dict
  API Call        OCR Text              Detection          Truth Verdict        state_after: dict
                  Accessibility Tree                                          evidence: hash
```

---

## 2. SEÑALES A USAR Y NO USAR COMO VERDAD ABSOLUTA

### 2.1 Fuentes de Verdad (High Priority)

**1. Process List + PID** (VERDAD ABSOLUTA)
- **Por qué**: Un proceso existe o no existe, no hay ambigüedad
- **Confianza**: 1.0
- **Uso**: Determinar si una herramienta está realmente ejecutándose
- **Limitaciones**: No indica estado de UI (puede estar corriendo pero congelado)

**2. Screenshot + SHA256** (VERDAD ABSOLUTA)
- **Por qué**: La imagen es evidencia directa de lo que hay en pantalla
- **Confianza**: 0.95 (si capture exitosa)
- **Uso**: Verificar estado visual de UI, detectar freezes
- **Limitaciones**: No captura estado interno, solo superficie

**3. Window Handle (HWND)** (VERDAD ABSOLUTA)
- **Por qué**: El handle es único e inmutable mientras la ventana existe
- **Confianza**: 1.0
- **Uso**: Rastrear ventanas específicas a través del tiempo
- **Limitaciones**: No indica si la ventana está visible o tiene foco

**4. Focus State** (VERDAD ABSOLUTA)
- **Por qué**: El OS tiene un único foco, no hay ambigüedad
- **Confianza**: 1.0
- **Uso**: Determinar qué ventana recibe input
- **Limitaciones**: Cambia rápidamente, puede ser race condition

### 2.2 Fuentes de Apoyo (Medium Priority)

**1. OCR Text** (APOYO)
- **Por qué**: Puede fallar en imágenes borrosas, baja resolución, texto complejo
- **Confianza**: 0.6-0.8
- **Uso**: Complementar screenshot cuando DOM no disponible
- **Limitaciones**: Falso positivo/negativo, lento

**2. Accessibility Tree** (APOYO)
- **Por qué**: No todas las apps exponen accessibility tree
- **Confianza**: 0.7-0.9 (si disponible)
- **Uso**: Complementar DOM para apps nativas
- **Limitaciones**: Incompleto, inconsistente entre apps

**3. Window Title** (APOYO)
- **Por qué**: Puede cambiar dinámicamente, puede ser genérico
- **Confianza**: 0.5-0.7
- **Uso**: Identificación rápida de ventanas
- **Limitaciones**: No único, puede ser "Untitled", "New Tab"

**4. DOM/CDP** (APOYO)
- **Por qué**: Solo disponible en browsers con CDP habilitado
- **Confianza**: 0.8-0.95 (si disponible)
- **Uso**: Estructura precisa de web apps
- **Limitaciones**: No disponible en apps nativas, headless

### 2.3 Fuentes de Baja Confianza (Low Priority)

**1. Log Files** (BAJA CONFIANZA)
- **Por qué**: Pueden estar desactualizados, incompletos, rotos
- **Confianza**: 0.3-0.5
- **Uso**: Correlación histórica, no tiempo real
- **Limitaciones**: Latencia de escritura, buffering, pérdida

**2. User Assertions** (BAJA CONFIANZA)
- **Por qué**: El usuario puede estar equivocado o impreciso
- **Confianza**: 0.4-0.6
- **Uso**: Hint inicial, requiere verificación
- **Limitaciones**: Subjetivo, puede ser engañoso

**3. Tool Registry Cache** (BAJA CONFIANZA)
- **Por qué**: Cache puede estar stale
- **Confianza**: 0.2-0.4
- **Uso**: Optimización, no fuente primaria
- **Limitaciones**: Desincronización con realidad

### 2.4 Regla de Fusión

```
VEREDICTO FINAL = 
  IF Process List + PID CONFIRMA → TRUST = 1.0
  IF Screenshot + SHA256 CONFIRMA → TRUST = 0.95
  IF HWND CONFIRMA → TRUST = 1.0
  IF Focus State CONFIRMA → TRUST = 1.0
  
  IF (Process List + PID) AND (Screenshot) AGREE → TRUST = 1.0
  IF (Process List + PID) AND (Screenshot) DISAGREE → TRUST = 0.5 (INVESTIGATE)
  
  IF (High Priority) CONFIRMA AND (Medium Priority) DISAGREE → TRUST High Priority
  IF (High Priority) MISSING AND (Medium Priority) CONFIRMA → TRUST Medium Priority WITH WARNING
  
  IF ALL SOURCES DISAGREE → TRUST = 0.0 (UNKNOWN)
```

---

## 3. ESQUEMA DE EVIDENCIA

### 3.1 EvidenceRecord (Core Schema)

```python
@dataclass(slots=True)
class EvidenceRecord:
    """Registro de evidencia multimodal con fusión de señales."""
    
    # Identificación
    evidence_id: str = field(default_factory=lambda: uuid4().hex)
    task_id: str = ""  # ID de la tarea asociada
    timestamp_utc: str = ""  # ISO 8601
    
    # Fuente de verdad
    truth_source: str = ""  # "process", "screenshot", "hwnd", "focus"
    truth_confidence: float = 0.0  # 0.0 - 1.0
    
    # Estado antes/después
    state_before: dict[str, Any] = field(default_factory=dict)
    state_after: dict[str, Any] = field(default_factory=dict)
    
    # Señales capturadas
    visual_signal: VisualSignal = field(default_factory=VisualSignal)
    process_signal: ProcessSignal = field(default_factory=ProcessSignal)
    event_signal: EventSignal = field(default_factory=EventSignal)
    
    # Evidencia
    evidence_hash: str = ""  # SHA256 de todas las señales fusionadas
    evidence_type: str = ""  # "action_visible", "action_invisible", "freeze", etc.
    
    # Metadatos
    source: str = ""  # "ai_action", "user_action", "system_event"
    action_type: str = ""  # "click", "type", "launch", "close", etc.
    surface_id: str = ""  # HWND o PID
    surface_title: str = ""
    
    # Correlación
    correlated_evidence_ids: list[str] = field(default_factory=list)
    inconsistency_detected: bool = False
    inconsistency_details: list[str] = field(default_factory=list)
    
    # Persistencia
    persisted: bool = False
    persistence_path: str = ""
```

### 3.2 VisualSignal

```python
@dataclass(slots=True)
class VisualSignal:
    """Señal visual: screenshot + OCR + accessibility."""
    
    screenshot_path: str = ""
    screenshot_sha256: str = ""
    screenshot_width: int = 0
    screenshot_height: int = 0
    screenshot_blank_probability: float = 0.0
    
    ocr_text: str = ""
    ocr_confidence: float = 0.0
    ocr_status: str = ""  # "available", "disabled", "failed"
    
    accessibility_tree: dict[str, Any] = field(default_factory=dict)
    accessibility_available: bool = False
    
    dom_text: str = ""
    dom_available: bool = False
    
    visual_labels: list[str] = field(default_factory=list)
    state_hypothesis: str = ""  # "visible", "minimized", "frozen", etc.
```

### 3.3 ProcessSignal

```python
@dataclass(slots=True)
class ProcessSignal:
    """Señal de proceso: PID + ventana + recursos."""
    
    pid: int = 0
    process_name: str = ""
    process_exe: str = ""
    
    window_handle: int = 0  # HWND
    window_title: str = ""
    window_class: str = ""
    window_rect: list[int] = field(default_factory=list)  # [left, top, right, bottom]
    window_visible: bool = False
    window_focused: bool = False
    
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    thread_count: int = 0
    
    process_uptime_seconds: float = 0.0
```

### 3.4 EventSignal

```python
@dataclass(slots=True)
class EventSignal:
    """Señal de eventos: input/output + focus + lifecycle."""
    
    input_events: list[InputEvent] = field(default_factory=list)
    output_events: list[OutputEvent] = field(default_factory=list)
    
    focus_change_event: FocusChangeEvent | None = None
    lifecycle_events: list[LifecycleEvent] = field(default_factory=list)
    
    task_state_events: list[TaskStateEvent] = field(default_factory=list)
    
    timestamp_utc: str = ""

@dataclass(slots=True)
class InputEvent:
    event_id: str = ""
    timestamp_utc: str = ""
    event_type: str = ""  # "key_press", "mouse_click", "touch"
    source: str = ""  # "ai", "user", "system"
    target_surface: str = ""
    data: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class OutputEvent:
    event_id: str = ""
    timestamp_utc: str = ""
    event_type: str = ""  # "screen_update", "response", "error"
    source: str = ""
    target_surface: str = ""
    data: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class FocusChangeEvent:
    event_id: str = ""
    timestamp_utc: str = ""
    previous_surface_id: str = ""
    current_surface_id: str = ""
    trigger: str = ""  # "user_action", "ai_action", "system_event"

@dataclass(slots=True)
class LifecycleEvent:
    event_id: str = ""
    timestamp_utc: str = ""
    surface_id: str = ""
    event_type: str = ""  # "launched", "opened", "closed", "focused", "minimized"
    success: bool = False

@dataclass(slots=True)
class TaskStateEvent:
    event_id: str = ""
    timestamp_utc: str = ""
    task_id: str = ""
    state_before: str = ""  # "pending", "running", "completed", "failed"
    state_after: str = ""
    reason: str = ""
```

### 3.5 Evidence Hash Calculation

```python
def calculate_evidence_hash(
    visual_signal: VisualSignal,
    process_signal: ProcessSignal,
    event_signal: EventSignal,
) -> str:
    """Calcula SHA256 de todas las señales fusionadas."""
    
    # Normalizar a JSON string determinista
    data = {
        "visual": {
            "screenshot_sha256": visual_signal.screenshot_sha256,
            "ocr_text": visual_signal.ocr_text[:200],  # Truncar para consistencia
            "accessibility_available": visual_signal.accessibility_available,
        },
        "process": {
            "pid": process_signal.pid,
            "window_handle": process_signal.window_handle,
            "window_title": process_signal.window_title[:100],
        },
        "event": {
            "focus_change": str(event_signal.focus_change_event),
            "lifecycle_count": len(event_signal.lifecycle_events),
        },
    }
    
    # Ordenar claves para consistencia
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    
    # SHA256
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
```

---

## 4. PRUEBAS DE CALIBRACIÓN

### 4.1 Test Suite Structure

```python
class MultimodalPerceptionCalibrationSuite:
    """Batería de pruebas para calibrar percepción multimodal."""
    
    def __init__(self, perception_service: MultimodalPerceptionService):
        self.perception = perception_service
        self.results: list[CalibrationTestResult] = []
    
    def run_all_tests(self) -> CalibrationReport:
        """Ejecuta todas las pruebas de calibración."""
        self.results = []
        
        # Test 1: Acción visible correcta
        self.results.append(self.test_action_visible_correct())
        
        # Test 2: Acción invisible pero persistida
        self.results.append(self.test_action_invisible_persisted())
        
        # Test 3: Foco perdido
        self.results.append(self.test_focus_lost())
        
        # Test 4: Freeze
        self.results.append(self.test_freeze_detection())
        
        # Test 5: Respuesta visible pero no persistida
        self.results.append(self.test_response_visible_not_persisted())
        
        # Test 6: Persistencia correcta pero UI no refleja
        self.results.append(self.test_persistence_correct_ui_not_reflecting())
        
        return self._generate_report()
```

### 4.2 Test 1: Acción Visible Correcta

**Objetivo**: Verificar que una acción visible (click, type) se captura correctamente en todas las señales.

**Escenario**:
1. Usuario hace clic en un botón visible
2. Sistema captura screenshot antes y después
3. Sistema captura evento de input
4. Sistema captura cambio de estado

**Expected Behavior**:
- Screenshot antes: botón visible
- Screenshot después: botón presionado o UI actualizada
- Event signal: input_event con type="mouse_click"
- Process signal: PID activo, ventana enfocada
- Evidence hash: diferente antes/después
- Truth confidence: > 0.9

**Failure Modes**:
- Screenshot no cambia → UI no respondió
- Event signal vacío → input no capturado
- Process signal inactivo → app congelada

### 4.3 Test 2: Acción Invisible pero Persistida

**Objetivo**: Verificar que acciones en segundo plano se registran aunque no sean visibles.

**Escenario**:
1. Sistema inicia tarea en segundo plano (ej: download, process)
2. Ventana no está enfocada o minimizada
3. Sistema debe registrar la acción con task_id

**Expected Behavior**:
- Screenshot: ventana minimizada o no visible
- Process signal: PID activo, CPU/memory cambiando
- Event signal: task_state_event con state_before="pending", state_after="running"
- Evidence record: task_id presente, source="system_event"
- Truth confidence: > 0.8 (basado en process signal)

**Failure Modes**:
- No hay evidence record → acción no persistida
- Process signal inactivo → tarea no iniciada
- Sin task_id → correlación imposible

### 4.4 Test 3: Foco Perdido

**Objetivo**: Detectar cuando el foco se pierde inesperadamente.

**Escenario**:
1. Ventana A tiene foco
2. Usuario cambia a ventana B
3. Sistema debe detectar cambio de foco

**Expected Behavior**:
- Focus change event: previous_surface_id=A, current_surface_id=B
- Process signal: ventana B enfocada
- Screenshot: ventana B visible
- Truth confidence: 1.0 (focus state es verdad absoluta)

**Failure Modes**:
- No hay focus change event → foco no capturado
- Process signal no actualiza → lag en detección
- Screenshot no cambia → captura falló

### 4.5 Test 4: Freeze Detection

**Objetivo**: Detectar cuando una app se congela.

**Escenario**:
1. App está activa
2. App deja de responder (CPU baja, UI no cambia)
3. Sistema debe detectar freeze

**Expected Behavior**:
- Screenshot: misma imagen por > 30 segundos
- Process signal: PID activo pero CPU baja (< 1%)
- Event signal: freeze_detection_event
- Evidence type: "freeze"
- Truth confidence: > 0.9

**Failure Modes**:
- No se detecta freeze → app sigue "viva" pero no responde
- Falso positivo → app lenta pero no congelada

### 4.6 Test 5: Respuesta Visible pero No Persistida

**Objetivo**: Detectar cuando UI muestra respuesta pero no se persiste.

**Escenario**:
1. Usuario envía mensaje
2. UI muestra respuesta
3. Logs no registran respuesta

**Expected Behavior**:
- Screenshot: respuesta visible
- OCR text: respuesta detectada
- Log files: sin evidencia de respuesta
- Inconsistency detected: True
- Truth confidence: 0.5 (conflicto entre fuentes)

**Failure Modes**:
- No se detecta inconsistencia → sistema asume que todo está bien
- Truth confidence alto → sistema confía en UI falsa

### 4.6 Test 6: Persistencia Correcta pero UI No Refleja

**Objetivo**: Detectar cuando datos persisten pero UI no los muestra.

**Escenario**:
1. Sistema guarda datos en DB
2. UI no muestra datos actualizados
3. Logs confirman persistencia

**Expected Behavior**:
- Log files: datos persistidos
- Screenshot: UI sin datos
- Process signal: PID activo
- Inconsistency detected: True
- Truth confidence: 0.7 (logs tienen prioridad sobre UI)

**Failure Modes**:
- No se detecta inconsistencia → usuario ve UI vieja
- Truth confidence bajo → sistema ignora logs válidos

---

## 5. GAPS DEL REPO ACTUAL

### 5.1 Gaps Críticos (High Priority)

**1. No hay captura de Accessibility Tree**
- **Estado**: No implementado
- **Impacto**: No se puede leer estructura de apps nativas
- **Solución**: Implementar UI Automation API (Windows UIA, macOS Accessibility, Linux AT-SPI)

**2. No hay captura de eventos de input/output**
- **Estado**: No implementado
- **Impacto**: No se puede rastrear acciones del usuario
- **Solución**: Implementar hooks de keyboard/mouse (pyautogui, pynput, OS-specific APIs)

**3. No hay fusión de señales**
- **Estado**: Cada sensor opera independientemente
- **Impacto**: No hay correlación entre fuentes
- **Solución**: Implementar SignalFusionCore con evidence hashing

**4. No hay TruthArbitrator**
- **Estado**: No hay lógica de prioridad de fuentes
- **Impacto**: Conflictos no resueltos
- **Solución**: Implementar TruthArbitrator con reglas de prioridad

**5. No hay registro de acciones en segundo plano**
- **Estado**: Solo se registran acciones visibles
- **Impacto**: Tareas background no trazables
- **Solución**: Implementar EvidenceRecorder con task_id tracking

### 5.2 Gaps Medios (Medium Priority)

**6. OCR no habilitado por defecto**
- **Estado**: OCR opcional, requiere IABV_ENABLE_VISUAL_OCR=1
- **Impacto**: No se puede leer texto cuando DOM no disponible
- **Solución**: Habilitar OCR en background con Tesseract o EasyOCR

**7. No hay pruebas de calibración**
- **Estado**: No hay test suite
- **Impacto**: No se puede validar percepción
- **Solución**: Implementar CalibrationTestSuite

**8. No hay detección de freezes**
- **Estado**: Detección básica en runtime_perception_and_verification_service
- **Impacto**: Freezes pueden pasar desapercibidos
- **Solución**: Mejorar detección con análisis de CPU + screenshot diff

**9. No hay correlación de evidencia**
- **Estado**: No hay índice de evidence hashes
- **Impacto**: Difícil encontrar evidencia relacionada
- **Solución**: Implementar índice de evidence hashes en EvidenceRecorder

### 5.3 Gaps Bajos (Low Priority)

**10. No hay captura de audio**
- **Estado**: No implementado
- **Impacto**: No se puede capturar comandos de voz
- **Solución**: Implementar captura de audio si es necesario

**11. No hay captura de red**
- **Estado**: No implementado
- **Impacto**: No se puede rastrear requests HTTP
- **Solución**: Implementar packet capture si es necesario

**12. No hay captura de filesystem**
- **Estado**: No implementado
- **Impacto**: No se puede rastrear cambios en archivos
- **Solución**: Implementar filesystem watcher si es necesario

---

## 6. PASOS MÍNIMOS PARA INTEGRACIÓN

### 6.1 Fase 1: Implementación Core (1-2 semanas)

**Paso 1.1: Crear MultimodalPerceptionService**
- Archivo: `src/iabv_v15/services/perception/multimodal_perception_service.py`
- Funcionalidad:
  - Orquestar captura de múltiples sensores
  - Coordinar timestamps sincronizados
  - Generar evidence hashes
- Dependencias: Ninguna (nuevo servicio)

**Paso 1.2: Implementar SignalFusionCore**
- Archivo: `src/iabv_v15/services/perception/signal_fusion_core.py`
- Funcionalidad:
  - Fusionar visual, process, event signals
  - Calcular evidence hashes
  - Detectar inconsistencias
- Dependencias: MultimodalPerceptionService

**Paso 1.3: Implementar TruthArbitrator**
- Archivo: `src/iabv_v15/services/perception/truth_arbitrator.py`
- Funcionalidad:
  - Aplicar reglas de prioridad de fuentes
  - Resolver conflictos
  - Emitir veredicto con confidence
- Dependencias: SignalFusionCore

**Paso 1.4: Implementar EvidenceRecorder**
- Archivo: `src/iabv_v15/services/perception/evidence_recorder.py`
- Funcionalidad:
  - Registrar evidence records con task_id
  - Persistir en JSONL
  - Indexar por evidence hash
- Dependencias: TruthArbitrator

### 6.2 Fase 2: Sensores Adicionales (1 semana)

**Paso 2.1: Implementar Accessibility Tree Capture**
- Archivo: `src/iabv_v15/infra/ui/accessibility_tree_provider.py`
- Funcionalidad:
  - Windows: UI Automation API
  - macOS: Accessibility API
  - Linux: AT-SPI
- Dependencias: Ninguna (nuevo proveedor)

**Paso 2.2: Implementar Event Capture**
- Archivo: `src/iabv_v15/infra/ui/event_capture_provider.py`
- Funcionalidad:
  - Keyboard hooks (pynput)
  - Mouse hooks (pynput)
  - Focus change events
- Dependencias: pynput

**Paso 2.3: Habilitar OCR por defecto**
- Archivo: Modificar `universal_perception_service.py`
- Funcionalidad:
  - Integrar Tesseract o EasyOCR
  - Ejecutar en background
- Dependencias: pytesseract o easyocr

### 6.3 Fase 3: Pruebas de Calibración (1 semana)

**Paso 3.1: Implementar CalibrationTestSuite**
- Archivo: `src/iabv_v15/services/perception/calibration_test_suite.py`
- Funcionalidad:
  - Test 1: Acción visible correcta
  - Test 2: Acción invisible pero persistida
  - Test 3: Foco perdido
  - Test 4: Freeze detection
  - Test 5: Respuesta visible pero no persistida
  - Test 6: Persistencia correcta pero UI no refleja
- Dependencias: MultimodalPerceptionService

**Paso 3.2: Integrar en bootstrap**
- Archivo: Modificar `bootstrap.py`
- Funcionalidad:
  - Iniciar MultimodalPerceptionService
  - Ejecutar calibration tests al startup
  - Registrar resultados en logs
- Dependencias: Todos los componentes anteriores

### 6.4 Fase 4: Integración con Servicios Existentes (1 semana)

**Paso 4.1: Integrar con RuntimePerceptionAndVerificationService**
- Archivo: Modificar `runtime_perception_and_verification_service.py`
- Funcionalidad:
  - Usar MultimodalPerceptionService como fuente de verdad
  - Reemplazar captura individual con fusión de señales
- Dependencias: MultimodalPerceptionService

**Paso 4.2: Integrar con UniversalPerceptionService**
- Archivo: Modificar `universal_perception_service.py`
- Funcionalidad:
  - Usar EvidenceRecorder para persistir evidencia
  - Usar TruthArbitrator para resolver conflictos
- Dependencias: EvidenceRecorder, TruthArbitrator

**Paso 4.3: Integrar con PerceptionCrossValidator**
- Archivo: Modificar `perception_cross_validator.py`
- Funcionalidad:
  - Usar evidence hashes para correlación
  - Usar truth confidence para prioridad
- Dependencias: SignalFusionCore

### 6.5 Fase 5: Documentación y Testing (1 semana)

**Paso 5.1: Documentar API**
- Crear docstrings completos
- Crear ejemplos de uso
- Crear diagramas de arquitectura

**Paso 5.2: Escribir tests unitarios**
- Tests para MultimodalPerceptionService
- Tests para SignalFusionCore
- Tests para TruthArbitrator
- Tests para EvidenceRecorder

**Paso 5.3: Escribir tests de integración**
- Tests de end-to-end
- Tests de calibración
- Tests de performance

### 6.6 Resumen de Tiempos

| Fase | Duración | Entregables |
|------|----------|-------------|
| Fase 1: Core | 1-2 semanas | MultimodalPerceptionService, SignalFusionCore, TruthArbitrator, EvidenceRecorder |
| Fase 2: Sensores | 1 semana | Accessibility Tree, Event Capture, OCR |
| Fase 3: Pruebas | 1 semana | CalibrationTestSuite, integración bootstrap |
| Fase 4: Integración | 1 semana | Integración con servicios existentes |
| Fase 5: Docs/Tests | 1 semana | Documentación, tests unitarios, tests de integración |
| **Total** | **5-6 semanas** | **Sistema completo de percepción multimodal** |

---

## 7. EJEMPLO DE USO

### 7.1 Captura de Acción Visible

```python
from iabv_v15.services.perception.multimodal_perception_service import (
    MultimodalPerceptionService,
)

# Iniciar servicio
perception = MultimodalPerceptionService(
    data_root="C:/Python/IABV_v1.5/data",
)
perception.start()

# Capturar acción
evidence = perception.capture_action(
    task_id="task_123",
    action_type="click",
    target_surface="hwnd_12345",
    source="ai_action",
)

# Verificar resultado
print(f"Truth confidence: {evidence.truth_confidence}")
print(f"Evidence hash: {evidence.evidence_hash}")
print(f"Inconsistency detected: {evidence.inconsistency_detected}")
```

### 7.2 Consulta de Evidencia por Task ID

```python
# Consultar evidencia de una tarea
evidence_records = perception.get_evidence_by_task_id("task_123")

for record in evidence_records:
    print(f"Timestamp: {record.timestamp_utc}")
    print(f"State before: {record.state_before}")
    print(f"State after: {record.state_after}")
    print(f"Truth confidence: {record.truth_confidence}")
```

### 7.3 Ejecutar Pruebas de Calibración

```python
from iabv_v15.services.perception.calibration_test_suite import (
    MultimodalPerceptionCalibrationSuite,
)

# Crear suite
suite = MultimodalPerceptionCalibrationSuite(perception)

# Ejecutar tests
report = suite.run_all_tests()

# Ver resultados
print(f"Tests passed: {report.tests_passed}")
print(f"Tests failed: {report.tests_failed}")
print(f"Overall confidence: {report.overall_confidence}")
```

---

## 8. CONCLUSIONES

### 8.1 Estado Actual

El repo IABV v1.5 tiene una base sólida de percepción con:
- `RuntimePerceptionAndVerificationService`: Percepción runtime universal
- `UniversalPerceptionService`: Percepción visual con OCR opcional
- `PerceptionCrossValidator`: Validación cruzada de percepción
- `UIScreenshotService`: Captura y persistencia de screenshots

Sin embargo, faltan componentes críticos para una percepción multimodal completa:
- Fusión de señales
- Arbitraje de verdad
- Registro de acciones en segundo plano
- Captura de accessibility tree
- Captura de eventos de input/output
- Pruebas de calibración

### 8.2 Recomendaciones

1. **Priorizar Fase 1 (Core)**: Implementar MultimodalPerceptionService, SignalFusionCore, TruthArbitrator, EvidenceRecorder
2. **Implementar pruebas de calibración**: Validar percepción antes de integración completa
3. **Habilitar OCR por defecto**: Mejorar capacidad de lectura de texto
4. **Integrar gradualmente**: No reemplazar servicios existentes de golpe, integrar incrementalmente
5. **Documentar extensivamente**: Asegurar que la arquitectura sea comprensible y mantenible

### 8.3 Impacto Esperado

Con la implementación completa de la capa de percepción runtime multimodal:
- **Verdad del sistema**: Fusión de múltiples señales con arbitraje de prioridad
- **Trazabilidad completa**: Acciones en segundo plano registradas con task_id
- **Detección de inconsistencias**: Conflictos entre fuentes detectados y resueltos
- **Calibración validada**: Pruebas automatizadas aseguran calidad de percepción
- **Robustez**: Sistema puede degradar gracefully si un sensor falla

### 8.4 Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Performance impact | Captura asíncrona, cache de sensores |
| Sensor failure | Degrada gracefully, usa fuentes disponibles |
| False positives | TruthArbitrator con confidence scores |
| Complexity | Arquitectura modular, documentación extensiva |
| Integration issues | Integración incremental, tests de regresión |

---

## 9. REFERENCIAS

### 9.1 Archivos Existentes Analizados

- `src/iabv_v15/services/perception/runtime_perception_and_verification_service.py`
- `src/iabv_v15/services/capture/universal_perception_service.py`
- `src/iabv_v15/services/evolution/perception_cross_validator.py`
- `src/iabv_v15/services/capture/ui_screenshot_service.py`
- `src/iabv_v15/infra/persistence/screenshot_store.py`
- `src/iabv_v15/infra/ui/mss_screenshot_provider.py`
- `src/iabv_v15/infra/ui/qt_screenshot_provider.py`

### 9.2 Patrones de Diseño

- **Observer Pattern**: Para captura de eventos
- **Strategy Pattern**: Para adaptadores de plataforma
- **Composite Pattern**: Para fusión de señales
- **Repository Pattern**: Para persistencia de evidencia

### 9.3 Tecnologías Recomendadas

- **OCR**: Tesseract (pytesseract) o EasyOCR
- **Accessibility**: Windows UIA, macOS Accessibility, Linux AT-SPI
- **Event Capture**: pynput
- **Hashing**: hashlib (SHA256)
- **Persistencia**: JSONL con índice de hashes

---

**Fin del documento**
