# M1A G1 — Independent governance enrollment authority: candidate design

- Date: 2026-10-24 (America/Bogota).
- Task: `M1A_G1_GOVERNANCE_OWNED_ENROLLMENT_AUTHORITY_DESIGN`.
- Repository: `jhonf463r/Python`.
- Design baseline: M1A v1.0.1, adopted as design only; implementation prerequisites remain open.
- Source baseline: live `main` `c3bc9d8b4f727483081cf24650d4e7209687024c`.
- Status: isolated documentary candidate; not canonical, not accepted for implementation, and not an authority artifact.
- Scope: define the evidence contract for the first unsatisfied G1 dependency. This document does not identify, create, enroll, trust, or appoint an authority.

## 1. Decision boundary and current truth

The current routing authority in [CURRENT-STATE.md](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md) records:

```text
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_AUTHORITY=NOT_IDENTIFIED_BY_OWNER; EXISTENCE_NOT_PROVEN_ABSENT
OWNER_TO_BOOTSTRAP_AUTHORITY=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
BOOTSTRAP_AUTHORITY_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

The decision to produce this design candidate is not a decision to revoke Option D. Until genuinely new independently verifiable authority evidence or a distinct explicit Owner decision changes the basis, no-bootstrap/fail-closed remains controlling.

Evidence classes used here:

- **MAIN_SOURCE_VERIFIED** — text retrieved from the exact public `main` commit above. It establishes the documented state and adopted design text, not local or runtime behavior.
- **OWNER_REPORTED** — a statement explicitly attributed to the Owner in canonical history; not independently authenticated.
- **DESIGN_REQUIREMENT** — a proposed acceptance property, not an existing mechanism.
- **UNKNOWN / NOT_ESTABLISHED** — the required evidence was not supplied or verified. This does not prove that an asset is absent.

No authority asset, root, custodian, mandate, verification channel, issuer credential, or exact-server binding is identified by this candidate.

## 2. Evidence basis and closed investigations

The following exact-main documents were consulted as design inputs:

1. [AGENTS.md](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/AGENTS.md)
2. [CHAT-ARCH README](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/README.md)
3. [CURRENT-STATE.md](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
4. [CONTEXT-INDEX.md](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md)
5. [MEMORY-OPERATING-PROTOCOL.md](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md)
6. [M1A v1.0.1 implementation-prerequisite evidence matrix](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md)
7. [Entry 274 — consolidated repository-read decision contract](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md)
8. [TPM preflight branch closure](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-TPM-preflight-branch-closure.md)
9. [Governance-owned bootstrap authority design static reconciliation](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-static-reconciliation.md)

The source conclusions relevant to this design are:

- The matrix marks G1's runtime trust anchor and authenticated principal as unverified and requires independently verifiable root material/chain, authority mandate, provenance/revocation, and exact instance/revision scope. It also states that G2 needs an authorized versioned catalogue and revocation, and G3 needs a versioned server-side operation-to-target resolver. All eight implementation gates remain open.
- Entry 274 separates requester, read-decision issuer, reader verifier, and operation ledger/receipt authority; approval is not authority; target identity must come from trusted server context; a read decision cannot release a governance block; and a missing/unavailable revocation or ledger fails closed. Entry 274 is a contract source, not proof those mechanisms are implemented.
- The TPM closure says historical TPM command output was not recovered, TPM availability is unverified, and that branch is closed for now. This design does not reopen TPM or any other previously closed identity investigation.
- The G1 reconciliation says a prior authority bootstrap document was a design candidate, not an implementation approval; a proposed bootstrap authority is a role, not an existing service. It records that no independent root, custodian, out-of-band channel, root mandate, or authenticated Owner binding was presented. Its reported prior candidate is not present as a file on this exact `main` revision; this document does not reconstruct or claim to preserve its bytes.

## 3. Terms and authority separation

For this design, an **enrollment authority** is a governance-authorized principal or institution that can establish an initial trust binding for the IABV authority chain. The term names a required role only. It does not assert that such a party or service exists.

The following roles MUST remain distinct and independently accountable:

1. **Owner / governance principal** — the human or governance principal entitled to make the relevant IABV decisions.
2. **Enrollment authority** — the independently trusted authority that verifies the governance mandate and authorizes enrollment. It cannot be created, selected, or vouched for solely by the requester, the future issuer, the reader, or IABV itself.
3. **Authorization issuer** — issues narrowly scoped, expiring decisions only after validating the enrolled trust chain and current policy.
4. **MCP server / reader verifier** — derives the actual server, workspace, checkout, operation, and target from its trusted execution context and independently checks each decision immediately before an operation.
5. **Catalogue publisher and revocation authority** — publishes versioned operation/policy material and current revocation state; neither is inferred from a file hash or issuer identity alone.
6. **Independent block owner/releaser** — decides any applicable operational-block release through a distinct authority path. A read authorization cannot release a block.
7. **Requester/agent** — may propose an operation and display its intent; cannot choose the authority, self-enroll, issue its own permit, supply authoritative target identity, or release a block.

Administrative control of a machine, a successful login/MFA event, a Windows SID, a GitHub account/commit, conversational consent, a self-signed key, or a hash without an authenticated publisher chain does not by itself satisfy G1.

## 4. Minimum G1 enrollment evidence package

G1 is eligible for reconsideration only if a verifier can validate all mandatory evidence below through a route independent of the requesting agent and the candidate issuer. The exact protocol, platform API, identity provider, cryptographic format, and custodial service remain unspecified until real, supported authority assets and their capabilities are evidenced.

### E1 — Authority identity and mandate

Evidence must identify the enrollment authority, its accountable custodian, and the governance mandate that permits it to enroll or delegate authority for this IABV deployment. The mandate must identify the covered project/deployment and its limits, effective period, and revocation mechanism.

**Producer:** the actual governing body or pre-existing institution that owns the mandate.  
**Verifier:** an independent party or verification service designated by governance, using an authenticated source not controlled by the requester or issuer.  
**Current state:** UNKNOWN; no authority/custodian/mandate is established.

### E2 — Independent trust anchor and verification channel

The authority's trust material (for example, a root public-key fingerprint or equivalent independently verifiable credential) must be obtained and checked through an already trusted, out-of-band channel. The verifier must establish source authenticity, chain validity, scope, validity period, and current revocation. A digest copied from the same repository, machine, chat, or candidate being authorized is not an independent trust path.

**Producer:** the pre-existing authority and its custodian.  
**Verifier:** a governance-designated independent verifier using the authority's documented channel and a separately authenticated reference.  
**Current state:** UNKNOWN; no qualifying root or channel is identified.

### E3 — Owner-to-governance-principal binding

Evidence must bind the accountable Owner to the principal recognized by the authority for the stated governance role. The binding must distinguish identity authentication from decision authority: MFA may authenticate a login but does not grant IABV governance mandate on its own. The verifier must check the authority's current role/mandate and revocation, not rely on a name, email, SID, or requester assertion.

**Producer:** the authority that owns the principal/role record.  
**Verifier:** the independent verifier from E2.  
**Current state:** NOT_ESTABLISHED. The Owner's reported Entra/Authenticator preparation is OWNER_REPORTED and is not trust in IABV.

### E4 — Authority-to-issuer delegation

A signed or equivalently verifiable delegation must bind the authority to a specific issuer identity/key, permitted decision classes, audience, deployment scope, validity interval, and revocation source. It must prohibit the issuer from delegating its own trust, widening scope, or releasing governance blocks unless separately authorized by the applicable block owner.

**Producer:** the enrolled authority.  
**Verifier:** the independent verifier and, on each use, the reader.  
**Current state:** NOT_ESTABLISHED; no issuer or credential is identified.

### E5 — Issuer-to-exact-server/reader binding

The issuer and reader identities must bind to the actual intended server instance and code/operation revision, not merely a hostname, user-provided path, repository name, transport label, or copied configuration. The binding must have a trusted, documented derivation from the running server context, be resistant to requester-controlled substitution, and specify what changes invalidate it. The method must also provide revocation and re-enrollment behavior.

**Producer:** the operator/platform that can measure or attest the actual server context under the authority's mandate.  
**Verifier:** the enrolled authority at enrollment and the reader before every protected operation.  
**Current state:** NOT_ESTABLISHED. No supported local instance-attestation mechanism is evidenced by the sources reviewed.

If an existing authority cannot produce any item, the evidence state is incomplete. Do not replace missing items with a newly created trust root, TOFU, a Git hash alone, or an implementation placeholder.

## 5. Enrollment sequence and state machine

This is a proposed protocol shape, not an existing flow:

```text
UNENROLLED
  -> EVIDENCE_SUBMITTED (provenance recorded; no trust implied)
  -> AUTHORITY_AND_MANDATE_VERIFIED
  -> OWNER_ROLE_BINDING_VERIFIED
  -> ISSUER_DELEGATION_VERIFIED
  -> SERVER_READER_BINDING_VERIFIED
  -> ENROLLED_FOR_NAMED_SCOPE
