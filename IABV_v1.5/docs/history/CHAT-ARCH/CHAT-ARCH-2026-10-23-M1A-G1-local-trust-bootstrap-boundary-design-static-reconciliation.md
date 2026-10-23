# M1A G1 — Local trust-bootstrap boundary design: static reconciliation

- Date: 2026-10-23 (America/Bogota).
- Task reviewed: `M1A_G1_LOCAL_TRUST_BOOTSTRAP_BOUNDARY_DESIGN_ONLY`.
- Review type: independent static/documentary review of the exact GitHub candidate; no implementation or runtime work.
- Candidate: [`codex/m1a-g1-local-trust-bootstrap-design-20261023`](https://github.com/jhonf463r/Python/tree/codex/m1a-g1-local-trust-bootstrap-design-20261023).
- Commit: [`35fc8f2cb72d0394b85d34f9b6aa5157a834efc6`](https://github.com/jhonf463r/Python/commit/35fc8f2cb72d0394b85d34f9b6aa5157a834efc6).
- Document: [M1A G1 local trust-bootstrap boundary design candidate](./CHAT-ARCH-2026-10-23-M1A-G1-local-trust-bootstrap-boundary-design-candidate.md).
- Document blob fetched from the exact commit: `ecbbdc0504fe4e337c40859472805fb2e08796d2`.

## 1. Independent identity and diff reconciliation

The public GitHub repository reports `main` at expected baseline `30554c56e36101638fb24513a7a1590f88e41ad7` at review start. The candidate commit's parent is exactly that baseline. GitHub comparison returns `ahead_by=1`, `behind_by=0`, and exactly one added path:
`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-local-trust-bootstrap-boundary-design-candidate.md`
(302 additions, zero deletions). The document was fetched through the branch and exact commit; both returned blob `ecbbdc0504fe4e337c40859472805fb2e08796d2`.

The five canonical files fetched from `main` at review start were:
- `IABV_v1.5/AGENTS.md` — `c59e1ce1faf212852a342478f03dbabead2190b9`
- `IABV_v1.5/docs/history/CHAT-ARCH/README.md` — `70f71073d402da1fb1c0a842ad25f2178336fadb`
- `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — `5a2cf6d1bab5beb4eff3a9f3f2bd7a37919e28e0`
- `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md` — `bbd86375f3cdbf940fbed62d1efde0d2fb6a5589`
- `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md` — `b96e9333f0b27b61ad443bee77f1641c32879f18`

The candidate's base-to-head diff changes no product code, tests, contracts, or canonical front doors. This review does not claim anything about the Owner's local checkout.

## 2. Static design verdict

**Disposition: `CONDITIONAL_DESIGN_REVIEW; RECEIPT_SEMANTICS_REPAIR_REQUIRED`.** Retain this as an unaccepted documentary candidate. The design is materially more complete than the previous attempt because it identifies the root-of-trust circularity, defines a conditional enrollment ceremony, separates logical roles and OS process boundaries, models signed decisions, names catalogue/revocation/target/release authorities, and keeps G1/READ_LIST fail-closed. It does not establish G1 and is not accepted for implementation.

Positive findings:
- It explicitly refuses first-run trust-on-first-use, self-enrollment, a SID as Owner identity, a generated key as root, and a digest as proof of authority.
- It separates Owner approval, issuer, reader, catalogue/revocation and independent block-release responsibilities.
- It identifies Windows service SID, CNG, named pipes and filesystem containment as mechanisms to validate later, rather than as evidence of current machine configuration.
- It names unresolved owner/governance decisions D1–D10 and makes the future implementation/test phases separately gated.

## 3. Required refinement and remaining open dependencies

### F1 — Receipt stage semantics

Section 8 step 10 requires “Commit durable del recibo de finalización y consumo antes de entregar contenido.” A record persisted before content delivery can prove a durable pre-release decision/result state, not by itself that delivery actually completed. Revise this distinction before using the design as an implementation contract: durable pre-release/authorization record → release/delivery attempt → separately correlated delivery/result receipt → canonical reconciliation. Persist failure/uncertainty without claiming unobserved delivery. This is required by UAAL-D018's separation of source result, projection, transport, receipt correlation, persistence and later causal reuse.

### F2 — Exact instance and process binding

The design proposes lifecycle identity, binary/release digest, service principal, process/session challenge and process-creation binding, and correctly says these properties must be proven in implementation. It does not yet identify the concrete authoritative OS evidence and race-safe method that makes those fields bind to the exact live reader instance under replacement/replay. Do not credit this as established; a later approved implementation plan must specify the mechanism and the evidence used to accept or reject it.

### A1 — Initial trust root and Owner binding remain unresolved

D1–D4 describe the relevant decisions but do not name an actual pre-existing independent root, its custodian, a pre-established out-of-band verification channel, or evidence binding that root to the Owner's IABV governance responsibility. This is the real G1 blocker. Do not infer the missing authority from the proposal, public GitHub, local admin, SID, conversational approval, Windows APIs, a new credential or the issuer itself. If no verifiable independent root/channel exists, remain blocked and ask governance to define an independently verifiable enrollment authority before implementation.

### A2 — Downstream runtime authorities remain unestablished

The design does not provide runtime evidence for the versioned target resolver, complete authenticated active-block-set snapshot, catalogue publisher, authoritative revocation, independent per-block release, durable ledger or race-resistant resource containment. These remain separate implementation prerequisites, not effects of adopting a design.

## 4. M1A version routing discrepancy reconciled

At review start, the most recent routing sections in the five canonical front doors still named v1.0.0 as adopted. However, the existing explicit Owner adoption receipt records the exact token `ACCEPT_M1A_V1_0_1_SUCCESSOR_BASELINE` and adoption of v1.0.1 as the current normative *design-only* baseline, blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`, with receipt blob `34bee2ad8b3b4beeb468e8d563b99f511f0b352d`. The implementation prerequisite matrix is blob `1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37`; all eight gates remain open.

The new canonical routing override records v1.0.1 as adopted design based on that exact existing Owner decision. This is reconciliation of documentary drift, not a new policy decision, not mutation of the immutable contract, and not evidence of operational effect. Historical stale references remain in the archive; the new override supersedes them for current routing.

## 5. Current status and limits

```text
TASK=M1A_G1_LOCAL_TRUST_BOOTSTRAP_BOUNDARY_DESIGN_ONLY
CANDIDATE_COMMIT=35fc8f2cb72d0394b85d34f9b6aa5157a834efc6
CANDIDATE_PARENT=30554c56e36101638fb24513a7a1590f88e41ad7
CANDIDATE_TREE=10985bad90b4bb781be77468793698c2ce05fc84
CANDIDATE_DIFF=ONE_NEW_DOCUMENT_ONLY
DOCUMENT_BLOB=ecbbdc0504fe4e337c40859472805fb2e08796d2
STATIC_REVIEW=CONDITIONAL_DESIGN_REVIEW; RECEIPT_SEMANTICS_REPAIR_REQUIRED
DESIGN_STATUS=DOCUMENTARY_CANDIDATE_NOT_ACCEPTED
M1A_NORMATIVE_DESIGN=v1.0.1; DESIGN_ONLY
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
INDEPENDENT_TRUST_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_SOURCE_CHANGES=NONE
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_OWNER_CHECKOUT_ACCESSED=NO
LOCAL_PROTECTED_READ=NOT_AUTHORIZED
CREDENTIALS_OR_SERVICES_CREATED=NO
MERGED=NO
DEPLOYED=NO
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_ONLY
```

The existing design-only authorization does not authorize runtime investigation, credential/service creation, product implementation, tests, transport, merge, deployment or release. The next authority decision must provide a verifiable independent root/Owner-to-principal binding route, or explicitly commission definition of such a governance-owned authority. A technical implementation must not simulate that authority.
