# Reconciliación Final - Verdad Canónica

**Fecha:** 2026-06-18
**Objetivo:** Resolver contradicciones entre reportes y dejar una única verdad canónica del estado del sistema

---

## Tabla de Verdad Canónica

| Componente | Estado Canónico | Evidencia Real | Evidencia Persistente | Contradicción Encontrada | Documentación Previa que lo Contradice | Decisión Final |
|-----------|-----------------|----------------|----------------------|-------------------------|--------------------------------------|----------------|
| InputListenerService | PARTIAL | verify_hybrid_real.py: iniciado, events_count: 0, has_real_data: False | audit_log.jsonl: logs de ejecución previa | Algunos reportes dicen READY, otros dicen NO VERIFICADO | VERIFICACION_RUNTIME_REAL_MINIMA.md dice NO VERIFICADO | PARTIAL - Ejecuta pero NO captura input humano real (events_count: 0) |
| OutputListenerService | READY | verify_hybrid_real.py: iniciado, 2 eventos reales, has_real_data: True | audit_log.jsonl: logs de ejecución previa | Ninguna | Ninguna | READY - Ejecuta y captura eventos reales del sistema |
| FocusChangeListener | READY | verify_hybrid_real.py: iniciado, 1 evento real, has_real_data: True | audit_log.jsonl: logs de ejecución previa | Ninguna | Ninguna | READY - Ejecuta y captura eventos reales del sistema |
| LifecycleListener | READY | verify_hybrid_real.py: iniciado, 1 evento real, has_real_data: True | audit_log.jsonl: logs de ejecución previa | Ninguna | Ninguna | READY - Ejecuta y captura eventos reales del sistema |
| FreezeDetectorService | READY | verify_hybrid_real.py: iniciado, 3 freezes reales | freeze_detections.jsonl: 21 registros | Ninguna | Ninguna | READY - Ejecuta y detecta freezes reales |
| AuditHUDService | UNVERIFIED | verify_cognitive_hud.py: funciona con datos de prueba (SIMULACIÓN) | Ninguna - NO persiste evidencia de visualización | Algunos reportes dicen READY, otros dicen UNVERIFIED | FINAL_RUNTIME_VERIFICATION.md no menciona | UNVERIFIED - NO verificado en pantalla real, solo con datos de prueba |
| TruthArbitrator | READY | verify_hybrid_real.py: arbitró con datos reales (truth_source: process, truth_confidence: 1.0) | evidence_records.jsonl: 44 registros | Ninguna | Ninguna | READY - Ejecuta y arbitra con datos reales |
| SignalFusionCore | READY | verify_hybrid_real.py: inició y ejecutó | contradiction_report.json: 31 contradicciones | Ninguna | Ninguna | READY - Ejecuta y detecta contradicciones |
| EvidenceRecorder | READY | verify_hybrid_real.py: persistió 44 evidence_records, 9 surface_observations, 21 freeze_detections | evidence_records.jsonl: 44 registros | Ninguna | Ninguna | READY - Ejecuta y persiste evidencia real |
| RuntimePerceptionAndVerificationService | PARTIAL | verify_hybrid_real.py: iniciado, 9 surface_observations con datos reales | surface_observations.jsonl: 9 registros | Ninguna | Ninguna | PARTIAL - Ejecuta pero InputListenerService NO captura input humano real |
| StructuralTruthService | UNVERIFIED | NO integrado con TruthArbitrator (base estable congelada) | Ninguna - NO persiste | Ninguna - todos los reportes coinciden | Ninguna | UNVERIFIED - NO integrado al runtime real, solo análisis post-hoc |
| UI Knowledge Graph | PARTIAL | Generado en runtime real pero solo 1 elemento | ui_knowledge_graph.jsonl: 1 elemento | Ninguna | Ninguna | PARTIAL - Solo 1 elemento, sin relaciones |
| Navigation Graph | PARTIAL | Generado en runtime real pero rutas inferidas (confidence=0.5, frequency=0) | navigation_graph.jsonl: rutas inferidas | Ninguna | Ninguna | PARTIAL - Rutas inferidas, no validadas |
| verify_interaction() | NOT_IMPLEMENTED | NO existe en código base | Ninguna - NO persiste | Ninguna - todos los reportes coinciden después de corrección | AUDIT_NO_VERIFICADOS.md original decía NO VERIFICADO | NOT_IMPLEMENTED - NO existe en código base |
| _scan_windows_windows() | READY | verify_hybrid_real.py: ejecutó, 9 SurfaceObservations con datos reales de ventanas | surface_observations.jsonl: 9 registros | AUDIT_NO_VERIFICADOS.md original decía NO VERIFICADO | AUDIT_NO_VERIFICADOS.md original decía NO VERIFICADO | READY - Implementación COMPLETA, VERIFICADO en runtime real |

---

## Resumen de Estados Canónicos

**READY (9 componentes):**
- OutputListenerService
- FocusChangeListener
- LifecycleListener
- FreezeDetectorService
- TruthArbitrator
- SignalFusionCore
- EvidenceRecorder
- _scan_windows_windows()

**PARTIAL (4 componentes):**
- InputListenerService (ejecuta pero NO captura input humano real)
- RuntimePerceptionAndVerificationService (ejecuta pero InputListenerService NO captura input humano real)
- UI Knowledge Graph (solo 1 elemento, sin relaciones)
- Navigation Graph (rutas inferidas, no validadas)

**UNVERIFIED (2 componentes):**
- AuditHUDService (NO verificado en pantalla real, solo con datos de prueba)
- StructuralTruthService (NO integrado al runtime real, solo análisis post-hoc)

**NOT_IMPLEMENTED (1 componente):**
- verify_interaction() (NO existe en código base)

---

## Calibración (Estado Canónico)

**ECE:** 0.5 (POBRE, umbral < 0.3)
**Truth source accuracy:** 0.400 (BAJA, umbral > 0.6)
**Contradiction rate:** 0.471 (ALTO, umbral < 0.3)
**Accuracy bin 0.8-1.0:** 0.25 (SOBRECONFIANZA SEVERA)

**Estado:** POBRE - No cumple con ninguno de los umbrales de referencia

---

## Verificación Runtime Real (Estado Canónico)

**Estado:** PARCIALMENTE VERIFICADO

**Evidencia real:**
- verify_hybrid_real.py ejecutó servicios reales
- OutputListenerService, FocusChangeListener, LifecycleListener, FreezeDetectorService capturaron datos reales del sistema operativo
- EvidenceRecorder persistió evidencia real (44 evidence_records, 9 surface_observations, 21 freeze_detections)
- TruthArbitrator arbitró con datos reales
- _scan_windows_windows() ejecutó y generó 9 SurfaceObservations con datos reales de ventanas

**Limitaciones:**
- InputListenerService NO capturó input humano real (events_count: 0)
- HUD NO se inició en esta verificación (verify_hybrid_real.py NO inicia el HUD)
- No hay evidencia de HUD en pantalla real

**Conclusión:** Hubo verificación runtime real de servicios de percepción, pero NO hubo verificación runtime real de HUD ni de input humano real.