```

Each transition requires a durable evidence reference, producer identity, verifier identity, source/channel, validity interval, applicable revocation check, and a negative-result record. A state transition is not inferred from collecting documents or setting a boolean. The final enrollment statement is signed/attested by the independent authority and identifies the exact scope and revisions it approves.

At any transition:

- failed/ambiguous identity, absent evidence, unsupported verifier, invalid chain, unknown mandate, expired material, revocation, or unavailable revocation source => remain un-enrolled and fail closed;
- evidence from the requester, candidate issuer, or reader about its own authority => reject as circular;
- a changed Owner role, issuer key, reader/server measurement, policy/catalogue revision, or scope => invalidate the affected binding and require fresh verification;
- revocation or compromise => revoke the delegation, stop issuance, and deny protected operations until a separately verified recovery ceremony completes;
- recovery cannot be approved by the compromised issuer or the requester alone and must use a documented independent authority plus audit record.

No state-machine transition here unlocks a protected read. Entry 274's fresh interactive approval, target/path checks, independent block-release rule, budgets, ledger, and reader-side revalidation still apply after G1; this design does not amend them.

## 6. G1-to-G2/G3 dependency order

```text
G1: independent authority + verified Owner role + issuer/server trust binding
  -> G2: authority-published, versioned catalogue and producer-class policy
       + integrity verification + current revocation/freshness
  -> G3: versioned server-side resolver mapping each registered operation/call site
       to its actual implementation and canonical target
  -> G4-G8: typed admission and validation, complete block aggregation and
       independent release, Entry 274 reader/ledger integration,
       separately authorized conformance tests, exact-revision independent review
