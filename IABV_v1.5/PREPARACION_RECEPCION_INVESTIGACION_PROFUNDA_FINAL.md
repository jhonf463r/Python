# PREPARACIÓN PARA RECEPCIÓN DE INVESTIGACIÓN PROFUNDA - SALIDA OBLIGATORIA

**Fecha:** 2026-06-17  
**Objetivo:** Dejar IABV v1.5 listo para recibir hallazgos de investigación profunda sin rehacer arquitectura.

---

## 1. Qué queda congelado

**Módulos principales congelados (no se rehacen, solo se auditan o ajustan mínimamente):**

- **TruthArbitrator:** Congelado con correcciones de sesgo aplicadas (gating para screenshot vacío, detección de contradicciones Accessibility Tree vs Process Signal, detección de input ausente pero output presente)
- **SignalFusionCore:** Congelado (detección de inconsistencias entre señales visuales y operativas)
- **EvidenceRecorder:** Congelado (persistencia de evidencia en JSONL con índice)
- **CapabilityDetector:** Congelado (detección de capacidades del sistema: screenshot, OCR, accessibility)
- **SurfaceClassifier:** Congelado (clasificación de superficies basada en geometría)
- **AdapterSelector:** Congelado (selección de adaptadores según capacidades)
- **MultimodalPerceptionService:** Congelado con correcciones de refresco de snapshot aplicadas (refresh de WorldModelService antes de capturar ventana/foco, distinción input/output real vs inferido, alertas de degradación mejoradas)

**Servicios externos congelados:**

- **UIScreenshotService:** Congelado (captura de screenshots con persistencia en PNG, índice JSONL, providers PIL/Qt/Noop)
- **WorldModelService:** Congelado (modelo del mundo con snapshot de ventanas, método scan para refrescar estado)

**Modelos de datos congelados:**

- **MultimodalDataModels:** Congelado con campos agregados para distinción real vs inferido (input_events_real_count, output_events_real_count, has_real_user_interaction, clipboard_events_count, focus_events_count)

**Documentación de congelamiento:**

- `CONGELAMIENTO_ARQUITECTURA_V1.5.md` - Documentación completa de módulos congelados, criterios de congelamiento, y qué se permite vs qué no se permite

---

## 2. Qué queda listo para auditar

**Zona de entrada de hallazgos:**

- `data/investigation_deep_findings/README.md` - Instrucciones de uso de la zona de entrada
- `data/investigation_deep_findings/template_hallazgo.md` - Template para registrar hallazgos con campos: resumen ejecutivo, hallazgo crítico, riesgos, sesgos potenciales, métricas recomendadas, módulos afectados, cambios mínimos sugeridos, pruebas a ejecutar
- `data/investigation_deep_findings/matriz_mapeo_hallazgos_modulos.md` - Matriz de mapeo hallazgo → módulo con columnas: módulos afectados, severidad, tipos de verdad (visual/operativa/persistente), componentes (foco/ventana/HWND, input/output, ownership, degradación), estado
- `data/investigation_deep_findings/pruebas_reconciliacion/README.md` - Pruebas de reconciliación con 8 escenarios definidos

**Pruebas de verificación:**

- `test_interpretation_audit.py` - Pruebas de auditoría de interpretación con 4 escenarios (screenshot vacío, accessibility mismatch, input ausente output presente, visual baja operational alta)
- `test_forced_empty_screenshot.py` - Prueba determinista forzada para verificar gating del TruthArbitrator cuando screenshot está vacío (fuerza manualmente screenshot_path="", width=0, height=0, sha256="")

**Documentación de correcciones previas:**

- `CORRECCION_SESGO_TRUTH_ARBITRATOR_FINAL.md` - Reporte de correcciones de sesgo aplicadas en la fase anterior
- `REPORTE_ESTADO_LISTO_RECEPCION.md` - Reporte de estado listo para recepción

**Evidencia persistente:**

- `data/multimodal_evidence/audit_interpretation_report.json` - Reporte de auditoría con resultados de 4 escenarios probados
- `data/multimodal_evidence/evolution/multimodal_evidence/evidence_records.jsonl` - Registros de evidencia generados durante pruebas

---

## 3. Qué hallazgos futuros podrán mapearse

**Matriz de mapeo preparada:**

La matriz `matriz_mapeo_hallazgos_modulos.md` permite mapear cada hallazgo futuro a:

- **Módulos afectados:** TruthArbitrator, SignalFusionCore, EvidenceRecorder, MultimodalPerceptionService, CapabilityDetector, SurfaceClassifier, AdapterSelector, UIScreenshotService, WorldModelService, MultimodalDataModels
- **Severidad:** critical, high, medium, low
- **Tipos de verdad:** Verdad visual, Verdad operativa, Verdad persistente
- **Componentes:** Foco/Ventana/HWND, Input/Output, Ownership, Degradación
- **Estado:** pending, in_progress, resolved, deferred

