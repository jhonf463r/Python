# M1A G1 — New-chat continuity handoff

**Date:** 2026-10-23 (America/Bogota)  
**Task:** `M1A_G1_NEW_CHAT_CONTINUITY_HANDOFF`  
**Active frontier:** `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`  
**Operating mode:** source-grounded coordination and documentary continuity only

## 1. Current verified checkpoint

- Remote `main` immediately before this writeback: `76708568d441b6172425367ae287b69a280cec38`.
- Parent tree: `03ce7631d0eedab9cff191065b518359cb3836ba`.
- The five canonical entries were re-fetched at this checkpoint in the mandatory order before preparing this handoff:
  1. `IABV_v1.5/AGENTS.md` — blob `535f5c41f9d877488a06105124e5e5743b6f8c22`
  2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md` — blob `a17803b6d9722cbfc9f5bc89f19bd3a93e9b6b71`
  3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — blob `5d71638decde77a5c0a097f7579f6bdd272bc0f5`
  4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md` — blob `8f92e2d3380b5196679c09bd959cf5e41cefaaa3`
  5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md` — blob `068cb734cf277358fbef972073dfa480c3664019`
- Latest bounded review supplied by the Owner: `M1A_G1_OWNER_APPROVED_MANIFEST_TPM_BOUND_ISSUER_REVIEW`, result `BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH`.
- The actual source result that continues to govern is `BLOCKED_MISSING_G1_TRUST_ANCHOR`. G1 was not established by the later design reviews.

## 2. Purpose and user intent for the next chat

The Owner's primary goal is to unblock IABV and resume the governed bridge, not to spend more turns configuring the personal phone or repeating feasibility inventories.

The Owner wants a low-friction path, no unnecessary paid service/new account, and does not want loss of the personal Android phone to remove all access. A syncable personal passkey with an offline recovery option remains a **candidate for the human-authorization gate only**. No IABV passkey, recovery credential, OAuth client or new authentication was created. Do not continue the Google-account setup checklist unless the Owner asks; it is not the blocker for G1.

Every prompt for another AI must identify the exact destination and capability near the beginning, carry the governing constraints, include the current evidence/provenance, name the first open edge, state stop conditions and require a structured final result. The Owner prefers complete prompts inline rather than instructions to retrieve prompts manually from another website.

## 3. Reviews already completed — do not repeat

### Windows G1 candidate attempt

The terminal Windows candidate attempt ended at `BLOCKED_MISSING_G1_TRUST_ANCHOR`. Windows service SID, CNG key ACLs, protected service state and named-pipe DACL are platform primitives, not proof that an integrated independent Owner-to-Windows-to-issuer-to-exact-server trust chain exists.

Candidate branch `m1a-g1-g3-governance-route-candidate-20261022` was previously verified at base/head `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db`, identical to its pinned base with zero product changes. Do not treat the branch as a completed fix.

### GitHub account/token route

The existing `gh` CLI token flow using broad `repo` scope is not G1 enrollment. A successful repository API response or GitHub login is not proof of local Windows identity, issuer-key custody or exact server instance. GitHub approval can be an audit/control-plane event tied to a manifest; it does not verify the truth of machine claims included in that manifest.

The account ID `28608338` remains a **candidate only** and has not been adopted as an immutable governance identity. Do not adopt it without an explicit Owner decision.

### Personal phone and passkey route

The Owner reported a personal Android phone. No pre-existing phone authenticator bound to IABV or authenticated secondary channel was found in the reviewed continuity evidence. Physical presence, a QR code, a manually displayed challenge or a button press is not automatically a machine-verifiable Owner identity assertion.

A syncable personal passkey and offline recovery may improve personal-account recovery. That does not establish IABV's initial trust anchor, issuer identity or server-instance identity. Do not create the passkey or new credentials without separate authorization.

### Google OIDC

Terminal result: `NOT_WORTH_EXTERNAL_SETUP`. A new Google Cloud project/OAuth client/redirect setup adds a credential surface but does not independently solve first enrollment, the Windows principal binding, issuer custody or exact-server binding. Do not repeat this design review or start OAuth registration.

### GitHub manifest + TPM-bound issuer

The Owner-supplied Sonnet review reported:
- GitHub approval could record the exact approved payload, but GitHub cannot independently validate embedded Windows SID, TPM or machine-instance claims.
- The Microsoft Platform Crypto Provider can support TPM-backed non-migratable keys, but non-exportability does not establish which exact server process/installation is authorized.
- TPM attestation depends on independently trusted EK/AIK provenance, a justified certificate trust chain, or an allowlist whose own initial provenance and protection are established. A component's self-assertion is not an acceptable trust root.
- A manually populated EKPub/AIKPub allowlist could be considered only if the identity value is obtained/verified through a genuinely independent process and the reader's trust in the allowlist itself is specified. Merely displaying a value on a potentially compromised Windows screen is not independent.
- The exact-instance binding and end-to-end reader verification remain unresolved even if a TPM identity is trusted.

Review result: `BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH`.

## 4. Reconciliation of tool/writeback experience

A previous documentation writeback initially placed a receipt and updated route files at repository-root paths rather than under `IABV_v1.5/`. This was detected during fetch-back and corrected in commit `2abc6f7c049a551ef158caba4b460c38626d6644`; a subsequent canonical-routing commit is `76708568d441b6172425367ae287b69a280cec38`.

Reusable procedure for every future continuity writeback:
1. Re-fetch the current `main` ref; never reuse an old SHA.
2. Read the five canonical entries in their prescribed order.
3. Pass repository-root-relative full paths (including `IABV_v1.5/`) to Git tree operations; never strip the project prefix when constructing tree entries.
4. Use compare-and-swap/expected-SHA on the branch ref.
5. After the commit, fetch `main`, recursively inspect the committed tree, fetch back the receipt and each canonical entry, verify exact link resolution, and confirm no misplaced root copies remain.
6. Do not declare the writeback complete before step 5. Record any writeback defect transparently and correct it before handoff.

This was a documentation-only path correction. It did not change product code or unlock any gate.

## 5. Governing evidence and unresolved authority chain

Required chain:

`independent Owner authority`
→ `explicit transaction-specific enrollment approval`
→ `authenticated Windows principal/SID`
→ `protected issuer key`
→ `exact installed server instance`
→ `independent reader verification and authoritative revocation`.

Current status:
- `OWNER_INTENT_TO_ENROLLMENT_REQUEST=NOT_ESTABLISHED`
- `OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED`
- `OWNER_TO_ISSUER=NOT_ESTABLISHED`
- `TPM_AVAILABILITY=UNVERIFIED`
- `TPM_ATTESTATION_TRUST=NOT_ESTABLISHED`
- `ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED`
- `READER_VERIFICATION=NOT_ESTABLISHED_END_TO_END`
- `REVOCATION_AUTHORITY_AND_CONSISTENCY=NOT_ESTABLISHED`.

## 6. Next-action rule

The previous review says that the remaining Owner-facing decision is whether the Owner would explicitly consider a manually adopted TPM-identity pin obtained through a genuinely independent channel, alongside a separately justified exact-instance binding. This is not a declaration that the route is feasible and not permission to create keys, inspect the device, authenticate, install services or implement.

The next chat must:
1. Read this receipt after the canonical five-file preflight.
2. Use the prior evidence and negative results rather than restarting the broad survey.
3. Keep `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, and all G1–G8 gates open.
4. Present only the specific Owner decision needed to determine whether a future bounded static design of independent TPM pin provenance is worth pursuing; if the Owner declines or no independent channel can be described, preserve the block.
5. Do not launch implementation or another review automatically. A generic `ok procede` authorizes only the specific bounded task then described; it does not authorize new authentication, hardware inspection, credential creation, services, tests, runtime, spend or release of a block.

## 7. Final state

```ini
TASK=M1A_G1_NEW_CHAT_CONTINUITY_HANDOFF
BASE_MAIN=76708568d441b6172425367ae287b69a280cec38
RESULT=BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
LAST_TERMINAL_TASK=M1A_G1_OWNER_APPROVED_MANIFEST_TPM_BOUND_ISSUER_REVIEW
GITHUB_ACCOUNT_ID_28608338=NOT_ADOPTED
GOOGLE_OIDC=NOT_WORTH_EXTERNAL_SETUP
PERSONAL_PASSKEY=NOT_CREATED; HUMAN_AUTHORIZATION_CANDIDATE_ONLY
TPM_AVAILABILITY=UNVERIFIED
TPM_ATTESTATION_TRUST=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
OWNER_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
READER_VERIFICATION=NOT_ESTABLISHED_END_TO_END
REPOSITORY_CHANGES=DOCUMENTATION_ONLY
PRODUCT_CODE_CHANGES=NONE
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=OWNER_DECISION_ONLY
AUTOMATIC_FOLLOW_ON=FALSE
```
