## 2026-10-11 OWNER DESIGN DECISION — OPTION A SELECTED

**Owner decision:** Option A — enrolled Windows account/principal plus explicit, intent-bound confirmation. Additional conditions: none stated.

**Authority scope:** design direction only. This is not authorization to implement, create or alter worktrees, modify source/configuration, run tests/builds, inspect/operate local processes, start/reconnect/use MCP, or disclose operational snapshots. Do not infer any such permission from this selection.

**Next design refinement:** define enrollment and verification requirements for the Windows principal (including the stable principal identifier and how enrollment is protected), exact UI confirmation content, the RQ223 receipt fields and integrity/expiry/single-use semantics, and the pre-effect verifier/consumer. Explicitly account for shared accounts, unlocked sessions, account switching, stale/replayed receipts and trusted-process compromise. A Windows SID or UI click alone is not an authorization receipt.

**Still unresolved:** the authorized source review did not establish that Option A already exists. RQ218 canonical root/protected paths, immutable baseline, exact allowlist and clean isolated worktree gates remain open. Preserve the dirty/detached worktree `e46d8304167708bed0764d3bf2be8fd6643e8944`. RQ224 remains open; global MCP readiness remains `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`.

---

# CHAT-ARCH-2026-10-10-228 — RQ224 Owner-Identity Trust Options (Design Only)

## STATUS / AUTHORITY BOUNDARY

**Historical classification at original issuance:** `OWNER_IDENTITY_TRUST_OPTIONS_READY_FOR_OWNER_SELECTION`. The Owner later selected Option A on 2026-10-11 in the decision block at the top of this file; the preselection status below is superseded.

**Design baseline:** remote `main @ fcc76be07d9b5845dc7ea95a610eec9deab17e3d`. The reviewed source is repository source only; this record says nothing about a running local instance or historically loaded bytes.

At the time this options record was initially prepared, the Owner had authorized comparison of options but had not yet selected one. The subsequent 2026-10-11 decision at the top of this file selects Option A as the design direction. That selection still does **not** authorize implementation, worktree creation, configuration changes, tests/builds, process inspection, runtime, MCP start/reconnect/tool calls, operational snapshot disclosure, or any mutation. Model A remains the accepted threat assumption only for the first supervised prototype: process/code integrity is trusted. This does not supply the missing Owner identity, authorization receipt, or anti-replay mechanism.

## 1. Source-grounded starting point

The authorized static inspection covered `IABV_v1.5/src/iabv_v15/services/security/` and `IABV_v1.5/src/iabv_v15/ui/` only.

