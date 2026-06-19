# FASE 0 - RESUMEN DEL ESTADO ACTUAL

**Fecha:** 2026-06-17  
**Objetivo:** Resumir qué quedó congelado, qué está listo, qué sigue parcial, y por qué la siguiente fase debe ser auditoría viva y no refactor base.

---

## 1. Qué quedó congelado

**Módulos principales congelados (7):**
- **TruthArbitrator:** Congelado con correcciones de sesgo aplicadas (gating para screenshot vacío, detección de contradicciones Accessibility Tree vs Process Signal, detección de input ausente pero output presente)
- **SignalFusionCore:** Congelado (detección de inconsistencias entre señales visuales y operativas)
- **EvidenceRecorder:** Congelado (persistencia de evidencia en JSONL con índice)
- **CapabilityDetector:** Congelado (detección de capacidades del sistema: screenshot, OCR, accessibility)
- **SurfaceClassifier:** Congelado (clasificación de superficies basada en geometría)
- **AdapterSelector:** Congelado (selección de adaptadores según capacidades)
- **MultimodalPerceptionService:** Congelado con correcciones de refresco de snapshot aplicadas (refresh de WorldModelService antes de capturar ventana/foco, distinción input/output real vs inferido, alertas de degradación mejoradas)

**Servicios externos congelados (2):**
- **UIScreenshotService:** Congelado (captura de screenshots con persistencia en PNG, índice JSONL, providers PIL/Qt/Noop)
- **WorldModelService:** Congelado (modelo del mundo con snapshot de ventanas, método scan para refrescar estado)

**Modelos de datos congelados (1):**
- **MultimodalDataModels:** Congelado con campos agregados para distinción real vs inferido (input_events_real_count, output_events_real_count, has_real_user_interaction, clipboard_events_count, focus_events_count)

**Criterio de congelamiento:**
- No se rehace arquitectura
- No se crean nuevas capas innecesarias
- Solo se audita o ajusta mínimamente si investigación profunda lo exige
- Se preservan las correcciones de sesgo aplicadas en la fase anterior

---

## 2. Qué está listo

**Zona de entrada de hallazgos:**
- `data/investigation_deep_findings/README.md` - Instrucciones de uso de la zona de entrada
- `data/investigation_deep_findings/template_hallazgo.md` - Template para registrar hallazgos
- `data/investigation_deep_findings/matriz_mapeo_hallazgos_modulos.md` - Matriz de mapeo hallazgo → módulo
- `data/investigation_deep_findings/pruebas_reconciliacion/README.md` - Pruebas de reconciliación con 8 escenarios definidos

**Pruebas de verificación:**
- `test_interpretation_audit.py` - Pruebas de auditoría de interpretación con 4 escenarios (screenshot vacío, accessibility mismatch, input ausente output presente, visual baja operational alta)
- `test_forced_empty_screenshot.py` - Prueba determinista forzada para verificar gating del TruthArbitrator cuando screenshot está vacío

**Documentación de correcciones previas:**
- `CORRECCION_SESGO_TRUTH_ARBITRATOR_FINAL.md` - Reporte de correcciones de sesgo aplicadas
- `CONGELAMIENTO_ARQUITECTURA_V1.5.md` - Documentación de módulos congelados
- `PREPARACION_RECEPCION_INVESTIGACION_PROFUNDA_FINAL.md` - Reporte de estado listo para recepción
- `REPORTE_ESTADO_LISTO_RECEPCION.md` - Reporte de estado listo para recepción

**Evidencia persistente:**
- `data/multimodal_evidence/audit_interpretation_report.json` - Reporte de auditoría con resultados de 4 escenarios probados
- `data/multimodal_evidence/evolution/multimodal_evidence/evidence_records.jsonl` - 29 registros de evidencia con truth_source, truth_confidence, truth_type, visual_truth_confidence, operational_truth_confidence, persistent_truth_confidence, truth_explanation, truth_conflicts, etc.
- `data/multimodal_evidence/evolution/multimodal_evidence/evidence_index.jsonl` - Índice de evidencia

**Capacidades del sistema:**
- Captura de screenshots (UIScreenshotService con providers PIL/Qt/Noop)
- Captura de Accessibility Tree (parcial, método foreground)
- Captura de proceso activo (PID, HWND, window_title, process_name)
- Captura de eventos de foco (FocusChangeEvent con trigger world_model_snapshot)
- Distinción entre input/output real e inferido (input_events_real_count, output_events_real_count)
- Gating de TruthArbitrator para degradar confidence cuando screenshot está vacío
- Detección de contradicciones entre Accessibility Tree y Process Signal
- Alertas de degradación (screenshot_completely_empty, visual_confidence_very_low, operational_dominates_without_visual, real_input_events_missing, focus_mismatch_accessibility_process)

---

## 3. Qué sigue parcial

**Verificación de gating:**
- TruthArbitrator tiene gating implementado pero no completamente verificado
- La prueba determinista forzada (`test_forced_empty_screenshot.py`) está creada pero no ejecutada
- No se pudo verificar el gating en pruebas anteriores porque UIScreenshotService capturó screenshots reales (no vacíos)

**Verificación de alertas:**
- Algunas alertas de degradación no se activaron en pruebas (operational_dominates_without_visual, focus_mismatch_accessibility_process)
- Estas alertas están implementadas pero requieren escenarios específicos para activarse