**Flujo de trabajo preparado:**

1. Investigación profunda genera hallazgos
2. Registrar hallazgos usando `template_hallazgo.md` en `data/investigation_deep_findings/hallazgos/`
3. Mapear a módulos usando `matriz_mapeo_hallazgos_modulos.md`
4. Definir pruebas en `data/investigation_deep_findings/pruebas_reconciliacion/`
5. Aplicar cambios mínimos si se aprueba (según criterio de cambios mínimos)
6. Ejecutar pruebas de reconciliación para verificar corrección
7. Actualizar estado del hallazgo en matriz

**Criterios de cambios mínimos:**

Un cambio se considera mínimo si:
- No requiere refactor arquitectónico
- No crea nuevas capas innecesarias
- No altera la base estable (TruthArbitrator, SignalFusionCore, EvidenceRecorder)
- Preserva las correcciones de sesgo aplicadas
- Es reversible si falla
- Tiene pruebas de verificación

---

## 4. Qué prueba determinista faltaba cerrar

**Prueba determinista forzada:**

- **Archivo:** `test_forced_empty_screenshot.py`
- **Objetivo:** Verificar gating del TruthArbitrator cuando screenshot está vacío
- **Estado:** Creada pero no ejecutada

**Por qué faltaba cerrar:**

En las pruebas de auditoría anteriores (`test_interpretation_audit.py`), el UIScreenshotService capturó screenshots reales (no vacíos) porque el servicio de captura funcionó correctamente. Por lo tanto, no se pudo verificar el gating para degradar truth_confidence cuando screenshot está vacío en un escenario real. El gating está implementado en el código, pero requiere un escenario donde el screenshot esté realmente vacío para verificarse completamente.

**Qué hace esta prueba:**

Fuerza manualmente un screenshot vacío estableciendo:
- screenshot_path = ""
- screenshot_width = 0
- screenshot_height = 0
- screenshot_sha256 = ""
- screenshot_blank_probability = 1.0

Luego verifica que:
- truth_confidence se degrada de 1.0 a 0.6
- truth_type = "operational"
- truth_source = "process"
- truth_explanation menciona "gating aplicado" y "screenshot vacío"
- degradation_alerts incluye alerta de screenshot vacío
- degradation_level es al menos "medium"

**Cómo ejecutar:**

```bash
python test_forced_empty_screenshot.py
```

**Resultado esperado:**

- truth_confidence = 0.6 (degradado)
- truth_type = "operational"
- truth_source = "process"
- degradation_alerts incluye "screenshot_completely_empty"
- degradation_level = "critical" o "high"
- truth_explanation menciona gating

**Resultado se guardará en:**

`data/investigation_deep_findings/pruebas_reconciliacion/test_forced_empty_screenshot_result.json`

---

## 5. Qué tests de reconciliación quedan preparados

**Tests de reconciliación preparados (8 escenarios):**

| Prueba | Estado | Archivo | Verificado en |
|--------|--------|---------|--------------|
| 1: Visual vacía + proceso activo | Pendiente | test_forced_empty_screenshot.py | Por ejecutar |
| 2: Accessibility Tree contradice Process Signal | Pendiente | Por crear | - |
| 3: Focus/HWND desfasados | Pendiente | Por crear | - |
| 4: input_events_count = 0 | Completado | test_interpretation_audit.py | Escenario 3 (PASS) |
| 5: output_events_count > 0 | Completado | test_interpretation_audit.py | Escenario 3 (PASS) |
| 6: Ownership con confianza baja | Completado | test_interpretation_audit.py | Todos (PASS) |
| 7: truth_confidence alta sin evidencia visual | Pendiente | Por crear | - |
| 8: Alertas de degradación activadas | Completado | test_interpretation_audit.py | Todos (PASS) |

**Cada prueba define:**

- **Módulo que toca:** TruthArbitrator, MultimodalPerceptionService, SignalFusionCore, etc.
- **Evidencia que debe producir:** Configuración específica de VisualSignal, ProcessSignal, EventSignal
- **Resultado correcto (PASS):** Criterios específicos de verdad
- **Resultado fallo (FAIL):** Criterios específicos de fallo

**Criterios de ejecución:**

- Después de aplicar cambios mínimos sugeridos por investigación profunda
- Antes de marcar un hallazgo como "resolved"
- Como parte de verificación de correcciones

**Documentación completa en:**

`data/investigation_deep_findings/pruebas_reconciliacion/README.md`

---

## 6. Qué no debe tocarse todavía

**No debe tocarse hasta leer la investigación profunda:**

