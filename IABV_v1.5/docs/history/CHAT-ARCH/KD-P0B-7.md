# KD-P0B-7

## TITLE
Modeled binding fields are not enforced unless consumed by runtime validation

## TYPE
NEGATIVE / BOUNDARY

## CLAIM
`ExternalActionAuthorization` model declares binding fields (assistant_kind, endpoint, action) but runtime validation may not consume them.

## EVIDENCE
The `validate_binding()` method only enforced task_id, tool_id, adapter_key, and prompt_digest. The optional fields (assistant_kind, endpoint, action) were ignored even if present in the authorization.

## WHAT IT PROVES
Having binding fields in the model does not guarantee they are enforced. Only fields actually consumed by `validate_binding()` provide security binding.

## WHAT IT DOES NOT PROVE
Whether these fields are needed for security or if their absence represents a gap.

## NEXT TEST
Determine if assistant_kind, endpoint, action should be enforced.

## RESOLUTION
Modified `ExternalActionAuthorization.validate_binding()` to optionally validate assistant_kind, endpoint, and action if they exist in the authorization. This enforces them when present but remains backward compatible.

---

## CORRECTIVE CYCLE REVISION (P0-B Audit Response)

### OBSERVATION
Audit identified that the digest only covered `task.objective`, but the adapter actually sends `objective + context_pack`. This allows modifying context after approval without invalidating the binding.

### EVIDENCE
Adapter code at line 1999-2002 builds the actual payload:
```python
context_pack = str(task.metadata.get('context_pack') or '') if task.metadata else ''
prompt = str(task.objective or '')
if context_pack:
    prompt = f'{prompt}\n\n--- context ---\n{context_pack}'
```

### INTERPRETATION
The authorization binding was incomplete. It only protected the objective but not the full payload actually transmitted. Context could be changed after approval without detection.

### POLICY CHANGE
**FIX-7:** Issuer now builds canonical payload including context_pack:
```python
context_pack = str(task.metadata.get('context_pack') or '').strip()
if context_pack:
    canonical_payload = f'{task.objective}\n\n--- context ---\n{context_pack}'
else:
    canonical_payload = task.objective or ''
prompt_digest = compute_canonical_prompt_digest(canonical_payload)
```
Adapter uses same canonicalization for validation at lines 1905-1912.

### REMAINING UNCERTAINTY
The canonical payload format (objective + "\n\n--- context ---\n" + context_pack) must match exactly between issuer and validator. Any drift in format would break binding.
