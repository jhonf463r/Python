# KD-SYNAPTIC-NONE-LIST-CONTRACT: Knowledge Delta - Synaptic Candidate None/[] Contract Fix

## Contexto
Este documento registra el fix del contrato None/[] en la resolución de candidatos de routing sináptico.
Baseline: `a2129c545ebf65c208a7c53a317c4ebd08c7cef0`
Branch: `p0b-first-causal-break`

## Previous Model

### Hipótesis Anterior
El código en `tool_teach_service.py` línea 1341:
```python
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds')
```

Debería distinguir entre:
- Ninguna clave suministrada → `None` (usar registry completo)
- Lista vacía explícita → `[]` (ningún candidato)
- Lista no vacía → lista exacta

### Evidence del Defecto
Claude Sonet observó que el uso de `or` causa una colisión semántica:
```python
goal_parameters = {"candidate_assistant_kinds": []}
# [] es falsy en Python
# Por tanto, el 'or' descarta [] y busca la segunda clave
# Si la segunda clave no existe: raw_candidates = None
# Esto viola el contrato: explicit [] → None → registry completo
# Debería ser: explicit [] → [] → ningún candidato
```

## Root Cause

### Por qué `[]` es destruido por truthiness
Python evalúa `[]` como `falsy`. Cuando se usa `or`:
```python
[] or None → None  # [] es falsy, se evalúa None
```

Por tanto, cuando `goal_parameters = {"candidate_assistant_kinds": []}`:
```python
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds')
# = [] or None
# = None
```

Esto viola el contrato operacional de `SynapticRouter`:
- `None` → usar todos los candidatos del registry
- `[]` → ningún candidato
- lista no vacía → exactamente esos candidatos

## Intervention

### Cambio Exacto
```python
# ANTES
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds')

# DESPUÉS
# Check presence of keys, not truthiness, to preserve explicit empty list
if 'candidate_assistant_kinds' in goal_parameters:
    raw_candidates = goal_parameters['candidate_assistant_kinds']
elif 'allowed_assistant_kinds' in goal_parameters:
    raw_candidates = goal_parameters['allowed_assistant_kinds']
else:
    raw_candidates = None
```

### Semántica Conservada
- Ninguna clave suministrada → `None` (usar registry completo)
- Lista vacía explícita → `[]` (ningún candidato)
- Lista no vacía → lista exacta
- Fallback a `allowed_assistant_kinds` cuando `candidate_assistant_kinds` no está presente

## Evidence

### PRE-FIX Result
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5 && PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src /c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_candidate_none_list_contract.py::test_synaptic_candidate_empty_list_truthiness_bug -v
```
**Resultado:** FAILED - Expected [], got None (truthiness destroyed explicit empty list)

### POST-FIX Result
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5 && PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src /c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_candidate_none_list_contract.py -v
```
**Resultado:** 4 passed

### Regression
- test_synaptic_router.py: 39 passed
- test_p0_b_external_action_authorization.py: 14 passed

## Semantic Matrix

| Input | Expected | Observed pre-fix | Observed post-fix |
|-------|----------|------------------|-------------------|
| `{}` | `None` | `None` | `None` |
| `{"candidate_assistant_kinds": []}` | `[]` | `None` (BUG) | `[]` (FIXED) |
| `{"candidate_assistant_kinds": ["codex", "windsurf"]}` | `["codex", "windsurf"]` | `["codex", "windsurf"]` | `["codex", "windsurf"]` |
| `{"allowed_assistant_kinds": ["codex"]}` | `["codex"]` | `["codex"]` | `["codex"]` |

## Epistemic Status

**implemented:** YES
**proven:** YES (pre-fix failed + post-fix passed)
**observed:** YES (test atraviesa código real de producción)
**caused:** YES (cambio de truthiness a presence check causó corrección)

## ΔK

### Nuevo Conocimiento
- El uso de `or` para resolver claves de candidatos destruye listas vacías explícitas
- La distinción entre "no suministrado" vs "explícitamente vacío" requiere checking de presencia de clave, no truthiness
- El contrato `None/[]` de SynapticRouter depende de esta distinción

## Δπ

### Cambio de Política
- Resolución de candidatos ahora usa checking de presencia de clave, no truthiness
- `[]` explícito se preserva como "ningún candidato"
- `None` se usa solo cuando ninguna clave está presente

## ΔB

**NOT MEASURED** (falta evidencia de routing completo)

## ΔY

**NOT MEASURED** (falta medición de outcome real)

## Next Causal Edge

`correct candidate resolution` → `SynapticRouter.decide()`

Este edge ahora puede ser verificado correctamente porque el contrato `None/[]` está preservado.

## Git Provenance

**Commit:** (pendiente)
**Remote branch:** `p0b-first-causal-break`
**Remote HEAD:** (pendiente)

## Conclusión

**Status final:** SUCCESS (pre-fix test failed + post-fix same test passed + regression tests passed)

El contrato `None/[]` en la resolución de candidatos ha sido corregido. Ahora `[]` explícito se preserva como "ningún candidato" en lugar de ser destruido por truthiness.

**NO declaro inflection completa.** Solo se ha corregido el contrato de entrada de candidatos. La verificación de routing completo es el siguiente edge.
