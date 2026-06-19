# Análisis de Re-calibración Real con Evidencia Real

**Fecha:** 2026-06-18
**Objetivo:** Reportar métricas reales de calibración sin simulación

---

## 1. Métricas Reales (calibration_report.json)

**Fuente:** calibration_report.json (IABV_FORENSIC_AUDIT_BUNDLE/interpretation/calibration_report.json)
**Clasificación:** REAL (no simulado)
**Data source:** runtime_real_persisted
**Validation status:** REAL
**Calibration status:** BEFORE_CALIBRATION
**Nota:** "Métricas de calibración ANTES de ajustes (runtime real persistido). NO incluye métricas post-calibración simuladas."

---

## 2. Expected Calibration Error (ECE)

**ECE real:** 0.5 (50%)

**Umbral de referencia:** < 0.3 (30%)

**Estado:** ❌ POR ENCIMA DEL UMBRAL (0.5 > 0.3)

**Conclusión:** La calibración es POBRE. El sistema está significativamente sobreconfiado en sus predicciones.

---

## 3. Truth Source Accuracy

**Truth source accuracy real:** 0.400 (40%)

**Por fuente:**
- process: 0.333 (33.3%)
- screenshot: 0.333 (33.3%)
- hwnd: 1.0 (100%)

**Umbral de referencia:** > 0.6 (60%)

**Estado:** ❌ POR DEBAJO DEL UMBRAL (0.400 < 0.6)

**Conclusión:** La precisión de las fuentes de verdad es BAJA. Solo HWND tiene precisión perfecta, pero process y screenshot tienen precisión pobre.

---

## 4. Detection Metrics

**True Positives (TP):** 6
**False Positives (FP):** 4
**True Negatives (TN):** 8
**False Negatives (FN):** 4

**Precision:** TP / (TP + FP) = 6 / (6 + 4) = 0.6 (60%)
**Recall:** TP / (TP + FN) = 6 / (6 + 4) = 0.6 (60%)
**F1 Score:** 2 * (Precision * Recall) / (Precision + Recall) = 0.6 (60%)

**Conclusión:** Precision y recall son MODERADOS (60%). Hay falsos positivos y fals negativos significativos.

---

## 5. Contradiction Rate

**Total evidence count:** 34
**Contradiction count:** 16
**Visual vs operational contradiction count:** 8

**Contradiction rate:** 16 / 34 = 0.471 (47.1%)

**Conclusión:** La tasa de contradicciones es ALTA (47.1%). Casi la mitad de las evidencias tienen contradicciones.

---

## 6. Accuracy por Bins de Confianza

**Bin 0.0-0.2:** accuracy = 0.0 (0%)
**Bin 0.2-0.4:** accuracy = 0.0 (0%)
**Bin 0.4-0.6:** accuracy = 1.0 (100%)
**Bin 0.6-0.8:** accuracy = 0.333 (33.3%)
**Bin 0.8-1.0:** accuracy = 0.25 (25%)

**Análisis:**
- **Bins bajos (0.0-0.4):** accuracy = 0.0 (ningún caso en estos bins)
- **Bin medio (0.4-0.6):** accuracy = 1.0 (perfecto, pero solo 2 casos)
- **Bin alto-medio (0.6-0.8):** accuracy = 0.333 (pobre, 6 casos)
- **Bin alto (0.8-1.0):** accuracy = 0.25 (muy pobre, 8 casos)

**Sobreconfianza severa en bins altos:**
- En bin 0.8-1.0, el sistema asigna confianza > 0.8 pero accuracy es solo 0.25
- Error de calibración en bin 0.8-1.0: 0.8 - 0.25 = 0.55 (55%)

**Conclusión:** El sistema está severamente sobreconfiado en bins altos. Cuando asigna confianza > 0.8, acierta solo el 25% de las veces.

---

## 7. Cobertura de Eventos Persistentes

**Total evidence count:** 34
**Audit log events:** 21 (audit_log.jsonl)

**Cobertura:** 21 / 34 = 0.618 (61.8%)

**Conclusión:** La cobertura de eventos persistentes es MODERADA (61.8%). No todos los eventos se persisten en la bitácora de auditoría.

---

## 8. Comparación contra Umbrales de Referencia

| Métrica | Valor Real | Umbral | Estado |
|---------|------------|--------|--------|
| ECE | 0.5 | < 0.3 | ❌ Por encima |
| Truth source accuracy | 0.400 | > 0.6 | ❌ Por debajo |
| Precision | 0.6 | > 0.7 | ❌ Por debajo |
| Recall | 0.6 | > 0.7 | ❌ Por debajo |
| Contradiction rate | 0.471 | < 0.3 | ❌ Por encima |
| Accuracy bin 0.8-1.0 | 0.25 | > 0.7 | ❌ Por debajo |

---

## 9. Conclusión Honestas

**ECE:** 0.5 > 0.3 (umbral) → La calibración es POBRE
**Truth source accuracy:** 0.400 < 0.6 (umbral) → La precisión de fuentes es BAJA
**Precision/Recall:** 0.6 < 0.7 (umbral) → La detección es MODERADA
**Contradiction rate:** 0.471 > 0.3 (umbral) → La tasa de contradicciones es ALTA
**Accuracy bin 0.8-1.0:** 0.25 < 0.7 (umbral) → Sobreconfianza severa en bins altos

**Estado general de calibración:** POBRE

**Sin maquillaje:** El sistema está significativamente sobreconfiado, tiene baja precisión en fuentes de verdad, alta tasa de contradicciones, y severa sobreconfianza en bins altos. No cumple con ninguno de los umbrales de referencia.

---

## 10. Causa Raíz de Calibración Pobre

**Sobreconfianza en casos duros:**
- Screenshot vacío + proceso activo → confidence = 0.3 (ajustado de 0.6, pero aún alto)
- Ghost window → confidence = 0.95 (debería ser < 0.4)
- Input/output mismatch → confidence = 1.0 (debería ser < 0.4)

**Truth source accuracy baja:**
- Process: 33.3% (solo 4 de 12 correctos)
- Screenshot: 33.3% (solo 2 de 6 correctos)
- HWND: 100% (2 de 2 correctos, pero muestra pequeña)

**Contradicciones frecuentes:**
- 47.1% de evidencias tienen contradicciones
- 8 contradicciones visuales vs operativas
- 22 contradicciones input/output
- 8 contradicciones accessibility

**Penalty por contradicción insuficiente:**
- Penalty actual: 0.3 por contradicción
- Penalty insuficiente para reducir sobreconfianza en bins altos

---

## 11. Recomendaciones de Calibración (Sin Modificar Base Estable)

**Documentar ajustes recomendados:**
1. Aumentar penalty por contradicción de 0.3 a 0.5
2. Degradar confianza en casos duros (ghost window, input/output mismatch) a < 0.4
3. Ajustar truth source priority basado en accuracy real (process=0.33, screenshot=0.33, hwnd=1.0)
4. Implementar gating más agresivo para screenshot vacío (confidence < 0.2)
5. Implementar gating para accessibility/process mismatch (confidence < 0.4)

**Nota:** Estos ajustes requieren modificación de TruthArbitrator (base estable congelada). No se pueden implementar sin reabrir la base.
