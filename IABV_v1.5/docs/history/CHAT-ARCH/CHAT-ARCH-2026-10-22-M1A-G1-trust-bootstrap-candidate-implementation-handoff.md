# M1A G1 trust-bootstrap — bounded candidate implementation handoff

- Date: 2026-10-22, America/Bogota.
- Task: `M1A_G1_TRUST_BOOTSTRAP_CANDIDATE_IMPLEMENTATION`.
- Parent: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.
- Destination: Codex, existing UI/session.
- Owner authorization: exact token `ACCEPT_G1_TRUST_BOOTSTRAP_POLICY_AND_AUTHORIZE_CANDIDATE_ONLY`, followed by the instruction to proceed with solving the remaining bridge prerequisites.
- Normative baseline: M1A v1.0.1 blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`.
- Entry 274 blob `5943a87d907436fc7ecac31534cbfcd31fe7de55`.
- Candidate branch: `m1a-g1-g3-governance-route-candidate-20261022`.
- Pinned base: `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db`.

## 1. Reason for this bounded task

The previous bounded attempt stopped before edits with `BLOCKED_MISSING_G1_TRUST_ANCHOR`. The exact unresolved edge is an independently trusted bootstrap/enrollment boundary linking the real Owner principal, the issuer credential and the intended server instance, with effective separation from the requester and reader. The candidate source currently does not demonstrate that route.

The Owner has now accepted the conditional G1 trust-bootstrap policy and has directed the coordinator to proceed. This handoff therefore asks Codex to attempt a concrete candidate implementation of an explicit Owner-controlled G1 bootstrap boundary, not to repeat the feasibility review.

Prior terminal receipt: [G1 trust-bootstrap candidate attempt result](./CHAT-ARCH-2026-10-22-M1A-G1-trust-bootstrap-candidate-attempt-result.md), blob `3c120ed84d1c19f6f205f3f7ed9b4dc620fcbf24`.

## 2. Required candidate behavior

Evaluate and, where safely supportable by documented platform APIs, implement the minimum G1 path:

- Owner-initiated enrollment through a local, explicit, interactive ceremony that is not exposed as an MCP/network tool.
- Windows WebAuthn / Windows Hello only as a candidate Owner-authentication factor; require fresh challenge-response and verify the returned assertion against the registered public credential, relying-party identity and expected challenge. Do not assert local availability or TPM support.
- A real issuer signing credential under platform key protection and access controls; the issuer must not expose its private key or enrollment write path to the requesting agent or read/list process.
- Explicit binding of the authenticated Owner principal, issuer identity/key, policy revision and exact server-instance identity.
- Reader-side verification using a trust record it cannot create or change for itself; all missing/unknown/malformed/untrusted/expired/revoked/conflicting evidence denies.
- Effective process/OS access-control separation and authenticated IPC if a separate issuer service/process is required. Different classes in the same caller-controlled process are not sufficient proof of separation.
- Key and credential lifecycle, rotation/revocation and durable audit events appropriate to the selected mechanism.
- No issuer or trust-administration operation reachable through the external MCP tunnel. No read decision releases an operational block.

Do not hardcode a credential, key, owner identity, public key, issuer ID, server fingerprint, trusted catalogue or authorization. First-run enrollment must be an explicit Owner ceremony, not trust-on-first-use silently accepted by the requester or reader.

## 3. Implementation scope and stop rules

Use the exact remote candidate branch only. Before editing, verify branch name, tip and parent/base. If the available Codex workspace might be the Owner's existing checkout or isolation cannot be proven, stop with `ISOLATED_CANDIDATE_IDENTITY_UNVERIFIED`; do not inspect it as a workaround.

Use current public-main routing docs to restore authorization and use the pinned candidate for product source. Relevant previous blobs are listed in the prior receipt. Do not repeat the broad source inventory or re-review the feasibility report.

Implement source changes only if the chosen bootstrap mechanism has a coherent and evidence-backed trust path. Do not stop merely because the route has to be newly implemented; that is the objective. But stop at the first dependency that cannot be responsibly implemented without inventing trust or relying on an unsupported platform guarantee.

A fail-closed contract/interface may be added only if it represents a real boundary and is wired to all relevant G1 call sites in the candidate. A stub, TODO, injectable fake, self-issued local JSON trust root, no-op verifier, caller-supplied identity, or class-name-based separation does not count as implementation.

Do not expand into G2 catalogue/producer/revocation implementation or G3 operation-to-target resolver implementation beyond identifying their G1 interactions. Do not claim G1 operationally closed from static code alone. Report what would still require explicit local enrollment and later independent verification.

## 4. Strict exclusions

No Owner pre-existing/dirty checkout; no other local candidate; no `data/`, SQLite, secrets, credentials or `.env`.

No shell/PowerShell, tests, builds, linters that execute product code, probes, IABV/MCP runtime, Codex App Server, Ollama, service installation, platform configuration changes, credential creation/enrollment, live reader invocation or real transport.

No machine security/GPU/model/network/environment changes. No merge, deployment, protected read or operational-block release. Do not ask the Owner to perform manual environment setup as a workaround.

Remote Git operations and source writes are confined to the exact candidate branch. If the existing Codex session cannot edit that remote candidate safely, stop and state the capability limitation.

## 5. Deliverable

Return one terminal status:

- `G1_BOOTSTRAP_IMPLEMENTED_IN_CANDIDATE_STATIC_UNVERIFIED`
- `PARTIAL_G1_CANDIDATE_WITH_EXACT_REMAINING_AUTHORITY_GAP`
- `BLOCKED_MISSING_G1_TRUST_ANCHOR`
- `ISOLATED_CANDIDATE_IDENTITY_UNVERIFIED`

Include exact base/head, every changed path and blob, evidence for each security boundary, where Owner enrollment would occur, how requester/issuer/reader separation is enforced, any unsupported platform prerequisite, and the smallest remaining dependency. Provide the diff/commit reference on the candidate branch if code changed; fetch back the resulting paths/blobs. Do not claim runtime readiness.

Required terminal state:

```ini
TASK=M1A_G1_TRUST_BOOTSTRAP_CANDIDATE_IMPLEMENTATION
OWNER_POLICY=ACCEPTED
IMPLEMENTATION=AUTHORIZED_FOR_ISOLATED_CANDIDATE_ONLY
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

Stop after this bounded candidate result. Do not start a follow-on task automatically.
