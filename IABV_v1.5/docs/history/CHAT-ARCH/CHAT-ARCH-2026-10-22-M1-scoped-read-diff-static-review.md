# M1 — Static review of Owner-supplied scoped-read candidate diff (2026-10-22)

## Provenance and verdict

The Owner pasted the complete `git diff --no-ext-diff --unified=80` output for the reported isolated candidate's two modified files. Review is source-text/static only. The candidate has no reported commit; the patch was not fetched from a candidate branch on GitHub, the local worktree was not inspected by this coordinator, and no test/build/runtime execution occurred.

```
REVIEW_INPUT=OWNER_SUPPLIED_COMPLETE_DIFF
STATIC_REVIEW=FAIL_REPAIRS_REQUIRED
SCOPE_REPAIR=PARTIALLY_SUPPORTED_BY_EXAMPLES; AUTHORITATIVE_SEMANTICS_NOT_ESTABLISHED
READER_LISTER=FAIL_CLOSED_IN_SUPPLIED_PATCH
SCOPED_READ_REQUEST_APPROVAL_FLOW=NOT_IMPLEMENTED
TESTS=NOT_RUN
LIVE_MCP_IDENTITY=UNVERIFIED
LIVE_CHECKOUT_IDENTITY=UNVERIFIED
CANDIDATE_COMMIT=NONE_REPORTED
GOVERNANCE=KEEP_BLOCKED
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
```

Base blob IDs in the pasted diff match the public-main source identity previously recorded for `server.py` (`17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`) and the test file (`93c11837d39eaee60d2c818e522284f0f9c261d6`). This supports the claimed diff base only; it does not authenticate the candidate working tree or its reported new blob IDs.

## F-01 — HIGH: non-applicability is inferred without a demonstrated authoritative/versioned scope model

**Patch location:** `_governance_block_for_route`: locally constructed `known_target_scopes`, `route_scopes`, and the branch that `continue`s for any known target scope not in `route_scopes`.

Entry 274's normative contract requires an authoritative, versioned supported-scope model and explicit dimension-combination semantics; an active block may be classified non-applicable only when trusted target identity and that model prove the mismatch. Unknown/unsupported scope, incomplete target identity, conflicting/partially evaluable metadata or unavailable scope semantics must fail closed. It expressly warns not to invent production scope dimensions from a test matrix.

The patch constructs its own static scope allowlist and infers applicability from `assistant_kind`, `requires_network`, the `gpu_benchmark` special case and an optional `operation_scope`. The pasted diff does not show that this set/mapping is loaded from, validated against, or versioned by an authoritative registry. As a result, a scope in the local allowlist can be silently treated as unrelated even when the available source has not established that the route's target is outside that scope. This is an important control-policy decision, not just a normalization detail.

**Required repair:** inspect only the already-authorized isolated candidate and directly relevant public source/docs for an existing authoritative scope registry and target-identity resolver. Reuse them if source evidence demonstrates they are authoritative and versioned. If none exists, do not improvise a production scope model: retain fail-closed behavior and report the precise blocker rather than returning “unrelated” for a scope whose non-applicability cannot be proven.

**Acceptance:** every known-scope exclusion points to a source-backed, versioned mapping and trusted route target identity; unsupported/incomplete/conflicting scope data denies; there is no implicit inference from a test fixture.

## F-02 — HIGH: `operation_scope` is not wired into any production tool call in this diff

The new optional argument allows a route to add a target scope, and `test_ui_focus_scope_only_blocks_matching_audit_operation` exercises it by calling the helper directly with `operation_scope="ui_focus_interaction"`. However, the diff changes no real tool call site to pass `operation_scope`. Therefore that test proves only direct-helper behavior, not that a real operation which should carry such a scope is actually evaluated against it. The allowlist contains `ui_focus_interaction`, but no real tool invocation in the supplied patch supplies that scope. This leaves the target-to-operation mapping unproven.

**Required repair:** where an authoritative mapping exists, wire the scope at the narrowest applicable real call sites and add static regression cases that use the registered tool surface. Do not add call-site scope labels by guessing. If the authoritative mapping is absent, retain fail-closed policy and report the unresolved mapping.

**Acceptance:** the tested path invokes the same registered MCP tool entrypoint as the relevant production operation; a target scope is neither silently ignored nor applied based only on a helper-only test.

## F-03 — HIGH: unknown or malformed `assistant_kind` is still silently excluded

The patch normalizes the record's `assistant_kind`, then immediately continues if the value is neither empty, `*` nor the current route. It does not distinguish a proven, supported different assistant kind from an unknown/invalid value. Thus an active record whose assistant dimension is malformed or outside the supported scope vocabulary can disappear from consideration before its target-scope uncertainty is evaluated.

Entry 274 requires unknown/malformed/unsupported scope and partially evaluable/conflicting metadata to fail closed. The patch's unknown-target test does not cover unknown `assistant_kind` values or their interaction with a relevant `target_scope`.

**Required repair:** resolve assistant-kind validity through the same authoritative scope model. Skip a block as unrelated only when that model proves the mismatch; if the kind is unsupported, malformed or not safely evaluable, fail closed. Do not invent an allowlist merely to pass the test matrix.

**Acceptance:** add authored (not executed) cases for unknown/malformed assistant kinds, known mismatches, global and wildcard values, and crossed assistant/target dimensions.

## Positive finding — read/list content remains denied

The supplied patch replaces direct calls to `audit_tools.read_repo_file` and `audit_tools.list_repo_directory` with `scoped_read_authority_unavailable` when the general route gate does not block. No reader grant or approval mechanism is present, so the returned content/listing remains closed. This is an appropriate fail-closed interim state, but it is not the governed read route and does not complete M1.

The new read tests assert denial without content. The changes intentionally remove former happy-path content assertions. Since all tests remained unexecuted, they provide proposed regression coverage only, not a behavioral pass.

## Disposition and single next action

Do not merge, publish, execute tests or label M1 as passed on this evidence. The scope correction has useful discriminating examples but is not safe to accept until F-01–F-03 are resolved against source-backed semantics.

**Single next action:** ask Codex, in the same isolated candidate, for the minimal repair of F-01–F-03 using only existing authoritative source/contracts. It must not invent a scope registry, must not run tests/build/runtime, must not touch the Owner's dirty checkout or `data/`, and must return a new diff for the same two code paths plus any narrowly necessary tests. If authoritative semantics cannot be found in those permitted sources, stop without implementing a guessed mapping and report that blocker.

Canonical contract: [Entry 274 — consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md).
