# IABV → CODEX — Canonical continuity handoff after v9 review

- Reference date: 2026-10-18 (America/Bogota)
- Repository: `jhonf463r/Python`
- Base snapshot for this documentary PR: `main @ d3a4212b6de36254bf45d5e655d684d0640a0706`
- Workstream route: IABV → Codex governed development bridge
- Status on this branch: `PROPOSED_CANONICAL_HANDOFF_PENDING_INDEPENDENT_REVIEW`
- Governance: `GOVERNANCE = KEEP_BLOCKED`
- Implementation: `IMPLEMENTATION = NOT_AUTHORIZED`
- Bridge: `BRIDGE_NOT_READY`
- Owner decision C remains binding: keep Codex launch blocked while static design and documentary review continue.

## 1. Canonical artifacts in this branch

### v9 contract candidate

Path: `IABV_CODEX_contract_review_bundle_v9_2026-10-18.md`

- Size: 177,272 bytes.
- SHA-256: `3fdfd2f6ea3ca6b38f179341b5807e70c95bdde1e8486b0a047032832d0c5e17`.
- Git blob SHA after read-back: `17c22a4e9eef3267115816b85bf2ef398b6567b6`.
- Identity verification: `BYTE_HASH_VERIFIED`; the Git blob SHA matches the locally computed Git object identity of the original artifact.

### Ninth-review reconciliation

Path: `IABV_V9_NINTH_REVIEW_RECONCILIATION_2026-10-18.md`

- Size: 6,911 bytes.
- SHA-256: `459de4cd6fae2ce48d4c3eee7e2211edb0d78e23850dd76c121a0a9461d45445`.
- Git blob SHA after read-back: `8e3b456672ee01a6879898b171984d7dc513501a`.
- Identity verification: `BYTE_HASH_VERIFIED`; the Git blob SHA matches the locally computed Git object identity of the original artifact.

The ninth-review text supplied in conversation declares `PASS`, but no separate report artifact with its own verifiable hash was available. Record the result as `PASS_REPORTED`; reviewer identity and independence remain `OWNER_REPORTED`. A contract hash establishes bytes, not reviewer identity, independence, semantic truth, capability existence or operational authorization.

## 2. Reconciled documentary findings

- `N-85 = ALREADY_COVERED / OPTIONAL_CLARIFICATION`: do not promote a redundant clarification into a new semantic defect.
- `N-86 = ALREADY_COVERED / OPTIONAL_CLARIFICATION`: the exact manual path-manifest route remains permissible without inventory where §2.6 allows it, without skipping MaterializationAuthorization or other applicable steps.
- `N-87 = DOCUMENTED_REQUIREMENT / CAPABILITY_NOT_DEMONSTRATED`: §2.12 specifies evidence needed for service-side exclusivity, but does not prove that such a pre-existing capability exists.
- `F-V8-02 = CONTRADICTED_BY_V8_SOURCE / NOT_ADOPTED_AS_NEW_DEFECT`: the transition `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE` was present in the exact v8 source; do not add a duplicate.
- Do not create v10 without a concrete surviving counterexample or explicit Owner decision.
- Do not inherit historical `CLOSED` statuses without source-level reconciliation; keep unrecoverable historical counterexamples `NOT_RECOVERED`.

## 3. Technical and governance boundary

The contract is a documentary candidate, not an accepted or implemented bridge. The following remain `UNPROVEN`, `UNRESOLVED`, or blocked under current constraints where applicable: the non-rollback reservation authority; service-side exclusivity across manual and automated channels; executor and descendant-process confinement; independent observation, revocation and termination; trustworthy receipt and verification roots; owner approval channel; IABV consumer; and any real-route authentication, usage/cost or compatibility facts.

No contract PASS authorizes launch or proves these capacities exist.

## 4. Pending independent deliverables

- **R10 v0.7.4:** `OWNER_REPORTED / NOT_ASSEMBLED / NOT_PUBLISHED` until the exact 99 evaluation rows are recovered and reconciled.
- **Candidate C:** `OWNER_REPORTED / VERDICT_NOT_EMITTED` until its exact evidence is recovered. Do not infer its verdict from v9.
- Do not change the priority of these items absent an explicit Owner decision.

## 5. Canonical navigation and workstream scope

The entry points updated in this proposed change are:

1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md)

This handoff is the proposed current route for the IABV → Codex workstream after this PR is independently reviewed and merged. It does not replace or reorder the independent M0B Entry 280 route in the memory operating protocol. The v5 handoff remains byte-for-byte immutable historical evidence.

## 6. Required continuation method

For every new session:

1. Resolve the current commit SHA and read the canonical pointers before acting.
2. Retrieve the exact v9 contract and reconciliation from the paths above; verify their file hashes before reviewing.
3. Separate `PROVEN_BY_SOURCE`, `OWNER_REPORTED`, `PROPOSED`, `UNPROVEN`, `UNRESOLVED`, `NOT_RECOVERED`, and `NOT_RUN`.
4. Cross-check every alleged missing clause against the exact artifact; do not treat a reviewer summary as a substitute for source.
5. Keep the next external review or action explicit, with `IA DESTINO`, required capability, scope, stop conditions and output contract.
6. Use GitHub PRs as the cross-IA documentary channel while the runtime bridge remains unavailable; do not make the Owner manually transport artifacts that connected tools can retrieve.

## 7. Non-negotiable restrictions

`GOVERNANCE = KEEP_BLOCKED`  
`IMPLEMENTATION = NOT_AUTHORIZED`  
`BRIDGE_NOT_READY`

No Codex CLI/App Server/model turn, local preflight, canary, test, build or runtime. No authentication, quota/usage query, installation, update, new spend, M0A access, inspection of local checkout, `data/`, SQLite, secrets or configuration, and no retry or bypass of the blocked MCP reader. No merge, implementation or promotion. Owner decision C remains binding.

The only scope of this change is documentary continuity. Publishing a pointer or receiving a documentary PASS does not release any operational gate.
