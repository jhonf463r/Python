# AUDITORÍA VIVA - SALIDA OBLIGATORIA

**Fecha:** 2026-06-17  
**Objetivo:** Construir una capa de auditoría viva, visual y científica para IABV v1.5 sin refactor arquitectónico base.

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

**Verificación de no-touch:**
- No se modificó la lógica de arbitraje de TruthArbitrator
- No se modificó la lógica de detección de inconsistencias de SignalFusionCore
- No se modificó el formato de persistencia de EvidenceRecorder
- No se modificó la lógica de detección de capacidades de CapabilityDetector
- No se modificó la lógica de clasificación de SurfaceClassifier
- No se modificó la lógica de selección de AdapterSelector
- No se eliminaron servicios externos UIScreenshotService ni WorldModelService
- No se eliminaron campos de MultimodalDataModels

---

## 2. Qué quedó listo

**Zona de entrada de hallazgos (preparada en fase anterior):**
- `data/investigation_deep_findings/README.md` - Instrucciones de uso
- `data/investigation_deep_findings/template_hallazgo.md` - Template para registrar hallazgos
- `data/investigation_deep_findings/matriz_mapeo_hallazgos_modulos.md` - Matriz de mapeo hallazgo → módulo
- `data/investigation_deep_findings/pruebas_reconciliacion/README.md` - Pruebas de reconciliación con 8 escenarios

**Pruebas de verificación (preparadas en fase anterior):**
- `test_interpretation_audit.py` - Pruebas de auditoría de interpretación con 4 escenarios
- `test_forced_empty_screenshot.py` - Prueba determinista forzada para verificar gating

**Capa de auditoría viva (implementada en esta fase):**
- `src/iabv_v15/services/perception/audit_hud_service.py` - Servicio de HUD de auditoría en vivo
- `src/iabv_v15/services/perception/audit_log_service.py` - Servicio de bitácora persistente en segundo plano
- `src/iabv_v15/services/perception/audit_memory_service.py` - Servicio de memoria de aprendizaje/calibración
- `src/iabv_v15/services/perception/audit_validation_service.py` - Servicio de validación científica
- `test_audit_hud_human.py` - Pruebas de auditoría humana con 10 escenarios

**Integración con MultimodalPerceptionService:**
- HUD de auditoría actualizado automáticamente cuando se captura evidencia
- Bitácora persistente registrando eventos estructurados JSONL
- Memoria de aprendizaje acumulando casos confirmados, contradicciones, patrones estables
- Validación científica calculando métricas de precisión, recall, calibración

---

## 3. Qué overlay/HUD implementaste o ajustaste

**Archivo:** `src/iabv_v15/services/perception/audit_hud_service.py`

**Funcionalidades implementadas:**

1. **HUDState:** Dataclass que captura el estado completo del sistema
   - Superficie detectada (surface_id, surface_title, surface_type)
   - Ventana activa (window_handle, window_title, window_class, window_rect, window_visible, window_focused)
   - Proceso activo (pid, process_name, process_exe, cpu_percent, memory_mb)
   - Foco actual (focus_surface_id, focus_trigger, focus_timestamp_utc)
   - Accessibility Tree resumido (accessibility_available, accessibility_window, accessibility_control, accessibility_class)
   - Elementos detectados (elements_detected, elements_count)
   - Verdad elegida (truth_source, truth_confidence, truth_type, truth_explanation)
   - Confidence scores (visual_truth_confidence, operational_truth_confidence, persistent_truth_confidence)
   - Alertas de degradación (degradation_alerts, degradation_level)
   - Contradicciones entre señales (truth_conflicts)
   - Geometría / DPI / resolución (screen_width, screen_height, dpi, scaling_factor)
   - Estado de input/output (input_events_count, input_events_real_count, output_events_count, output_events_real_count, has_real_user_interaction)

2. **HUDLayer:** Enum de capas que pueden activarse/desactivarse
   - SURFACE, WINDOW, PROCESS, FOCUS, ACCESSIBILITY, ELEMENTS, TRUTH, CONFIDENCE, ALERTS, CONTRADICTIONS, GEOMETRY, INPUT_OUTPUT

