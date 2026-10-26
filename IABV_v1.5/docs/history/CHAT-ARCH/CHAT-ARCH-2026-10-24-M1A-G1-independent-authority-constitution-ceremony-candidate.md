# M1A G1 — Governance constitution and appointment ceremony for an independent enrollment authority

- **Task:** `M1A_G1_GOVERNANCE_AUTHORITY_CONSTITUTION_CEREMONY_DESIGN_ONLY`
- **Date:** 2026-10-24 (America/Bogota)
- **Artifact class:** documentary design candidate; not canonical; not accepted
- **Base `main`:** `c3bc9d8b4f727483081cf24650d4e7209687024c`
- **Existing related candidate:** PR [#478 — evidence contract for G1 enrollment authority](https://github.com/jhonf463r/Python/pull/478)
- **Prior design input:** [governance-owned bootstrap authority design at commit `675c3bdd`](https://github.com/jhonf463r/Python/blob/675c3bdd046de04e4e7d6bb70d616dbce1354e06/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-candidate.md)

## 1. Purpose and exact gap

Prior design work already defines a conditional bootstrap ceremony, role separation, the minimum G1 evidence package, and the rule that a candidate root cannot vouch for itself. This document does **not** repeat that evidence contract or propose another technical identity mechanism.

It addresses the remaining upstream governance question:

> If no qualifying enrollment authority is currently known, who has legitimate mandate to constitute or appoint one, and how can an independent verifier authenticate that constituting act without trusting the system being bootstrapped?

The process must distinguish two separate claims:

1. **Constitution legitimacy:** a real person, body, or institution already has a verifiable mandate to establish or appoint the proposed authority for this deployment.
2. **Independent authenticity:** a verifier can authenticate that mandate and the appointment through a route not controlled solely by the requester, the candidate authority, the future issuer, or the reader being authorized.

Both claims are mandatory. Proof of only one is insufficient. A ceremony can organize evidence and decisions; it cannot manufacture the legitimacy or independent trust anchor that its own validity depends on.

## 2. Current evidence boundary

The live canonical `CURRENT-STATE.md` identifies `OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP` and `NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION`.

The Owner's current authorization commissions this **documentary design only**. It does not revoke Option D, identify an actual institution, establish an authority, accept a root, create credentials, or authorize implementation.

The following remain unknown or unestablished:

- `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`
- qualifying constituent authority, mandate, and accountable custodian
- independently authenticated channel for verifying a constituting act
- Owner-to-governance-principal binding
- authority-to-issuer delegation and issuer-to-exact-reader/server binding
- `G1=G2=G3=NOT_ESTABLISHED`
- `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`
- `GOVERNANCE=KEEP_BLOCKED`; `READ_LIST=FAIL_CLOSED`
- `IMPLEMENTATION=NOT_AUTHORIZED`; `BRIDGE=BRIDGE_NOT_READY`

“Not established” is not a finding that such an authority or asset is absent. No authority asset was inspected by this document.

## 3. Non-negotiable principle: authority cannot bootstrap itself

A newly named “Governance Bootstrap Authority” (GBA) is only a role until the mandate to establish it and the authenticity of that mandate have been independently verified.

The following do **not**, by themselves, establish an independent authority or trust root:

- the Owner's request or statement in chat;
- successful sign-in or MFA, including Entra/Authenticator;
- control of the local machine, administrator rights, a Windows SID, TPM availability, or a locally generated key;
- a GitHub account, repository, branch, commit, signed-looking document, hash, or PR;
- a candidate issuer or reader asserting its own authority;
- a self-signed certificate or key created during first run;
- a charter whose author and only verifier are the same party;
- an AI agent's recommendation, label, or attestation.

Cryptographic signing proves a relation to a key only after the relevant key and its authority are independently authenticated. A signature cannot, by itself, establish the signer's mandate.

## 4. Distinct roles and accountability

These roles must be identified and assessed separately. A role may be combined with another only if the governing mandate explicitly permits it, the threat model justifies it, and independence is not thereby defeated.

1. **Accountable Owner/requester** — expresses the intended project scope and may nominate candidates. A nomination is not proof of authority.
2. **Constituting authority** — the already legitimate governance body or institution with mandate to establish/delegate authority for this IABV deployment. Its own identity and mandate must be verifiable before it appoints anyone.
3. **Proposed enrollment authority (GBA)** — the candidate body/principal to be appointed for a narrowly documented enrollment mandate. It cannot validate its own appointment.
4. **Mandate custodian** — maintains the authoritative charter/delegation and can produce it through its official channel.
5. **Independent verifier** — checks the constituting authority, mandate, appointment, and channel from a separate trust path. It must not be the constituting authority or mandate custodian whose authority or record it is validating, the requester, the proposed GBA, the future issuer, or the reader validating its own authority.
6. **Authorization issuer** — later issues narrowly scoped, expiring decisions under a verified delegation; it cannot widen that delegation.
7. **MCP server/reader verifier** — later validates decisions against the actual server and operation context; it cannot appoint the GBA or authorize itself.
8. **Catalogue/revocation authority** — administers versioned catalogue and revocation material under a separately verified role.
9. **Independent operational-block releaser** — exercises any block-release power through a distinct route. G1 enrollment or read approval is not block release.

If no distinct independent verifier or source of legitimate mandate can be identified, the ceremony does not progress to trust establishment.

## 5. Three permissible governance outcomes

### Outcome A — A qualifying authority already exists

A real parent organization, board, governance body, regulator, custodian, or other institution may already hold the mandate. This outcome is eligible only after the mandate, scope, accountable custodian, current authority, and official verification channel are independently evidenced.

A name supplied by the Owner is only a candidate lead. It is not accepted evidence.

### Outcome B — A new enrollment authority is appointed by a verified constituent authority

A new GBA role may be appointed only if a **pre-existing, independently authenticated constituent authority** is first shown to have the mandate to make that appointment. The appointment must be explicit, scoped, time-bounded, revocable, and authenticated through a separate verification route.

This outcome delegates authority; it does not create a trust root from nothing. A newly appointed GBA still cannot be trusted by IABV until its appointment, mandate, custodianship, and root/delegation material meet the independent evidence requirements in the related G1 evidence contract.

### Outcome C — No legitimate constituent authority or independent route can be established

Stop. Preserve the no-bootstrap/fail-closed decision. Do not create a self-appointed GBA, call a generated key “the root,” or implement first-run trust-on-first-use to make the process appear complete.

This is a valid terminal outcome, not a process failure to be worked around by the agent. Reopening requires genuinely new authority evidence or a separate explicit Owner decision that changes the basis of the canonical routing; even that decision does not, by itself, satisfy the technical evidence gates.

## 6. Proposed constitution and appointment procedure

This is a future documentary protocol shape. None of these steps was executed.

### Phase 0 — Freeze scope and record the decision basis

Record the deployment/project covered, the requested governance powers, the current canonical baseline SHA, current no-bootstrap decision, evidence references, and what must remain blocked. Do not collect credentials or private keys in chat, a public issue, or a candidate document.

### Phase 1 — Establish the source of constituting authority

Identify the actual governing instrument or institutional mandate that gives the proposed constituting authority power over this deployment. Examples of *possible evidence classes*, not assumptions about this project, include an authenticated organizational charter, an authorized board decision, a contract/delegation, or an independently verifiable official mandate.

The evidence must demonstrate all of the following:
- the source's identity and authority to issue the mandate;
- that the mandate covers this project/deployment and the power to appoint an enrollment authority;
- the named decision-makers, any quorum or approval rule, scope, effective period, and revocation/supersession route;
- the accountable custodian and the official channel by which an independent verifier can authenticate the source.

A source controlled solely by the candidate GBA, issuer, reader, or requester is not an independent source.

### Phase 2 — Independently authenticate the source and mandate

A verifier distinct from the requester, proposed GBA, constituting authority, and mandate custodian obtains the mandate from an independently authenticated source. Before its finding can be relied on, the verifier's own identity, mandate, scope, effective period, and current revocation status must also be supported by a trust basis established before this ceremony and independently verifiable from the requester, proposed GBA, issuer, reader, and constituting authority/appointment under review. The verifier cannot authenticate its own mandate solely with its own claims, keys, repositories, documents, or signatures, or rely solely on the same appointment it is evaluating. The verification route must permit detection of expiry, revocation, or loss of the verifier's authority. The verifier records what was checked, source/channel, date, authority and scope, validity, limitations, and how revocation or later supersession will be detected.

This requirement does not create an infinite chain of verifiers. It terminates at a trust anchor or authority basis established before this ceremony and independently authenticated under the applicable governance or institutional process. This design neither names nor creates that basis. If no such prior basis can be verified, stop at terminal `VERIFIER_TRUST_ANCHOR_UNAVAILABLE`: do not accept the mandate or appointment, do not complete the ceremony, and preserve Option D with G1 blocked. If the source itself cannot be independently authenticated, the mandate is ambiguous, the appointment power is missing, or revocation cannot be checked, stop at `CONSTITUTING_AUTHORITY_UNVERIFIED`.

### Phase 3 — Adopt a bounded appointment decision

Only after Phase 2 succeeds may the verified constituting authority decide whether to appoint a candidate. The decision must state:
- exact identity of the appointee and accountable custodians;
- mandate and explicitly excluded powers;
- covered deployment and permitted enrollment functions;
- term, review date, expiry, succession and removal rules;
- who may delegate, issue, publish, revoke, verify and recover;
- conflicts of interest and which roles may not be combined;
- an independent verifier and the authoritative publication/verification channel;
- how appointment changes, revocation, key rotation and compromise are evidenced.

The candidate must accept the role under the verified procedure. Acceptance is not evidence that the appointing authority was legitimate; that was a separate prior phase.

### Phase 4 — Verify appointment authenticity through a separate path

The independent verifier checks that the appointment was actually issued by the authority verified in Phases 1–2, follows its decision rules, and has not been superseded or revoked. The verifier must obtain the official record through a channel independent of the candidate's own repository or server.

If the only way to learn the new authority's identity/key is from the new authority itself, there is no independent pin yet. Use the previously authenticated constituent authority's official channel or another independently rooted channel. If neither exists, stop.

### Phase 5 — Define custody, continuity, revocation and recovery

Before any technical enrollment, the governance decision must establish accountable custody, independent verification, audit/receipt retention, compromise handling, expiry, succession, revocation and recovery. Recovery must not be authorized solely by the compromised authority, the issuer whose delegation is affected, or the reader whose trust is being recovered.

This phase creates no key, certificate, service, app registration, or credential in the present task. It specifies which governance and evidence decisions would be needed before a future separately authorized implementation could be considered.

### Phase 6 — Evaluate the existing G1 evidence contract

Only once the constituting authority and appointment are independently verified may the separate G1 evidence contract be evaluated for its remaining requirements, including:
- root/authority identity and mandate;
- Owner-to-governance-principal binding;
- authority-to-issuer delegation;
- issuer-to-exact-server/reader binding;
- current revocation and recovery;
- evidence provenance and independent verification receipts.

A successful governance appointment is not equivalent to completed G1. Missing any required link means `G1=NOT_ESTABLISHED`.

### Phase 7 — Independent disposition before any future change in routing

The independent reviewer reports one of: `AUTHORITY_APPOINTMENT_VERIFIED`, `INSUFFICIENT_EVIDENCE`, `CONFLICT_OR_CIRCULARITY`, or `NO_QUALIFYING_CONSTITUTING_AUTHORITY`. The report lists evidence and limitations; it does not grant read permission.

Any change to canonical routing must be handled later under a separate, explicit governance decision and reviewed change. This candidate does not update `CURRENT-STATE.md`, adopt policy, or change a gate.

## 7. Required evidence packet for the constitution decision

The evidence packet should contain references and safe metadata, not secrets or unnecessary personal data:

| Item | Required claim | Independent check | Fail-closed result |
|---|---|---|---|
| C1 — Constituting source | A real authority exists and has power over the named deployment | Authenticate the source and source of mandate independently | `CONSTITUTING_AUTHORITY_UNVERIFIED` |
| C2 — Appointment power | The source may appoint/delegate the GBA role | Verify scope, approval rules, effective period and revocation | `APPOINTMENT_POWER_UNPROVEN` |
| C3 — Appointment record | The named candidate was properly appointed | Retrieve/validate official record via a separate channel | `APPOINTMENT_UNVERIFIED` |
| C4 — Custody and conflicts | Roles, custodians, removal and separation are accountable | Check role map and conflict-of-interest controls | `GOVERNANCE_SEPARATION_INCOMPLETE` |
| C5 — Independent verification channel | The verifier can authenticate records outside the candidate's control and has a separately verifiable prior authority basis | Confirm channel origin, integrity, freshness, verifier mandate and revocation source | `INDEPENDENT_CHANNEL_UNAVAILABLE` / `VERIFIER_TRUST_ANCHOR_UNAVAILABLE` |
| C6 — Lifecycle and recovery | Expiry, supersession, compromise and recovery have an independent procedure | Verify responsible parties and evidence path | `RECOVERY_GOVERNANCE_INCOMPLETE` |

C1–C6 being documented does not automatically establish trust. The actual evidence must be independently checked; a template or checklist alone is not evidence.

## 8. Decision gates and stop conditions

| Gate | Pass condition | Otherwise |
|---|---|---|
| G-A: Mandate | A real source with authority over the deployment is independently authenticated | Stop; Outcome C |
| G-B: Appointment power | That source can validly appoint the named role within the required scope | Stop; no GBA |
| G-C: Appointment | The actual appointment is authentic, current and revocable | Stop; candidate remains untrusted |
| G-D: Independence | Verifier has a prior independently verifiable authority basis and is not validating its own mandate; verifier, source and candidate do not rely circularly on each other | Stop; `VERIFIER_TRUST_ANCHOR_UNAVAILABLE` or record conflict/circularity |
| G-E: G1 evidence | The separate G1 evidence package is complete and independently verified | G1 remains not established |
| G-F: Governance adoption | A separate authorized decision changes canonical routing, if warranted | Keep current canonical route |

Any unavailable source, ambiguous mandate, disputed appointment, unverified identity or verifier mandate, missing prior verifier trust basis, broken chain, unqueryable revocation state, or conflict of interest returns a blocked outcome. No timeout, error, or missing evidence may be interpreted as approval.

## 9. Explicit anti-shortcut rules

The following substitutions are prohibited:
- Owner preference for a named candidate → authority mandate;
- institution's public visibility → proof that it has authority over this deployment;
- a legal name, domain, email, or web page alone → authenticated official mandate;
- appointment document found only in the candidate's own GitHub repository → independent authentication;
- MFA or login → governance-role authorization;
- GBA appointment → completed G1;
- completed G1 → completed G2/G3 or permission for protected reads;
- read approval → operational-block release;
- a signed receipt → proof of content delivery, persistence, or later causal reuse;
- a design artifact or static review → implemented or runtime-verified security.

Do not repeat general Windows/TPM/OIDC/WebAuthn feasibility research, rerun closed investigations, inspect protected local state, or bypass a denied reader as part of this design task.

## 10. Future validation requirements — not run here

If a future, separately authorized implementation arises, independent review must include negative cases for:
1. no constituting authority or unknown mandate;
2. authority exists but lacks power to appoint this role;
3. a self-appointed, self-signed or requester-controlled GBA;
4. an appointment published only by the candidate;
5. invalid quorum, expired appointment or superseded mandate;
6. unavailable/unknown revocation or recovery source;
7. requester, issuer, reader and independent verifier roles collapsing into one actor;
8. authority appointment present but Owner/principal, issuer/server binding, catalogue, resolver, or operational block gates still incomplete.

No tests, build, runtime, transport, protected read, or resource deployment is authorized or reported by this design.

## 11. Relationship to canonical state and adjacent candidate

This document complements, but does not replace, PR #478's minimum G1 evidence contract. PR #478 addresses what evidence is required to reconsider G1. This document addresses the prior decision layer: what would make an appointment of an authority legitimate and independently verifiable if a new authority were proposed.

Neither candidate establishes that a qualifying institution or constituent authority exists. Neither is adopted policy. Both remain subordinate to canonical `CURRENT-STATE.md`.

**Current decision and reconsideration boundary:** no further Owner confirmation of Option D is requested. `CURRENT-STATE.md` already records `OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP` and the fail-closed `NEXT_ACTION`; preserve both. Reconsider only if genuinely new authority evidence is independently verified, or if the Owner makes a new explicit decision that changes the basis of canonical routing. Neither condition by itself establishes G1 or authorizes implementation. The agent must not pick or invent a constituent authority.

## 12. Candidate terminal state

```text
TASK=M1A_G1_GOVERNANCE_AUTHORITY_CONSTITUTION_CEREMONY_DESIGN_ONLY
DESIGN_STATUS=DOCUMENTARY_CANDIDATE; NOT_CANONICAL; NOT_ACCEPTED
BASE_MAIN_SHA=c3bc9d8b4f727483081cf24650d4e7209687024c
OWNER_AUTHORIZATION=DOCUMENTATION_ONLY; NO_CHANGE_TO_OPTION_D
CONSTITUTING_AUTHORITY=UNKNOWN; NOT_INDEPENDENTLY_VERIFIED
APPOINTMENT_POWER=NOT_ESTABLISHED
ENROLLMENT_AUTHORITY=PROPOSED_ROLE_ONLY
INDEPENDENT_VERIFICATION_CHANNEL=NOT_ESTABLISHED
VERIFIER_TRUST_ANCHOR=NOT_ESTABLISHED
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
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

## References

- [Canonical CURRENT-STATE.md on the exact base](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
- [PR #478 — minimum G1 enrollment-authority evidence contract](https://github.com/jhonf463r/Python/pull/478)
- [Prior governance-owned bootstrap design at immutable historical commit](https://github.com/jhonf463r/Python/blob/675c3bdd046de04e4e7d6bb70d616dbce1354e06/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-governance-owned-bootstrap-authority-design-candidate.md)
- [M1A v1.0.1 implementation-prerequisite evidence-gate matrix](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md)
- [Entry 274 — consolidated repository-read decision contract](https://github.com/jhonf463r/Python/blob/c3bc9d8b4f727483081cf24650d4e7209687024c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md)