**Captura de input real:**
- input_events_real_count es 0 en todos los registros de evidencia
- No hay servicio de captura de input real (por ejemplo, usando pynput para teclado/mouse)
- Solo se captura clipboard como output real

**Captura de Accessibility Tree:**
- Accessibility Tree se captura pero es parcial (método foreground)
- No hay captura completa del árbol de accesibilidad
- dom_text está limitado a foreground y control

**Overlay/HUD de auditoría:**
- No existe overlay/HUD de auditoría en vivo
- No hay capa visual para que un humano vea qué detecta el sistema en tiempo real
- No hay resaltado de elementos detectados
- No hay visualización de decisiones del árbitro en tiempo real

**Panel persistente en segundo plano:**
- EvidenceRecorder persiste evidencia en JSONL, pero no hay bitácora persistente específica para auditoría humana
- No hay registro estructurado de eventos de foco, clicks, teclas, cambios de ventana, etc.
- No hay registro de contradicciones detectadas en tiempo real

**Memoria de aprendizaje/calibración:**
- No existe memoria de aprendizaje
- No hay acumulación de casos confirmados, corregidos, falsos positivos, falsos negativos
- No hay detección de patrones estables por superficie/dispositivo
- No hay ajuste de reglas o pesos basado en aprendizaje

**Validación científica:**
- No hay métricas científicas de precisión, recall, tasa de falsos positivos, tasa de falsos negativos
- No hay calibración de confianza
- No hay medición de tasa de contradicciones visual vs operativa
- No hay medición de exactitud de truth_source
- No hay medición de cobertura de eventos persistentes
- No hay medición de utilidad del overlay para auditor humano
- No hay medición de mejora de la interpretación con el tiempo

---

## 4. Cuál es el hueco operativo más importante

**Hueco operativo más importante:**

**Falta de visibilidad en tiempo real para auditoría humana.**

El sistema IABV v1.5 actualmente:
- Captura señales multimodales (screenshot, Accessibility Tree, proceso, eventos)
- Arbitra entre fuentes de verdad con gating y detección de contradicciones
- Persiste evidencia en JSONL
- Genera alertas de degradación

Pero:
- **No hay overlay/HUD de auditoría en vivo** para que un humano vea qué detecta el sistema en tiempo real
- **No hay resaltado de elementos detectados** (ventana activa, proceso activo, foco, elementos de Accessibility Tree)
- **No hay visualización de decisiones del árbitro** en tiempo real (truth_source, truth_confidence, truth_type, truth_explanation)
- **No hay visualización de contradicciones detectadas** en tiempo real
- **No hay visualización de alertas de degradación** en tiempo real

**Por qué es el hueco más importante:**

1. **La investigación profunda concluyó que las señales más valiosas son las estructuradas (árbol de accesibilidad, ventana/proceso), pero el sistema no las muestra en tiempo real.**

2. **El sistema debe mostrar sus detecciones en vivo para un humano, pero actualmente no hay capa visual para auditoría.**

3. **Screenshot/OCR aportan contexto pero pueden introducir ruido, y el sistema no permite que un humano vea qué ruido está introduciendo.**

4. **El sistema debe dejar un registro persistente en segundo plano con eventos estructurados JSONL, pero actualmente solo persiste EvidenceRecord completo, no eventos estructurados específicos de auditoría.**

5. **Sin visibilidad en tiempo real, es imposible auditar si el sistema está interpretando correctamente la realidad.**

---

## 5. Por qué la siguiente fase debe ser auditoría viva y no refactor base

**Por qué auditoría viva y no refactor base:**

1. **La arquitectura base ya está congelada y lista:**
   - TruthArbitrator tiene gating implementado
   - MultimodalPerceptionService tiene refresh de snapshot implementado
   - EventSignal tiene distinción real vs inferido implementada
   - Alertas de degradación están mejoradas
   - No hay necesidad de refactor arquitectónico base

2. **El hueco operativo es de visibilidad, no de arquitectura:**
   - El sistema captura señales correctamente
   - El sistema arbitra correctamente
   - El sistema persiste correctamente
   - Lo que falta es visibilidad en tiempo real para auditoría humana

3. **La investigación profunda concluyó que se necesita auditoría viva:**
   - Las señales más valiosas son las estructuradas (árbol de accesibilidad, ventana/proceso)
   - El sistema debe mostrar sus detecciones en vivo para un humano
   - El sistema debe dejar un registro persistente en segundo plano con eventos estructurados JSONL

4. **Refactor base sería innecesario y contraproducente:**
   - Refactor arquitectónico rompería el congelamiento
   - Refactor arquitectónico no resolvería el hueco de visibilidad
   - Refactor arquitectónico introduciría riesgo sin beneficio

5. **Auditoría viva es la siguiente fase lógica:**
   - Construir overlay/HUD de depuración en vivo
   - Construir panel persistente en segundo plano
   - Construir memoria de aprendizaje/calibración
   - Construir validación científica
   - Construir pruebas de auditoría humana

**Conclusión:**

La siguiente fase debe ser **auditoría viva** porque:
- La arquitectura base ya está congelada y lista
- El hueco operativo es de visibilidad, no de arquitectura
- La investigación profunda concluyó que se necesita auditoría viva
- Refactor base sería innecesario y contraproducente
- Auditoría viva es la siguiente fase lógica

---

**Fin de FASE 0 - Resumen del estado actual**
