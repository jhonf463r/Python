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
