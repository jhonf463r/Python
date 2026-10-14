# CHAT-ARCH-2026-10-13-271 — M0B-R7 approval-broker chain adjudication

- Episode ID: CHAT-ARCH-2026-10-13-271
- Reported local time (America/Bogota): 2026-10-13, approximately 21:00
- Documentation baseline before write: `main` identical to `bc6db14f10c07eac7e1378b8db8d57674aac31bf`
- Pinned code baseline: `559f4ea20a9a9163cd9a9839b11d9991933f8c07`
- Input: Owner-supplied result `INCOMPLETE_AUTHORITY_CHAIN_KEEP_BLOCKED`
- Independent adjudication: `PARTIAL_APPROVAL_WORKFLOW_FOUND`; `NO_PRODUCTION_EXTERNAL_ACTION_AUTHORIZATION_ISSUER_FOUND_IN_BOUNDED_PUBLIC_SEARCH`; `APPROVAL_RESULT_NOT_EQUIVALENT_TO_VERIFIED_HUMAN_IDENTITY`; `KEEP_BLOCKED`
- Boundary: public GitHub source only; no local M0A access, retries, execution, tests, code changes, credentials or authentication.

## 1. Executive finding

The new evidence confirms a real human-approval workflow, but it does not close the missing authority chain. `HumanApprovalBroker` can either return an `ApprovalResult` after a UI callback or accept a result from a configured pre-approver. `ApprovalMemory` implements such a pre-approver and can auto-resolve a matching request as approved without presenting a prompt. The returned `ApprovalResult` records the request and outcome but not a verified actor/principal identity.

Within bounded public code search, references to the constructor `ExternalActionAuthorization(` resolve to its model definition and two test helper factories. References to `ExternalActionAuthorizationStatus.VALIDATED` / `approved_by=` resolve to the model and those test helpers, not to a production issuer. No production edge was found that transforms a human-specific `ApprovalResult` into an `ExternalActionAuthorization`, sets its status to `VALIDATED`, and establishes the trusted meaning of `approved_by`.

Therefore the adjudication is **PARTIAL_CHAIN**, not an existing reusable repository-read authority. This is bounded negative evidence; do not claim global absence from all code, branches, private settings, or local M0A.

## 2. Exact source provenance and corrected anchors

The supplied report again cites `models.py:2989–3063` and `bootstrap.py:2413–2569` for declarations that do not occur at those positions in the exact pinned blobs. The coordinator fetched each named file at the immutable commit and at current `main`; the blobs are identical between the two refs.

| File | Verified Git blob SHA | Relevant declaration / anchors |
|---|---|---|
| `src/iabv_v15/domain/models.py` | `a9033d21052c519e09f482097599c704a62ea916` | `ExternalActionAuthorizationStatus` 3218–3224; `ExternalActionAuthorization` 3227–3298; fields including `approved_by` 3246–3261; `is_valid` 3263–3275; `validate_binding` 3277–3290; `consume` 3292–3298 |
| `src/iabv_v15/bootstrap.py` | `e4befa6b683fc87aed7481f377f1332f5753e2c3` | `_devin_create_session` 145–191; `_devin_send_message` 194–234; they validate state and consume but do not create an authorization |
| `src/iabv_v15/services/security/human_approval_broker.py` | `4a447149cf1b2771f6959658338a72b381f00b19` | `ApprovalRequest` / `ApprovalResult` 87–116; broker class 123–135; request flow 179–267; pre-approver dispatch 218–225; UI prompt and result wait 227–267; `approve` 269–285 |
| `src/iabv_v15/services/security/approval_memory.py` | `ed85408d96fb0cdfddb05489d6c38cf714275f91` | explicit policy creation via `remember` 118–145; `pre_approver` 188–229; approved auto-result with `auto_resolved=True` 218–223 |
| `tests/test_p0_b_external_action_authorization.py` | `c800f6b6c667a7e9eb4c53074db5dd36a09618ac` | Test-only `_create_authorization` 35–56 sets `VALIDATED` and a fixture value for `approved_by` |
| `tests/test_e29_synaptic_to_delegation_with_intercepted_transport.py` | `6b38c0f9e2ed5132c43a1618357e2f8752bd5fbf` | Test-only `_create_external_authorization` 227–246 sets `VALIDATED` and fixture `approved_by` |

The public file-fetch route exposed the per-file Git blob SHAs for independent verification. The source code SHAs above are facts from fetched Git objects, not inferred values. No claim is made that the owner-supplied tool itself exposed those SHAs.

## 3. Minimal approval workflow

### 3.1 Generic broker

`human_approval_broker.py` defines an `ApprovalRequest` containing a request ID, kind, reason, scope, optional payload schema, sensitivity flag and request timestamp (87–98). `ApprovalResult` contains a request ID, booleans such as `approved`, `rejected`, `timed_out`, `cancelled`, `auto_resolved`, and payload metadata (100–115). There is no authenticated actor/principal identity field in this result object.

In `request(...)` (179–267), the broker invokes a configured pre-approver before registering/emitting a UI prompt (218–225). If no pre-approver resolves the request, the broker registers pending state and invokes a prompt handler (227–252), then waits for the future result or timeout (253–267). The UI-facing `approve(request_id, payload=...)` returns an outcome using the pending entry (269–285); this API does not accept a separate verified actor identity.

This establishes a way to ask for or resolve a generic approval, but not cryptographic or authenticated provenance for the person behind that result, and not a repository-read grant.

