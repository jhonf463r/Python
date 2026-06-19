# Auditoría de Coherencia Final

**Fecha:** 2026-06-18
**Objetivo:** Cerrar la brecha entre lo que el código realmente hace, lo que los reportes dicen, y lo que queda probado en runtime real.

---

## Matriz de Coherencia Única

| Componente | Archivo Real | Estado Real | Evidencia de Ejecución | Evidencia de Persistencia | Evidencia de Correlación | Discrepancia con Documentación | Acción Requerida |
|-----------|-------------|-------------|------------------------|---------------------------|-------------------------|--------------------------------|------------------|
| TruthArbitrator | truth_arbitrator.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en evidence_records.jsonl | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| SignalFusionCore | signal_fusion_core.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en contradiction_report.json | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| EvidenceRecorder | evidence_recorder.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en evidence_records.jsonl (42 registros) | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| RuntimePerceptionAndVerificationService | runtime_perception_and_verification_service.py | PARTIAL | ✅ Ejecuta en runtime real | ✅ Persiste en surface_observations.jsonl (7 registros) | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice PARTIAL ✅ | Ninguna |
| InputListenerService | input_listener_service.py | PARTIAL | ✅ Ejecuta en runtime real | ✅ Persiste en audit_log.jsonl | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice PARTIAL ✅ | Ninguna |
| OutputListenerService | output_listener_service.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en audit_log.jsonl | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| FocusChangeListener | focus_change_listener.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en audit_log.jsonl | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| LifecycleListener | lifecycle_listener.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en audit_log.jsonl | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| FreezeDetectorService | freeze_detector_service.py | READY | ✅ Ejecuta en runtime real | ✅ Persiste en freeze_detections.jsonl (16 registros) | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md dice READY ✅ | Ninguna |
| StructuralTruthService | structural_truth_service.py | UNVERIFIED | ❌ NO ejecuta en runtime real | ❌ NO persiste | ❌ NO correlacionado | No mencionado en FINAL_RUNTIME_VERIFICATION.md | Integrar con TruthArbitrator o usar solo como análisis post-hoc |
| UI Knowledge Graph | ui_knowledge_graph.jsonl | PARTIAL | ✅ Generado en runtime real | ✅ Persiste (solo 1 elemento) | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md no menciona | Mejorar generación de grafos cognitivos |
| Navigation Graph | navigation_graph.jsonl | PARTIAL | ✅ Generado en runtime real | ✅ Persiste (rutas inferidas) | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md no menciona | Validar rutas contra runtime real |
| HUD | audit_hud_service.py | UNVERIFIED | ❌ NO verificado en runtime real | ❌ NO persiste evidencia de visualización | ❌ NO correlacionado | FINAL_RUNTIME_VERIFICATION.md no menciona | Verificar en runtime real que HUD se muestra |
| Memory | audit_memory_service.py | PARTIAL | ✅ Ejecuta en runtime real | ✅ Persiste en audit_memory.json (153 registros) | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md no menciona | Implementar filtrado de ruido, detección de sesgos, ajuste de pesos |
| Validation | audit_validation_service.py | PARTIAL | ✅ Ejecuta en runtime real | ✅ Persiste en validation_metrics.json | ✅ Correlacionado post-hoc (100%) | FINAL_RUNTIME_VERIFICATION.md no menciona | Mejorar calibración (ECE=0.5 > 0.3) |
| `_scan_windows_windows()` | runtime_perception_and_verification_service.py (líneas 480-574) | READY | ✅ Implementación COMPLETA usando Win32 API | ✅ Persiste en surface_observations.jsonl | ✅ Correlacionado post-hoc (100%) | AUDIT_NO_VERIFICADOS.md dice NO VERIFICADO ❌ | Actualizar AUDIT_NO_VERIFICADOS.md para reflejar implementación completa |
| `verify_interaction()` | runtime_perception_and_verification_service.py | NOT_IMPLEMENTED | ❌ NO existe en código base | ❌ NO persiste | ❌ NO correlacionado | AUDIT_NO_VERIFICADOS.md dice NO VERIFICADO ❌ | Actualizar AUDIT_NO_VERIFICADOS.md para reflejar que NO EXISTE |

