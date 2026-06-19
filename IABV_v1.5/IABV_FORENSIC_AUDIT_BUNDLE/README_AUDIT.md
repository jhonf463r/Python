# IABV FORENSIC AUDIT BUNDLE - README

**Fecha de generación:** 2026-06-18
**Versión de IABV:** v1.5
**Plataforma:** Windows
**Propósito:** Auditoría forense de interpretación de entorno en runtime real
**Estado del bundle:** PARTIAL - Evidencia persistida existente, no runtime real nuevo

---

## ⚠️ CLASIFICACIÓN ESTRICTA DE EVIDENCIA

Este bundle usa una clasificación estricta para distinguir entre evidencia real, derivada y simulada. **NO mezclar estas categorías.**

### A. EVIDENCIA REAL (33 archivos)

**Definición:** Evidencia capturada en runtime real y persistida por el sistema. Puede usarse como evidencia definitiva para auditoría externa.

**Archivos REAL:**
- **raw_evidence/evidence_records.jsonl** - 43 registros de evidencia multimodal capturados en runtime real
- **raw_evidence/validation_metrics.json** - Métricas de calibración ANTES de ajustes (ECE=0.500, truth source accuracy=0.400)
- **raw_evidence/audit_log.jsonl** - 21 registros de bitácora de auditoría persistidos
- **raw_evidence/audit_memory.json** - Memoria de casos persistida
- **raw_evidence/ui_knowledge_graph.jsonl** - Grafo de conocimiento UI persistido
- **raw_evidence/navigation_graph.jsonl** - Grafo de navegación persistido
- **raw_evidence/navigation_states.jsonl** - Estados de navegación persistidos
- **raw_evidence/ui_elements_index.jsonl** - Índice de elementos UI persistido
- **raw_evidence/runtime_audit.jsonl** - 9541 líneas de logs de runtime persistidos
- **raw_evidence/surface_observations.jsonl** - 8 observaciones de superficie persistidas
- **raw_evidence/freeze_detections.jsonl** - 16 detecciones de freeze persistidas
- **visual_evidence/*.png** (20 archivos) - Screenshots capturados en runtime real
- **visual_evidence/index.json** - Índice de screenshots generado por el sistema
- **interpretation/calibration_report.json** - Métricas de calibración ANTES de ajustes (REAL, no simulado)

**Cómo usar:** Esta evidencia puede usarse como prueba definitiva de qué vio el sistema en runtime real.

---

### B. EVIDENCIA DERIVADA (6 archivos)

**Definición:** Interpretaciones, reportes y comparaciones derivados de evidencia real. No es evidencia primaria. Veredictos son interpretaciones, no hechos brutos.

**Archivos DERIVED_FROM_REAL (PARTIAL):**
- **interpretation/interpretation_report.json** - Estadísticas generales derivadas de evidence_records.jsonl
- **interpretation/truth_arbitration_report.json** - Decisiones de arbitraje derivadas de evidence_records.jsonl
- **interpretation/contradiction_report.json** - Análisis de contradicciones derivado de evidence_records.jsonl
- **comparisons/case_comparisons.json** - Comparaciones crudo vs interpretado derivadas de evidence_records.jsonl
- **comparisons/raw_vs_interpreted_matrix.csv** - Matriz CSV de comparaciones derivada de evidence_records.jsonl
- **hard_cases/hard_cases_report.json** - Casos duros identificados por patrones en evidence_records.jsonl

**Cómo usar:** Use estos archivos para entender cómo el sistema interpretó la evidencia, pero NO como evidencia primaria. Veredictos de consistencia (CONFIRMED/DISPUTED/PARTIAL) son interpretaciones, no hechos brutos.

---

### C. EVIDENCIA SIMULADA (0 archivos)

**Definición:** Evidencia generada sintéticamente. NO puede usarse como evidencia de runtime real.

**Archivos SIMULATED (NO INCLUIDOS):**
- **validation_metrics_post_calibration.json** - NO INCLUIDO porque es SIMULADO (ECE=0.048, contradiction_rate=1.0, total_records=100)
  - Este archivo fue generado por el script `validate_runtime_post_calibration.py` con datos sintéticos
  - NO representa runtime real
  - NO puede usarse como evidencia de mejora de calibración

**Por qué NO está incluido:** Incluir evidencia simulada como si fuera real sería engañoso para un auditor externo. Este bundle NO contiene evidencia simulada.

---

### D. METADATOS (1 archivo)

**Definición:** Metadatos generados para el bundle de auditoría.

**Archivos METADATA:**
- **MANIFEST.json** - Inventario con clasificación estricta de todos los archivos

**Cómo usar:** Use para verificar integridad del bundle y entender la clasificación de cada archivo.

---

## ¿Qué es este bundle?

Este bundle contiene evidencia forense con disciplina de verdad estricta para auditar si IABV v1.5 interpreta correctamente su entorno en runtime real. Incluye evidencia cruda REAL (capturada en runtime real), evidencia derivada (interpretaciones de evidencia real), y NO incluye evidencia simulada.

**IMPORTANTE:** Este bundle es PARTIAL porque contiene evidencia persistida existente, no nueva evidencia runtime real generada específicamente para esta auditoría.

---

## Estructura del Bundle

### 1. MANIFEST.json
Lista completa de archivos incluidos con:
- Hashes SHA256 para integridad
- Timestamps UTC
- Tamaños de archivos
- **Clasificación estricta:** REAL / PARTIAL / SIMULATED
- **Fuente:** runtime_real_persisted / derived_from_real / generated
- **Nota breve** explicando por qué se asignó esa clasificación

**Cómo usarlo:** Verificar integridad del bundle y entender qué evidencia es REAL vs DERIVED.

---

### 2. raw_evidence/ (Evidencia Cruda REAL)

Archivos de datos crudos capturados en runtime real (11 archivos REAL):

- **evidence_records.jsonl** - 43 registros de evidencia multimodal
- **validation_metrics.json** - Métricas de validación ANTES de calibración
- **audit_log.jsonl** - 21 registros de bitácora de auditoría
- **audit_memory.json** - Memoria de casos confirmados, corregidos, patrones estables
- **ui_knowledge_graph.jsonl** - Grafo de conocimiento de UI
- **navigation_graph.jsonl** - Grafo de navegación
- **navigation_states.jsonl** - Estados de navegación
- **ui_elements_index.jsonl** - Índice de elementos UI
- **runtime_audit.jsonl** - 9541 líneas de logs de runtime
- **surface_observations.jsonl** - 8 observaciones de superficie
- **freeze_detections.jsonl** - 16 detecciones de freeze

**Estado:** REAL - Evidencia cruda capturada en runtime real y persistida por el sistema.

**Cómo usarlo:** Analizar los datos crudos para entender qué vio el sistema antes de interpretar.

---

### 3. visual_evidence/ (Evidencia Visual REAL)

Screenshots y evidencia visual real (21 archivos REAL):

- 20 Screenshots PNG (228KB-356KB cada uno)
- 1 index.json (índice de screenshots)

**Estado:** REAL - Screenshots capturados en runtime real y persistidos por el sistema.

**Cómo usarlo:** Comparar screenshots con las interpretaciones en evidence_records.jsonl para validar que el sistema interpretó correctamente lo que vio.

**Correspondencia temporal:** Screenshots pueden emparejarse con evidence_records por timestamp_utc, pero no hay garantía de sincronización perfecta.

---

### 4. interpretation/ (Evidencia de Interpretación)

Reportes de interpretación generados desde evidencia cruda real (4 archivos):

- **interpretation_report.json** - Estadísticas generales (truth sources, truth types, distribución de confianza)
  - **Estado:** PARTIAL (DERIVED_FROM_REAL)
  - **Nota:** Interpretación derivada de evidencia cruda persistida
- **truth_arbitration_report.json** - 43 decisiones de arbitraje de verdad
  - **Estado:** PARTIAL (DERIVED_FROM_REAL)
  - **Nota:** Decisiones derivadas de evidencia cruda persistida
- **contradiction_report.json** - Análisis de contradicciones detectadas
  - **Estado:** PARTIAL (DERIVED_FROM_REAL)
  - **Nota:** Contradicciones detectadas en evidencia cruda persistida
- **calibration_report.json** - Métricas de calibración ANTES de ajustes
  - **Estado:** REAL (runtime_real_persisted)
  - **Nota:** Métricas de calibración ANTES de ajustes (runtime real persistido). NO incluye métricas post-calibración simuladas.

**Cómo usarlo:** Comparar con evidencia cruda para validar que las interpretaciones son consistentes con los datos crudos.

**Estado:** PARTIAL (excepto calibration_report.json que es REAL) - Interpretación derivada de evidencia persistida, no runtime real nuevo.

---

### 5. comparisons/ (Comparaciones Crudo vs Interpretado)

Comparaciones entre evidencia cruda y evidencia interpretada (2 archivos PARTIAL):

- **case_comparisons.json** - 43 comparaciones detalladas caso por caso
  - **Estado:** PARTIAL (DERIVED_FROM_REAL)
  - **Nota:** Comparaciones derivadas de evidencia cruda persistida
  - **Veredictos:** CONFIRMED (27), DISPUTED (8), PARTIAL (7)
- **raw_vs_interpreted_matrix.csv** - Matriz CSV de comparaciones
  - **Estado:** PARTIAL (DERIVED_FROM_REAL)
  - **Nota:** Matriz derivada de evidencia cruda persistida

**Cómo usarlo:** Validar que la interpretación no contradice la evidencia cruda sin explicación. Revisar casos donde hay discrepancias (DISPUTED).

**Estado:** PARTIAL - Comparaciones derivadas de evidencia persistida. Veredictos son interpretaciones.

---

### 6. hard_cases/ (Casos Duros)

Casos difíciles identificados para auditoría (1 archivo PARTIAL):

- **hard_cases_report.json** - 12 casos duros con veredictos
  - **Estado:** PARTIAL (DERIVED_FROM_REAL)
  - **Nota:** Casos duros identificados por patrones en evidencia cruda persistida
  - **Veredictos:** DISPUTED (todos los casos duros)

**Casos duros identificados:**
- Screenshot vacío + proceso activo
- Accessibility tree presente + visual ausente
- Input sin output
- Output sin input
- Confianza alta sin corroboración

**Cómo usarlo:** Revisar estos casos específicamente para validar que el sistema manejó correctamente situaciones difíciles.

**Estado:** PARTIAL - Casos duros identificados por patrones en datos existentes, no generados específicamente para auditoría. Veredictos son interpretaciones.

---

## Flujo de Auditoría Recomendado

### Paso 1: Verificar Integridad y Clasificación
1. Abrir MANIFEST.json
2. Verificar que el número de archivos coincide con lo esperado (40 archivos)
3. Verificar hashes SHA256 si se requiere validación de integridad
4. Verificar clasificación: 33 REAL, 6 PARTIAL, 0 SIMULATED, 1 METADATA
5. Notar que runtime_status es "PARTIAL" y validation_status es "PARTIAL"

### Paso 2: Revisar Evidencia Cruda REAL
1. Abrir raw_evidence/evidence_records.jsonl
2. Revisar algunos registros para entender qué datos crudos se recolectaron
3. Abrir visual_evidence/ y revisar screenshots correspondientes
4. Notar que esta evidencia es REAL (capturada en runtime real)

### Paso 3: Revisar Interpretación DERIVED
1. Abrir interpretation/interpretation_report.json para ver estadísticas generales
2. Abrir interpretation/truth_arbitration_report.json para ver decisiones de arbitraje
3. Abrir interpretation/contradiction_report.json para ver contradicciones detectadas
4. Notar que estos son PARTIAL (derivados de evidencia real)
5. Abrir interpretation/calibration_report.json (REAL) para ver métricas ANTES de calibración

### Paso 4: Comparar Crudo vs Interpretado
1. Abrir comparisons/case_comparisons.json
2. Buscar casos donde el veredicto es DISPUTED (8 casos)
3. Abrir comparisons/raw_vs_interpreted_matrix.csv para análisis rápido
4. Notar que estos son PARTIAL (derivados de evidencia real)
5. Veredictos: CONFIRMED (27), DISPUTED (8), PARTIAL (7)

### Paso 5: Revisar Casos Duros
1. Abrir hard_cases/hard_cases_report.json
2. Revisar cada caso duro (12 casos, todos DISPUTED)
3. Verificar que la confianza sea apropiada para cada caso
4. Notar que estos son PARTIAL (identificados por patrones en datos existentes)

### Paso 6: Revisar Calibración REAL
1. Abrir interpretation/calibration_report.json (REAL)
2. Verificar ECE (Expected Calibration Error) - debe ser < 0.3 para calibración aceptable
3. **NOTA:** ECE actual es 0.500 (pobre, umbral < 0.3)
4. Verificar truth source accuracy - debe ser > 0.6 para aceptable
5. **NOTA:** Truth source accuracy actual es 0.400 (baja, umbral > 0.6)
6. Revisar accuracy por bin de confianza para detectar sobreconfianza
7. **NOTA:** Bin 0.8-1.0 tiene accuracy=0.250, error=0.650 (sobreconfianza severa)
8. **IMPORTANTE:** Este reporte es REAL (ANTES de calibración). NO hay reporte post-calibración porque validation_metrics_post_calibration.json es SIMULADO y NO está incluido.

---

## Qué Validar

### Validación de Interpretación Correcta
- ¿La verdad elegida coincide con la evidencia cruda?
- ¿La confianza asignada es apropiada para la evidencia disponible?
- ¿Las contradicciones detectadas son reales o falsos positivos?
- ¿Los veredictos de consistencia (CONFIRMED/DISPUTED/PARTIAL) son justificados?

### Validación de Calibración
- ¿ECE < 0.3? (Expected Calibration Error)
- **NOTA:** ECE actual es 0.500 (pobre, umbral < 0.3)
- ¿Truth source accuracy > 0.6?
- **NOTA:** Truth source accuracy actual es 0.400 (baja, umbral > 0.6)
- ¿Los bins de alta confianza (0.8-1.0) no están sobreconfiados?
- **NOTA:** Bin 0.8-1.0 tiene accuracy=0.250, error=0.650 (sobreconfianza severa)
- **IMPORTANTE:** Solo hay métricas ANTES de calibración (REAL). NO hay métricas post-calibración porque validation_metrics_post_calibration.json es SIMULADO.

### Validación de Casos Duros
- ¿Screenshot vacío + proceso activo tiene confianza baja (< 0.4)?
- ¿Accessibility tree mismatch degrada confianza?
- ¿Input sin output o output sin input se detecta como contradicción?
- ¿La confianza alta requiere corroboración estructural?
- ¿Los veredictos DISPUTED están justificados?

---

## Limitaciones del Bundle

### Evidencia Runtime Real
- Este bundle contiene evidencia persistida existente, NO nueva evidencia runtime real generada específicamente para esta auditoría
- Los datos son de ejecuciones anteriores del sistema
- No hay ejecución runtime real nueva en este bundle
- **runtime_status: PARTIAL**

### Casos Duros
- Los casos duros identificados están basados en patrones en los datos existentes
- No hay casos duros específicamente generados para esta auditoría
- Veredictos (CONFIRMED/DISPUTED/PARTIAL) son interpretaciones, no hechos brutos
- **validation_status: PARTIAL**

### Calibración
- validation_metrics.json contiene métricas ANTES de calibración (REAL)
- validation_metrics_post_calibration.json NO está incluido porque es SIMULADO
- La calibración real requiere ejecución runtime prolongada para generar nueva evidencia
- **calibration_status: BEFORE_CALIBRATION**

### Correspondencia Temporal
- Screenshots y JSONL están emparejados por timestamp_utc
- No hay garantía de sincronización perfecta
- **validation_status: PARTIAL**

---

## Estado del Bundle

**Estado:** PARTIAL - Evidencia persistida existente, no nueva evidencia runtime real

**Completitud:**
- ✅ Evidencia cruda persistida incluida (REAL - 11 archivos)
- ✅ Evidencia visual incluida (REAL - 21 archivos)
- ✅ Reportes de interpretación generados (PARTIAL - 3 archivos DERIVED_FROM_REAL)
- ✅ Comparaciones crudo vs interpretado generadas (PARTIAL - 2 archivos DERIVED_FROM_REAL)
- ✅ Casos duros identificados (PARTIAL - 1 archivo DERIVED_FROM_REAL)
- ✅ MANIFEST.json con clasificación estricta (METADATA - 1 archivo)
- ✅ README_AUDIT.md con diferenciación clara (METADATA)
- ⚠️ Evidencia runtime real nueva: NO INCLUIDA (limitación de entorno)
- ⚠️ Casos duros específicamente generados: NO INCLUIDOS
- ⚠️ Calibración post-calibración: NO INCLUIDA (validation_metrics_post_calibration.json es SIMULADO)
- ⚠️ HUD snapshots: NO INCLUIDOS
- ⚠️ Correspondencia temporal perfecta: NO GARANTIZADA
- ✅ Evidencia simulada: 0 archivos (NO INCLUIDA)

---

## Marcadores de Validación

Todos los reportes incluyen marcadores de validación:

- **evidence_classification:** "REAL" / "DERIVED_FROM_REAL" / "SIMULATED"
- **data_source:** "runtime_real_persisted" / "derived_from_real" / "simulated"
- **validation_status:** "REAL" / "PARTIAL" / "SIMULATED"
- **runtime_status:** "PARTIAL"
- **calibration_status:** "BEFORE_CALIBRATION"

---

## Contacto y Soporte

Para preguntas sobre este bundle de auditoría, referirse a:
- Documentación de IABV v1.5
- Reportes de calibración y validación previos
- Código fuente en src/iabv_v15/

---

**Última actualización:** 2026-06-18
**Generado por:** Cascade AI Assistant
**Versión:** IABV v1.5
**Estado del bundle:** PARTIAL
**Clasificación:** 33 REAL, 6 PARTIAL, 0 SIMULATED, 1 METADATA
