# PRUEBAS DE RECONCILIACIÓN - INVESTIGACIÓN PROFUNDA

**Fecha de creación:** 2026-06-17  
**Objetivo:** Conjunto mínimo de pruebas para verificar correcciones cuando lleguen hallazgos de investigación profunda.

---

## Instrucciones de uso

1. Cada prueba define un escenario específico que debe ser verificado
2. Cada prueba especifica qué módulo toca, qué evidencia debe producir, y qué resultado es correcto
3. Cuando llegue un hallazgo de investigación profunda, ejecutar las pruebas relevantes
4. Comparar resultados con los criterios de PASS/FAIL definidos
5. Si una prueba falla, revisar el hallazgo y aplicar cambios mínimos sugeridos

---

## Prueba 1: Visual vacía + proceso activo

**Módulos afectados:** TruthArbitrator, MultimodalPerceptionService

**Escenario:**
- Screenshot está completamente vacío (path="", width=0, height=0, sha256="")
- Proceso está activo (pid > 0, process_name válido)
- HWND es válido (> 0)

**Evidencia que debe producir:**
- VisualSignal con screenshot_path="", screenshot_width=0, screenshot_height=0, screenshot_sha256=""
- ProcessSignal con pid > 0, process_name válido
- TruthArbitrator debe aplicar gating

**Resultado correcto (PASS):**
- truth_confidence < 1.0 (degradado a 0.6)
- truth_type = "operational"
- truth_source = "process"
- truth_explanation menciona "gating aplicado" y "screenshot vacío"
- degradation_alerts incluye "screenshot_completely_empty" o similar
- degradation_level = "critical" o "high"

**Resultado fallo (FAIL):**
- truth_confidence = 1.0 (no degradado)
- truth_explanation NO menciona gating
- degradation_alerts NO incluye alerta de screenshot vacío
- degradation_level = "none" o "low"

**Archivo de prueba:** `test_forced_empty_screenshot.py`

---

## Prueba 2: Accessibility Tree contradice Process Signal

**Módulos afectados:** TruthArbitrator, SignalFusionCore, MultimodalPerceptionService

**Escenario:**
- Accessibility Tree detecta ventana "App A"
- Process Signal reporta proceso "App B"
- No hay coincidencia parcial entre nombres

**Evidencia que debe producir:**
- VisualSignal con accessibility_available=True, dom_text="foreground:App A|..."
- ProcessSignal con process_name="App B"
- TruthArbitrator debe detectar contradicción

**Resultado correcto (PASS):**
- truth_conflicts incluye contradicción Accessibility Tree vs Process Signal
- truth_explanation menciona "contradicción Accessibility Tree vs Process Signal"
- degradation_alerts incluye "focus_mismatch_accessibility_process" o similar
- degradation_level = "high"

**Resultado fallo (FAIL):**
- truth_conflicts NO incluye contradicción
- truth_explanation NO menciona contradicción
- degradation_alerts NO incluye alerta de mismatch
- degradation_level = "none" o "low"

**Archivo de prueba:** Por crear (requiere simular escenario real)

---

## Prueba 3: Focus/HWND desfasados

**Módulos afectados:** MultimodalPerceptionService, WorldModelService, TruthArbitrator

**Escenario:**
- HWND reportado por Process Signal es X
- Focus reportado por EventSignal es Y
- X != Y (desfaso temporal)

**Evidencia que debe producir:**
- ProcessSignal con window_handle=X
- EventSignal con focus_change_event.current_surface_id=Y
- X != Y

**Resultado correcto (PASS):**
- truth_conflicts incluye contradicción HWND vs Focus
- truth_explanation menciona desfaso de foco/HWND
- degradation_alerts incluye alerta de desfaso
- degradation_level = "high"

**Resultado fallo (FAIL):**
- truth_conflicts NO incluye contradicción
- truth_explanation NO menciona desfaso
- degradation_alerts NO incluye alerta de desfaso
- degradation_level = "none" o "low"

**Archivo de prueba:** Por crear (requiere simular escenario real)

---

## Prueba 4: input_events_count = 0

**Módulos afectados:** MultimodalPerceptionService, EvidenceRecorder, TruthArbitrator

**Escenario:**
- input_events_count = 0
- input_events_real_count = 0
- No hubo input del usuario

**Evidencia que debe producir:**
- EventSignal con input_events_count=0, input_events_real_count=0
- has_real_user_interaction=False

**Resultado correcto (PASS):**
- degradation_alerts incluye "real_input_events_missing"
- truth_explanation menciona "input ausente"
- degradation_level = "medium" o "high"
- has_real_user_interaction=False

**Resultado fallo (FAIL):**
- degradation_alerts NO incluye alerta de input ausente
- truth_explanation NO menciona input ausente
- degradation_level = "none" o "low"
- has_real_user_interaction=True (incorrecto)

**Archivo de prueba:** Ya verificado en `test_interpretation_audit.py` (Escenario 3)

---

## Prueba 5: output_events_count > 0

