# Owner continuity and approval-request protocol

- Date: 2026-10-26, America/Bogota.
- Purpose: preserve the Owner's intent and correct the collaboration protocol across IABV → Codex → ChatGPT sessions.
- Status: supporting protocol; not a replacement for the canonical route.
- Canonical route authority remains [CURRENT-STATE.md](./CURRENT-STATE.md). Every new session must fetch it from live `main` before material action.
- This document does not authorize code changes, protected reads, trust-root provisioning, tests/runtime, merge/rebase, or deployment.



## Latest cross-chat handoff — 2026-10-27: GitHub App key recovery

For the active local GitHub App key-recovery episode, read the [2026-10-27 cross-chat handoff](https://github.com/jhonf463r/Python/blob/chat-continuity-key-recovery-handoff-20261027/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-27-M1A-GITHUB-APP-KEY-RECOVERY-CROSS-CHAT-HANDOFF.md) before asking the Owner for further action. Section 14 records that local Codex accepted the newly obtained PEM as a valid RSA PKCS#1 private key (2048 bits) and computed its public fingerprint in memory, but did not compare it with GitHub. The 40-character “Copyable key fingerprint” remains a format discrepancy against the documented SHA-256/Base64 representation. Use section 14's local clipboard comparison prompt; keep the value off the model/chat/transcript, and return NOT_VERIFIED if the format cannot be reconciled. Do not repeat the old TXT or generic download instructions, store the key, or generate tokens/call the App API. This is supporting continuity, not a replacement for CURRENT-STATE.md; re-fetch canonical main first. Never ask for the private key in chat.

## 1. Owner intent and correction

The Owner wants project continuity across chats, less repetition, and use of previous deductions, mistakes, rejected attempts, and live GitHub evidence. The Owner primarily uses the ChatGPT phone app and expects Codex/IABV to ask for approvals in clear language when an actual Owner decision is required.

**Do not ask the Owner to choose unexplained technical/governance options (such as A/B/C/D) as the first step.** First recover the route and prior decisions, inspect exact repository evidence available within the permitted scope, and narrow the unresolved decision. Explain what is being proposed, why now, what will change, the risk, how it will be verified, and only then ask one plain-language question if the decision cannot responsibly be inferred.

The Owner's wish for Codex/IABV to request authorization is evidence of the intended user experience. It does not prove that a runtime trust root, mandate, authenticated issuer, G2 publisher, G3 target registry, secure IPC, or production approval flow is already implemented.

## 2. How continuity actually works

Do not claim that every chat automatically contains all prior conversations or that ChatGPT memory is a live copy of the repository. Use this repeatable loop:

1. Read the latest live `CURRENT-STATE.md` first. Its current top-level route is the sole operational routing authority.
2. Use conversation memory/recent-chat summaries to recover Owner intent, terminology, chronology, prior failures, and useful document/PR pointers. Treat summaries as navigation aids, not current-state evidence.
3. Re-fetch exact GitHub refs needed for the active frontier: main commit, PR head/base, source blob, run/job state, or evidence receipt. A previously recorded SHA is historical until confirmed live.
4. Classify consequential claims as verified fact, source-bound observation, inference, hypothesis, open question, or Owner decision.
5. Preserve chronology, provenance, competing explanations, contradictory evidence, rejected approaches and prior versions. Correct a mistaken conclusion without erasing the trace that explains the correction.
6. Take one bounded action that discriminates between live possibilities. Avoid repeating an inspection, prompt, or workflow unless a material precondition changed.
7. Record the exact delta, limits, and next dependency in an approved durable location. Fetch back and verify every write.

The “Mente Espacio-Tiempo” concept is implemented here as a method of longitudinal traceability and causal prioritization, not a claim of consciousness or a separate runtime brain. Capture ideas before relevance filtering; low relevance means deferred, not deleted. Repetition, retrieval frequency, a hash, a successful write, or a plausible explanation does not establish authority or learning.

## 3. Four things that must not be confused

- **Owner decision:** permission for a stated, bounded action.
- **GitHub account/repository identity:** evidence of an account or repository permission under the relevant GitHub mechanism.
- **Bridge runtime authority:** a production mechanism that independently verifies the root, mandate, principal, scope, freshness, revocation and target.
- **Operation result:** evidence that a specific read/action actually occurred and was checked.

These layers may be connected by a design, but one does not automatically prove the next. In particular, access by this assistant through a connected GitHub tool does not prove that IABV authenticates the Owner through GitHub. GitHub OAuth/user authorization is a candidate to investigate, not an established G1 solution. A repository permission, signed commit, merge event, conversational “yes”, local key or hash is not by itself the bridge's independent trust root.

## 4. Approval request contract

When approval is genuinely required, the agent must state:

- **Action and target:** exact repository, branch/PR and commit or the bounded resource/action.
- **Reason:** the specific dependency that makes this step necessary and the evidence for it.
- **Effects:** files, settings, permissions, data, execution and what will remain untouched.
- **Risk and reversibility:** realistic consequences and any recovery path.
- **Verification:** exact observable result and where it will be recorded.
- **Decision:** one direct question in everyday Spanish; offer distinct options only if the Owner really must choose.

Do not ask for passwords, API tokens, private keys, payment details, or for the Owner to design a cryptographic protocol. The agent should do the technical investigation first. If no Owner decision is actually required for a safe, authorized, read-only/documentary step, proceed rather than ask another redundant question.

Approval is scoped to the exact action, target/revision and stated effects. “Continue”, “proceed”, or approval of a design must not be expanded into authorization to provision a trust root, create credentials, access protected content, run code/tests/workflows, merge/rebase, or deploy.

Codex/IABV may be the intended interface for future approval requests, but it is not an operational runtime path until the project demonstrates that the request reaches the actual Owner and the response is authenticated, fresh, bound to the exact operation/target, replay-safe and independently rechecked at the protected boundary. Until then, use the permitted conversational interface for human decisions without treating the chat itself as runtime trust infrastructure.

## 5. Correct order of work

1. Preserve the existing fail-closed boundary.
2. Investigate, within permitted evidence scope, whether a real, pre-existing root, mandate and independent verification channel exist. This is an agent-side research question first—not a request for the Owner to solve key management.
3. If evidence cannot establish G1, identify precisely what was inspected and what remains unknown. Do not infer non-existence from one absent source file or branch.
4. Only after G1 is established should G2's authorized, fresh catalogue/policy and revocation producers, then G3's versioned operation-to-target producer, be evaluated as closable gates.
5. Treat implementation, protected reads, tests/runtime, merge/rebase and deployment as separate gated actions with exact, revision-bound authorization.
6. Keep the GitHub Actions billing-lock blocker separate from G1/G2/G3. Zero-job startup failures mean tests did not run; they neither prove nor refute the trust root. Do not repeat unchanged workflows or completed billing/support investigations without material new evidence.
7. Keep PR #531, #546 and #547 in their own scopes. A design PR is not canonical adoption or bridge readiness.

## 6. Required beginning/end of every session

**Before asking the Owner anything:** re-read live `CURRENT-STATE.md`; identify the current main SHA; fetch only the active frontier's exact references; distinguish what the Owner has already decided from what evidence establishes; and state the current blocker in plain language.

**After each material action:** record what changed and what did not, exact SHA/blob/run and links, whether the outcome was fetched back, what remains unknown, and the single next dependency. If an update is blocked or unsafe, report that rather than silently switching to another write route.

## 7. Starting state recorded with this protocol

At authoring time, the route remains:
- `ACTIVE_FRONTIER=G1_INDEPENDENT_ROOT_MANDATE_AND_VERIFICATION_CHANNEL`
- `G1/G2/G3=NOT_ESTABLISHED`
- `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`
- `PROTECTED_READS=FAIL_CLOSED`
- `BRIDGE=BRIDGE_NOT_READY`
- `TESTS=NOT_RUN; RUNTIME=NOT_RUN`
- GitHub Actions billing-lock root cause remains unknown.
- PR #531, #546 and #547 are independent open draft candidates, not evidence of production readiness.

These values are a dated snapshot, not perpetual facts: the next session must revalidate live references through `CURRENT-STATE.md`.


## Latest bounded route recheck — 2026-10-26

- Live canonical route is still [CURRENT-STATE.md](./CURRENT-STATE.md), blob `7a261129c8611cc0b5ed3788fc00c5d90ae189ea`; do not replace it with this supporting protocol.
- The prior G1 asset task is terminal for source-locator search: no local asset locator was found in inspected source; Windows trust-store/service/ACL/IPC metadata was **NOT_RUN**. The resulting authority state remains UNKNOWN/NOT_INSPECTED, not absent. See [terminal route correction](./CHAT-ARCH-2026-10-25-TERMINAL-TASK-ROUTER-TRANSITION-CORRECTION.md) and the [bounded assessment receipt with its exact prompt](./CHAT-ARCH-2026-10-25-M1A-G1-OWNER-DECISION-EXISTING-TRUST-ASSETS-READONLY-ASSESSMENT-RECEIPT.md).
- This ChatGPT session has GitHub repository access but no exposed connection to the Owner's existing Codex UI or local Windows session. Do not claim local metadata inspection was performed or use an alternate path to bypass that boundary. New GitHub account/repository metadata confirms control-plane access only; it does not establish IABV runtime authority or the Owner-to-Windows/issuer binding.
- Owner's latest instruction asks agents to keep using continuity and to request bounded approvals in plain language. It does not create a root or automatically authorize protected reads, implementation, tests/runtime, merge/rebase or deployment. `G1/G2/G3=NOT_ESTABLISHED`; `PROTECTED_READS=FAIL_CLOSED`; `BRIDGE=BRIDGE_NOT_READY`.

## Codex approvals (2026-10-26)

OpenAI documents approval controls for eligible Codex actions and mobile access to compatible desktop Codex chats through Remote. This may let the already-authorized task run in the existing local session if connected. Codex action approval does not establish IABV G1 root or Owner-to-Windows/issuer binding. Reuse the [existing task receipt/prompt](./CHAT-ARCH-2026-10-25-M1A-G1-OWNER-DECISION-EXISTING-TRUST-ASSETS-READONLY-ASSESSMENT-RECEIPT.md); no broad rescan or cloud substitute. Ref: https://help.openai.com/es-419/articles/20001275-chatgpt-work-and-codex
