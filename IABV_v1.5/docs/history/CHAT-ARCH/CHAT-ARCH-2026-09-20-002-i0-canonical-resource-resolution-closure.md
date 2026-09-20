# CHAT-ARCH 2026-09-20-002 — I0 Canonical Assistant↔Tool Resolution Closure

## PROVENANCE

Repository: `jhonf463r/Python`

Implementation branch:
`devin/i0-canonical-tool-registry-resolution-fix-2026-09-20`

Verified implementation commit:
`4710a668541225ffe3b9d1335d31bb5da8b1e685`

Parent:
`a7ae929ae476469c1467f3ac4a29d83aeb16f87d`

Independent audit:
Sonnet second forensic audit of the remote artifact.

## STATUS

**I0 CANONICAL RESOURCE-RESOLUTION SEAM = VERIFIED EFFECTIVE**

This closes the bounded seam:

`assistant_kind → ToolRegistry → canonical tool_id set → resource ranking → UniversalResource → credential_ref`

It does **not** close the complete I0 external-agent runtime chain.

## EVIDENCE

Sonnet independently verified:

1. `ToolRegistry.resolve_tool_ids_by_assistant_kind()` derives canonical tool IDs from `ToolCard.metadata["assistant_kind"]`, without a hardcoded Devin mapping.
2. `bootstrap.py` creates `ToolRegistry` before `LocalRoleRouter` and passes the same instance through `tool_registry=self.tool_registry`.
3. `LocalRoleRouter.worker_health_gate()` now separates:
   - no target → historical general ranking;
   - direct canonical tool ID → direct ranking;
   - assistant kind → ToolRegistry resolution;
   - unknown/resolution failure → fail closed;
   - registry unavailable → legacy direct-target compatibility.
4. The previous undefined `target` reference is removed.
5. Router-level tests invoke `worker_health_gate()` and verify assistant resolution, credential propagation, direct tool ID compatibility, no-target behavior, unknown-assistant fail-closed behavior, resolver-error fail-closed behavior and one-to-many routing.
6. `bootstrap.py` changed by one surgical line; no encoding/line-ending conversion was introduced by the fix.

## ACCEPTED CAUSAL EDGE

`assistant_kind='devin'`

→ `ToolRegistry.resolve_tool_ids_by_assistant_kind('devin')`

→ `ToolCard.metadata['assistant_kind']=='devin'`

→ `tool_id='devin_api'`

→ `rank_workers_for_target('devin_api')`

→ `UniversalResource(tool_id='devin_api')`

→ selected resource

→ `credential_ref`

## NEGATIVE KNOWLEDGE PRESERVED

The rejected predecessor `a7ae929ae` demonstrated why test counts alone were insufficient:

- production bootstrap was not actually wired;
- `worker_health_gate()` had a reachable `NameError`;
- no-target behavior was regressed;
- direct tool ID compatibility was coupled to the presence of ToolRegistry;
- the added tests did not cross the actual router boundary.

Those failures remain part of the reusable verification method.

## REMAINING I0 BOUNDARY

This closure is **not** evidence that a real Devin credential is available or that Devin HTTP authentication/external execution succeeds.

The next open operational edge remains:

`credential availability → authorization/authentication → transport → external effect → observable result → independent verification`

The recorded Windows runtime blocker remains relevant: without a real supported Devin credential in the controlled runtime, I0/I1 external-agent execution cannot be promoted.

## NON-BLOCKING FOLLOW-UPS

Two audit observations are retained as improvements, not blockers for this seam:

- resolver exceptions currently fail closed without an explicit diagnostic signal;
- multi-tool-ID merge is concatenation + score sorting without an explicit uniqueness guarantee.

Neither observation invalidates the verified canonical-resolution seam.

## CROSS-IA METHOD LEARNED

The strongest verification sequence here was:

`Codex ownership adjudication → Devin bounded implementation → GitHub remote read-back → Sonnet independent forensic audit → corrected implementation → Sonnet re-audit`

The method, not any single actor's reputation, is the reusable knowledge.

## NEXT DISCRIMINATING ACTION

Do not reopen assistant↔tool ownership or repeat this seam without contradictory evidence.

Advance to the first open runtime edge: securely make a supported real Devin credential available to the controlled Windows runtime and execute the smallest existing I0 Phase-A connection/authentication experiment. Stop at the first causal break and preserve exact provenance.
