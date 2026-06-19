# IABV AUDIT BUNDLE - README

**Fecha de generación:** 2026-06-18
**Versión de IABV:** v1.5
**Plataforma:** Windows
**Propósito:** Auditoría externa de interpretación de entorno en runtime real

---

## ¿Qué es este bundle?

Este bundle contiene evidencia completa, trazable y reproducible para auditar si IABV v1.5 interpreta correctamente su entorno en runtime real. Incluye evidencia cruda, evidencia interpretada, comparaciones entre ambas, y casos duros identificados.

---

## Estructura del Bundle

### 1. MANIFEST.json
Lista completa de archivos incluidos con:
- Hashes SHA256 para integridad
- Timestamps UTC
- Tamaños de archivos
- Rutas relativas

**¿Qué representa?** Inventario y trazabilidad de todos los artefactos del bundle.

**¿Cómo usarlo?** Verificar integridad del bundle comparando hashes SHA256.

---

### 2. raw_evidence/ (Evidencia Cruda)

Archivos de datos crudos recolectados en runtime:

- **evidence_records.jsonl** - Registros de evidencia multimodal (visual, process, event)
- **validation_metrics.json** - Métricas de validación antes de calibración
- **validation_metrics_post_calibration.json** - Métricas de validación después de calibración
- **audit_log.jsonl** - Bitácora de auditoría de eventos
- **audit_memory.json** - Memoria de casos confirmados, corregidos y patrones estables
- **ui_knowledge_graph.jsonl** - Grafo de conocimiento de UI
- **navigation_graph.jsonl** - Grafo de navegación
- **navigation_states.jsonl** - Estados de navegación
- **ui_elements_index.jsonl** - Índice de elementos UI

**¿Qué representa?** Evidencia primaria cruda recolectada por el sistema.

**¿Cómo usarlo?** Analizar los datos crudos para entender qué vio el sistema antes de interpretar.

---

### 3. visual_evidence/ (Evidencia Visual)

Screenshots y evidencia visual:

- Screenshots sin recorte (PNG)
- Screenshots del mismo instante que los registros JSONL
- Evidencia visual correspondiente a cada evidence_record

**¿Qué representa?** Evidencia visual cruda que el sistema vio en runtime.

**¿Cómo usarlo?** Comparar screenshots con las interpretaciones en evidence_records.jsonl para validar que el sistema interpretó correctamente lo que vio.

**Correspondencia temporal:** Cada screenshot puede emparejarse con un evidence_record por timestamp_utc.

---

### 4. interpretation/ (Evidencia de Interpretación)

Reportes de interpretación generados por el sistema:

- **interpretation_report.json** - Estadísticas generales de interpretación (truth sources, truth types, distribución de confianza)
- **truth_arbitration_report.json** - Detalle de decisiones de arbitraje de verdad
- **contradiction_report.json** - Análisis de contradicciones detectadas
- **calibration_report.json** - Métricas de calibración (ECE, accuracy por bin, truth source accuracy)

**¿Qué representa?** Evidencia derivada: cómo el sistema interpretó la evidencia cruda.

**¿Cómo usarlo?** Comparar con evidencia cruda para validar que las interpretaciones son consistentes con los datos crudos.

---

### 5. comparisons/ (Comparaciones Crudo vs Interpretado)

Comparaciones entre evidencia cruda y evidencia interpretada:

- **case_comparisons.json** - Comparaciones detalladas caso por caso
- **raw_vs_interpreted_matrix.csv** - Matriz CSV de comparaciones

**¿Qué representa?** Comparación directa entre datos crudos y su interpretación.

**¿Cómo usarlo?** Validar que la interpretación no contradice la evidencia cruda sin explicación. Revisar casos donde hay discrepancias.

---

### 6. hard_cases/ (Casos Duros)

Casos difíciles identificados para auditoría:

- **hard_cases_report.json** - Lista de casos duros con razones

**Casos duros identificados:**
- Screenshot vacío + proceso activo
- Accessibility tree presente + visual ausente
- Input sin output
- Output sin input
- Confianza alta sin corroboración

