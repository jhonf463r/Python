# M1A G1 — Governance-owned bootstrap authority design: static reconciliation

- Date: 2026-10-23 (America/Bogota).
- Task: `M1A_G1_GOVERNANCE_OWNED_BOOTSTRAP_AUTHORITY_DESIGN_ONLY`.
- Review type: independent static/documentary review against the exact public GitHub commit; no local checkout or runtime access.
- Candidate branch: `codex/m1a-g1-governance-owned-bootstrap-authority-design-20261023`.
- Candidate commit: [`675c3bdd046de04e4e7d6bb70d616dbce1354e06`](https://github.com/jhonf463r/Python/commit/675c3bdd046de04e4e7d6bb70d616dbce1354e06).
- Candidate document: [Governance-owned bootstrap authority design candidate](./CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-candidate.md).
- Verified candidate blob: `feb61c72e44ec61179fba7827515ab58348f4890`.

## 1. Candidate identity and diff

GitHub confirms:
- Remote `main` at review start and expected baseline: `af5fc7e7b10ac9941406f67bdf2a0cf2aa5b6b68`.
- Candidate commit parent: exactly `af5fc7e7b10ac9941406f67bdf2a0cf2aa5b6b68`.
- Candidate tree: `b4e8c3bfb438fa4c326735993367cae03896f131`.
- Compare: `ahead_by=1`, `behind_by=0`, exactly one added file and no deletions.
- Only changed path: `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-candidate.md`, 256 additions and zero deletions.
- The document was fetched at both the branch ref and exact commit; both yielded blob `feb61c72e44ec61179fba7827515ab58348f4890`.

The five canonical front doors at the expected baseline were fetched and identity-checked using the blobs recorded in the document. The candidate diff modifies none of them, no product sources, tests, contracts, or runtime files. This is evidence about public GitHub refs only, not the Owner's local checkout.

## 2. Static design verdict

**Disposition: `CONDITIONAL_DESIGN_REVIEW; OPTION_D_REQUIRED_WITH_CURRENT_EVIDENCE`.** The document is a materially usable design proposal for the *decision boundary*, but it remains a documentary candidate and is not accepted for implementation. It recommends option D—no bootstrap and fail-closed denial—because the existing evidence does not establish a pre-existing independent trust root, its custodian/channel, the root's mandate over IABV, or the Owner-to-local-principal binding.

Positive findings:
- It compares four distinct paths: pre-existing Owner root (A), pre-existing organizational authority (B), a new-root ceremony delegated from an already trusted authority (C), and no demonstrated anchor (D).
- It correctly rejects a self-generated root, first-run trust-on-first-use, local administrator privilege, a Windows SID alone, GitHub hashes/commits, conversational consent, or the future issuer itself as proof of initial authority.
- It defines a proposed Governance Bootstrap Authority (GBA) as a role, not an existing service, and separates governance, identity, installation, issuer, reader, catalogue/revocation, target resolver, block release and ledger custody.
- It provides a conditional enrolment sequence, a state machine, delegated artefacts, lifecycle/recovery controls, explicit pending decisions, and a future conformance matrix.
- It maintains `GOVERNANCE=KEEP_BLOCKED`, `G1=NOT_ESTABLISHED`, and `READ_LIST=FAIL_CLOSED`.

## 3. Previous receipt-semantics finding addressed

The prior design reconciliation required a separation between a durable pre-release record and evidence of actual delivery. The current candidate section 8 now distinguishes:
1. durable decision/pre-release record;
2. operation attempt;
3. observed operation result;
4. delivery attempt/outcome;
5. correlated receipt;
6. canonical persistence/fetch-back;
7. later causal reuse.

It explicitly says an attempt does not prove content was delivered, missing observation stays `UNKNOWN`, visible output does not prove canonical persistence, and matching IDs alone do not prove causal learning. This addresses the previous documentary finding at design-text level. It does not prove any of these mechanisms exist or operate correctly.

## 4. Remaining hard boundary

No existing independent root, root custodian, out-of-band verification channel, or authenticated evidence linking the root to the human Owner's responsibility for IABV has been presented. Options A and B are usable only if actual independently verifiable evidence is supplied. Option C is not a way to manufacture trust from nothing: its ceremony is admissible only when an already-trusted external authority establishes the new root and its mandate. If that first authority cannot be verified, option D remains mandatory.

The following remain unestablished and are not closed by this design:
- `OWNER_TO_BOOTSTRAP_AUTHORITY` and `OWNER_TO_WINDOWS_PRINCIPAL`;
- `BOOTSTRAP_AUTHORITY_TO_ISSUER` and exact server/reader binding;
- real issuer key custody and requester/issuer/reader separation;
- runtime reader-side decision verification;
- catalogue publisher, authenticated complete active-block set and authoritative revocation/freshness;
- versioned server-side operation-to-target resolver;
- independent per-block release;
- durable ledger and correlated runtime receipts;
- race-resistant resource containment.

The source's design verdict `PASS_WITH_OPEN_AUTHORITY_DECISIONS` is therefore accepted only as the candidate author's documentary characterization, not as operational PASS or independent authority evidence. Our review disposition remains conditional. M1A v1.0.1 is the adopted normative design baseline only; all eight implementation prerequisite gates remain open.

## 5. Routing and next decision

The present evidence requires **option D**. Owner/governance must either:
- provide/designate an authority whose identity, mandate, root/fingerprint, custodian, revocation and independent verification channel can actually be evidenced; or
- ratify that no qualifying authority is available and retain the block.

Do not create a root, credential, issuer, service, authority registry, or implementation placeholder to escape the block. Do not repeat broad Windows/TPM/OIDC/WebAuthn investigations. No implementation, tests, build, runtime, real transport, protected read, merge, deployment or release is authorized. There is no automatic follow-on.

```text
TASK=M1A_G1_GOVERNANCE_OWNED_BOOTSTRAP_AUTHORITY_DESIGN_ONLY
CANDIDATE_BRANCH=codex/m1a-g1-governance-owned-bootstrap-authority-design-20261023
CANDIDATE_HEAD=675c3bdd046de04e4e7d6bb70d616dbce1354e06
CANDIDATE_PARENT=af5fc7e7b10ac9941406f67bdf2a0cf2aa5b6b68
CANDIDATE_TREE=b4e8c3bfb438fa4c326735993367cae03896f131
CANDIDATE_BLOB=feb61c72e44ec61179fba7827515ab58348f4890
CANDIDATE_DIFF=ONE_NEW_DOCUMENT_ONLY
STATIC_REVIEW=CONDITIONAL_DESIGN_REVIEW; OPTION_D_REQUIRED_WITH_CURRENT_EVIDENCE
RECEIPT_STAGE_SEMANTICS=DESIGN_DEFINED; NOT_RUNTIME_VERIFIED
ROOT_BOOTSTRAP_OPTION=D_REQUIRED_WITH_CURRENT_EVIDENCE
EXISTING_TRUST_ROOT=NOT_ESTABLISHED
ROOT_AUTHORITY_CUSTODIAN=UNRESOLVED
ROOT_VERIFICATION_CHANNEL=UNRESOLVED
OWNER_TO_BOOTSTRAP_AUTHORITY=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
BOOTSTRAP_AUTHORITY_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
M1A_NORMATIVE_DESIGN=V1.0.1_DESIGN_ONLY
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
G1=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
READ_LIST=FAIL_CLOSED
PRODUCT_SOURCE_CHANGES=NONE
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_OWNER_CHECKOUT_ACCESSED=NO
CREDENTIALS_OR_SERVICES_CREATED=NO
MERGED=NO
DEPLOYED=NO
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_ONLY
NEXT_OWNER_DECISION=PROVIDE_VERIFIABLE_INDEPENDENT_AUTHORITY_EVIDENCE_OR_RATIFY_OPTION_D
```
