# Análisis de Correlación Entre EvidenceRecord y SurfaceObservation

**Fecha:** 2026-06-18
**Objetivo:** Documentar el problema de correlación entre capa puntual y capa continua

---

## 1. Problema Identificado

**Evidencia cruda (evidence_records.jsonl):**
- task_id: "runtime_real_verification", "prompt_ownership_verification"
- evidence_hash: "4f4ab048eea6cf7195b7cdb85e69acc4f564afdeebda61a5c7cba657cb05e435", "9ef10bce972692e972fb591f20a348143cc43fec9a7069a231ce930c670881d0"
- surface_id: "" (vacío en la mayoría de registros)
- truth_source: "unknown", "screenshot", "process"
- truth_confidence: 0.0, 0.95, 1.0

**Observaciones de superficie (surface_observations.jsonl):**
- task_id: "hybrid_verification"
- evidence_hash: "cd6e1f22ad6149d57d49a0a8efa5ea9fbf1e1e174fc300821847cf2707a5ce12", "9577d4c4f3b47077cd107e69c53d2419b3b6b9adfae2fef0c05819eb53526d75", etc.
- surface_id: "" (vacío)
- truth_source: "process"
- truth_confidence: 1.0

**Problema:** Los task_id NO coinciden entre archivos, impidiendo correlación directa.

---

## 2. Causa Raíz

**Capa puntual (MultimodalPerceptionService):**
- Genera EvidenceRecords con task_id proveniente de la tarea específica ("runtime_real_verification", "prompt_ownership_verification")
- No comparte un identificador común con la capa continua

**Capa continua (RuntimePerceptionAndVerificationService):**
- Genera SurfaceObservations con task_id proveniente de la verificación híbrida ("hybrid_verification")
- No recibe el task_id de la capa puntual

**Resultado:** No hay trazabilidad unificada entre capas. No se puede reconstruir la cadena completa: evento → evidencia → interpretación → contradicción → calibración.

---

## 3. Solución Propuesta (Sin Modificar Base Estable)

**Opción A: Identificador Estable Compartido (session_id)**
- Crear un session_id único por sesión de verificación
- Pasar session_id entre capa puntual y capa continua
- Usar session_id como identificador de correlación en ambos archivos
- Requiere modificación de: MultimodalPerceptionService, RuntimePerceptionAndVerificationService, EvidenceRecorder

**Opción B: Correlación Post-Hoc por Timestamp**
- Usar timestamp_utc como identificador de correlación
- Correlacionar registros por proximidad temporal (±5 segundos)
- Requiere lógica de correlación post-procesamiento
- No requiere modificación de código base

**Opción C: Correlación por surface_id + process_id**
- Usar surface_id + process_id como identificador compuesto
- Requiere que ambos archivos generen surface_id consistente
- Requiere modificación de código base

---

## 4. Recomendación

**Dado que la base está congelada, recomiendo Opción B: Correlación Post-Hoc por Timestamp**

Esta opción:
- NO requiere modificación de código base
- Permite correlación entre archivos existentes
- Es implementable en script post-procesamiento
- Tiene limitaciones (ventanas de tiempo, ambigüedad en casos de alta frecuencia)

**Implementación propuesta:**
```python
def correlate_evidence_by_timestamp(
    evidence_records: list[dict],
    surface_observations: list[dict],
    time_window_seconds: int = 5,
) -> dict[str, list[str]]:
    """Correlaciona EvidenceRecords con SurfaceObservations por timestamp."""
    correlations = {}
    
    for obs in surface_observations:
        obs_time = datetime.fromisoformat(obs["timestamp_utc"])
        obs_id = obs["observation_id"]
        
        correlated_evidence = []
        for record in evidence_records:
            record_time = datetime.fromisoformat(record["timestamp_utc"])
            time_diff = abs((obs_time - record_time).total_seconds())
            
            if time_diff <= time_window_seconds:
                correlated_evidence.append(record["evidence_id"])
        
        if correlated_evidence:
            correlations[obs_id] = correlated_evidence
    
    return correlations
```

---

## 5. Estado Actual

**Correlación:** PARTIAL - No hay correlación directa por task_id, pero se puede correlacionar post-hoc por timestamp

**Trazabilidad:** PARTIAL - Cadena de trazabilidad existe pero no está completamente conectada

**Impacto:** MEDIO - Impide auditoría completa pero no impide funcionamiento del sistema

---

## 6. Conclusión

La correlación entre EvidenceRecord y SurfaceObservation es PARTIAL debido a task_id inconsistentes. La solución recomendada es correlación post-hoc por timestamp, que NO requiere modificación de código base y permite auditoría completa de datos existentes.
