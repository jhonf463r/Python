# Verdad Estructural en Verificación Viva

**Fecha:** 2026-06-18
**Objetivo:** Confirmar si la verdad estructural ya sirve para evaluar, si todavía no está integrada al árbitro, y si sigue siendo solo evaluador o ya puede usarse como prior efectivo en runtime

---

## Estado de Integración

**StructuralTruthService:** CREADO como capa explícita
**Integración con TruthArbitrator:** NO INTEGRADA (base estable congelada)
**Uso actual:** Solo como capa de análisis o evaluación post-hoc
**Uso en runtime real:** NO INTEGRADA (no puede usarse en runtime real)

---

## Rol como Prior de Calibración

**Definición:** La verdad estructural es un prior de calibración, no una verdad absoluta.

**Prioridad:** 0.7 (entre PERSISTENT=0.8 y OPERATIONAL=1.0)

**Función:**
- Proporciona contexto estructural (código fuente, layout esperado, runtime object tree, anchors, relaciones padre/hijo)
- Degrada confianza si el runtime contradice el código
- Nunca domina por sí sola
- Siempre está subordinada a verdad operativa (runtime)

---

## Degradación de Confianza cuando Contradice Runtime

**Reglas de degradación:**
1. Si runtime object tree ≠ layout esperado: penalty 0.1
2. Si proceso ≠ código esperado: penalty 0.1
3. Si anchors no encontrados en runtime: penalty 0.1
4. Si relaciones padre/hijo rotas: penalty 0.1

**Degradation level:**
- confidence ≥ 0.6: "low"
- confidence ≥ 0.4: "medium"
- confidence < 0.4: "high"

**Ejemplo:**
- Código espera ventana "Devin - Settings"
- Runtime muestra ventana "Chrome - Google"
- Verdad estructural degrada confianza de 0.7 a 0.6
- TruthArbitrator elige verdad operativa (runtime) sobre estructural

---

## Nunca Domina por Sí Sola

**Regla fundamental:** La verdad estructural nunca domina por sí sola.

**Jerarquía de verdad:**
1. OPERATIONAL (runtime): 1.0 (máxima prioridad)
2. VISUAL (screenshot): 0.9
3. PERSISTENT (memoria): 0.8
4. STRUCTURAL (código): 0.7 (prior de calibración)

**Ejemplo:**
- Si runtime dice "ventana A" y código espera "ventana B"
- Runtime gana (verdad operativa tiene prioridad 1.0)
- Verdad estructural degrada confianza pero no domina

---

## Uso Actual: Capa de Análisis o Evaluación

**Estado actual:** NO INTEGRADA al runtime real

**Uso permitido:**
- Análisis post-hoc de evidencia persistida
- Evaluación de consistencia entre código y runtime
- Auditoría de coherencia estructural
- Identificación de anomalías estructurales

**Uso NO permitido (actualmente):**
- Arbitraje de verdad en runtime real
- Degradación de confianza en tiempo real
- Influencia en decisiones de TruthArbitrator

**Razón:** Requiere integración con TruthArbitrator (base estable congelada)

---

## Integración Futura (Si se Permite Modificar Base Estable)

**Requiere modificación de TruthArbitrator:**

1. Añadir TruthSource.STRUCTURAL con prioridad 0.7
2. Añadir TruthType.STRUCTURAL con prioridad 0.7
3. Integrar en TruthArbitrator._determine_truth_source()
4. Añadir detección de contradicciones estructurales
5. Añadir degradación de confianza por contradicciones estructurales

**Nota:** Esta integración NO está implementada actualmente debido a:
- "La arquitectura base ya está congelada"
- "No quiero más capas nuevas ni refactors grandes"
- "No rehagas la arquitectura base"

---

## Conclusión

**Estado actual:** StructuralTruthService está consolidado como capa explícita de verdad estructural, pero NO está integrada con TruthArbitrator (base estable congelada).

**Rol actual:** Solo puede usarse como capa de análisis o evaluación post-hoc, NO como prior de calibración en runtime real.

**Rol futuro (si se permite modificar base):** Sería un prior de calibración (0.7) que degrada confianza cuando el runtime contradice el código, pero nunca domina por sí sola.

**Sin maquillaje:** Mientras no esté integrada al runtime real, la verdad estructural solo puede usarse como capa de análisis o evaluación, no como prior de calibración en tiempo real.