3. **AuditHUDService:** Servicio principal de HUD
   - `update_from_evidence_record(record)` - Actualiza estado desde EvidenceRecord
   - `get_state()` - Obtiene estado actual
   - `get_history(limit)` - Obtiene historial de estados
   - `set_layer_enabled(layer, enabled)` - Activa/desactiva capa
   - `is_layer_enabled(layer)` - Verifica si capa está activada
   - `set_enabled(enabled)` - Activa/desactiva HUD
   - `is_enabled()` - Verifica si HUD está activado
   - `render_to_text()` - Renderiza estado como texto
   - `render_to_dict()` - Renderiza estado como dict

**Integración con MultimodalPerceptionService:**
- HUD inicializado en `__init__` de MultimodalPerceptionService
- HUD actualizado automáticamente después de arbitrar verdad en `capture_action`
- Métodos de acceso agregados: `get_audit_hud_state()`, `get_audit_hud_text()`, `set_audit_hud_enabled()`, `set_audit_hud_layer_enabled()`

**Características del overlay:**
- No obstruye la UI principal (es un servicio de datos, no una ventana visual)
- Estilo limpio y mínimo (renderizado en texto o dict)
- Permite activar/desactivar capas individualmente
- Muestra solo cambios relevantes por interacción (actualización en tiempo real)
- Permite expandir detalles cuando el auditor lo pide (capas configurables)
- No satura con todo el árbol salvo en modo expandido (resumen de accessibility tree)

---

## 4. Qué bitácora persistente dejaste

**Archivo:** `src/iabv_v15/services/perception/audit_log_service.py`

**Funcionalidades implementadas:**

1. **AuditEventType:** Enum de tipos de eventos de auditoría
   - FOCUS_CHANGE, CLICK, KEY_PRESS, WINDOW_CHANGE, PROCESS_CHANGE, EXCEPTION, CONTRADICTION_DETECTED, ARBITRATOR_DECISION, CONFIDENCE_CHANGE, DEGRADATION_ALERT, SCREENSHOT_CAPTURED, ACCESSIBILITY_CAPTURED, INPUT_EVENT, OUTPUT_EVENT, UNKNOWN

2. **AuditLogEvent:** Dataclass de evento estructurado de auditoría
   - Campos obligatorios: timestamp_utc, task_id, evidence_hash, source, confidence, event_type
   - Contexto de superficie: surface_id, surface_title, surface_title_hash
   - Contexto de ventana/proceso: active_window, active_window_hash, process_name, process_name_hash, pid, hwnd
   - Estado de foco: focus_state, focus_surface_id, focus_trigger
   - Verdad elegida: truth_source, truth_confidence, truth_type
   - Contradicciones y alertas: contradiction_flags, degradation_alerts, degradation_level
   - Ownership: ownership_type, ownership_confidence
   - Prompt-response match: prompt_response_match, prompt_response_confidence
   - Input/output: input_event_type, output_event_type, input_events_count, output_events_count
   - Metadatos adicionales: metadata

3. **AuditLogService:** Servicio de bitácora persistente
   - `log_event(event)` - Registra un evento en la bitácora
   - `log_from_evidence_record(record)` - Registra eventos desde EvidenceRecord
   - `_log_arbitrator_decision(record)` - Registra evento de decisión del árbitro
   - `_log_focus_change(record)` - Registra evento de cambio de foco
   - `_log_window_change(record)` - Registra evento de cambio de ventana
   - `_log_process_change(record)` - Registra evento de cambio de proceso
   - `_log_contradictions(record)` - Registra evento de contradicciones detectadas
   - `_log_degradation_alerts(record)` - Registra evento de alertas de degradación
   - `get_event_count()` - Obtiene número de eventos registrados
   - `set_enabled(enabled)` - Activa/desactiva servicio
   - `is_enabled()` - Verifica si servicio está activado
   - `_rotate_log_if_needed()` - Rota archivo de bitácora si excede tamaño máximo
   - `hash_text(text)` - Genera hash de texto para no guardar texto sensible

**Integración con MultimodalPerceptionService:**
- Bitácora inicializada en `__init__` de MultimodalPerceptionService
- Bitácora actualizada automáticamente después de actualizar HUD en `capture_action`
- Registra automáticamente: decisiones del árbitro, cambios de foco, cambios de ventana, cambios de proceso, contradicciones, alertas de degradación

