# M1A G1 — TPM preflight branch closure

- **Date:** 2026-10-23 (America/Bogota)
- **Task:** `M1A_G1_TPM_PREFLIGHT_BRANCH_CLOSURE`
- **Decision provenance:** Owner's "ok procede" in direct response to the recommendation `CLOSE_TPM_PREFLIGHT_BRANCH`
- **Baseline verified before writeback:** `c0fb911959725a1168c61674d67a7df16bb8ec7c`
- **Primary outcome:** `GOVERNED_IABV_CODEX_BRIDGE`
- **Decision status:** `OWNER_DECISION_RECEIVED`
- **Closure result:** `TPM_PREFLIGHT_BRANCH_CLOSED_FOR_NOW`
- **Governance:** `KEEP_BLOCKED`

## 1. Bounded decision

The Owner accepted the recommended closure of the TPM preflight branch. This closes the current TPM diagnostic path for now; it does not establish TPM presence or absence, fix the capture mechanism, validate EK certificates, establish an issuer trust root, or close G1.

This decision authorizes no new TPM command, output-recovery lookup, EK inspection, certificate-chain construction, Windows probe, installation, credential creation, product code change, test, build, runtime, transport, merge, deploy or gate release.

## 2. Reconciled evidence

Prior Owner-supplied receipts reported a successful `Get-Tpm` invocation but left `TPM_PRESENT`, `TPM_READY`, `TPM_ENABLED`, `TPM_ACTIVATED` and `TPM_OWNED` as `UNKNOWN`. The original object/output was not recovered. The corrected-capture static review is documented but its candidate implementation was not executed. `Get-TpmEndorsementKeyInfo` and EK certificate-chain validation were not run.

These historical command results remain `OWNER_REPORTED`; this coordinator did not independently invoke PowerShell or observe the Windows host.

## 3. Decision and side-effect ledger

```text
TPM_PREFLIGHT_BRANCH=CLOSED_FOR_NOW
TPM_AVAILABILITY=UNVERIFIED
CAPTURE_ROOT_CAUSE=UNRESOLVED
GET_TPM_REEXECUTED=NO
RECOVERY_LOOKUP_REPEATED=NO
EK_INFO_CMDLET_EXECUTED=NO
EKCERT_CHAIN_VALIDATION=NOT_RUN
PRODUCT_CHANGES=NONE
TESTS=NOT_RUN
BUILD=NOT_RUN
PRODUCT_RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
COORDINATOR_RUNTIME=NOT_PROVEN
CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN
AUTOMATIC_FOLLOW_ON=FALSE
```

## 4. Next open edge — not automatically authorized

The North Star remains `GOVERNED_IABV_CODEX_BRIDGE`; the active frontier remains `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`. The next candidate is a distinct, bounded **read-only assessment of already-existing trust assets and any independently grounded Owner-to-issuer-to-exact-server binding**. Its scope must avoid repeating the closed TPM, GitHub-manifest/TPM, Google OIDC, phone/passkey, independent TPM-pin and broad Windows-bootstrap reviews.

This new assessment is **not authorized by this closure**. Before it begins, the Owner must explicitly authorize the bounded task and the exact permitted source/route. A denied or unavailable local reader must not be bypassed with another tool, browser, AI, transport, or public-main proxy for a dirty local checkout. If the authorized source route is unavailable, return `NOT_RUN` / `SUPPORTED_ROUTE_NOT_FOUND` with evidence and stop.

The next human-facing step is to obtain that separate authorization through an exact, copyable prompt. No Codex or other-AI invocation has been made by this receipt.

## 5. Canonical state after closure

```text
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
LAST_TERMINAL_TASK=M1A_G1_TPM_PREFLIGHT_BRANCH_CLOSURE
NEXT_ACTION=OWNER_DECISION_ONLY
NEXT_CANDIDATE=M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT
TPM_PREFLIGHT_BRANCH=CLOSED_FOR_NOW
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

No product/runtime behavior or governance gate was changed. This receipt records a control decision and routing transition only.
