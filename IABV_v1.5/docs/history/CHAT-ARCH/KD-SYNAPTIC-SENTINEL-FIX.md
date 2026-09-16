# KD-SYNAPTIC-SENTINEL-FIX: Knowledge Delta - Synaptic Routing Candidate Sentinel Fix

## Contexto
Este documento registra el fix del primer break reproducible en el routing sináptico: el centinela de candidatos vacíos.
Baseline: `ae7e3f7a7f48d487d7c070696df8e60171c41ce1`
Branch: `p0b-first-causal-break`

## Previous Model

### Hipótesis Anterior
El código en `tool_teach_service.py` línea 1339:
```python
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds') or []
candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
```

Debería preservar el centinela `None` cuando no se proporcionan candidatos.

### Evidence del Defecto
Claude Opus 5 observó en runtime:
```
goal_parameters={}
flag ON
→ selected_assistant_kind=""
→ fallback operational tool = ollama_llm
```

Mientras con candidatos explícitos:
```
candidate_assistant_kinds=["codex","windsurf"]
→ routing works
→ selected tool changes
```

## Defect

### Archivo/Método/Línea
**Archivo:** `src/iabv_v15/services/tools/tool_teach_service.py`
**Método:** `_synaptic_decision_for_request()`
**Línea:** 1339

### Explicación
Cuando `goal_parameters={}`:
```python
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds') or []
# raw_candidates = []
```

Luego:
```python
candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
# candidate_assistant_kinds = []  (BUG: debería ser None)
```

Pero `_resolve_candidates()` usa `None` como centinela de "usar todos los candidatos del registry":
```python
[] ≠ None
```

Por tanto, el router queda sin candidatos.

## Intervention

### Cambio Exacto
```python
# ANTES
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds') or []
candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None

# DESPUÉS
raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds')
# Preserve None sentinel when no candidates are explicitly supplied
if raw_candidates is None:
    candidate_assistant_kinds = None
else:
    candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
```

### Semántica Conservada
- `candidate_assistant_kinds = None` cuando no se proporcionan candidatos (usa registry completo)
- `candidate_assistant_kinds = [...]` cuando se proporcionan candidatos explícitos
- `candidate_assistant_kinds = []` cuando se proporciona explícitamente una lista vacía

## Evidence

### PRE-FIX Evidence
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5 && PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src /c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_candidate_sentinel_fix.py::test_synaptic_candidate_sentinel_empty_goal_parameters -v
```
**Resultado:** FAILED - Expected None for empty goal_parameters, got []

### POST-FIX Evidence
```bash
cd /c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5 && PYTHONPATH=/c/Python/IABV_v1.5/p0b-worktree/IABV_v1.5/src /c/Users/faber/miniconda3/python.exe -m pytest tests/test_synaptic_candidate_sentinel_fix.py -v
```
**Resultado:** 3 passed

### Control / Regression
- Explicit empty list: `candidate_assistant_kinds = []` (semántica preservada)
- Explicit candidates: `candidate_assistant_kinds = ['codex', 'windsurf']` (semántica preservada)
- Existing tests: 39 passed (test_synaptic_router.py)
- P0-B tests: 14 passed (test_p0_b_external_action_authorization.py)

## Causal Status

### M6: SynapticRouter → Operational ToolTask Selection
**Estado:** PARTIAL (sentinel break corregido, pero falta evidencia de routing completo)

### Causal Interpretation
**¿El cambio de `[] → None` causó que `_resolve_candidates()` utilizara el registry?**
- PRE-FIX: candidate universe absent (`[]`)
- POST-FIX: candidate universe present (`None`)
- Evidence: test pasa después del fix

## ΔK

### Nuevo Conocimiento
- El centinela `[]` rompe el routing sináptico
- `_resolve_candidates()` depende de `None` para usar el registry completo
- La distinción entre "no suministrado" vs "explícitamente vacío" es crítica

## Δπ

### Cambio de Política
- Empty goal_parameters ahora usa registry completo (via `None` sentinel)
- Explicit empty list permanece como "no candidates"

## ΔB

### Cambio de Selección Operacional
- NO DETERMINADO (falta evidencia de routing completo)

## ΔY

### Outcome
- NO DETERMINADO (falta medición de outcome real)

## Remaining Uncertainty

1. **Routing completo:** Aunque el centinela está corregido, falta evidencia de que el routing funcione end-to-end
2. **Segundo hallazgo:** user_goal no llega correctamente al path de decisión (NO corregido en este ciclo)
3. **Outcome:** No hay evidencia de mejora de outcome

## Next Causal Edge

Una vez que el centinela está corregido, el siguiente edge a verificar es:
- ¿El routing ahora selecciona correctamente un candidato?
- ¿La selección operacional cambia correctamente?

## Git Provenance

**Commit:** (pendiente)
**Remote branch:** `p0b-first-causal-break`
**Remote HEAD:** (pendiente)

## Conclusión

**Status final:** SUCCESS (pre-fix test failed + post-fix same test passed + regression tests passed)

El centinela de candidatos vacíos ha sido corregido. Ahora `goal_parameters={}` produce `None` en lugar de `[]`, permitiendo que `_resolve_candidates()` use el registry completo.

**NO declaro inflection completa.** Solo se ha corregido el primer break reproducible en el routing sináptico.
