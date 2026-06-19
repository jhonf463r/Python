# Consolidación de Verdad Estructural Formal

**Fecha:** 2026-06-18
**Objetivo:** Consolidar verdad estructural formal sin modificar base estable

---

## 1. Estado Actual

**StructuralTruthService:** Creado en sesión anterior como capa explícita de verdad estructural formal.
**Integración con TruthArbitrator:** NO integrada (base estable congelada según AUDITORIA_VIVA_SALIDA_OBLIGATORIA.md).
**Ubicación:** `C:\Python\IABV_v1.5\src\iabv_v15\services\perception\structural_truth_service.py`

---

## 2. Representación de Verdad Estructural

**Hash de código fuente relevante:**
- Calcula SHA256 de archivos Python relevantes (multimodal_perception_service.py, truth_arbitrator.py, signal_fusion_core.py, evidence_recorder.py)
- Hash combinado de todos los archivos
- Método: `compute_source_code_hash(source_dir: Path) -> str`

**Layout esperado:**
- Diccionario de element_id -> geometry_expected
- Versión de layout
- Representa geometría prevista de elementos UI

**Runtime object tree:**
- Diccionario de element_id -> properties
- Hash del runtime object tree
- Método: `compute_runtime_object_tree_hash(runtime_tree: dict[str, Any]) -> str`

**Anchors:**
- Diccionario de anchor_id -> properties
- Puntos de anclaje estables (botones, campos, menús)

**Relaciones padre/hijo:**
- Diccionario de parent_id -> [child_ids]
- Jerarquía estructural (containers → elements)

**Versión/hash de referencia:**
- Hash combinado de todas las propiedades estructurales
- Timestamp de referencia
- Método: `update_reference_hash() -> str`

---

## 3. Cruce con Otros Tipos de Verdad

**Verdad visual:**
- Se cruza con screenshot, OCR, accessibility tree
- Detecta contradicciones: runtime object tree ≠ layout esperado
- Método: `detect_structural_contradictions(visual_signal, process_signal) -> list[str]`

**Verdad operativa:**
- Se cruza con process signal (PID, HWND, foco)
- Detecta contradicciones: proceso ≠ código esperado
- Método: `detect_structural_contradictions(visual_signal, process_signal) -> list[str]`

**Verdad persistente:**
- Se cruza con evidencia persistida
- Detecta contradicciones: anchors no encontrados en runtime
- Método: `detect_structural_contradictions(visual_signal, process_signal) -> list[str]`

---

## 4. Degradación de Confianza

**Prioridad de calibración:** 0.7 (no absoluto)

**Reglas de degradación:**
- Si runtime object tree ≠ layout esperado: penalty 0.1
- Si proceso ≠ código esperado: penalty 0.1
- Si anchors no encontrados en runtime: penalty 0.1
- Si relaciones padre/hijo rotas: penalty 0.1
- Penalty total: 0.1 × número de contradicciones

**Degradation level:**
- confidence ≥ 0.6: "low"
- confidence ≥ 0.4: "medium"
- confidence < 0.4: "high"

**Método:** `degrade_confidence_if_needed() -> float`

---

## 5. Nunca Domina por Sí Sola

**Prioridad:** 0.7 (entre PERSISTENT=0.8 y OPERATIONAL=1.0)

**Regla:** La verdad estructural es un prior de calibración, no una verdad absoluta. Si el runtime contradice el código, el runtime tiene prioridad.

**Ejemplo:**
- Código espera ventana "Devin - Settings"
- Runtime muestra ventana "Chrome - Google"
- Verdad estructural degrada confianza, pero no domina
- TruthArbitrator elige verdad operativa (runtime) sobre estructural

---

## 6. Integración Futura (Sin Modificar Base Estable)

**Requiere modificación de TruthArbitrator (base estable congelada):**

1. Añadir TruthSource.STRUCTURAL con prioridad 0.7
2. Añadir TruthType.STRUCTURAL con prioridad 0.7
3. Integrar en TruthArbitrator._determine_truth_source()
4. Añadir detección de contradicciones estructurales
5. Añadir degradación de confianza por contradicciones estructurales

**NO implementado actualmente debido a:**
- "La arquitectura base ya está congelada"
- "No quiero más capas nuevas ni refactors grandes"
- "No rehagas la arquitectura base"

---

## 7. Estado Final

**Verdad estructural formal:** CREADA como capa explícita
**Integración con TruthArbitrator:** NO integrada (base estable congelada)
**Funcionalidad:** Disponible para uso post-hoc o integración futura
**Documentación:** Completa en structural_truth_service.py y este documento

**Conclusión:** La verdad estructural formal está consolidada como capa explícita, pero NO está integrada con TruthArbitrator debido a la base estable congelada. Está disponible para uso post-hoc (análisis offline) o integración futura cuando se permita modificar la base estable.
