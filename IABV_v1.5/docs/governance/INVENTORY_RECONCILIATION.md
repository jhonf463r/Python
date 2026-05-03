# IABV v1.5 — Nota de Reconciliación de Inventario

**Fecha:** 2026-05-03  
**Sesión:** Devin session `2b36b4fec0f84edb872a43580eb90f4f`

---

## Por qué los conteos no coinciden entre reportes

Los diferentes reportes y snapshots miden **cosas distintas**. Esta nota
aclara cada fuente de conteo para que no se confundan.

---

## Fuentes de conteo y qué mide cada una

### 1. Test suite (`pytest`)
| Métrica | Valor | Qué mide |
|---|---|---|
| passed | 2391 | Tests que ejecutaron y pasaron |
| failed | 29 | Tests que ejecutaron y fallaron (pre-existentes) |
| skipped | 25 | Tests que se omitieron por condición (`skipIf`, etc.) |
| **Total test items** | **2445** | Total de items recolectados por pytest |

**Nota:** Los 29 fallos son pre-existentes y no fueron introducidos en esta
sesión. Ver UNRESOLVED U9 para el desglose por módulo.

### 2. Source discovery (`find src/ -name "*.py"`)
| Métrica | Valor | Qué mide |
|---|---|---|
| Archivos Python en src/ | 240 | Módulos fuente del proyecto |
| Archivos Python en tests/ | 193 | Archivos de test |
| **Total archivos Python** | **433** | Todo el código Python del proyecto |

**No confundir:** 193 archivos de test ≠ 2445 tests. Un archivo de test
puede contener múltiples funciones/tests.

### 3. Backlog priorizado (`docs/governance/BACKLOG_PRIORIZADO.md`)
| Métrica | Valor | Qué mide |
|---|---|---|
| Items totales | 41 | Tareas técnicas identificadas |
| Pendientes | 25 | Tareas no empezadas |
| En progreso | 10 | Tareas en curso |
| Completados | 6 | Tareas terminadas |

**Clasificación por severidad:**
- Critical: 6
- High: 16
- Medium: 14
- Low: 5

**No confundir:** 41 items de backlog ≠ tests fallidos. Son categorías
independientes. Un item de backlog puede no tener test asociado y viceversa.

### 4. Control Master (`data/evolution/control_master/latest.json`)
| Métrica | Valor | Qué mide |
|---|---|---|
| objectives (active) | 4 | Objetivos de evolución vigentes |
| unresolved_items | 10 | Items marcados UNRESOLVED |
| tests_state | 2391/29/25 | Reflejo del estado de pytest |

### 5. UNRESOLVED Registry (`docs/governance/UNRESOLVED_REGISTRY.md`)
| Métrica | Valor | Qué mide |
|---|---|---|
| Items U1-U10 | 10 | Cosas que no pueden confirmarse con evidencia |

---

## Tabla de reconciliación cruzada

| Pregunta | Respuesta |
|---|---|
| ¿Por qué hay 2391 tests pero solo 193 archivos? | Un archivo de test contiene múltiples funciones de test (promedio ~12.7 tests/archivo) |
| ¿Por qué el backlog dice 25 pendientes y los tests dicen 25 skipped? | **Coincidencia numérica.** Son métricas independientes que no se refieren a lo mismo |
| ¿Por qué 29 failed en tests pero 10 UNRESOLVED? | UNRESOLVED son dudas arquitectónicas. Failed tests son fallos de ejecución. Solo U9 los conecta |
| ¿El snapshot de tests cambió entre sesiones? | No. El baseline se midió antes de tocar código (2391/29/25) y se confirmó después del lazy init |
| ¿Hubo lectura parcial del repo? | No. El `find` recorrió todo `src/` y `tests/`. Los 240+193 archivos son exhaustivos |
| ¿Los 41 items de backlog incluyen los 29 tests fallidos? | No directamente. U9 registra los 29 fallos como un solo UNRESOLVED. El backlog tiene items de diseño/implementación |

---

## Conclusión

Los conteos no coinciden **porque miden dimensiones distintas** del proyecto:
- **Tests:** cobertura funcional (2445 items)
- **Source:** tamaño del código (433 archivos)
- **Backlog:** deuda técnica planificada (41 tareas)
- **UNRESOLVED:** dudas sin evidencia (10 items)
- **Control Master:** estado consolidado de gobierno

No hubo lectura parcial ni snapshot distinto. Cada fuente es correcta
dentro de su dominio.