**¿Qué representa?** Casos donde la interpretación es más difícil o propensa a errores.

**¿Cómo usarlo?** Revisar estos casos específicamente para validar que el sistema manejó correctamente situaciones difíciles.

---

## Flujo de Auditoría Recomendado

### Paso 1: Verificar Integridad
1. Abrir MANIFEST.json
2. Verificar que el número de archivos coincide con lo esperado (37 archivos)
3. Verificar hashes SHA256 si se requiere validación de integridad

### Paso 2: Revisar Evidencia Cruda
1. Abrir raw_evidence/evidence_records.jsonl
2. Revisar algunos registros para entender qué datos crudos se recolectaron
3. Abrir visual_evidence/ y revisar screenshots correspondientes

### Paso 3: Revisar Interpretación
1. Abrir interpretation/interpretation_report.json para ver estadísticas generales
2. Abrir interpretation/truth_arbitration_report.json para ver decisiones de arbitraje
3. Abrir interpretation/contradiction_report.json para ver contradicciones detectadas

### Paso 4: Comparar Crudo vs Interpretado
1. Abrir comparisons/case_comparisons.json
2. Buscar casos donde la interpretación podría contradecir la evidencia cruda
3. Abrir comparisons/raw_vs_interpreted_matrix.csv para análisis rápido

### Paso 5: Revisar Casos Duros
1. Abrir hard_cases/hard_cases_report.json
2. Revisar cada caso duro para validar que el sistema manejó correctamente la situación
3. Verificar que la confianza sea apropiada para cada caso

### Paso 6: Revisar Calibración
1. Abrir interpretation/calibration_report.json
2. Verificar ECE (Expected Calibration Error) - debe ser < 0.3 para calibración aceptable
3. Verificar truth source accuracy - debe ser > 0.6 para aceptable
4. Revisar accuracy por bin de confianza para detectar sobreconfianza

---

## Qué Validar

### Validación de Interpretación Correcta
- ¿La verdad elegida coincide con la evidencia cruda?
- ¿La confianza asignada es apropiada para la evidencia disponible?
- ¿Las contradicciones detectadas son reales o falsos positivos?

### Validación de Calibración
- ¿ECE < 0.3? (Expected Calibration Error)
- ¿Truth source accuracy > 0.6?
- ¿Los bins de alta confianza (0.8-1.0) no están sobreconfiados?
- ¿La confianza refleja mejor la evidencia real después de la calibración?

### Validación de Casos Duros
- ¿Screenshot vacío + proceso activo tiene confianza baja (< 0.4)?
- ¿Accessibility tree mismatch degrada confianza?
- ¿Input sin output o output sin input se detecta como contradicción?
- ¿La confianza alta requiere corroboración estructural?

---

## Limitaciones del Bundle

### Evidencia Runtime Real
- Este bundle contiene evidencia persistida existente, no nueva evidencia runtime real generada específicamente para esta auditoría
- Los datos son de ejecuciones anteriores del sistema
- No hay ejecución runtime real nueva en este bundle

### Calibración
- validation_metrics_post_calibration.json contiene métricas simuladas, no de runtime real
- La calibración real requiere ejecución runtime prolongada para generar nueva evidencia

### Casos Duros
- Los casos duros identificados están basados en patrones en los datos existentes
- No hay casos duros específicamente generados para esta auditoría

---

## Estado del Bundle

**Estado:** PARCIAL - Evidencia persistida existente, no nueva evidencia runtime real

**Completitud:**
- ✅ Evidencia cruda persistida incluida
- ✅ Evidencia visual incluida
- ✅ Reportes de interpretación generados
- ✅ Comparaciones crudo vs interpretado generadas
- ✅ Casos duros identificados
- ✅ MANIFEST.json con hashes
- ⚠️ Evidencia runtime real nueva: NO INCLUIDA (limitación de entorno)
- ⚠️ Casos duros específicamente generados: NO INCLUIDOS
- ⚠️ Calibración post-calibración: SIMULADA, no runtime real

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