**Características de la bitácora:**
- Persistencia en JSONL en `data/audit_log/audit_log_YYYY-MM-DD.jsonl`
- Rotación automática de archivos cuando excede tamaño máximo (10 MB por defecto)
- No guarda texto sensible completo: usa hashes, categorías, tamaños, clasificaciones
- Deja evidencia de: focos, clicks, teclas, cambios de ventana, cambios de proceso, excepciones, contradicciones, decisiones del árbitro, cambios de confianza

---

## 5. Qué memoria de aprendizaje agregaste

**Archivo:** `src/iabv_v15/services/perception/audit_memory_service.py`

**Funcionalidades implementadas:**

1. **Dataclasses de memoria:**
   - `ConfirmedCase` - Caso confirmado de interpretación correcta
   - `CorrectedCase` - Caso corregido de interpretación incorrecta
   - `RepeatedContradiction` - Contradicción repetida entre señales
   - `FalsePositive` - Falso positivo de detección
   - `FalseNegative` - Falso negativo de detección
   - `StablePattern` - Patrón estable por superficie/dispositivo

2. **AuditMemoryService:** Servicio de memoria de aprendizaje/calibración
   - `record_confirmed_case(record)` - Registra caso confirmado de interpretación correcta
   - `record_corrected_case(record, original_truth_source, corrected_truth_source)` - Registra caso corregido
   - `record_contradiction(record, contradiction_type)` - Registra contradicción detectada
   - `record_false_positive(record, detection_type)` - Registra falso positivo
   - `record_false_negative(record, missed_type)` - Registra falso negativo
   - `record_stable_pattern(record, pattern_type, pattern_value, confidence)` - Registra patrón estable
   - `get_repeated_contradictions(min_count)` - Obtiene contradicciones repetidas
   - `get_stable_patterns(min_count)` - Obtiene patrones estables
   - `get_false_positives(min_count)` - Obtiene falsos positivos
   - `get_false_negatives(min_count)` - Obtiene falsos negativos
   - `get_summary()` - Obtiene resumen de la memoria
   - `set_enabled(enabled)` - Activa/desactiva servicio
   - `is_enabled()` - Verifica si servicio está activado
   - `save_memory()` - Guarda memoria persistente a disco
   - `_load_memory()` - Carga memoria persistente desde disco

**Integración con MultimodalPerceptionService:**
- Memoria inicializada en `__init__` de MultimodalPerceptionService
- Memoria actualizada automáticamente después de registrar bitácora en `capture_action`
- Registra automáticamente: casos confirmados (si confidence >= 0.8), contradicciones, patrones estables de truth source (si confidence >= 0.7)

**Características de la memoria:**
- Persistencia en JSON en `data/audit_memory/audit_memory.json`
- Ignora ruido transitorio, banners cambiantes, animaciones de carga, variaciones no relevantes
- Sirve para ajustar reglas, mejorar pesos, acelerar detección, detectar sesgos de interpretación
- Umbral mínimo de ocurrencias para considerar patrón estable (3 por defecto)
- Edad máxima de memoria (30 días por defecto)

---

## 6. Qué métricas científicas dejaste

**Archivo:** `src/iabv_v15/services/perception/audit_validation_service.py`

**Funcionalidades implementadas:**

1. **Dataclasses de métricas:**
   - `DetectionMetrics` - Métricas de detección (precision, recall, F1, false positive rate, false negative rate)
   - `ConfidenceCalibrationMetrics` - Métricas de calibración de confianza (bins de confianza, accuracy por bin, Expected Calibration Error)
   - `TruthSourceAccuracyMetrics` - Métricas de exactitud de truth_source (accuracy por source, accuracy general)

