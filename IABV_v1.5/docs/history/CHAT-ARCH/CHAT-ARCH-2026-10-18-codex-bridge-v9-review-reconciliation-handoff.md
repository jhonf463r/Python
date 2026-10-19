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

Path: `IABV_v1.5/docs/history/CHAT-ARCH/IABV_CODEX_contract_review_bundle_v9_2026-10-18.md`

- Size: 177,272 bytes.
- SHA-256: `3fdfd2f6ea3ca6b38f179341b5807e70c95bdde1e8486b0a047032832d0c5e17`.
- Git blob SHA after read-back: `17c22a4e9eef3267115816b85bf2ef398b6567b6`.
- Identity verification: `BYTE_HASH_VERIFIED`; the Git blob SHA matches the locally computed Git object identity of the original artifact.

### Ninth-review reconciliation

Path: `IABV_v1.5/docs/history/CHAT-ARCH/IABV_V9_NINTH_REVIEW_RECONCILIATION_2026-10-18.md`

- Size: 6,911 bytes.
- SHA-256: `459de4cd6fae2ce48d4c3eee7e2211edb0d78e23850dd76c121a0a9461d45445`.
- Git blob SHA after read-back: `8e3b456672ee01a6879898b171984d7dc513501a`.
- Identity verification: `BYTE_HASH_VERIFIED`; the Git blob SHA matches the locally computed Git object identity of the original artifact.

The ninth-review text supplied in conversation declares `PASS`, but no separate report artifact with its own verifiable hash was available. Record the result as `PASS_REPORTED`; reviewer identity and independence remain `OWNER_REPORTED`. A contract hash establishes bytes, not reviewer identity, independence, semantic truth, capability existence or operational authorization.

## 2. Reconciled documentary findings

