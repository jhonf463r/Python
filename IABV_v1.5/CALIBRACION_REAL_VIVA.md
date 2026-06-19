# Calibración Real (Evidencia Persistida)

**Fecha:** 2026-06-18
**Objetivo:** Usar datos reales para reportar métricas de calibración

---

## Métricas Reales (calibration_report.json)

**Fuente:** calibration_report.json (IABV_FORENSIC_AUDIT_BUNDLE/interpretation/calibration_report.json)
**Clasificación:** REAL (no simulado)
**Data source:** runtime_real_persisted
**Validation status:** REAL
**Calibration status:** BEFORE_CALIBRATION

---

## Expected Calibration Error (ECE)

**ECE real:** 0.5 (50%)

**Umbral de referencia:** < 0.3 (30%)

**Estado:** ❌ POR ENCIMA DEL UMBRAL (0.5 > 0.3)

**Sobreconfianza:** SÍ, el sistema está significativamente sobreconfiado

**Conclusión:** La calibración es POBRE. El sistema está significativamente sobreconfiado en sus predicciones.

---

## Truth Source Accuracy

**Truth source accuracy real:** 0.400 (40%)

**Por fuente:**
- process: 0.333 (33.3%)
- screenshot: 0.333 (33.3%)
- hwnd: 1.0 (100%)

**Umbral de referencia:** > 0.6 (60%)

**Estado:** ❌ POR DEBAJO DEL UMBRAL (0.400 < 0.6)

**Sobreconfianza por fuente:**
- process: SÍ, sobreconfiado (33.3% accuracy)
- screenshot: SÍ, sobreconfiado (33.3% accuracy)
- hwnd: NO, accuracy perfecta (100%) pero muestra pequeña

**Conclusión:** La precisión de las fuentes de verdad es BAJA. Solo HWND tiene precisión perfecta, pero process y screenshot tienen precisión pobre.

---

## Detection Metrics

**True Positives (TP):** 6
**False Positives (FP):** 4
**True Negatives (TN):** 8
**False Negatives (FN):** 4

**Precision:** TP / (TP + FP) = 6 / (6 + 4) = 0.6 (60%)
**Recall:** TP / (TP + FN) = 6 / (6 + 4) = 0.6 (60%)
**F1 Score:** 2 * (Precision * Recall) / (Precision + Recall) = 0.6 (60%)

**Umbral de referencia:** > 0.7 (70%)

**Estado:** ❌ POR DEBAJO DEL UMBRAL (0.6 < 0.7)

**Conclusión:** Precision y recall son MODERADOS (60%). Hay falsos positivos y fals negativos significativos.

---

## Contradiction Rate

**Total evidence count:** 34
**Contradiction count:** 16
**Visual vs operational contradiction count:** 8

**Contradiction rate:** 16 / 34 = 0.471 (47.1%)

**Umbral de referencia:** < 0.3 (30%)

**Estado:** ❌ POR ENCIMA DEL UMBRAL (0.471 > 0.3)

**Sobreconfianza:** SÍ, alta tasa de contradicciones indica sobreconfianza

**Conclusión:** La tasa de contradicciones es ALTA (47.1%). Casi la mitad de las evidencias tienen contradicciones.

---

## Accuracy por Bins de Confianza

**Bin 0.0-0.2:** accuracy = 0.0 (0%)
**Bin 0.2-0.4:** accuracy = 0.0 (0%)
**Bin 0.4-0.6:** accuracy = 1.0 (100%)
**Bin 0.6-0.8:** accuracy = 0.333 (33.3%)
**Bin 0.8-1.0:** accuracy = 0.25 (25%)

**Sobreconfianza por bin:**
- **Bin 0.8-1.0:** SÍ, sobreconfianza SEVERA (confidence > 0.8, accuracy = 0.25)
- **Bin 0.6-0.8:** SÍ, sobreconfianza MODERADA (confidence > 0.6, accuracy = 0.333)
- **Bin 0.4-0.6:** NO, accuracy perfecta (1.0) pero solo 2 casos
- **Bins 0.0-0.4:** NO APLICABLE (ningún caso en estos bins)

**Error de calibración en bin 0.8-1.0:** 0.8 - 0.25 = 0.55 (55%)

**Conclusión:** El sistema está severamente sobreconfiado en bins altos. Cuando asigna confianza > 0.8, acierta solo el 25% de las veces.

---

## Cobertura de Eventos Persistentes

**Total evidence count:** 34
**Audit log events:** 21 (audit_log.jsonl)

**Cobertura:** 21 / 34 = 0.618 (61.8%)

**Conclusión:** La cobertura de eventos persistentes es MODERADA (61.8%). No todos los eventos se persisten en la bitácora de auditoría.

---

## Comparación contra Umbrales

| Métrica | Valor Real | Umbral | Estado | Sobreconfianza |
|---------|------------|--------|--------|----------------|
| ECE | 0.5 | < 0.3 | ❌ Por encima | SÍ |
| Truth source accuracy | 0.400 | > 0.6 | ❌ Por debajo | SÍ (process, screenshot) |
| Precision | 0.6 | > 0.7 | ❌ Por debajo | SÍ |
| Recall | 0.6 | > 0.7 | ❌ Por debajo | SÍ |
| Contradiction rate | 0.471 | < 0.3 | ❌ Por encima | SÍ |
| Accuracy bin 0.8-1.0 | 0.25 | > 0.7 | ❌ Por debajo | SÍ (SEVERA) |
| Accuracy bin 0.6-0.8 | 0.333 | > 0.7 | ❌ Por debajo | SÍ (MODERADA) |

---

## Conclusión de Sobreconfianza

**Sigue habiendo sobreconfianza:** SÍ

**En qué bins:**
- Bin 0.8-1.0: sobreconfianza SEVERA (accuracy = 0.25)
- Bin 0.6-0.8: sobreconfianza MODERADA (accuracy = 0.333)

**En qué fuentes:**
- Process: sobreconfianza (accuracy = 0.333)
- Screenshot: sobreconfianza (accuracy = 0.333)
- HWND: NO sobreconfianza (accuracy = 1.0)

**Qué casos duros siguen fallando:**
- Ghost window (confidence = 0.95, debería ser < 0.4)
- Input/output mismatch (confidence = 1.0, debería ser < 0.4)
- Screenshot vacío + proceso activo (confidence = 0.3, debería ser < 0.2)

---

## Estado General de Calibración

**Estado:** POBRE

**Sin maquillaje:** El sistema está significativamente sobreconfiado, tiene baja precisión en fuentes de verdad, alta tasa de contradicciones, y severa sobreconfianza en bins altos. No cumple con ninguno de los umbrales de referencia.
