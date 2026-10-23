# M1A G1 trust-bootstrap feasibility — reconciliation of Codex report

- Date: 2026-10-22, America/Bogota.
- Task: `M1A_G1_TRUST_BOOTSTRAP_FEASIBILITY_REVIEW`.
- Parent: `M1A_G1_TRUST_BOOTSTRAP_DECISION`.
- Report provenance: `OWNER_SUPPLIED_CODEX_REPORT`; the pasted report is not presented as a fresh direct Codex tool receipt.
- Canonical router: [CURRENT-STATE.md](./CURRENT-STATE.md).
- Normative M1A v1.0.1 blob: `7c72474a5f7c114c02320c177d6ea2aea68ad28f`.
- Entry 274 blob: `5943a87d907436fc7ecac31534cbfcd31fe7de55`.

## 1. Disposition

The report's core result is accepted as a bounded feasibility conclusion:

`G1_FEASIBILITY=CONDITIONAL_NOT_DEMONSTRATED`

Windows Hello/WebAuthn is a possible Owner-authentication factor only if the actual enrollment, Owner-to-credential binding, relying-party/server identity, and platform assurances are established. Documentation of an API is not evidence that the current device is configured, that IABV integrates it, or that it establishes an authoritative governance issuer.

The report does not establish an operational trust anchor, independent issuer, verified reader-side decision path, current revocation source, or block-release authority. No implementation readiness follows.

## 2. Coordinator verification and provenance reconciliation

In the current ChatGPT coordination session, the public GitHub branch references were retrieved directly:

- `main` tip: `14fd0976b1cc747fb568b93e6faafb0409bb08a1`.
- Candidate branch: `m1a-g1-g3-governance-route-candidate-20261022`.
- Candidate tip at verification: `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db`.
- Candidate tree: `ca963f8013809d4efcf56133a37d2efe148517e9`.
- Candidate tip still equals its pinned base; no source change was made in that branch by this coordinator.

Thus the Codex report's `HEAD=OWNER_REPORTED` describes the evidence available in that report/session. The coordinator independently verified the branch tip through the GitHub connector in this session. This does not authenticate the live local MCP server or Owner's checkout.

The Entry 274 public blob was also independently retrievable from GitHub by this coordinator at the stated SHA. Its verification is separate from what Codex says it inspected in its session.

Relevant public source blobs, previously fetched for static inspection:

- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`: `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`.
- `IABV_v1.5/src/iabv_v15/services/system_identity_registry.py`: `8fa7ba60202d947a254352bb1d7927f76becf90a`.
- `IABV_v1.5/src/iabv_v15/services/security/human_approval_broker.py`: `4a447149cf1b2771f6959658338a72b381f00b19`.
- `IABV_v1.5/src/iabv_v15/services/security/approval_memory.py`: `ed85408d96fb0cdfddb05489d6c38cf714275f91`.
- `IABV_v1.5/src/iabv_v15/services/security/credential_broker.py`: `95a2e36401159995b253ff496a3a90cc2d5ffb92`.

## 3. Contract taxonomy correction

M1A G3 means the authoritative, versioned server-side operation-to-target resolver that binds a real registered operation/call site to its canonical target. A durable record correlating request, approval, decision, operation and result is a separate receipt/ledger requirement from Entry 274 and the later integration gates; it must not replace or redefine G3.

The pasted report's “G3 — registro durable...” label is therefore a terminology/traceability error. The target resolver remains `G3=NOT_ESTABLISHED`; durable receipt/ledger integration also remains unproven as a separate dependency.

G2 remains the authorized catalogue publisher, producer-class authorization, catalogue integrity/version lifecycle and authoritative revocation source. Do not transfer all server/checkout identity and receipt requirements into G2.

## 4. Owner decision frontier

The next active task is `M1A_G1_TRUST_BOOTSTRAP_POLICY_ADJUDICATION`, status `WAITING_OWNER`. The proposed direction is not adopted yet:

- Owner authentication may use Windows Hello/WebAuthn as a factor only after a bounded engineering review confirms the necessary platform and enrollment guarantees.
- The initial binding between the human Owner, credential, governance issuer and intended server instance must be explicit and must not be self-authorized by the requester or reader.
- The issuing authority and the read-enforcing component must have independently enforced responsibilities; names or separate classes in one process do not prove security separation.
- Read decisions must be scoped, time-bounded, revocable, verified at the reader boundary, and accompanied by correlated durable receipts.
- A read decision cannot release an applicable operational block; block release stays independently authorized.
- Accepting this design direction would authorize design/implementation work only in the isolated candidate as separately specified. It would not authorize protected local reads, tests, runtime, real transport, merge, deployment or block release.

No technology is presumed available on the device. No new key, identity, issuer, registry or receipt is created by this reconciliation.

## 5. Terminal evidence state

```ini
TASK=M1A_G1_TRUST_BOOTSTRAP_POLICY_ADJUDICATION
PRIOR_RESULT=G1_FEASIBILITY_CONDITIONAL_NOT_DEMONSTRATED
OWNER_DECISION=PENDING
IMPLEMENTATION=NOT_AUTHORIZED_FOR_NEW_TRUST_BOOTSTRAP
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
DURABLE_OPERATION_RECEIPT=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_CHECKOUT=DO_NOT_ACCESS
PROTECTED_LOCAL_READ=NOT_AUTHORIZED
MERGE_DEPLOY=NOT_AUTHORIZED
BLOCK_RELEASE=NOT_AUTHORIZED
BRIDGE=BRIDGE_NOT_READY
```

No local checkout, `data/`, SQLite, secrets, credentials or `.env` were accessed. No tests, builds, runtime, processes, transport, source writes, merge, deploy, protected read or block release occurred in this reconciliation.