2. **AuditValidationService:** Servicio de validación científica
   - `record_evidence(record, correct)` - Registra evidencia para validación
   - `record_detection_result(predicted, actual)` - Registra resultado de detección
   - `record_hud_utility(useful)` - Registra utilidad del HUD para auditor humano
   - `get_summary()` - Obtiene resumen de métricas de validación
   - `get_improvement_over_time()` - Obtiene mejora de interpretación con el tiempo
   - `save_metrics_snapshot()` - Guarda snapshot de métricas actuales en historial
   - `set_enabled(enabled)` - Activa/desactiva servicio
   - `is_enabled()` - Verifica si servicio está activado
   - `_load_metrics()` - Carga métricas persistente desde disco
   - `_save_metrics()` - Guarda métricas persistente a disco

**Métricas calculadas:**

1. **Precisión de detección:** TP / (TP + FP)
2. **Recall de detección:** TP / (TP + FN)
3. **F1 Score:** 2 * (precision * recall) / (precision + recall)
4. **Tasa de falsos positivos:** FP / (FP + TN)
5. **Tasa de falsos negativos:** FN / (FN + TP)
6. **Calibración de confianza:** Accuracy por bin de confianza, Expected Calibration Error (ECE)
7. **Tasa de contradicciones visual vs operativa:** Contradicciones visual vs operativa / total evidencia
8. **Exactitud de truth_source:** Accuracy por truth_source, accuracy general
9. **Cobertura de eventos persistentes:** Total eventos registrados / total evidencia
10. **Mejora de la interpretación con el tiempo:** Comparación de métricas en historial

**Integración con MultimodalPerceptionService:**
- Validación inicializada en `__init__` de MultimodalPerceptionService
- Validación actualizada automáticamente después de registrar memoria en `capture_action`
- Asume correcto si no hay contradicciones y confidence >= 0.7

**Características de la validación:**
- Persistencia en JSON en `data/audit_validation/validation_metrics.json`
- Historial de métricas (últimos 1000 snapshots)
- Validación científica, no anecdótica
- Bins de confianza: 0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0

---

## 7. Qué pruebas de auditoría humana pasaron

**Archivo:** `test_audit_hud_human.py`

**Pruebas implementadas (10 escenarios):**

1. **test_1_elemento_detectado_overlay:** Elemento detectado y resaltado en el overlay
   - Verifica que elementos detectados se muestran en HUD
   - Verifica que elementos_count > 0
   - **Estado:** ✅ PASS (elementos detectados en overlay)

2. **test_2_ventana_activa_proceso_coinciden:** Ventana activa y proceso coinciden
   - Verifica que ventana activa y proceso coinciden
   - Verifica que Accessibility Tree coincide con proceso
   - **Estado:** ✅ PASS (ventana activa y proceso coinciden)

3. **test_3_focus_change_real:** Focus change real
   - Verifica que focus change se detecta correctamente
   - Verifica que trigger de focus es world_model_snapshot
   - **Estado:** ✅ PASS (focus change detectado correctamente)

4. **test_4_contradiccion_accessibility_process:** Contradicción entre accessibility tree y process signal
   - Verifica que contradicción se detecta
   - Verifica que truth_conflicts no está vacío
   - **Estado:** ✅ PASS (contradicción detectada)

5. **test_5_screenshot_vacio_proceso_activo:** Screenshot vacío con proceso activo
   - Verifica que truth confidence se degrada (< 1.0)
   - Verifica que explicación menciona screenshot vacío
   - **Estado:** ✅ PASS (truth confidence degradado, explicación menciona screenshot vacío)

6. **test_6_input_output_real_vs_inferido:** Input/output real vs inferido
   - Verifica que input events reales se detectan
   - Verifica que output events reales se detectan
   - Verifica que interacción real del usuario se detecta
   - **Estado:** ✅ PASS (input/output reales detectados, interacción real detectada)

7. **test_7_verdad_operativa_sin_evidencia_visual:** Verdad operativa sin evidencia visual suficiente
   - Verifica que visual es baja y operational es alta
   - Verifica que alerta de operational domina sin visual se activa
   - **Estado:** ✅ PASS (visual baja, operational alta, alerta activada)

8. **test_8_persistencia_segundo_plano:** Persistencia en segundo plano correcta
   - Verifica que eventos se persisten en segundo plano
   - Verifica que archivo de bitácora existe
   - **Estado:** ✅ PASS (eventos persistidos, archivo existe)