- [`human_approval_broker.py`](https://github.com/jhonf463r/Python/blob/fcc76be07d9b5845dc7ea95a610eec9deab17e3d/IABV_v1.5/src/iabv_v15/services/security/human_approval_broker.py): request/result objects and `approve(request_id, payload)`; source does not demonstrate an authenticated Owner principal, trust source, or mutation-bound receipt.
- [`bootstrap.py`](https://github.com/jhonf463r/Python/blob/fcc76be07d9b5845dc7ea95a610eec9deab17e3d/IABV_v1.5/src/iabv_v15/bootstrap.py): the inspected signal-wiring path connects credential, clarification, dependency and activity callbacks, but does not register the broker's `prompt_handler`.
- [`evolution_center_viewmodel.py`](https://github.com/jhonf463r/Python/blob/fcc76be07d9b5845dc7ea95a610eec9deab17e3d/IABV_v1.5/src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py) and [`EvolutionCenterPage.qml`](https://github.com/jhonf463r/Python/blob/fcc76be07d9b5845dc7ea95a610eec9deab17e3d/IABV_v1.5/src/iabv_v15/ui/qml/pages/EvolutionCenterPage.qml): the dashboard exposes pending requests and learned policies, but the inspected path does not prove an authenticated approve/reject return.
- [`centro_vivo_viewmodel.py`](https://github.com/jhonf463r/Python/blob/fcc76be07d9b5845dc7ea95a610eec9deab17e3d/IABV_v1.5/src/iabv_v15/ui/viewmodels/centro_vivo_viewmodel.py): `approveAccountSwitch()` records a user-selected account for a particular tool. It is not Owner authentication or general mutation authority.
- [`control_center_viewmodel.py`](https://github.com/jhonf463r/Python/blob/fcc76be07d9b5845dc7ea95a610eec9deab17e3d/IABV_v1.5/src/iabv_v15/ui/viewmodels/control_center_viewmodel.py): `SystemIdentityRegistry` exposes IABV subsystem/root/health metadata. The registry is not evidence of a human principal.

These are bounded negative findings, not a claim that authentication is absent throughout the repository or in external/OS components. Do not repeat RQ219/RQ220 discovery or expand into a general authentication-system search.

## 2. Contract that every viable option must satisfy

Authentication and authorization remain separate:
1. Authenticate an enrolled Human Domain Owner principal to the confidence required by the chosen threat model.
2. Present the exact intent that will be authorized.
3. Bind the decision to the RQ223 tuple `A = (P, O, R, S, D, T, N)`: principal, operation, canonical target resource, exact scope, approved content/delta where relevant, validity conditions and a unique single-use identifier.
4. Verify the receipt before the first effect; consume it once and fail closed on absent, unknown, stale, malformed, denied, consumed, mismatched or unverifiable authority.
5. Correlate intent → prompt → Owner decision → verification/consumption → effect/result. An audit record or `approved=True` alone is not authorization.
6. Keep the Model A limitation explicit: if the process itself is compromised, an in-process verifier/receipt is not an independent defense.

## 3. Alternatives for explicit Owner selection

### Option 0 — No automated mutation authorization (safe fallback)

Keep MCP read-only or planning-only for this tranche. For mutations, IABV presents a proposed diff/action and the Owner applies it manually using a separately trusted tool/UI.

- **Guarantee:** does not falsely claim a missing trust source; avoids granting privileged write authority to the current unverified broker/UI path.
- **Limitations:** does not deliver autonomous self-update; retains a manual hand-off and does not solve the long-term `human ↔ IABV` goal.
- **Use when:** no available identity option is accepted or source-grounded authority cannot be established.

### Option A — Enrolled Windows account + explicit, intent-bound IABV confirmation

Candidate for a single-owner Windows laptop. During an explicit enrollment step, bind the Owner profile to an OS principal identifier (for example a Windows user SID acquired through an appropriate OS API). For each covered operation, display a human-readable immutable intent: operation, canonical target, exact scope, and relevant proposed content/diff. A confirmed decision would produce the RQ223 receipt, with expiry and single-use nonce, and a consumer would verify/consume it before the effect.

- **Could provide:** binding to a specific OS account; explicit confirmation in the IABV UI; exact operation/resource/scope binding if correctly implemented.
- **Does not prove:** that a distinct human is physically present merely because a process runs under that account; that account is not shared; that an unlocked desktop cannot be used by another person; or resilience to process compromise.
- **Model A fit:** compatible with the accepted trusted-process assumption, but only after the Owner explicitly accepts the account/session limitations.
- **Unproven prerequisite:** no such Owner enrollment or SID-verification mechanism was found in the authorized IABV directories. OS identity is a design candidate, not existing repository capability.

### Option B — Fresh OS-mediated user-presence verification for each privileged decision

A native authenticator/user-presence step (for example a supported Windows Hello/platform-authenticator flow) would be challenged for each high-risk operation and bound to the exact intent digest before the application issues a receipt.

- **Could provide:** stronger evidence of a fresh user-presence gesture and, depending on the API and authenticator, proof tied to an enrolled local account.
- **Does not automatically provide:** operation/resource/scope enforcement or replay prevention; these still require the receipt contract and pre-effect verifier.
- **Costs/limitations:** Windows-specific integration, enrollment/recovery UX, additional prompts, API availability and testing. If the application process is trusted under Model A, the implementation still assumes that trusted process correctly associates the verified challenge with the displayed intent.
- **Unproven prerequisite:** no Windows Hello or platform-authenticator integration was found in the authorized source scope. This option is not implemented.

### Option C — External identity provider with a challenge-bound decision

An OIDC/enterprise identity provider or WebAuthn-capable service could authenticate the Owner and return a fresh assertion/challenge response bound to an immutable mutation-intent digest.

- **Could provide:** an externally managed identity, policy and potentially multi-device authentication/audit.
- **Limitations:** external service, network and outage dependencies; enrollment/account recovery; new integration and token-lifecycle complexity. A generic login/token is not a receipt for a specific mutation. Under Model A, local code must still verify and correctly bind the response; this option alone does not resist a compromised local process.
- **Use when:** the Owner needs portable or enterprise identity beyond one Windows account and accepts the added operational dependency.
- **Unproven prerequisite:** no provider or existing integration has been selected or verified for this purpose.

### Option D — Independently enforced trust boundary (Model B, outside current prototype)

A separately enforced authorization service/process or hardware-backed boundary would verify and consume authority such that the main IABV process cannot silently bypass it.

- **Could provide:** a route toward surviving some forms of compromise of the main process/verifier.
- **Limitations:** substantially more demanding architecture, isolation, lifecycle, threat analysis and operational work. Merely moving a Python verifier into another in-process module or another UI window would not establish independence.
- **Status:** not selected. Model A is the current first-prototype assumption; Option D is included only to make the limit explicit and must not silently creep into the first tranche.

## 4. Comparison matrix

| Dimension | Option 0 | Option A | Option B | Option C | Option D |
|---|---|---|---|---|---|
| Automated mutation | No | Possible after receipt contract | Possible after receipt contract | Possible after receipt contract | Possible with separate boundary |
| Owner principal source | None claimed | OS account enrollment | OS account + fresh presence | External identity | Independent authority boundary |
| Exact mutation binding | Manual diff/process | Required in receipt | Required in receipt | Required in receipt | Required in external boundary |
| Works offline | Yes for manual path | Potentially | Depends on API | Usually not for fresh external auth | Depends on design |
| Complexity | Lowest | Low–medium | Medium | High | Very high |
| Resists compromised IABV process | Not applicable for automated writes | No | No, not by itself | No, not by itself under Model A | Target requirement |

## 5. Non-negotiable boundaries, regardless of selected option

- No pre-approver/learned policy can replace fresh Owner approval for the first privileged tranche.
- A local account SID, UI click, broker result, task persistence, log line or PR approval cannot substitute for the complete mutation-bound receipt.
- The exact canonical workspace root, protected paths, immutable baseline, clean separate worktree and file allowlist remain RQ218 Owner gates.
- The existing dirty/detached worktree at `e46d8304167708bed0764d3bf2be8fd6643e8944` must remain untouched.
- Source edits, worktree creation/change, tests/builds, runtime/process operations, MCP startup/reconnect/tool calls and snapshot disclosure are not authorized by this options document. They each retain separate gates.
- The prospective launch-provenance plan has a timing caveat: recording after `AppBootstrap` cannot attest startup side effects that may already have occurred.

## 6. Historical owner decision prompt — superseded on 2026-10-11

At original issuance, select one path for design refinement. This prompt was resolved by the Owner's Option A decision at the top of this file; the alternatives below are retained as historical comparison, not current open choices:
- **0** — keep automated mutation authority off; keep planning/read-only scope.
- **A** — enrolled Windows principal plus explicit intent-bound confirmation, accepting shared/unlocked-session and trusted-process limitations.
- **B** — add fresh OS-mediated user-presence authentication per privileged decision.
- **C** — external identity provider with challenge-bound mutation decision.
- **D** — pause Model A and authorize a separate Model B trust-boundary design.
- **None yet** — historical preselection state only; no longer the current decision.

A selection only chooses the design direction. It does not authorize implementation, identify an already-existing trust source, close RQ224, or override the RQ218/RQ223 gates.

## 7. Historical classification at original issuance

`OWNER_IDENTITY_TRUST_OPTIONS_READY_FOR_OWNER_SELECTION` (superseded for decision status by the 2026-10-11 Owner selection of Option A above).

RQ224 remains open. Global MCP readiness remains `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. The selected direction is a static design artifact only and does not authorize implementation.

END OF RECORD
