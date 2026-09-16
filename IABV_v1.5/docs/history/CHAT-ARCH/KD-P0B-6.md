# KD-P0B-6

## TITLE
Adapter identity must be independently sourced

## TYPE
NEGATIVE / BOUNDARY

## CLAIM
Adapter binding validation was tautological: `authorization.adapter_key == authorization.adapter_key`.

## EVIDENCE
Code audit of `DevinApiToolAdapter._check_external_authorization()` showed it passed `auth.adapter_key` to `auth.validate_binding()`, comparing the authorization's value with itself. This provides no security binding to the actual executing adapter.

## WHAT IT PROVES
The binding check was meaningless as a security measure. Any authorization would match itself regardless of which adapter executed.

## WHAT IT DOES NOT PROVE
Whether other binding fields (assistant_kind, endpoint, action) have the same tautological issue.

## NEXT TEST
Verify binding validation uses actual adapter identity.

## RESOLUTION
Modified `DevinApiToolAdapter._check_external_authorization()` to pass `actual_adapter_key = 'devin_api'` instead of `auth.adapter_key`. The adapter's canonical identity is now independently sourced from the runtime, not from the authorization object itself.

---

## CORRECTIVE CYCLE REVISION (P0-B Audit Response)

### OBSERVATION
Audit confirmed adapter identity was independently sourced but assistant_kind, endpoint, and action fields were passed as empty strings, making those binding checks inert.

### EVIDENCE
Adapter code passed:
```python
actual_assistant_kind = ''  # TODO: extract from runtime if available
actual_endpoint = ''  # TODO: extract from runtime if available
actual_action = ''  # TODO: extract from runtime if available
```

### INTERPRETATION
The binding check for adapter_key was fixed, but optional fields remained unenforced because no runtime values were available. The authorization model includes these fields but the execution boundary does not provide them.

### POLICY CHANGE
**FIX-4:** Fields are only populated from task.metadata if they exist in runtime:
- `assistant_kind` from `task.metadata.get('synaptic_preferred_assistant_kind')`
- `endpoint` from `task.metadata.get('github_action')`
- `action` from `task.metadata.get('action_type')`
Empty values are not fabricated. TODO comments mark gaps where runtime extraction is not yet available.

### REMAINING UNCERTAINTY
Assistant kind, endpoint, and action extraction from actual runtime execution boundary requires deeper integration with the adapter/transport layer. Currently these fields are only available if explicitly provided in task metadata.