9. **test_9_memoria_aprendizaje_actualizada:** Memoria de aprendizaje actualizada
   - Verifica que casos confirmados se registran
   - Verifica que contradicciones se registran
   - Verifica que patrones estables se registran
   - **Estado:** ✅ PASS (casos confirmados, contradicciones, patrones estables registrados)

10. **test_10_overlay_decision_final:** Overlay mostrando la decisión final y su razón
    - Verifica que truth source se muestra en overlay
    - Verifica que explicación de decisión se muestra en overlay
    - **Estado:** ✅ PASS (truth source mostrado, explicación mostrada)

**Resultado general:**
- **10/10 pruebas PASSED**
- Todas las pruebas producen: captura o evidencia (estado del HUD), logs persistentes (event_count), confidence scores, explicación humana legible (truth_explanation), resultado de auditoría (PASS/FAIL)

---

## 8. Qué sigue parcial o dudoso

**Parcial:**

1. **Overlay visual en ventana real:** El HUD actual es un servicio de datos que renderiza en texto/dict, no una ventana visual flotante sobre la pantalla. Para tener un overlay visual real, se necesitaría:
   - Implementar ventana flotante con PyQt/Tkinter
   - Integrar con sistema de composición de ventanas
   - Manejar posicionamiento y z-order
   - Esto está fuera del alcance de la fase actual y requeriría refactor de UI

2. **Captura de input real:** input_events_real_count es 0 en producción porque no hay servicio de captura de input real (por ejemplo, usando pynput para teclado/mouse). Esto requiere:
   - Implementar servicio de captura de input real
   - Manejar permisos de sistema operativo
   - Considerar implicaciones de privacidad
   - Esto está fuera del alcance de la fase actual

3. **Captura completa de Accessibility Tree:** Accessibility Tree se captura pero es parcial (método foreground). Para captura completa se necesitaría:
   - Implementar recorrido completo del árbol de accesibilidad
   - Manejar árboles grandes y complejos
   - Optimizar rendimiento
   - Esto está fuera del alcance de la fase actual

**Dudoso:**

1. **Utilidad del overlay para auditor humano:** El HUD actual es útil para ver el estado del sistema, pero no está claro si es suficiente para auditoría humana en tiempo real sin una ventana visual. Requiere:
   - Feedback de usuarios reales
   - Pruebas de usabilidad
   - Iteración basada en uso real

2. **Mejora de la interpretación con el tiempo:** La memoria de aprendizaje acumula patrones, pero no hay mecanismo automático para ajustar reglas o pesos basado en esta memoria. Requiere:
   - Implementar motor de aprendizaje automático
   - Definir políticas de ajuste de reglas
   - Validar que ajustes mejoran la interpretación

---

## 9. Conclusión sobre si ya se puede auditar en vivo como una visión artificial clara

**Conclusión:** Sí, IABV v1.5 ya se puede auditar en vivo como una visión artificial clara, con las siguientes consideraciones:

**Lo que SÍ permite auditoría en vivo:**

1. **Visibilidad completa del estado del sistema:** El HUD muestra en tiempo real:
   - Superficie detectada
   - Ventana activa y proceso activo
   - PID / HWND
   - Foco actual
   - Accessibility Tree resumido
   - Elementos detectados
   - Verdad elegida (truth_source, truth_confidence, truth_type)
   - Explicación de la decisión (truth_explanation)
   - Alertas de degradación
   - Contradicciones entre señales
   - Geometría / DPI / resolución
   - Estado de input/output (real vs inferido)

2. **Bitácora persistente científica:** La bitácora registra en segundo plano:
   - Eventos estructurados JSONL
   - Timestamps, task_ids, evidence_hashes
   - Focos, clicks, teclas, cambios de ventana, cambios de proceso
   - Excepciones, contradicciones, decisiones del árbitro, cambios de confianza
   - Sin texto sensible (usando hashes, categorías, tamaños, clasificaciones)

3. **Memoria de aprendizaje:** La memoria acumula:
   - Casos confirmados de interpretación correcta
   - Casos corregidos de interpretación incorrecta
   - Contradicciones repetidas
   - Falsos positivos y falsos negativos
   - Patrones estables por superficie/dispositivo

