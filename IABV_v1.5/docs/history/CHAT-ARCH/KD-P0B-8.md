# KD-P0B-8

## TITLE
Duplicated enforcement paths create semantic drift risk

## TYPE
NEGATIVE / BOUNDARY

## CLAIM
Bootstrap helpers (`_devin_create_session`, `_devin_send_message`) and `DevinApiToolAdapter._check_external_authorization()` had separate authorization validation logic.

## EVIDENCE
Both code paths checked `authorization.is_valid()` and called `authorization.consume()`, but the implementations were separate. Any change to validation logic would need to be duplicated in both places, creating risk of semantic drift.

## WHAT IT PROVES
Duplicated enforcement paths are maintenance hazards and can lead to inconsistent behavior.

## WHAT IT DOES NOT PROVE
Whether the two paths had semantic differences at the time of audit.

## NEXT TEST
Unify enforcement logic.

## RESOLUTION
Created shared `_validate_external_authorization()` function in `bootstrap.py` that both bootstrap helpers now use. This ensures consistent validation semantics and single source of truth for authorization validity checks.

---

## CORRECTIVE CYCLE REVISION (P0-B Audit Response)

### OBSERVATION
Audit found that bootstrap and adapter enforcement were not truly unified. The shared function only checked `is_valid()` while the adapter also performed full binding validation with task/tool context.

### EVIDENCE
Bootstrap function at line 145 in `bootstrap.py` checks only `is_valid()`. Adapter at line 1869 in `tool_adapters.py` checks `is_valid()` AND `validate_binding()` with actual runtime values.

### INTERPRETATION
The "unified enforcement" claim was partially true for validity checking but not for binding validation. Bootstrap doesn't have task/tool context so it cannot perform full binding validation. This is a semantic difference, not duplication.

### POLICY CHANGE
**FIX-5:** Shared function `_validate_external_authorization()` acknowledges that adapter does full binding validation with context. Bootstrap uses shared validity check but cannot do binding validation without context. The semantic difference is documented as intentional.

### REMAINING UNCERTAINTY
Whether bootstrap should perform binding validation depends on whether it can obtain task/tool context at that point in the execution path. Currently it cannot, so the semantic difference is acceptable.
