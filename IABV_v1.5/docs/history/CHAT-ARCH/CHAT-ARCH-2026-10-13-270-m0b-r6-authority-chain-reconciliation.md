# CHAT-ARCH-2026-10-13-270 — M0B-R6 authority-chain reconciliation and source-anchor correction

- Episode ID: CHAT-ARCH-2026-10-13-270
- Reported local time (America/Bogota): 2026-10-13, approximately 20:49 onward
- Documentation baseline observed before write: `main` identical to commit `109e4e34c40b71c6b8b7cffc173f319d75921770`
- Pinned code baseline: `559f4ea20a9a9163cd9a9839b11d9991933f8c07`
- Input: Owner-supplied result `LIMITED_REPO_READ_AUTHORITY_NOT_ESTABLISHED` / `KEEP_BLOCKED`
- Adjudication: `NO_EXISTING_REPO_READ_AUTHORITY_CHAIN_FOUND_IN_BOUNDED_SCOPE`; `EXTERNAL_ACTION_AUTHORIZATION_HAS_A_DEVIN-SPECIFIC_CONSUMER_BUT_NO_PROVEN_PRODUCTION_ISSUER`; `REPORT_LINE_ANCHORS_MISMATCH_PINNED_BLOBS`
- Operational posture: `KEEP_BLOCKED` for local M0A access, implementation, tests/runtime, and IABV/Codex/App Server launch.

## 1. Executive finding

The supplied report's principal conclusion remains correct: the inspected public code does not establish a legitimate, scoped authorization for reading the local repository. `ExternalActionAuthorization` is a real model, and the bounded follow-up found a consumer in `DevinApiToolAdapter` in addition to the two bootstrap helpers. That is a narrow external-action approval mechanism, not a repository-read authority chain.

The report under-described this consumer path and its cited line ranges do not match the source objects at the claimed pinned commit. We fetched the complete named files at the immutable source commit, recorded the actual Git blob SHAs, located the declarations by content, and compared the relevant blobs with the current default branch. The source blobs match between the pinned commit and current `main`; the line corrections below are therefore reproducible against both.

No production code path was found in the bounded search that constructs/issues `ExternalActionAuthorization` or binds it to an authenticated owner principal. Search results for constructor calls showed the model definition and test helper factories, not a production issuer. The adapter consumer validates a Devin action against task/tool/prompt properties; it has no repository, checkout, allowed-file, or read-operation binding. The result remains a bounded negative finding, not proof that no such mechanism exists anywhere in all branches, uninspected components, private configuration, or local M0A.

## 2. Public baseline and provenance

A GitHub commit comparison reported `main` identical to `109e4e34c40b71c6b8b7cffc173f319d75921770` at the time of inspection. The following files were fetched both at source baseline `559f4ea20a9a9163cd9a9839b11d9991933f8c07` and at default-branch `main`; each pair had the same blob SHA and line count:

| File | Verified Git blob SHA | Lines | Correct anchors / result |
|---|---|---:|---|
| `src/iabv_v15/domain/models.py` | `a9033d21052c519e09f482097599c704a62ea916` | 3298 | `ExternalActionAuthorizationStatus` 3218–3224; `ExternalActionAuthorization` 3227–3298; fields 3246–3261; `is_valid` 3263–3275; `validate_binding` 3277–3290; `consume` 3292–3298 |
| `src/iabv_v15/bootstrap.py` | `e4befa6b683fc87aed7481f377f1332f5753e2c3` | 5386 | `_devin_create_session` 145–191; `_devin_send_message` 194–234; Devin adapter construction 639–648; briefing callables 1142–1153 |
| `src/iabv_v15/services/tools/tool_adapters.py` | `f8ce508342d2da96f30b2152ffa242f08b187987` | 2845 | `DevinApiToolAdapter.__init__` 1833–1845; `_check_external_authorization` 1865–1904; guarded non-sandbox call 1948–1963 |
| `src/iabv_v15/services/tools/tool_teach_service.py` | `7f0412627c98074b1e3df0d0f6e76ab5998e3505` | 1923 | No `ExternalActionAuthorization` reference in the fetched file. Lines 689–716 are `preview_external_consultation`; `execute_external_consultation` begins at 718. |
| `tests/test_p0_b_external_action_authorization.py` | `c800f6b6c667a7e9eb4c53074db5dd36a09618ac` | 641 | Test-only factory `_create_authorization` at 35–56; fixtures manually set status/approver fields. |
| `tests/test_e29_synaptic_to_delegation_with_intercepted_transport.py` | `6b38c0f9e2ed5132c43a1618357e2f8752bd5fbf` | 511 | Test-only factory `_create_external_authorization` at 227–246. |