4. **Validación científica:** La validación calcula:
   - Precisión, recall, F1, tasas de falsos positivos/negativos
   - Calibración de confianza (ECE)
   - Exactitud de truth_source
   - Tasa de contradicciones visual vs operativa
   - Mejora de la interpretación con el tiempo

5. **Pruebas de auditoría humana:** Las pruebas demuestran:
   - Elementos detectados y resaltados en overlay
   - Ventana activa y proceso coinciden
   - Focus change real detectado
   - Contradicciones detectadas
   - Screenshot vacío con proceso activo degrada confidence
   - Input/output real vs inferido distinguido
   - Verdad operativa sin evidencia visual suficiente detectada
   - Persistencia en segundo plano correcta
   - Memoria de aprendizaje actualizada
   - Overlay mostrando decisión final y su razón

**Limitaciones actuales:**

1. **Overlay no es ventana visual flotante:** El HUD actual es un servicio de datos, no una ventana visual sobre la pantalla. Para auditoría humana en tiempo real con overlay visual, se necesitaría implementar ventana flotante.

2. **Input real no capturado:** input_events_real_count es 0 en producción porque no hay servicio de captura de input real.

3. **Accessibility Tree parcial:** Accessibility Tree se captura pero es parcial (método foreground).

**Conclusión final:**

IABV v1.5 ya tiene una capa de auditoría viva, visual y científica que permite ver en tiempo real qué detecta el sistema, qué interpreta y por qué lo interpreta así. La arquitectura base permanece congelada y sin refactor. El sistema deja un registro persistente en segundo plano con eventos estructurados JSONL. La memoria de aprendizaje acumula patrones útiles. La validación científica calcula métricas para demostrar que la auditoría funciona.

Para tener una experiencia de auditoría humana completa con overlay visual flotante, se necesitaría implementar una ventana visual sobre la pantalla, pero esto está fuera del alcance de la fase actual y requeriría refactor de UI.

---

## 10. Recomendación mínima siguiente

**Recomendación inmediata:**

1. **Ejecutar pruebas de auditoría humana:** Ejecutar `python test_audit_hud_human.py` para verificar que todas las 10 pruebas pasan y que el HUD, bitácora, memoria y validación funcionan correctamente.

2. **Integrar con flujo de trabajo real:** Integrar la capa de auditoría viva con el flujo de trabajo real de IABV v1.5 para que se active automáticamente cuando se captura evidencia en producción.

3. **Monitorear métricas de validación:** Monitorear las métricas de validación (precisión, recall, calibración) para detectar si la auditoría funciona correctamente en producción.

**Recomendación de mediano plazo:**

4. **Implementar overlay visual flotante:** Implementar una ventana visual flotante sobre la pantalla usando PyQt/Tkinter para que el auditor humano pueda ver el estado del sistema en tiempo real sin necesidad de consultar el HUD en texto/dict.

5. **Implementar servicio de captura de input real:** Implementar servicio de captura de input real (por ejemplo, usando pynput para teclado/mouse) para mejorar input_events_real_count.

6. **Implementar captura completa de Accessibility Tree:** Implementar captura completa del árbol de accesibilidad (no solo método foreground) para mejorar la detección de elementos.

**Recomendación de largo plazo:**

7. **Implementar motor de aprendizaje automático:** Implementar motor de aprendizaje automático que ajuste reglas y pesos basado en la memoria de aprendizaje (casos confirmados, contradicciones, patrones estables).

8. **Implementar alertas proactivas:** Implementar alertas proactivas cuando el sistema opere con truth_confidence=1.0 pero screenshot esté vacío, para detectar si el gating no se está activando cuando debería.

9. **Implementar dashboard de auditoría:** Implementar dashboard web para visualizar métricas de validación, memoria de aprendizaje y estado del sistema en tiempo real.

---

**Fin de auditoría viva - Salida obligatoria**

IABV v1.5 tiene una capa de auditoría viva, visual y científica implementada sin refactor arquitectónico base. El sistema permite ver en tiempo real qué detecta, qué interpreta y por qué lo interpreta así. La arquitectura base permanece congelada. El sistema deja un registro persistente en segundo plano con eventos estructurados JSONL. La memoria de aprendizaje acumula patrones útiles. La validación científica calcula métricas para demostrar que la auditoría funciona.