**v8 provenance:** the cited artifact is the Owner-supplied file `IABV_CODEX_contract_review_bundle_v8_2026-10-18.md` (167,312 bytes; SHA-256 `1e7d4fa3a497d329305dba225a9b45d382d07f345e84e6b16d4d8c60c579726b`). Its bytes were hash-verified from the supplied artifact. v8 is not in the public repository tree, so a reviewer with only the repository cannot independently reproduce v8-dependent claims; the public v9 transition row remains directly checkable at §2.8 line 438.
- `N-85 = BEHAVIOR_TEXT_PRESENT_IN_OWNER_SUPPLIED_V8 / OPTIONAL_CLARIFICATION / PENDING_NINTH_REVIEW`: the supplied v8 text addresses the behavior in §2.8 lines 354–355 and invariant N-80 at line 460. Preserve `SEMANTIC_ACCEPTANCE = NOT_ESTABLISHED`; text presence does not establish semantic acceptance.
- `N-86 = BEHAVIOR_TEXT_PRESENT_IN_OWNER_SUPPLIED_V8 / OPTIONAL_CLARIFICATION / PENDING_NINTH_REVIEW`: the supplied v8 text permits the exact manual path-list route without inventory in §2.6 step 3 at line 259, without skipping MaterializationAuthorization or other applicable steps. Preserve `SEMANTIC_ACCEPTANCE = NOT_ESTABLISHED`.
- `N-87 = DOCUMENTED_REQUIREMENT / CAPABILITY_NOT_DEMONSTRATED`: §2.12 specifies evidence needed for service-side exclusivity, but does not prove that such a pre-existing capability exists.
- `F-V8-02 = CONTRADICTED_BY_V8_SOURCE / NOT_ADOPTED_AS_NEW_DEFECT`: the transition `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE` is present in the Owner-supplied v8 artifact (§2.8 line 429) and in the public v9 bundle (§2.8 line 438). The v8 basis is subject to the provenance limitation above; do not add a duplicate defect.
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
3. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`

This handoff is the proposed current route for the IABV → Codex workstream after this PR is independently reviewed and merged. It does not replace or reorder the independent M0B Entry 280 route in the memory operating protocol. The v5 handoff remains byte-for-byte immutable historical evidence.

## 6. Mandatory continuation and global-frame activation

For every new IABV session, the acting AI must do the following before choosing an actor, drafting a prompt, or asking the Owner to restate context:

1. Read `IABV_v1.5/AGENTS.md` for repository instructions and verify the current remote `main` SHA. Pin source reads to that revision; separately identify any PR branch/head being reviewed.
2. Follow the canonical experience-activation sequence in `MEMORY-OPERATING-PROTOCOL.md`: `README.md → CURRENT-STATE.md top routing snapshot → objective-conditioned records via CONTEXT-INDEX.md → MEMORY-OPERATING-PROTOCOL.md → relevant source/history`. `CURRENT-STATE.md` remains the only current routing authority; historical `NEXT ACTOR` values and task-specific handoffs do not independently override it.
3. Classify the actual objective before retrieving history. For global vision, universal reasoning, cross-AI coordination, memory, learning or continuity, explicitly activate `UAAL-ROOT-001` and the relevant lineage listed in §7 below. Do not narrow the product objective to the current Codex/MCP subproblem merely because that subproblem is the active workstream.
4. Reconcile the current objective, current verified truth, settled Owner decisions, negative knowledge, previous failures/false positives, closed edges, existing-organ ownership and first open causal/evidential edge. Reopen completed work only for new contradictory evidence, a source change, a missing mandatory artifact or an explicit Owner instruction.
5. Recover exact artifacts before asking the Owner to resend them: search current-conversation attachments and the Files Library using the supported retrieval path, then check the exact repository path/ref. Verify byte identity or blob SHA on read-back when artifact identity matters. Never guess a sandbox path. Keep `NOT_SEARCHED`, `NOT_FOUND`, `NOT_RECOVERED` and `UNRESOLVED` distinct.
6. Recompute the actor from the first open edge using required capability, actual access, independence, intervention cost and expected information gain. Every cross-IA handoff must name `IA DESTINO`, exact source revision/paths/identities, scope, prior evidence, required result, forbidden actions, stop conditions and verifier where determinable.
7. Turn relevant prior failures into concrete task constraints or acceptance gates; merely quoting history or paraphrasing the Owner's already-settled idea does not satisfy experience activation. If the user says the point is already established, perform the canonical retrieval and state what existing concept/record covers it before asking for additional explanation.
8. After any material actor result, reconcile claims against the exact source, classify its evidence status, derive any justified Knowledge/Method/Relation/Routing Delta, update only the appropriate existing memory projection, and fetch the writeback back to verify it. A report/comment is not published until read-back confirms it.

## 7. Global objective, parent lineage and architecture guardrails

**This PR is a task-specific IABV → Codex bridge-continuity route. It is not the Universal Adaptive Algorithm, not the whole product objective, and not a new memory/coordinator organ.** Its place is beneath the existing universal concept hierarchy and collaboration protocol. Never let the immediate bridge work redefine the root objective.

The following source artifacts were read from the canonical base snapshot `main @ d3a4212b6de36254bf45d5e655d684d0640a0706`. They are part of the established project context, not new theories introduced by this PR:

- `UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md` — Git blob `2e42ce7dd1615f83cb690b226e2a27af90190751`; defines `UAAL-ROOT-001`, derived concept genealogy and promotion gates.
- `CHAT-ARCH-2026-10-03-037-laptop-native-free-first-cross-ai-objective.md` — blob `b873bc27b5124240abffdd4002ea31bd9d0ac7d6`; defines the broader laptop-native, free-first, cross-AI objective.
- `CHAT-ARCH-2026-10-03-042-unified-interaction-memory-space-time-continuity.md` — blob `f9eef31860d039bce5507c5b9dd795e32c580edb`; defines the time-indexed interaction-episode model and the boundary between historical record and current routing authority.
- `CHAT-ARCH-2026-10-06-094-chat-full-absorption-universal-routing-reconciliation.md` — blob `23505c9e3a6a1bd2d1aeb08c310d2bfb9d9f16eb`; defines capability-fit routing and reserves “learning” for verified prior experience later reused to change a decision or behavior.
- `IABV-COLLABORATION-COORDINATION-PROTOCOL-2026-10-04.md` — blob `b5f614c11ca894b80e62a03c854b539d9493209b`; defines canonical frame-entry, objective-conditioned retrieval, actor routing, frame-exit and writeback.

Apply the existing model rather than inventing a parallel one:

`objective → current verified truth → relevant activated experience → first open causal/evidential edge → required capability → capability-fit actor/realization → smallest discriminating action → expected observation → observation → independent verification → reconciliation → Knowledge/Method/Relation/Routing Delta → later reuse test`.

Treat `CURRENT-STATE.md` as current routing authority; `CONTEXT-INDEX.md` as objective-conditioned navigation; `MEMORY-OPERATING-PROTOCOL.md` as memory/evidence method; `SYMBIOSIS-MAP.md` as cross-IA capability/transfer evidence; `UNRESOLVED-KNOWLEDGE.md` as unresolved ideas/open questions; `ARCHIVE-REGISTRY.md` as provenance/absorption index; and registered `CHAT-ARCH` records as episode/history evidence. Do not create competing authorities or indiscriminately copy the whole archive into every task.

Relevant concept families already identify `UAAL-D003` (capability/resource fabric), `UAAL-D004` (adaptive realization selection), `UAAL-D006` (external AIs as capability realizations) and `UAAL-D008` (knowledge plasticity). Their source documents classify the complete causal loop as partial or not proven end-to-end. GitHub coordination currently serves as an externalized control surface; it is not proof that the IABV runtime already performs autonomous context activation, actor launch, result ingestion and causal reuse.

The actual developmental success criterion is stronger than storing memory or getting an AI to agree: a later non-identical objective must retrieve verified experience, use it to change a justified decision/action, permit independent verification of that change and reduce routine Owner transport without losing provenance or governance. Until that is observed, describe the universal loop as design intent / hypothesis, not a completed capability.

## 8. Non-negotiable restrictions

`GOVERNANCE = KEEP_BLOCKED`  
`IMPLEMENTATION = NOT_AUTHORIZED`  
`BRIDGE_NOT_READY`

No Codex CLI/App Server/model turn, local preflight, canary, test, build or runtime. No authentication, quota/usage query, installation, update, new spend, M0A access, inspection of local checkout, `data/`, SQLite, secrets or configuration, and no retry or bypass of the blocked MCP reader. No merge, implementation or promotion. Owner decision C remains binding.

The only scope of this change is documentary continuity. Publishing a pointer or receiving a documentary PASS does not release any operational gate.