The supplied ranges `models.py:2989–3063` and `bootstrap.py:2413–2495 / 2497–2569` do not locate the declarations in the fetched pinned blobs. They must not be repeated as verified citations. The report's statement that ToolTeachService has no class references is corroborated, but its consultation-flow description should be anchored to the actual `preview_external_consultation` lines 689–716 and `execute_external_consultation` beginning at 718 if cited.

## 3. Minimal authority/consumer graph

### 3.1 Model — schema, not proof of a trusted issuer

At `models.py` blob `a9033d21052c519e09f482097599c704a62ea916`:

- `ExternalActionAuthorization` defines task/tool/adapter/assistant binding, endpoint/action, prompt digest, nonce, state, issue/expiry/consume timestamps, `approved_by`, reason and free-form metadata (3227–3261).
- `is_valid()` accepts status `VALIDATED` when not expired (3263–3275).
- `validate_binding()` compares task ID, tool ID, adapter key and prompt digest (3277–3290).
- `consume()` marks the object consumed (3292–3298).

The model has no repository root, exact checkout identity, server identity, operation class for repository reading, relative-path allowlist, read budget, or receipt-verification contract. The string `approved_by` is a field; the model itself does not prove who authenticated that principal or who legitimately changed the object to `VALIDATED`.

### 3.2 Existing consumer — Devin adapter only

At `tool_adapters.py` blob `f8ce508342d2da96f30b2152ffa242f08b187987`, the `DevinApiToolAdapter` constructor accepts an optional `external_authorization` value and stores it (1833–1845). Its `_check_external_authorization` path (1865–1904):

1. rejects a missing or non-matching model object;
2. calls `is_valid()`;
3. computes a digest for the prompt;
4. calls `validate_binding()` against the task ID, task tool ID and prompt digest;
5. consumes the authorization if checks pass.

The non-sandbox Devin run invokes this verifier and returns a refusal when the authorization is missing or invalid (1948–1963). This establishes a Devin-specific consumer for external-action authorization. It does not establish repository-read permission. The verifier passes `auth.adapter_key` back as the expected `adapter_key` parameter (1891–1896), so that comparison is self-referential rather than independently binding to a separately supplied expected adapter key. This further cautions against repurposing the method as a general trust verifier.

### 3.3 Bootstrap helpers — guarded external requests, no authority issuance

At `bootstrap.py` blob `e4befa6b683fc87aed7481f377f1332f5753e2c3`, `_devin_create_session` (145–191) and `_devin_send_message` (194–234) each reject a missing authorization, check `is_valid()`, and consume the object before their external HTTP request. Neither helper calls `validate_binding()`; the helpers are not a general receipt verifier or repository-reader gate.

The standard `DevinApiToolAdapter` is constructed at lines 639–648 with `api_key` and `org_id`, but no `external_authorization` argument. The `SessionStartBriefingService` callables at 1142–1153 invoke the bootstrap helpers without supplying their optional `authorization` parameter. These are not proof of a working production issuance chain; those particular helper invocations lack the required authorization argument and fail closed. The bootstrap module creates/consumes a passed authorization but does not issue one.

### 3.4 Issuer search — no production creation path found in bounded public code search