```

G2 may not be bootstrapped by the issuer signing its own catalogue. It requires a publisher identity and revocation authority rooted in the independently verified G1 chain. G3 may not trust caller-provided `operation_scope`, repo/path strings, or names; the server must resolve the actual registered operation and target using a versioned authority-controlled mapping and actual execution context.

G1 completion is necessary but not sufficient for G2/G3, repository-read authorization, or bridge readiness. No gate should be marked closed because a design or evidence template exists.

## 7. Required receipts and evidence lifecycle

The future authority system must distinguish:

1. **Evidence receipt** — what source/authority submitted which artifact, when, and through what channel.
2. **Verification receipt** — which independent verifier checked which claims and revocation state against which authority/policy revision, with result and limitations.
3. **Enrollment decision receipt** — authority-signed/attested decision binding Owner principal, issuer, exact server/reader identity, scope, validity, and revocation handles.
4. **Use/operation receipt** — a separate request, approval, operation-intent, observed result, delivery outcome, and correlation reference recorded by the server-side ledger.
5. **Reconciliation/fetch-back receipt** — proof that the durable records can be read back and match their committed identities; this is not proof of later learning.

Receipts are evidence, never authority by themselves. No receipt may contain credentials, private keys, secrets, unnecessary personal data, or protected file content. A failed ledger write, mismatched identity, unknown result, or missing revocation response denies content delivery. An attempt or a returned success flag does not prove content delivery or persistence.

Custody, tamper evidence, retention, access, recovery, and revocation of these receipts require separate governance decisions. No durable store or receipt service is asserted to exist.

## 8. Owner and governance decisions that cannot be delegated to the agent

Before any authority enrollment can be considered, the Owner/governance must provide a decision or evidence for each unresolved item:

1. Identify or designate the *real, pre-existing* governance authority that already has a mandate over the IABV deployment, or state that none is known and continue Option D.
2. Name the accountable custodian and independent verifier, and provide an independently reachable official verification channel. These roles must not collapse into the requester/issuer/reader.
3. Supply the authority mandate and the evidence linking the Owner's governance role to the verified principal. Do not publish personal identifiers or secrets in a public PR.
4. Identify how the actual server/reader instance can be independently bound using a supported platform mechanism; if no such mechanism is available, keep this requirement open.
5. Decide who controls catalogue publication, issuer revocation, receipt custody, and independent block release. These are separate powers.
6. State whether a new design amendment is needed after these facts are established. This candidate itself does not amend M1A v1.0.1 or Option D.

An Owner naming an authority in chat may nominate a candidate, but does not prove its identity, mandate, custody, independent channel, or binding. The agent must not choose among institutions, register credentials, create services, or assert that a nominated authority is suitable.

## 9. Stop conditions

Stop with `G1=NOT_ESTABLISHED` and preserve the fail-closed state if:

- no existing authority and independent verification channel are evidenced;
- authority mandate or Owner-to-principal binding is absent;
- the enrollment authority is controlled by the requester, issuer, or reader;
- exact server/reader binding has no supported trusted derivation;
- current revocation cannot be independently queried;
- the purported proof is only an Owner assertion, MFA success, SID, GitHub account/hash/commit, candidate document, local file, or self-issued signature;
- a governance block is active and its owner has not issued a distinct, valid release through a supported route;
- any required evidence is ambiguous, stale, inaccessible, or unverifiable.

The valid outcome in any of these cases is `UNENROLLED / BLOCKED`, not a guessed fallback. Reconsideration requires genuinely new authority evidence or a separate explicit Owner decision that changes the basis recorded in canonical routing.

## 10. Candidate disposition

This document proposes the minimum evidence contract for reconsidering G1; it does not claim the required authority exists. It neither modifies the adopted M1A v1.0.1 design nor displaces the ratified no-bootstrap decision.

```text
TASK=M1A_G1_GOVERNANCE_OWNED_ENROLLMENT_AUTHORITY_DESIGN
DESIGN_STATUS=DOCUMENTARY_CANDIDATE; NOT_CANONICAL; NOT_ACCEPTED
BASE_MAIN_SHA=c3bc9d8b4f727483081cf24650d4e7209687024c
CURRENT_OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
CURRENT_NEXT_ACTION=PRESERVED
EXISTING_AUTHORITY_EVIDENCE=UNKNOWN; NOT_INSPECTED
OWNER_TO_AUTHORITY=NOT_ESTABLISHED
OWNER_TO_GOVERNANCE_PRINCIPAL=NOT_ESTABLISHED
AUTHORITY_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER_READER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
PROTECTED_READS=NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

**Single Owner/governance decision that would unlock the first real prerequisite:** identify/designate a real pre-existing independent authority and submit its mandate, custodian, independent verification channel, and Owner-to-authority/principal binding evidence for independent verification. If that evidence cannot be supplied, retain Option D and the current block.

## References

- [Current canonical routing and Option D](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
- [M1A v1.0.1 evidence-gate matrix](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md)
- [Entry 274](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md)
- [TPM preflight closure](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-TPM-preflight-branch-closure.md)
- [G1 design reconciliation](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-static-reconciliation.md)