---

## Resumen de Estados

**READY (9 componentes):**
- TruthArbitrator
- SignalFusionCore
- EvidenceRecorder
- OutputListenerService
- FocusChangeListener
- LifecycleListener
- FreezeDetectorService
- `_scan_windows_windows()`

**PARTIAL (5 componentes):**
- RuntimePerceptionAndVerificationService
- InputListenerService
- UI Knowledge Graph
- Navigation Graph
- Memory
- Validation

**UNVERIFIED (2 componentes):**
- StructuralTruthService
- HUD

**NOT_IMPLEMENTED (1 componente):**
- `verify_interaction()`

---

## Discrepancias con Documentación

**AUDIT_NO_VERIFICADOS.md está DESACTUALIZADO:**
- Dice que `_scan_windows_windows()` está NO VERIFICADO → Realidad: READY (implementación COMPLETA)
- Dice que `verify_interaction()` está NO VERIFICADO → Realidad: NOT_IMPLEMENTED (NO EXISTE)

**FINAL_RUNTIME_VERIFICATION.md está ALINEADO:**
- Dice que RuntimePerceptionAndVerificationService es PARTIAL → Realidad: PARTIAL ✅
- Dice que InputListenerService es PARTIAL → Realidad: PARTIAL ✅
- Dice que los listeners principales son READY → Realidad: READY ✅

**VERDAD_ESTRUCTURAL_CONSOLIDADA.md está ALINEADO:**
- Dice que StructuralTruthService está consolidado pero NO integrado → Realidad: UNVERIFIED (NO ejecuta en runtime) ✅

**RECALIBRACION_REAL_CONSOLIDADA.md está ALINEADO:**
- Dice que calibración es POBRE (ECE=0.5) → Realidad: POBRE ✅
- Dice que truth source accuracy es 0.400 → Realidad: 0.400 ✅

---

## Acciones Requeridas

**Prioridad ALTA (corregir documentación):**
1. Actualizar AUDIT_NO_VERIFICADOS.md para reflejar que `_scan_windows_windows()` está READY
2. Actualizar AUDIT_NO_VERIFICADOS.md para reflejar que `verify_interaction()` es NOT_IMPLEMENTED

**Prioridad MEDIA (mejorar componentes):**
3. Integrar StructuralTruthService con TruthArbitrator o usar solo como análisis post-hoc
4. Verificar HUD en runtime real
5. Mejorar generación de UI Knowledge Graph (solo 1 elemento)
6. Validar Navigation Graph contra runtime real (rutas inferidas)
7. Implementar filtrado de ruido, detección de sesgos, ajuste de pesos en Memory
8. Mejorar calibración (ECE=0.5 > 0.3, truth source accuracy=0.400 < 0.6)

**Prioridad BAJA (implementar funcionalidad faltante):**
9. Implementar `verify_interaction()` si se requiere validación de interacciones del usuario

---

## Conclusión de Coherencia

**Lo que está realmente listo:** 9 componentes READY (arquitectura base, listeners, freeze detector, _scan_windows_windows)

**Lo que sigue parcial:** 6 componentes PARTIAL (runtime perception, input listener, grafos cognitivos, memoria, validación)

**Lo que sigue no verificado:** 2 componentes UNVERIFIED (structural truth, HUD)

**Lo que está no implementado:** 1 componente NOT_IMPLEMENTED (verify_interaction)

**Documentación desalineada:** AUDIT_NO_VERIFICADOS.md está desactualizado (2 discrepancias)

**Estado general de coherencia:** ALINEADO con excepción de AUDIT_NO_VERIFICADOS.md
