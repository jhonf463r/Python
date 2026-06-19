# CONGELAMIENTO DE ARQUITECTURA IABV v1.5

**Fecha:** 2026-06-17  
**Objetivo:** Dejar IABV v1.5 listo para recibir hallazgos de investigación profunda sin rehacer arquitectura.

---

## FASE 0 — CONGELAR EL ESTADO ACTUAL

### Módulos congelados (no se rehacen, solo se auditan o ajustan mínimamente)

#### 1. TruthArbitrator
**Archivo:** `src/iabv_v15/services/perception/truth_arbitrator.py`

**Estado:** Congelado con correcciones de sesgo aplicadas (FASE 1 de corrección anterior).

**Por qué está congelado:**
- Es el núcleo de arbitraje de verdad multimodal
- Ya tiene gating implementado para degradar confidence cuando screenshot está vacío
- Ya tiene detección de contradicciones entre Accessibility Tree y Process Signal
- Ya tiene detección de input ausente pero output presente
- Ya tiene explicación mejorada con gating aplicado

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación determinista

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en la jerarquía de verdad (OPERATIONAL > VISUAL > PERSISTENT)
- Eliminación de gating existente

---

#### 2. SignalFusionCore
**Archivo:** `src/iabv_v15/services/perception/signal_fusion_core.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Es responsable de detectar inconsistencias entre señales
- Ya tiene lógica de indexación de evidencia
- Ya tiene detección de conflictos visuales vs operativos

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en la lógica de detección de inconsistencias

---

#### 3. EvidenceRecorder
**Archivo:** `src/iabv_v15/services/perception/evidence_recorder.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Es responsable de persistir evidencia en JSONL
- Ya tiene lógica de serialización de EvidenceRecord
- Ya mantiene índice de evidencia

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación

**Qué NO se permite:**
- Cambios en formato de persistencia (JSONL)
- Eliminación de campos existentes

---

#### 4. CapabilityDetector
**Archivo:** `src/iabv_v15/services/perception/capability_detector.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Es responsable de detectar capacidades del sistema
- Ya tiene lógica de detección de screenshot, OCR, accessibility
- Ya selecciona adaptadores apropiados

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en la lógica de selección de adaptadores

---

#### 5. SurfaceClassifier
**Archivo:** `src/iabv_v15/services/perception/surface_classifier.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Es responsable de clasificar superficies (ventanas, áreas de pantalla)
- Ya tiene lógica de clasificación basada en geometría

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en la lógica de clasificación

---

#### 6. AdapterSelector
**Archivo:** `src/iabv_v15/services/perception/adapter_selector.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Es responsable de seleccionar adaptadores según capacidades
- Ya tiene lógica de selección basada en CapabilityDetector

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en la lógica de selección

---

#### 7. MultimodalPerceptionService
**Archivo:** `src/iabv_v15/services/perception/multimodal_perception_service.py`

**Estado:** Congelado con correcciones de refresco de snapshot aplicadas (FASE 2 de corrección anterior).

**Por qué está congelado:**
- Es el orquestador central de percepción multimodal
- Ya tiene refresh de WorldModelService antes de capturar ventana/foco
- Ya tiene distinción entre input/output real e inferido
- Ya tiene alertas de degradación mejoradas

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige
- Pruebas de verificación

**Qué NO se permite:**
- Refactor arquitectónico
- Eliminación de servicios externos (UIScreenshotService, WorldModelService)

---

### Inventario de servicios externos (no se rehacen)

#### UIScreenshotService
**Archivo:** `src/iabv_v15/services/capture/ui_screenshot_service.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Servicio de captura de screenshots con persistencia
- Ya tiene providers (PIL, Qt, Noop)
- Ya tiene índice de screenshots

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en formato de persistencia

---

#### WorldModelService
**Archivo:** `src/iabv_v15/services/evolution/world_model_service.py`

**Estado:** Congelado.

**Por qué está congelado:**
- Servicio de modelo del mundo con snapshot de ventanas
- Ya tiene lógica de scan y snapshot
- Ya mantiene estado de ventana activa

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige

**Qué NO se permite:**
- Refactor arquitectónico
- Cambios en formato de snapshot

---

### Modelos de datos (no se rehacen)

#### MultimodalDataModels
**Archivo:** `src/iabv_v15/services/perception/multimodal_data_models.py`

**Estado:** Congelado con campos agregados para distinción real vs inferido (FASE 3 de corrección anterior).

**Por qué está congelado:**
- Define los modelos de datos de señales multimodales
- Ya tiene campos para input_events_real_count, output_events_real_count, etc.
- Ya tiene campos para has_real_user_interaction

**Qué se permite:**
- Auditoría de comportamiento
- Ajustes mínimos si investigación profunda lo exige

**Qué NO se permite:**
- Eliminación de campos existentes
- Cambios en estructura de dataclasses

---

## Resumen de congelamiento

**Total de módulos congelados:** 7 módulos principales + 2 servicios externos + 1 modelo de datos

**Criterio de congelamiento:**
- No se rehace arquitectura
- No se crean nuevas capas innecesarias
- Solo se audita o ajusta mínimamente si investigación profunda lo exige
- Se preservan las correcciones de sesgo aplicadas en la fase anterior

**Estado actual del sistema:**
- TruthArbitrator tiene gating implementado pero no completamente verificado
- MultimodalPerceptionService tiene refresh de snapshot implementado
- EventSignal tiene distinción real vs inferido implementada
- Alertas de degradación están mejoradas
- Pruebas de auditoría se ejecutaron pero no cubrieron todos los escenarios

**Qué falta para verificación completa:**
- Prueba determinista forzada para screenshot vacío
- Verificación de gating en producción
- Verificación de alertas que no se activaron en pruebas

---

**Fin de FASE 0 - Estado actual congelado**