The bounded GitHub search for `ExternalActionAuthorization(` found the model definition and two test helper factories. The search for `ExternalActionAuthorizationStatus.VALIDATED` found the model's state check and test fixtures that manually instantiate an already-validated object; no production issuer was found in the returned results. Search for `external_authorization` found the adapter field/check and tests that inject objects into the adapter. In the bootstrap construction path examined above, no authorization is injected.

This supports `NO_PRODUCTION_ISSUER_FOUND_IN_BOUNDED_SCOPE`. It does **not** support the stronger claim that an issuer cannot exist in every uninspected/private/local path. The search was intentionally not expanded into a general identity or authentication audit.

## 4. Adjudication of the supplied report

| Supplied claim | Independent result |
|---|---|
| A model describes task/tool/adapter/prompt binding, nonce, expiry and consumption. | **Upheld**, with corrected exact blob and line anchors. The model is a data contract, not by itself a trusted authority. |
| Bootstrap uses the object before Devin session/message requests, without calling `validate_binding()`. | **Upheld but incomplete**. Actual definitions are at 145–191 and 194–234, not the cited 2413+ ranges. The standard bootstrap call sites omit the authorization argument. |
| No repository-read authority is established. | **Upheld**. No repo/checkout/path/operation scope exists in the model or Devin consumer chain. |
| ToolTeachService has no references to the model. | **Upheld for the fetched full blob**. Its cited range is an external consultation preview/execution path, not an issuer/verifier for this authorization type. |
| The next step is to inspect direct issuer/verifier callers if possible without widening to general auth. | **Completed within the narrow scope**. The Devin consumer was located; no production issuer or read-authority binding was established. Stop rather than fan out into general authentication. |

## 5. Evidence labels and unresolved facts

- **PROVEN_BY_SOURCE:** the model fields and methods at the anchors in §2; the Devin-specific consumer at `tool_adapters.py:1865–1904`; its non-sandbox gate at 1948–1963; the two guarded bootstrap helper definitions; the standard bootstrap construction/call sites do not pass a production authorization value in the inspected code.
- **PROVEN_BY_SOURCE, bounded:** no production constructor/issuer for `ExternalActionAuthorization` was found in the directly related public code search; the only constructor matches returned outside the class were test fixtures.
- **OWNER_REPORTED:** the prior local repository reader was blocked; this public investigation did not retrieve that runtime payload.
- **UNPROVEN:** authenticated owner-principal provenance for `approved_by`; production issuer outside inspected paths; any issuer/verifier bound to a specific MCP server/workspace/checkout and path allowlist; local M0A identity/content/state; analogous private or unindexed mechanisms.
- **NOT PERFORMED:** local checkout reads, blocked-reader retries, bypass attempts, command execution, tests/builds, runtime, source edits, credential inspection, authentication, installs/updates or additional model/API spend.

## 6. Next step and hard boundary

This bounded search has reached its discriminating result: a Devin-oriented external-action object and consumer exist, but a trusted production issuer and repository-scoped read authority do not emerge from the direct public references. Do not treat `ExternalActionAuthorization`, `approved_by`, a `VALIDATED` status, Devin's consumer, the bootstrap helpers or observation permission as a grant to read local repository files.

Further exploration into a general identity/authentication subsystem would exceed this narrow scope and needs a separate explicit Owner decision. In the meantime, no implementation is authorized and local M0A access remains `KEEP_BLOCKED`. Do not ask the Owner to gather code manually; technical retrieval and source reconciliation remain AI tasks within their authorized scope.

## 7. Canonical continuity

Use the route `README.md → CURRENT-STATE.md → CONTEXT-INDEX.md → MEMORY-OPERATING-PROTOCOL.md → this Entry 270 and exact source objects`. Entry 270 supersedes the pending-next-action wording in Entry 269 only for the bounded R6 inspection: the direct-reference pass has now been performed and stopped with no repository-read authority chain established. Entry 269 remains the source-anchor reconciliation for R5 and records the original gate history.