**Módulos afectados:** MultimodalPerceptionService, EvidenceRecorder, TruthArbitrator

**Escenario:**
- output_events_count > 0
- output_events_real_count > 0
- Hubo output (ej: clipboard)

**Evidencia que debe producir:**
- EventSignal con output_events_count > 0, output_events_real_count > 0
- clipboard_events_count > 0 (si es clipboard)

**Resultado correcto (PASS):**
- output_events_real_count > 0
- output_events_count = output_events_real_count + output_events_inferred_count
- Si input_events_real_count=0, debe haber conflicto "input ausente pero output presente"

**Resultado fallo (FAIL):**
- output_events_real_count = 0 cuando output_events_count > 0
- NO hay conflicto cuando input=0 y output>0

**Archivo de prueba:** Ya verificado en `test_interpretation_audit.py` (Escenario 3)

---

## Prueba 6: Ownership con confianza baja

**Módulos afectados:** MultimodalPerceptionService, TruthArbitrator

**Escenario:**
- ownership_record.confidence < 0.7
- No se puede determinar con certeza quién ejecutó la acción

**Evidencia que debe producir:**
- ownership_record con confidence < 0.7
- ownership_record.type = "unknown" o "ai" con baja confianza

**Resultado correcto (PASS):**
- degradation_alerts incluye "ownership_low_confidence"
- degradation_level = "medium" o "high"
- truth_explanation menciona baja confianza de ownership

**Resultado fallo (FAIL):**
- degradation_alerts NO incluye alerta de ownership baja
- degradation_level = "none" o "low"
- truth_explanation NO menciona ownership

**Archivo de prueba:** Ya verificado en `test_interpretation_audit.py` (todos los escenarios)

---

## Prueba 7: truth_confidence alta sin evidencia visual

**Módulos afectados:** TruthArbitrator, SignalFusionCore

**Escenario:**
- truth_confidence >= 0.9
- visual_truth_confidence < 0.3
- operational_truth_confidence >= 0.7

**Evidencia que debe producir:**
- EvidenceRecord con truth_confidence >= 0.9
- visual_truth_confidence < 0.3
- operational_truth_confidence >= 0.7

**Resultado correcto (PASS):**
- degradation_alerts incluye "operational_dominates_without_visual" o "visual_confidence_very_low"
- degradation_level = "high"
- truth_explanation menciona contradicción visual vs operativa

**Resultado fallo (FAIL):**
- degradation_alerts NO incluye alerta de operational domina sin visual
- degradation_level = "none" o "low"
- truth_explanation NO menciona contradicción

**Archivo de prueba:** Por crear (requiere simular escenario con visual_confidence baja)

---

## Prueba 8: Alertas de degradación activadas

**Módulos afectados:** MultimodalPerceptionService, TruthArbitrator

**Escenario:**
- Hay múltiples problemas de degradación
- Sistema debe generar alertas explícitas

**Evidencia que debe producir:**
- degradation_alerts no vacío
- degradation_level != "none"

**Resultado correcto (PASS):**
- degradation_alerts contiene al menos una alerta
- degradation_level = "low", "medium", "high", o "critical"
- Cada alerta tiene: type, severity, message, impact

**Resultado fallo (FAIL):**
- degradation_alerts vacío
- degradation_level = "none"
- Alertas faltan campos requeridos

**Archivo de prueba:** Ya verificado en `test_interpretation_audit.py` (todos los escenarios)

---

## Matriz de estado de pruebas

| Prueba | Estado | Archivo | Verificado en |
|--------|--------|---------|--------------|
| 1: Visual vacía + proceso activo | Pendiente | test_forced_empty_screenshot.py | Por ejecutar |
| 2: Accessibility Tree contradice Process Signal | Pendiente | Por crear | - |
| 3: Focus/HWND desfasados | Pendiente | Por crear | - |
| 4: input_events_count = 0 | Completado | test_interpretation_audit.py | Escenario 3 |
| 5: output_events_count > 0 | Completado | test_interpretation_audit.py | Escenario 3 |
| 6: Ownership con confianza baja | Completado | test_interpretation_audit.py | Todos |
| 7: truth_confidence alta sin evidencia visual | Pendiente | Por crear | - |
| 8: Alertas de degradación activadas | Completado | test_interpretation_audit.py | Todos |

---

## Criterios de ejecución

**Cuando ejecutar:**
- Después de aplicar cambios mínimos sugeridos por investigación profunda
- Antes de marcar un hallazgo como "resolved"
- Como parte de verificación de correcciones

**Cómo ejecutar:**
- Ejecutar pruebas relevantes para el hallazgo
- Comparar resultados con criterios PASS/FAIL
- Documentar resultados en archivo de hallazgo
- Si falla, revisar y ajustar cambios mínimos

**Qué hacer si falla:**
- Revisar el hallazgo original
- Verificar que los cambios mínimos se aplicaron correctamente
- Ajustar cambios si necesario
- Re-ejecutar pruebas
- Documentar ajustes en hallazgo

---

**Fin de pruebas de reconciliación**