- **Arquitectura base:** No rehacer arquitectura de percepción multimodal (TruthArbitrator, SignalFusionCore, EvidenceRecorder como núcleo)
- **Jerarquía de verdad:** No cambiar jerarquía OPERATIONAL > VISUAL > PERSISTENT
- **Gating existente:** No eliminar gating implementado en TruthArbitrator (gating para screenshot vacío, gating en _determine_winning_truth_type)
- **Correcciones de sesgo:** No revertir correcciones de sesgo aplicadas (gating, detección de contradicciones, distinción real vs inferido)
- **Servicios externos:** No alterar UIScreenshotService o WorldModelService (preservar providers, formato de persistencia, método scan)
- **Formato de persistencia:** No cambiar formato JSONL de EvidenceRecorder
- **Modelos de datos:** No eliminar campos existentes de dataclasses (preservar input_events_real_count, output_events_real_count, has_real_user_interaction, etc.)
- **Refresh de snapshot:** No eliminar refresh de WorldModelService en _capture_process_signal y _capture_event_signal
- **Alertas de degradación:** No eliminar alertas de degradación agregadas (screenshot_completely_empty, visual_confidence_very_low, operational_dominates_without_visual, real_input_events_missing, focus_mismatch_accessibility_process)

**Solo se permite:**

- Auditoría de comportamiento de módulos congelados
- Ajustes mínimos si investigación profunda lo exige (según criterio de cambios mínimos)
- Pruebas de verificación determinista
- Aplicación de cambios mínimos sugeridos por hallazgos de investigación profunda

---

## 7. Qué debe esperar a la investigación profunda

**Debe esperar a la investigación profunda para:**

- **Aplicar cambios adicionales:** No aplicar cambios más allá de los ya implementados (gating, refresh de snapshot, distinción real vs inferido, alertas de degradación)
- **Crear nuevos servicios:** No crear servicios nuevos sin aprobación de investigación profunda
- **Refactor arquitectónico:** No refactor arquitectura sin análisis profundo y justificación
- **Cambiar jerarquía:** No cambiar jerarquía de verdad (OPERATIONAL > VISUAL > PERSISTENT) sin evidencia de investigación
- **Eliminar gating:** No eliminar gating implementado sin justificación de investigación
- **Alterar servicios externos:** No alterar UIScreenshotService o WorldModelService sin aprobación de investigación
- **Cambiar formato de persistencia:** No cambiar formato JSONL sin aprobación de investigación
- **Eliminar campos de modelos:** No eliminar campos de dataclasses sin aprobación de investigación

**Criterio para aplicar cambios mínimos cuando llegue investigación:**

Un cambio se considera mínimo si:
- No requiere refactor arquitectónico
- No crea nuevas capas innecesarias
- No altera la base estable (TruthArbitrator, SignalFusionCore, EvidenceRecorder)
- Preserva las correcciones de sesgo aplicadas
- Es reversible si falla
- Tiene pruebas de verificación
- Está justificado por hallazgo de investigación profunda

---

## 8. Recomendación mínima siguiente

**Recomendación inmediata:**

1. **Ejecutar prueba determinista forzada:** Ejecutar `python test_forced_empty_screenshot.py` para verificar que el gating funciona correctamente cuando screenshot está vacío. Esto cerrará la verificación pendiente del gating implementado.

2. **Monitorear producción:** Monitorear logs de producción para verificar si el gating se activa en escenarios reales donde UIScreenshotService falle o capture screenshots vacíos.

3. **Esperar investigación profunda:** No aplicar cambios adicionales hasta que lleguen hallazgos de investigación profunda. La arquitectura está congelada y lista para recibir hallazgos.

**Recomendación de mediano plazo:**

4. **Crear pruebas faltantes:** Crear pruebas para escenarios 2 (Accessibility Tree contradice Process Signal), 3 (Focus/HWND desfasados), y 7 (truth_confidence alta sin evidencia visual) cuando la investigación profunda lo requiera.

5. **Mejorar captura de input real:** Implementar servicio de captura de input real (por ejemplo, usando pynput para teclado/mouse) si la investigación profunda lo recomienda para mejorar input_events_real_count.

**Recomendación de largo plazo:**

6. **Monitoreo continuo:** Implementar monitoreo continuo de métricas de interpretación (truth_confidence, visual_confidence, operational_confidence, degradation_level) para detectar si el gating se activa correctamente en producción.

7. **Alertas proactivas:** Implementar alertas proactivas cuando el sistema opere con truth_confidence=1.0 pero screenshot esté vacío, para detectar si el gating no se está activando cuando debería.

---

**Fin de preparación para recepción de investigación profunda**

IABV v1.5 está listo para recibir hallazgos de investigación profunda sin rehacer arquitectura. La base está congelada, la zona de entrada de hallazgos está preparada, las pruebas de reconciliación están definidas, y el criterio para aplicar cambios mínimos está establecido.
