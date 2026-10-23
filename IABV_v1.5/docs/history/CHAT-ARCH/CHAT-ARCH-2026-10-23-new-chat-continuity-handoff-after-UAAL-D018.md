# IABV — New-chat continuity handoff after UAAL-D018

- **Date:** 2026-10-23, America/Bogota
- **Purpose:** Restore project state without repeating closed work
- **Source baseline:** `8c453dbdd0b3bb0b606fb46f6b243df525ac10f8`
- **Current project north star:** `GOVERNED_IABV_CODEX_BRIDGE`
- **Single active frontier:** `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`
- **Governance:** `KEEP_BLOCKED`

## 1. Startup protocol — mandatory order

In the new chat, verify remote `main` first, then read:

1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — sole active-task and next-action authority
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`
6. The objective-relevant sources linked by the current routing entry, including the UAAL-D018 receipt, TPM capture review, UAAL root/lineage and coordination protocol as needed.

Do not assume this handoff's baseline remains HEAD after the next commit. Revalidate the live branch before acting. When a later canonical route supersedes this handoff, follow the new route.

## 2. What we are building

The North Star is a real governed IABV → Codex → IABV path: identify and invoke a supported route, correlate the actual response, ingest safely, persist and fetch back evidence, then show a later decision was improved by reuse. The architectural goal is capability and reliable governed flow, not more services, prompts, dashboards or documents.

The root reasoning loop is `UAAL-ROOT-001`: objective → perceive/represent/interpret → preserve uncertainty → infer capability → discover/select realization under constraints → govern → act → observe → verify → update reusable knowledge → reuse/adapt → next decision.

The documented “space-time coordinator” is the project control method, **not proof of an autonomous runtime mind or consciousness**. `COORDINATOR_RUNTIME=NOT_PROVEN` and `CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN` remain mandatory epistemic limits until a correlated future run demonstrates them.

## 3. Current status at this baseline

The latest method refinement is `UAAL-D018_EXECUTION_TO_EVIDENCE_STAGE_SEPARATION_METHOD_REFINEMENT`, persisted in commit `8c453dbdd0b3bb0b606fb46f6b243df525ac10f8`. Its canonical receipt is [UAAL-D018 — Execution-to-Evidence Stage Separation and Projection Observability](./CHAT-ARCH-2026-10-23-UAAL-D018-execution-to-evidence-stage-separation.md), blob `6eeeb84c4ee4fc1d22e477f32f42f4c6fbe5b5bb`.

The method's invariant is:

`source success ≠ observation success ≠ projection success ≠ receipt correlation ≠ persistence ≠ causal reuse`.

Track authority, exact artifact/input, destination, invocation, source result, output shape, per-field projection, serialization/transport, coordinator reconciliation, canonical fetch-back and subsequent causal reuse as separate evidence stages. A task name or prose-only repair is not proof that a mechanism changed.

The latest TPM-specific static review is [M1A G1 — TPM projection-capture mechanism static review](./CHAT-ARCH-2026-10-23-M1A-G1-TPM-projection-capture-mechanism-static-review.md), blob `25336d97408169f2d3d8f453c14d644002b433ab`. The prior diagnostic receipt is [TPM/EKCert corrected-capture preflight failure](./CHAT-ARCH-2026-10-23-M1A-G1-TPM-EKCert-corrected-capture-failure.md), blob `d1b0bb55dd950c7fa30312f023a5c14bfa798d73`.

## 4. TPM preflight — terminal for now, do not repeat unchanged

Owner-supplied receipts report one `Get-Tpm` call with `SUCCESS`, but `TPM_PRESENT`, `TPM_READY`, `TPM_ENABLED`, `TPM_ACTIVATED` and `TPM_OWNED` all remained `UNKNOWN`. The original output/object was not retained. `Get-TpmEndorsementKeyInfo` was not run; EKCert count and chain validation remain unexamined.

These command outcomes are `OWNER_REPORTED`, not independently observed by this coordinator. `UNKNOWN` does not mean TPM absent. The actual capture script/source-stage trace is unavailable, so `CAPTURE_ROOT_CAUSE=UNRESOLVED`.

**Do not** rerun `Get-Tpm`, perform another recovery lookup, query EK information, build a certificate chain, or switch tools/channels to bypass this stop. Reopen only after a separate explicit bounded decision and use the exact corrected candidate with stage-specific, safe diagnostics and a correlated receipt. The current user authorization covered method improvement and continuity writeback, not a new TPM execution.

## 5. G1 trust boundary — prior findings that remain valid

`G1=NOT_ESTABLISHED`; `GOVERNANCE=KEEP_BLOCKED`; `BRIDGE=BRIDGE_NOT_READY`.

Unresolved edges remain Owner authority → authenticated Windows principal → trusted issuer credential → exact IABV server instance → independent reader enforcement → authoritative revocation. TPM key non-exportability, a target-displayed fingerprint, measured boot, GitHub manifest approval, or a local certificate-chain result does not alone close this chain.

Do not repeat the broad Windows bootstrap review, GitHub-manifest/TPM review, Google OIDC review, personal phone/passkey setup, or static independent TPM-pin design unless genuinely new evidence invalidates their prior outcomes. Google OIDC was judged not worth the external setup; GitHub account ID `28608338` remains unadopted; a personal passkey is not an IABV trust root.

## 6. Method and interaction rules to carry forward

- Keep one active project task and one next action. Park unrelated ideas instead of switching the task automatically.
- Restore canonical state before reasoning; do not ask the Owner to repeat decisions already recorded.
- Give complete prompts inline with the exact destination when another AI session is required. Do not point to a website as the only source of a prompt. Never claim dispatch without a correlated result.
- Distinguish `OWNER_REPORTED`, `CONFIRMED_BY_SOURCE`, `PROPOSED`, `UNRESOLVED`, `NOT_RUN`, `DOCUMENTED`, `INVOKED`, `OBSERVED`, `VERIFIED`, `CAUSAL` and `REUSED`.
- Don't turn a bounded failure into a broad scan. Pursue only observations that discriminate the earliest unproven stage.
- Every material document write needs branch/commit/blob fetch-back. Saving text alone does not prove runtime learning.
- Technical derivations can be coordinator-led; normative authority, trust-root adoption, credential creation, implementation, tests/build/runtime, real transport, merge and block release stay behind their respective approvals.
- Do not describe the architecture as conscious or the coordinator as already autonomous.

## 7. Single next action — owner decision only

```text
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
LAST_TERMINAL_TASK=UAAL_D018_EXECUTION_TO_EVIDENCE_STAGE_SEPARATION_METHOD_REFINEMENT
METHOD_DELTA=UAAL-D018_DOCUMENTED_ONLY
CAPTURE_ROOT_CAUSE=UNRESOLVED
TPM_AVAILABILITY=UNVERIFIED
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=OWNER_DECISION_ONLY
CHOICES=AUTHORIZE_ONE_FIXED_TPM_CAPTURE_RUN | CLOSE_TPM_PREFLIGHT_BRANCH
AUTOMATIC_FOLLOW_ON=FALSE
COORDINATOR_RUNTIME=NOT_PROVEN
CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN
```

Do not automatically perform either choice. If the Owner authorizes the one fixed capture run, use the exact candidate code in the TPM projection-capture static review, enforce its no-secret/no-network/no-file constraints, and return one correlated safe JSON receipt. EK inspection is not part of that capture action. If the branch is closed, leave TPM availability unverified and continue to identify the next genuinely authorized path toward the North Star without repeating the closed investigations.

No product code changed in this episode. Product tests/build/runtime, local checkout observation and real bridge transport remain `NOT_RUN`.
