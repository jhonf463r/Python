# M1A G1 — Owner ratification of Option D: no bootstrap, remain fail-closed

- Date: 2026-10-23 (America/Bogota).
- Task: `M1A_G1_OPTION_D_OWNER_RATIFICATION`.
- Project outcome: `GOVERNED_IABV_CODEX_BRIDGE`.
- Active technical frontier: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.
- Receipt type: documentary record of the Owner's explicit decision in this conversation.
- Provenance: explicit Owner message in ChatGPT; the decision is recorded as communicated, not as an independently authenticated external identity event.
- Exact remote base verified before the write: `main` at `439d9604037f156160a970dd33d1b3ad76009bdf`.
- Isolated branch: `codex/iabv-option-d-ratification-20261023`.
- Scope: documentation only; this receipt creates no authority, trust anchor, credentials, implementation permission or operational release.

## 1. Owner decision as supplied

The Owner explicitly supplied the decision token:

```text
IABV: RATIFICO_OPCION_D_SIN_BOOTSTRAP.
```

The Owner states that, given the evidence currently recorded, they do not know of a pre-existing independent authority whose mandate over IABV can be verified through an independent channel.

The Owner also explicitly recognizes the already-completed, Owner-reported progress:
- Microsoft Entra organizational directory configured.
- Dedicated `IABV Owner` account created.
- Microsoft Authenticator enrolled and sign-in verification succeeded.

This setup must not be requested or performed again. It is progress on human authentication; it does not by itself establish an IABV trust root, protected-read authority, Owner-to-Windows-principal binding, issuer-to-exact-server binding, or permission to implement.

## 2. Interpretation and strict scope

The decision ratifies **Option D: do not bootstrap a new trust root; preserve the no-bootstrap and fail-closed posture with current evidence**.

It does not claim that trust assets do not exist. The prior Codex response was `STATUS=NOT_RUN` and `REASON=SUPPORTED_ROUTE_NOT_FOUND`; the assistant did not inspect assets. Therefore:
- `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`
- `SUPPORTED_ROUTE_NOT_FOUND` describes the reported bounded Codex session; it is not proof of global absence.
- No reader/list operation is authorized by this ratification.
- No attempt may be made to reach the same protected local assets via another tool or transport as a workaround.
- No new authority, root, issuer, registry, service, placeholder or credential may be manufactured to move past the block.

Option D is a governance decision to remain blocked; it is not implementation acceptance or evidence that the technical prerequisites have been fulfilled.

## 3. Canonical state required after the receipt is reviewed and merged

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
OWNER_DECISION_PROVENANCE=EXPLICIT_CHAT_MESSAGE
ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY; DO_NOT_REPEAT_SETUP
IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID; NOT_YET_TRUSTED_BY_IABV
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_AUTHORITY=NOT_IDENTIFIED_BY_OWNER; EXISTENCE_NOT_PROVEN_ABSENT
AUTHORIZED_PROTECTED_READ_ROUTE=SUPPORTED_ROUTE_NOT_FOUND_IN_REPORTED_CODEX_SESSION
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
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

## 4. No automatic follow-on

This receipt authorizes only recording the Owner decision. It does not authorize:
- access to protected local files, databases or any denied reader/list tool;
- a new Entra app registration, secret, credential, account or directory;
- Azure billing changes, paid licenses, spending, resource deployment or tunnel launch;
- product-source modification, tests, build, runtime, real transport or implementation;
- a merge or deployment triggered automatically by this decision;
- closing G1, G2, G3 or any of the eight implementation prerequisite gates;
- release of a governance block or claims that the bridge is ready.

The routing/index update in this branch is a documentation proposal only. Its diff must be verified, and it must remain unmerged until review. If merged later, the canonical route is to maintain the already-ratified Option D fail-closed posture, not to ask the same decision again.

## 5. Receipt verification

The receipt is a versioned GitHub document. A commit or blob hash proves which document was recorded at a repository ref; it is not authority by itself and does not independently authenticate the Owner. The source of the decision remains the explicit Owner message stated in section 1.

```text
TASK=M1A_G1_OPTION_D_OWNER_RATIFICATION
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
DECISION_SOURCE=EXPLICIT_OWNER_CHAT_MESSAGE
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```
