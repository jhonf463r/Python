# IABV new-chat continuity — M1A G1 Windows OS trust-bootstrap route

- Date: 2026-10-22, America/Bogota.
- Purpose: safely resume the same IABV work in a new ChatGPT conversation without repeating the closed attempt, losing the new Windows research, or making the Owner manually retrieve a prompt from GitHub.
- This is a coordination/continuity record. It does not authorize any new machine access, service installation, credential enrollment, protected read, merge, deployment, or operational block release.

## 1. Canonical routing — read in this order on the next chat

On current public `main`, re-fetch and read the current versions of:
1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md)

Then read:
- `CHAT-ARCH-2026-10-22-M1A-G1-trust-bootstrap-candidate-implementation-result.md` — closed prior attempt.
- `CHAT-ARCH-2026-10-22-M1A-G1-Windows-OS-trust-bootstrap-route-research.md` — new public Microsoft evidence and limits.
- `CHAT-ARCH-2026-10-22-M1A-G1-Windows-OS-trust-bootstrap-candidate-handoff.md` — complete Codex prompt already prepared.

Treat this document as a continuity receipt, not as a replacement for canonical files. Re-check remote branch and refs before any write. Do not scan the project again broadly.

## 2. Single active task

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE
PARENT_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
STATUS=OWNER_AUTHORIZED_FOR_CANDIDATE_ONLY; HANDOFF_READY_NOT_DISPATCHED
OWNER_SIGNAL="ok procede"
PRIOR_TASK=M1A_G1_TRUST_BOOTSTRAP_CANDIDATE_IMPLEMENTATION
PRIOR_RESULT=BLOCKED_MISSING_G1_TRUST_ANCHOR
NEW_EVIDENCE=WINDOWS_SERVICE_SID_CNG_KEY_ACL_NAMED_PIPE_DACL_DOCUMENTED
RESEARCH_RESULT=OS_SECURITY_PRIMITIVES_CONFIRMED; PROJECT_BOOTSTRAP_NOT_YET_IMPLEMENTED_OR_VERIFIED
RESEARCH_BLOB=0316f3b897ed5db98e185bf55db1ba482b7dcaf5
CODEX_HANDOFF_BLOB=0f9be4908d63dd525e572519c1e1891c894fea0a
CANDIDATE_BRANCH=m1a-g1-g3-governance-route-candidate-20261022
CANDIDATE_BASE=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
LAST_VERIFIED_CANDIDATE_HEAD=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
LAST_VERIFIED_CANDIDATE_TREE=ca963f8013809d4efcf56133a37d2efe148517e9
CANDIDATE_COMPARE=IDENTICAL; AHEAD_BY=0; BEHIND_BY=0; CHANGED_FILES=0
CANDIDATE_PRODUCT_CHANGES=NONE
CODEX_PROMPT_DISPATCHED=NO
PROMPT_DELIVERY_MODE=INLINE_IN_CHAT
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
```

## 3. What changed in understanding

The first bounded implementation task ended without code changes because the existing source did not show an independent G1 bootstrap authority. New public Microsoft documentation now grounds an alternative static architecture worth attempting in the isolated candidate:
- separate issuer Windows service with its own restricted service SID/token;
- persisted CNG signing key with an explicit restrictive DACL;
- protected installation/configuration/enrollment state;
- named-pipe IPC with a restrictive explicit DACL and actual OS-token/SID authorization;
- explicit Owner-initiated enrollment; never trust-on-first-use or startup auto-enrollment;
- bind the authenticated local Windows principal, issuer public key, policy revision and exact server instance;
- reader-side scoped signature/freshness/revocation verification at every protected reader call site, while the reader cannot modify the root or use the issuer private key.

Microsoft documentation establishes availability of relevant APIs/primitives in supported Windows configurations; it does NOT demonstrate the machine's configuration or project integration. Windows Hello/WebAuthn is only a possible factor. Creating a new credential does not prove the first registrant is the Owner. A local Windows SID only identifies a local principal, not automatically a civil identity or external identity-provider identity. If a real independent Owner ceremony and exact server-instance identity binding cannot be established without unsupported assumptions, stop with the exact gap.

## 4. Immediate next steps for the next chat

1. Revalidate canonical routing documents and remote candidate branch through GitHub. Ensure current `main` is read; do not rely solely on the SHAs above, which are the last verified values at the time of this receipt.
2. Do not repeat the previous broad source inventory, G1 feasibility report, or old terminal conclusion.
3. The full candidate-only implementation prompt is already saved in the handoff document. **The next assistant must also provide the full copy-ready Codex prompt inline in the chat**; do not make the Owner open GitHub to obtain the prompt. The intended destination is `Codex — existing UI/session`.
4. The existing UI has not received the prompt from ChatGPT. Keep `CODEX_PROMPT_DISPATCHED=NO` unless an actual Codex response is returned and correlated. The Owner may paste the inline prompt; then review the result and verify candidate head/diff/blob directly via GitHub.
5. Writes are allowed only to the exact isolated remote candidate branch and only if Codex can prove its write target. If the authorized remote candidate cannot be distinguished from the Owner's existing local/dirty checkout, stop.
6. Do not execute source or install/test the service. This attempt is source/documentary only. Explicitly defer live OS ACL verification, service installation, CNG provider availability, credential enrollment, tests/build/runtime, reader invocation and real transport.
7. Preserve the exact separation: G3 is the versioned operation-to-canonical-target resolver; Entry 274 request/approval/decision/operation/result receipts are a distinct ledger requirement.

## 5. Non-negotiable prohibitions

- No local or dirty checkout; no `data/`, SQLite, secrets, credentials or `.env`.
- No shell/PowerShell, local OS probes, tests, build, executable linters, runtime, service/process launch, MCP calls, protected reads or real transport.
- No service installation/config changes, no key generation or credential enrollment on the Owner's machine, no new auth, no paid plan, no extra spend.
- No fabricated issuer, trust root, Owner identity, server identity, key/allowlist, auto-enrollment, no-op verifier or separation by class names only.
- No merge, deployment or block release.
- No automatic follow-on after a terminal result. All eight implementation gates stay open unless evidence independently satisfies a gate.

## 6. Final state expected before the next chat's Codex handoff

```text
TASK=M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE
STATUS=OWNER_AUTHORIZED_FOR_CANDIDATE_ONLY; HANDOFF_READY_NOT_DISPATCHED
GOVERNANCE=KEEP_BLOCKED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
LOCAL_CHECKOUT=NOT_ACCESSED
LOCAL_OS_PROBE=NOT_AUTHORIZED
SERVICE_INSTALLATION=NOT_PERFORMED
CREDENTIAL_ENROLLMENT=NOT_PERFORMED
REAL_TRANSPORT=NOT_RUN
MERGE_DEPLOY=NOT_AUTHORIZED
BLOCK_RELEASE=NOT_AUTHORIZED
BRIDGE=BRIDGE_NOT_READY
```
