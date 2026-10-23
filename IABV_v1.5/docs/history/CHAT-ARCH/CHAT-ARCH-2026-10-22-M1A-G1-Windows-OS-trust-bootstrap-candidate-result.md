# M1A G1 Windows OS trust-bootstrap candidate — terminal reconciliation

- Date: 2026-10-22, America/Bogota.
- Task: `M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE`.
- Parent frontier: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.
- Result source: Owner-supplied Codex terminal output, correlated to this task. The prompt was not dispatched directly by ChatGPT.
- Terminal result: `BLOCKED_MISSING_G1_TRUST_ANCHOR`.

## 1. Independent GitHub verification

Immediately before this continuity writeback, GitHub returned:

| Item | Verified value |
|---|---|
| `main` HEAD | `5879ad3f66a9899ecbfa80c4028fe5429d34868b` |
| `main` tree | `68b0a87e5b63704190e3cbe5d27dd9133dfa5155` |
| Candidate branch | `m1a-g1-g3-governance-route-candidate-20261022` |
| Candidate HEAD | `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db` |
| Candidate tree | `ca963f8013809d4efcf56133a37d2efe148517e9` |
| Pinned candidate base | `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db` |
| Candidate vs pinned base | `identical`, `ahead_by=0`, `behind_by=0`, zero changed files |
| Candidate vs `main` at reconciliation start | `behind`, `ahead_by=0`, `behind_by=72` |

The tree SHA was directly confirmed via the GitHub branch/commit object, not only inferred from the prior continuity record. The candidate remains byte-for-byte identical to its pinned base. The canonical writeback updates documentation on `main` only; it does not advance, rebase or otherwise modify the candidate.

## 2. Attempt outcome and evidence boundary

The Codex report says no product files were modified, no blobs were created in the candidate, and no candidate commit was created. Direct GitHub comparison independently confirms no candidate diff exists to inspect. Therefore there are no new candidate blobs or changed code paths to credit to this attempt.

The blocker is an independently trusted enrollment/registration authority that can establish the relationship:

`IABV Owner responsibility → authenticated local Windows principal → authorized issuer credential → exact server instance`.

A local Windows SID identifies a local principal; by itself it does not prove that the principal is the Owner responsible for IABV. Conversational consent, an arbitrary username, first-run registration, or creation of a new key likewise does not establish that relationship. The candidate source and prior static inspection do not demonstrate an independent authority to validate the Owner-to-principal link or enforce the issuer/requester/reader boundary.

## 3. Relevant static source evidence from the prior candidate inspection

These blobs are prior inspected candidate source, not new modifications from this attempt:

| Path | Blob | Limitation relevant to G1 |
|---|---|---|
| `IABV_v1.5/src/iabv_v15/infra/mcp/server.py` | `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c` | The reviewed protected-reader path did not show an independently verified G1 authorization gate before the read. |
| `IABV_v1.5/src/iabv_v15/services/system_identity_registry.py` | `8fa7ba60202d947a254352bb1d7927f76becf90a` | System/subsystem identity metadata does not establish Owner identity or issuer authority. |
| `IABV_v1.5/src/iabv_v15/services/security/human_approval_broker.py` | `4a447149cf1b2771f6959658338a72b381f00b19` | Approval handling does not, by itself, authenticate the approving person or establish a signed authority. |
| `IABV_v1.5/src/iabv_v15/services/security/approval_memory.py` | `ed85408d96fb0cdfddb05489d6c38cf714275f91` | Stored/auto-resolved approvals are not an independent trust anchor. |
| `IABV_v1.5/src/iabv_v15/services/security/credential_broker.py` | `95a2e36401159995b253ff496a3a90cc2d5ffb92` | The reviewed contract does not demonstrate the required issuer/root authority or process isolation. |
| `IABV_v1.5/src/iabv_v15/services/capture/secret_vault.py` | `0ac57ea7da197519a753e0a90318184418288033` | Optional credential storage, including an in-memory fallback, is not proof of protected issuer-key custody. |

The public Microsoft research receipt `CHAT-ARCH-2026-10-22-M1A-G1-Windows-OS-trust-bootstrap-route-research.md`, blob `0316f3b897ed5db98e185bf55db1ba482b7dcaf5`, grounds relevant Windows primitives (restricted service SID, CNG key ACLs, explicit named-pipe DACL). Those sources support an architecture hypothesis only. They do not prove local configuration, successful deployment, Owner identity binding, server-instance identity binding, or an operational G1 path.

## 4. Terminal state and routing

No follow-on implementation is started by this receipt. Do not repeat the broad G1 inventory or the earlier Windows feasibility review. Re-open this frontier only when new, verifiable evidence establishes a supported independent Owner-to-principal and exact-server enrollment authority.

```ini
TASK=M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE
RESULT=BLOCKED_MISSING_G1_TRUST_ANCHOR
RESULT_PROVENANCE=OWNER_SUPPLIED_CODEX_OUTPUT; GITHUB_CANDIDATE_STATE_INDEPENDENTLY_VERIFIED
MAIN_AT_RECONCILIATION_START=5879ad3f66a9899ecbfa80c4028fe5429d34868b
CANDIDATE_BRANCH=m1a-g1-g3-governance-route-candidate-20261022
CANDIDATE_BASE=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
CANDIDATE_HEAD=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
CANDIDATE_TREE=ca963f8013809d4efcf56133a37d2efe148517e9
COMPARE_TO_BASE=IDENTICAL; AHEAD_BY=0; BEHIND_BY=0; CHANGED_FILES=0
COMPARE_TO_MAIN_AT_RECONCILIATION_START=BEHIND; AHEAD_BY=0; BEHIND_BY=72
FILES_MODIFIED=NONE
NEW_CANDIDATE_BLOBS=NONE
CANDIDATE_COMMIT_CREATED=NO
OWNER_TO_WINDOWS_PRINCIPAL_BINDING=NOT_ESTABLISHED
OWNER_TO_ISSUER_BINDING=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER_BINDING=NOT_ESTABLISHED
ENFORCED_ISSUER_REQUESTER_READER_SEPARATION=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
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
ACTIVE_FRONTIER=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
NEXT_ACTION=NO_AUTOMATIC_FOLLOW_ON; REQUIRE_NEW_INDEPENDENT_AUTHORITY_EVIDENCE
```