### 3.2 Persisted approval policy can auto-resolve

`ApprovalMemory.remember(...)` explicitly persists an approval/rejection policy (118–145). Its `pre_approver` checks matching policies for requests without a non-empty `payload_schema` and returns an `ApprovalResult` with `approved=True` and `auto_resolved=True` when the stored decision is approved (188–229). This is consistent with the module's contract: remembered policy can resolve a future request without a fresh UI prompt.

Accordingly, an `ApprovalResult.approved == True` is not proof that a human was present for that specific operation. For any future repository-read gate, `auto_resolved=True` must not satisfy a requirement for fresh interactive approval. Merely disabling one UI capture or assuming that a prompt occurred is not sufficient.

### 3.3 Model and Devin consumer remain disconnected from the broker

`ExternalActionAuthorization` is defined in the model blob listed above. Its `approved_by` value is a string and `is_valid()` checks state and time; the class does not verify the human identity behind that string. Its binding covers task/tool/adapter/prompt digest, not repository/checkout/read-path scope.

The inspected Devin bootstrap helpers (145–234) validate and consume a supplied instance before an external API call, but do not issue it or call `validate_binding()`. Direct public search for `ExternalActionAuthorization(` found the model plus two test factories only. The matching `VALIDATED` and `approved_by=` results were likewise model/test fixtures. That search did not find a production edge from the broker's approval result to a validated authorization object.

## 4. Adjudication of the supplied report

| Supplied assertion | Independent result |
|---|---|
| The model has a validation state, expiry and task/tool/adapter/prompt binding. | **Upheld**, with corrected blob SHA and lines. |
| Bootstrap helpers consume the passed authorization but do not issue it. | **Upheld**, with corrected anchors 145–234; the supplied 2413+ ranges are misaligned. |
| HumanApprovalBroker returns an approval result with request ID and scope. | **Upheld and narrowed**: result holds request/outcome and payload metadata; request has scope. The result itself does not include verified actor identity. |
| ApprovalMemory may auto-resolve a future request. | **Upheld**: `pre_approver` may return `approved=True, auto_resolved=True` without UI prompting. |
| No production chain converting broker result into ExternalActionAuthorization was found in consulted fragments. | **Upheld within the direct-source-search scope**. The class constructor, `VALIDATED`, and `approved_by` public search results show the model/test fixtures, not a production issuer. This is not an exhaustive global-absence proof. |
| A repository-read authority is still missing. | **Upheld**: no proven bridge from verified human principal → operation-scoped approval → issued/verified read decision bound to exact checkout and paths. |

## 5. Evidence labels / what remains unproven

- **PROVEN_BY_SOURCE:** the source blobs and anchors in §2; the broker's pre-approver-before-UI control flow; `ApprovalMemory` can set `auto_resolved=True`; `ApprovalResult` does not include a verified actor field; the external-action model checks its state/binding fields but does not verify the identity represented by `approved_by`.
- **PROVEN_BY_SOURCE, bounded:** direct public symbol searches returned the class definition and two test helper constructors for `ExternalActionAuthorization`, without a production issuer in the searched results.
- **OWNER_REPORTED:** the local M0A reader remains blocked; no local runtime payload was obtained by this public investigation.
- **UNPROVEN:** authenticated Owner principal identity and provenance; production authority issuer outside inspected/directly indexed paths; a broker-to-external-authorization mapping outside the searched paths; any decision verifiable for exact MCP server/workspace/checkout + relative-path allowlist; local M0A identity/state.
- **NOT PERFORMED:** local M0A reads; blocked-reader retry/bypass; command execution, tests/builds or runtime; source edits; secret/credential inspection; authentication; installs/updates; API/model calls or extra spend.

## 6. Next action: stop reuse search, specify the missing authority boundary

The bounded reuse search has now covered the known external-action model/consumer, bootstrap helpers, generic broker and persisted approval memory. It has found a partial approval mechanism but not an authority chain suitable for repository reads. Do not repeat the same symbol search or broaden into general identity/authentication by implication.

The next useful step is a **public contract-only delta**, not implementation: specify a dedicated read decision and its verifier as a distinct capability. At minimum the spec must require (1) proven server/workspace/checkout identity; (2) explicit operation and relative-path allowlist plus bounded byte/file/entry/call budgets; (3) short expiry and unique decision ID; (4) trusted actor/principal provenance; (5) a fresh-interactive-approval requirement that rejects memory auto-resolution; (6) issuer and consumer binding, expiry/revocation checks before every read; and (7) fail-closed behavior for missing/mismatched evidence. A generic `approved=True`, an `approved_by` string, `VALIDATED`, or observation permission must not constitute the grant.

This spec does not itself grant implementation or local access. A future implementation would still require explicit authorization, an established trustworthy principal source, and a separately resolved local M0A access gate. Keep `KEEP_BLOCKED`.

## 7. Continuity routing

Recover in order: `docs/history/CHAT-ARCH/README.md → CURRENT-STATE.md → CONTEXT-INDEX.md → MEMORY-OPERATING-PROTOCOL.md → Entry 271, Entry 270, and the exact source blobs`. Entry 271 adds the broker/ApprovalMemory finding and supersedes Entry 270 only on the next-action decision: the bounded reuse chain search has now reached its stopping result; do not repeat it. Entry 270 remains canonical for the previous external-action-consumer adjudication.
