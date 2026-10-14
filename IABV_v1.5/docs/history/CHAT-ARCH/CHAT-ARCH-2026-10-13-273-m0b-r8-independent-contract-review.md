# CHAT-ARCH-2026-10-13-273 — Independent review of M0B-R8 repository-read contract

- Episode ID: CHAT-ARCH-2026-10-13-273
- Review date: 2026-10-13, America/Bogota
- Public documentation baseline before this write: `main` at `0c9d06c306064c2e0b3c7c218702e40ebd45ca98`
- Reviewed contract: Entry 272, Git blob `5a55a9dd4ca2d7e16ee727950111a093470bf8b4`
- R5 governance/source reconciliation: Entry 269, Git blob `05fe1fe713e6282ba5e1e7338bec93ec92d99d53`
- Pinned public source baseline cited by the earlier review: `559f4ea20a9a9163cd9a9839b11d9991933f8c07`
- Result: `M0B_R8_CONTRACT_PASS_WITH_REQUIRED_REPAIRS`
- Design disposition: R8's separation-of-authority model is accepted as a provisional design baseline with the two normative clarifications in this record.
- Operational posture: `KEEP_BLOCKED`; no implementation, local M0A access, tests/runtime, or IABV/Codex App Server launch.

## 1. Review scope and decision

This was an independent contract review against Entry 272 and the R5 source/governance reconciliation in Entry 269. It did not repeat the bounded authority search, inspect private/local source, or assert anything about the actual M0A checkout.

**Verdict: PASS WITH REQUIRED REPAIRS.** R8 has the correct core separation and conservative denial posture. Its effective design baseline must include the two clarifications below before an implementation contract can be considered complete: (A) race-resistant path/object binding at the actual reader boundary, and (B) explicit, fail-closed semantics for determining which governance blocks apply to a target.

These are contract-level refinements, not evidence that an implementation already exists.

## 2. What passes

The proposed contract is consistent with Entry 269/R5 and Entries 270–272 in keeping separate:

1. a metadata-only diagnostic that never grants access;
2. evidence of a fresh interactive approval, with independently verifiable principal provenance;
3. issuance of a distinct, target- and scope-bound read decision by a trusted authority;
4. reader-side verification immediately before each file read or directory listing; and
5. a durable, correlatable operation receipt with finite, atomic accounting.

R8 correctly rejects generic `approved=True`, a free-form `approved_by`, `VALIDATED`, ApprovalMemory auto-resolution, Devin external-action authorization, and observation permission as substitutes for repository-read authority. It also preserves the reader's existing path/sensitive-file controls and the 1 MiB per-file and 200-entry per-listing ceilings. It does not claim that the proposed five-minute lifetime is an existing code fact.

No conflict with R5's diagnostic/read separation was identified. A supported, explicit release of the applicable governance block remains a separate prerequisite; the contract must not infer that a read decision automatically clears a block.

## 3. Required clarification A — race-resistant path and object binding

**Issue:** Entry 272 requires normalization, containment, rejection of traversal and symlink/junction/reparse escapes, and revalidation before each operation. Those requirements are necessary, but the contract should explicitly prevent a time-of-check/time-of-use (TOCTOU) race between checking a pathname and opening or enumerating it.

**Normative addendum for R8.1:**

- The reader MUST bind the authorization check to the actual filesystem object used for the operation, not merely to a string path checked earlier.
- File open and directory enumeration MUST use race-resistant, root-contained handle-based operations (or a platform-equivalent mechanism) that prevent links/reparse points or concurrent path substitution from redirecting access outside the authorized checkout.
- The reader MUST verify the opened handle/object's identity and containment against the approved checkout/path scope and MUST read/enumerate through that same verified handle/object.
- The reader MUST NOT rely only on “canonicalize path, then open path by name” where the name can change between check and use.
- If the supported runtime/platform cannot establish these guarantees, the operation MUST be denied. No fallback reader or alternate tool is allowed.

This addendum narrows how existing path-containment requirements are enforced; it does not authorize a new path around the governance gate.

## 4. Required clarification B — applicable-block scope semantics

**Issue:** Entry 269 records a separate source-level risk: the inspected `_governance_block_for_route` active-block filter checks `assistant_kind`, not `target_scope`. Entry 269 explicitly does not establish this as the cause of the reported M0A refusal. Entry 272 requires an applicable-block check, but the effective contract must make scope matching unambiguous and cannot silently trust the current helper as a complete scope evaluator.

**Normative addendum for R8.1:**

- Before any grant or block release, the reader/authority MUST evaluate active-block applicability against the verified request identity and every supported scope dimension in the governance contract.
- The conformance matrix MUST distinguish at least: an active global block; an active matching assistant-scoped block; an active matching resource/workspace/checkout-scoped block; a proven nonmatching scoped block; multiple concurrent blocks; and an unknown, malformed, or unsupported scope.
- Unknown or unsupported scope, missing target identity, conflicting block metadata, or inability to evaluate applicability MUST fail closed. A block cannot be ignored merely because a field was not examined by an existing filter.
- A nonmatching block may be treated as non-applicable only when the relevant target identity is independently established and the supported scope semantics prove the mismatch.
- A read decision MUST NOT clear or override a block unless an independent, trusted mechanism explicitly supports release of that exact block for the authorized scope.
- Add a separate conformance case for the currently documented `assistant_kind` versus `target_scope` discrepancy. Preserve it as an independent hazard; do not describe it as the proven cause of the M0A denial.

The exact set and meaning of scope values must be derived from the authoritative governance model at implementation time; this review does not invent a new production schema.

## 5. Evidence and provenance classification

- `PROVEN_BY_SOURCE`: Entry 269 records verified public-source behavior and a bounded observation that the inspected active-block filter checks `assistant_kind` rather than `target_scope`; its cited object SHAs/anchors should be used instead of earlier mismatched line ranges.
- `OWNER_REPORTED`: earlier reports describe a local reader being blocked and distinguish M0A from other worktrees. This review did not inspect the local checkout or receive fresh local proof.
- `PROPOSED`: all Entry 272 data contracts/tests, the two R8.1 normative addenda above, handle-based TOCTOU mitigation, and the expanded block-scope conformance matrix.
- `UNPROVEN`: authenticated Owner-principal provenance; production issuer and integrity boundary; exact live MCP/workspace/checkout identity; reliable target-state binding; supported release semantics for the actual active block; and whether any private/local implementation provides these properties.

Do not elevate design language or a GitHub document commit into proof of an implemented authority.

## 6. Adoption boundary and next action

The **architectural decomposition** in R8 is accepted as the provisional design baseline, amended by Sections 3 and 4 of this entry. It is **not implementation-ready** until those clauses are incorporated into the design artifact and independently challenged.

Next actor: **Sonnet/Claude**, as a focused adversarial design reviewer, to assess Entry 272 together with this R8.1 addendum. That review must stay at the contract level; no new broad code archaeology is needed for this step.

The review does not authorize code changes, tests, builds, runtime execution, credentials/authentication, use of the blocked reader, local M0A inspection, or launch. Any future implementation and any future local read remain separate explicit decisions. Maintain `KEEP_BLOCKED`.

## 7. Verification boundary

This episode used read-only GitHub retrieval of the canonical memory documents and contract, plus independent semantic analysis. No local checkout, private source, credentials, runtime, or test environment was accessed. No code was changed and no tests/builds were executed. The only writeback associated with this episode is documentation of the review and its continuity pointers.
