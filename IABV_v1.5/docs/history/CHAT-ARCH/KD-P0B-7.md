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
