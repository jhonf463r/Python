# IABV ChatGPT operational continuity and execution protocol — corrective override

- Date: 2026-10-23 (America/Bogota).
- Task: `M1A_G1_CHATGPT_CONTINUITY_PROTOCOL_CORRECTION`.
- Status at authoring: `DOCUMENTARY_CORRECTION_PROPOSED` on an isolated docs-only branch. Check live remote `main` for actual adoption status; this line does not prove present merge state.
- Branch: `codex/iabv-chatgpt-protocol-correction-20261023`.
- Exact base: `c95fb23c8ae5f7b6fdd1f94b4dba253347bb89cd`.
- Project outcome: `GOVERNED_IABV_CODEX_BRIDGE`.
- Active technical frontier: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.

## Subsequent Owner decision supersedes the original pending-decision snapshot (2026-10-23)

The Owner subsequently supplied the explicit decision `IABV: RATIFICO_OPCION_D_SIN_BOOTSTRAP`. Its receipt is [M1A G1 Owner Option D ratification](./CHAT-ARCH-2026-10-23-M1A-G1-owner-option-d-no-bootstrap-ratification-receipt.md), blob `408229370babd4b53da3247d3aaef6392be5b268`, authored on isolated branch `codex/iabv-option-d-ratification-20261023` from baseline `439d9604037f156160a970dd33d1b3ad76009bdf`.

This explicit decision supersedes the prior status in this protocol that said Option D had not yet been ratified. It does not establish that authority assets are absent: `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`. The current routing amendment and receipt remain a review proposal until merged. All gates remain open, and no protected read, implementation, test, build, runtime, transport, tunnel, paid resource, deployment or block release is authorized.

---

## 1. Purpose and precedence

This document corrects a recurring continuity failure: the assistant has preserved the user's Entra setup but still asked a poorly contextualized authority question because multiple long routing overlays repeated and contradicted one another.

Apply these rules whenever this protocol is present on live `main`. The continuity protocol itself was merged in commit `439d9604037f156160a970dd33d1b3ad76009bdf`; the subsequent Option D decision receipt and routing amendment in branch `codex/iabv-option-d-ratification-20261023` remain a separate documentation proposal until reviewed and merged:

1. `CURRENT-STATE.md` is the **single source of current routing and the single owner of `NEXT_ACTION`**. Other front-door files state rules, provenance, or navigation; they must not establish a competing next action.
2. `AGENTS.md` defines repository-work behavior. `README.md` is navigation. `CONTEXT-INDEX.md` points to evidence and history. `MEMORY-OPERATING-PROTOCOL.md` defines continuity, provenance and conflict resolution. None overrides the newest valid routing in `CURRENT-STATE.md`.
3. If these documents disagree, do not merge their instructions informally and do not repeat every conflicting branch of history. Prefer the latest routing block on the live remote `main` in `CURRENT-STATE.md`; record the discrepancy, make a bounded documentation correction, and preserve fail-closed controls.
4. Do not prepend another full, independent copy of the current state to every file. Keep a compact synchronized pointer in the other entry files and the detailed routing snapshot only in `CURRENT-STATE.md`. Preserve historical records below the current override.
5. At the time of authoring, this branch is a proposal. Verify adoption against live remote `main`; do not infer that the correction is active from the branch or PR alone.

## 2. Mandatory startup preflight

At each new chat or substantial continuation, use live public GitHub, not memory alone. Revalidate remote `main` and record its exact commit SHA. Fetch these files in this exact order from that same SHA:

1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`

Then read the latest handoff and the specifically referenced current assessment, applicable gate matrix, adopted normative design, Owner adoption receipt, and Entry 274 contract. Follow the current index; do not scan the entire archive or repeat closed investigations unless new evidence changes the decision.

Before acting, emit an internal-to-the-task routing ledger with: baseline SHA, active task, latest applicable decision, last verified progress, provenance, unresolved gate, authority actually granted, prohibited actions, and one immediate next action. State only what the fetched source supports. If the required documents cannot be fetched or disagree materially, stop writes and protected actions; report the exact limitation.

## 3. Continuity and provenance rules

Use these labels precisely:

- `VERIFIED_PUBLIC_REPO`: fetched at a named remote ref/SHA.
- `OWNER_REPORTED`: the Owner reported it; it is not independently authenticated by this coordinator.
- `UNKNOWN`: existence or value is not known.
- `NOT_INSPECTED`: no inspection occurred.
- `SUPPORTED_ROUTE_NOT_FOUND`: this bounded session did not expose an admissible route; not proof that no route or asset exists globally.
- `NOT_ESTABLISHED`: the required evidence chain is incomplete.
- `NOT_AUTHORIZED`: the action is outside the granted scope.
- `NOT_RUN`: no test/build/runtime/transport execution occurred.
- `FAIL_CLOSED`: deny the protected operation while preserving unknowns; it does not mean the asset is absent.

Never turn `UNKNOWN`, `NOT_INSPECTED`, `SUPPORTED_ROUTE_NOT_FOUND`, or a blocked call into proof of absence. Never upgrade `OWNER_REPORTED` to independently verified without evidence. Never claim tool dispatch, local access, runtime state, causal reuse, or autonomous persistent memory without correlated evidence.

## 4. Acknowledge completed work before identifying the remaining gate

The following is already recorded and must not be asked again as if it were undone:

- The Owner reports that the Microsoft Entra organizational directory and dedicated `IABV Owner` account were created.
- The Owner reports that Microsoft Authenticator was enrolled and sign-in verification succeeded.
- Exact tenant and user identifiers are intentionally excluded from public history.

Treat this as `ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY`. It is meaningful progress for **human authentication**. Do not ask the Owner to repeat account creation, phone enrollment, or the successful login unless new evidence establishes a specific failure requiring remediation.

Equally, do not overstate that progress: it does not by itself establish IABV trust, a governance root, authorization for protected reads, Owner-to-Windows principal binding, issuer-to-exact-server binding, token validation, revocation, or the M1A gates. Entra is a candidate identity provider, not yet trusted by IABV.

## 5. Decision boundary for the current G1 task

Current known state at the proposal's base:

```text
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY
IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID; NOT_YET_TRUSTED_BY_IABV
EXISTING_INDEPENDENT_AUTHORITY=UNKNOWN; NOT_INSPECTED
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
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
AUTOMATIC_FOLLOW_ON=FALSE
```

The static reconciliation establishes that no qualifying independent root, root custodian, external verification channel, mandate over IABV, or Owner-to-Windows-principal binding has been demonstrated in the available evidence. Governance Bootstrap Authority (GBA) is a proposed role, not an existing service or authority. The prior design verdict is `CONDITIONAL_DESIGN_REVIEW; OPTION_D_REQUIRED_WITH_CURRENT_EVIDENCE`.

The only valid outcomes are:

- **Independent authority evidence is supplied:** define the minimum non-secret evidence and admissible independent verification route before any inspection or action. Do not ask for credentials, access tokens, OTPs, QR codes, secrets, or private account identifiers in chat or public history.
- **The Owner explicitly ratifies Option D:** record no-bootstrap/fail-closed as an Owner decision; do not infer that ratification from confusion, silence, or an "I don't know why you're asking" response.
- **The Owner says they do not know, or no admissible route is available:** keep authority assets `UNKNOWN/NOT_INSPECTED`, preserve all gates as blocked, and stop authority-investigation attempts. Do not interpret uncertainty as proof of absence and do not re-ask the same question repeatedly. Resume this decision only when genuinely new evidence or a new explicit decision context exists.

The previous assistant question was insufficiently contextualized: the Owner's confusion is not an answer and is not Option D ratification. Once this protocol correction is adopted, ChatGPT may present one corrected, concise G1 decision if the Owner is asking to advance the project beyond the protocol fix. That single presentation must first acknowledge the completed Entra/Authenticator work, explain the difference between human authentication and IABV bootstrap authority, and state the evidence/Option D outcomes with the safe default. Record the reply and provenance. After the Owner says unknown or gives a decision, do not ask the same question again unless genuinely new evidence materially changes the decision.

## 6. Anti-loop and route-denial protocol

Before every tool invocation or proposed experiment:

1. Check whether the exact route/action was already attempted and what result it returned.
2. Check whether that result is recorded as closed, denied, unsupported, or not authorized.
3. If the same route has already failed with `operational_block_active`, `governance_blocked=true`, or `SUPPORTED_ROUTE_NOT_FOUND`, do not retry it with the same inputs.
4. Do not reach the same protected local assets through GitHub, a browser, another model, another transport, a hidden command, or a different tool as a workaround for a denied local route. Use public GitHub only for genuinely public-source evidence and for documented changes that are themselves authorized.
5. If no route exists, state `SUPPORTED_ROUTE_NOT_FOUND`, keep the asset state `UNKNOWN; NOT_INSPECTED`, and stop. A failed route is not technical absence; a denied read is not permission to probe.
6. Do not repeat closed Windows/TPM, Google OIDC, phone/passkey, broad tool-catalogue, or previous source-scan investigations unless genuinely new evidence changes their prior disposition.
7. Before doing more work, ask: does this action reduce the currently blocking uncertainty, and is its route and authority established? If no, do not do it.

## 7. Authorization and cost gates

Treat every activity as separately scoped. Design adoption is not implementation authorization; a docs-only authorization is not authority to modify product code. A green static review is not a runtime pass. A branch commit is not a merge. A merge is not deployment. Authentication is not IABV authorization.

Without separate explicit authorization, do not:
- access protected local files or databases, or invoke a denied reader/list tool;
- register an Entra application, create secrets/credentials, create additional identities/directories, or change account/billing settings;
- buy licenses, remove Azure spending limits, deploy billable resources, or spend money;
- modify product source, run tests/build/runtime/transport, launch/reconnect a tunnel, merge, deploy, or release a block;
- infer that a public MCP tunnel is active from static source, or launch one to check.

Public source review says the documented HTTP MCP route lacks token authentication, and the inspected constructor disables DNS-rebinding protection while accepting wildcard hosts/origins when the SDK setting is available. Actual process/tunnel state remains `UNVERIFIED`. Do not expose the HTTP endpoint publicly. Preserve a local/non-public route until transport protection and separate per-operation IABV authorization are implemented and independently tested.

Documentation-only governance corrections may be performed on a new isolated branch when the user asks for them. Do not modify `main` or merge automatically; verify the exact diff and use a draft PR when appropriate.

## 8. Standard output and response behavior

After preflight, tell the user only the materially useful result in direct language:

- What is already done (recognize prior work and provenance).
- What is proven versus owner-reported, unknown, not inspected, or not authorized.
- The single blocker that matters now and why prior progress does not satisfy it.
- What was actually changed or executed, with commit/branch links and explicit non-actions.
- One next action, without making the user repeat old setup or re-answer a question already asked.

Do not say the coordinator is a conscious or autonomous "supermind." Treat that phrase as the user's metaphor for continuity across canonical records and verified receipts. Never claim that memory alone carries a complete or synchronized state.

## 9. Required routing snapshot after adoption

The canonical current-state block must preserve the following values after the separate Option D receipt and routing amendment is reviewed and merged:

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
ENTRA_DIRECTORY_AND_AUTHENTICATOR=OWNER_REPORTED_READY; DO_NOT_REPEAT_SETUP
EXISTING_INDEPENDENT_AUTHORITY=UNKNOWN_UNLESS_NEW_EVIDENCE
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
OWNER_DECISION_ON_OPTION_D=RATIFIED_OPTION_D_NO_BOOTSTRAP; RECEIPT=CHAT-ARCH-2026-10-23-M1A-G1-owner-option-d-no-bootstrap-ratification-receipt.md
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
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

This document changes operating/documentation guidance only. It does not close a gate, create trust, authorize implementation, or ratify Option D on the Owner's behalf.
