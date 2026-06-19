# MATRIZ DE MAPEO HALLAZGO → MÓDULO

**Fecha de creación:** 2026-06-17  
**Objetivo:** Puente entre hallazgos de investigación profunda y módulos de código.

---

## Instrucciones de uso

1. Para cada hallazgo registrado en `hallazgos/`, agregar una fila a esta matriz
2. Marcar con "X" las columnas que apliquen
3. Especificar severidad y módulos afectados
4. Esto permitirá identificar rápidamente qué módulos necesitan ajustes

---

## Matriz de mapeo

| ID Hallazgo | Título | Severidad | Módulos afectados | Verdad Visual | Verdad Operativa | Verdad Persistente | Foco/Ventana/HWND | Input/Output | Ownership | Degradación | Estado |
|-------------|--------|-----------|-------------------|---------------|------------------|-------------------|------------------|-------------|-----------|-------------|--------|
| 001 | [Ejemplo: Screenshot vacío con confidence 1.0] | [critical/high/medium/low] | TruthArbitrator, MultimodalPerceptionService | X | X | | X | | | X | [pending/in_progress/resolved/deferred] |
| 002 | [Ejemplo: Accessibility Tree contradice Process Signal] | [critical/high/medium/low] | TruthArbitrator, SignalFusionCore | X | X | | X | | | X | [pending/in_progress/resolved/deferred] |
| 003 | [Ejemplo: Input events ausentes pero output presente] | [critical/high/medium/low] | MultimodalPerceptionService, EvidenceRecorder | | X | | | X | X | X | [pending/in_progress/resolved/deferred] |
| 004 | [Ejemplo: Focus/HWND desfasados] | [critical/high/medium/low] | MultimodalPerceptionService, WorldModelService | | X | | X | | | X | [pending/in_progress/resolved/deferred] |
| 005 | [Ejemplo: Ownership confidence baja] | [critical/high/medium/low] | MultimodalPerceptionService | | X | | | | X | X | [pending/in_progress/resolved/deferred] |
| 006 | [Ejemplo: Truth confidence alta sin evidencia visual] | [critical/high/medium/low] | TruthArbitrator | X | X | | | | | X | [pending/in_progress/resolved/deferred] |
| 007 | [Ejemplo: Alertas de degradación no activadas] | [critical/high/medium/low] | MultimodalPerceptionService | X | X | X | X | X | X | X | [pending/in_progress/resolved/deferred] |
| | | | | | | | | | | | |

---

## Catálogo de módulos afectables

### Módulos principales de percepción

- **TruthArbitrator:** `src/iabv_v15/services/perception/truth_arbitrator.py`
  - Responsable: Arbitraje de verdad multimodal
  - Tipos de verdad: Visual, Operativa, Persistente
  
- **SignalFusionCore:** `src/iabv_v15/services/perception/signal_fusion_core.py`
  - Responsable: Fusión de señales y detección de inconsistencias
  - Tipos de verdad: Visual, Operativa, Persistente
  
- **EvidenceRecorder:** `src/iabv_v15/services/perception/evidence_recorder.py`
  - Responsable: Persistencia de evidencia en JSONL
  - Tipos de verdad: Visual, Operativa, Persistente
  
- **MultimodalPerceptionService:** `src/iabv_v15/services/perception/multimodal_perception_service.py`
  - Responsable: Orquestación de percepción multimodal
  - Componentes: Foco/Ventana/HWND, Input/Output, Ownership, Degradación
  
- **CapabilityDetector:** `src/iabv_v15/services/perception/capability_detector.py`
  - Responsable: Detección de capacidades del sistema
  - Componentes: Screenshot, OCR, Accessibility
  
- **SurfaceClassifier:** `src/iabv_v15/services/perception/surface_classifier.py`
  - Responsable: Clasificación de superficies
  - Componentes: Ventanas, áreas de pantalla
  
- **AdapterSelector:** `src/iabv_v15/services/perception/adapter_selector.py`
  - Responsable: Selección de adaptadores
  - Componentes: Adaptadores según capacidades

### Servicios externos

- **UIScreenshotService:** `src/iabv_v15/services/capture/ui_screenshot_service.py`
  - Responsable: Captura de screenshots
  - Componentes: Screenshot, SHA256, dimensiones
  
- **WorldModelService:** `src/iabv_v15/services/evolution/world_model_service.py`
  - Responsable: Modelo del mundo con snapshot de ventanas
  - Componentes: Foco/Ventana/HWND, snapshot

### Modelos de datos

- **MultimodalDataModels:** `src/iabv_v15/services/perception/multimodal_data_models.py`
  - Responsable: Modelos de datos de señales multimodales
  - Componentes: VisualSignal, ProcessSignal, EventSignal, EvidenceRecord

---

## Criterios de severidad

- **Critical:** El hallazgo causa interpretación incorrecta de la realidad con alto impacto en decisiones
- **High:** El hallazgo causa degradación significativa de la percepción pero no bloquea completamente
- **Medium:** El hallazgo causa degradación moderada con impacto limitado
- **Low:** El hallazgo causa degradación menor con impacto mínimo

---

## Criterios de estado

- **Pending:** Hallazgo registrado pero no revisado
- **In Progress:** Hallazgo siendo analizado y corregido
- **Resolved:** Hallazgo corregido y verificado
- **Deferred:** Hallazgo pospuesto para revisión futura

---

## Flujo de trabajo de mapeo

1. **Registrar hallazgo** en `hallazgos/XXX_descripcion.md`
2. **Agregar fila** a esta matriz con información básica
3. **Marcar columnas** que apliquen (X)
4. **Especificar módulos** afectados
5. **Definir severidad** según impacto
6. **Actualizar estado** según progreso

---

## Ejemplo de uso

Supongamos que la investigación profunda descubre que el TruthArbitrator no degrada confidence cuando screenshot está vacío:

| ID Hallazgo | Título | Severidad | Módulos afectados | Verdad Visual | Verdad Operativa | Verdad Persistente | Foco/Ventana/HWND | Input/Output | Ownership | Degradación | Estado |
|-------------|--------|-----------|-------------------|---------------|------------------|-------------------|------------------|-------------|-----------|-------------|--------|
| 001 | Screenshot vacío con confidence 1.0 | critical | TruthArbitrator, MultimodalPerceptionService | X | X | | | | | X | pending |

Este mapeo indica que:
- El hallazgo afecta a TruthArbitrator y MultimodalPerceptionService
- Toca verdad visual y operativa
- Toca degradación
- Severidad es critical
- Estado es pending (pendiente de revisión)

---

**Fin de matriz de mapeo**
