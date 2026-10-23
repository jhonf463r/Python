# M1A G1 — Owner-Approved Manifest + TPM-Bound Issuer Feasibility Review

**Date:** 2026-10-22 (America/Bogota)  
**Task:** `M1A_G1_OWNER_APPROVED_MANIFEST_TPM_BOUND_ISSUER_REVIEW`  
**Mode:** read-only static design/feasibility review  
**Parent:** `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`

## Terminal outcome

`RESULT=BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH`

This report preserves the user-supplied Sonnet review and an independent, later coordinator revalidation. It does not establish G1, authorize another implementation, or declare the local machine's capabilities.

## Provenance and checkpoint

- Sonnet reported that its own GitHub API access hit a rate limit; its `MAIN_SHA_VERIFICATION=UNVERIFIED_RATE_LIMITED`. That original review therefore treated `bf3174025bd1eee97cd345bd2deaf0ae76fea2fe` as a pinned snapshot, not a fresh observation.
- Immediately before this documentation-only continuity writeback, the coordinator independently fetched `refs/heads/main` and verified it at `bf3174025bd1eee97cd345bd2deaf0ae76fea2fe`, tree `4bbc0252b5a0e2f82fac5b0fb7bd7fc0004053b1`.
- Canonical preflight blobs at that checkpoint:
  - `IABV_v1.5/AGENTS.md`: `0b158712267a23fa192faab178e0724a8dbdfd7b`
  - `IABV_v1.5/docs/history/CHAT-ARCH/README.md`: `3a76fa636b652a9c4f8a49e3d66030f8d3e2536c`
  - `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`: `85e199a995b6e78917190fb336b26ebe030d6b6a`
  - `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`: `60f2a0b1dcb7960fa91a35b7c59f39fcaf41eaab`
  - `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`: `bb03bb1c1f1d9e1b7f1325cc2b2384da453e8886`
- Official Microsoft sources independently consulted by the coordinator for this reconciliation:
  - [CNG key storage providers](https://learn.microsoft.com/en-us/windows/win32/seccertenroll/cng-key-storage-providers)
  - [MS-WCCE §1.3.2.2, Key Attestation](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wcce/adc2aab5-701b-4f91-9dc0-5615543712bf)
  - [TPM attestation concepts](https://learn.microsoft.com/en-us/azure/attestation/tpm-attestation-concepts)
- Evidence boundary: the technical conclusions below are source-grounded design analysis, not proof of the Owner's actual TPM, Windows configuration, GitHub account security, service configuration, or runtime behavior.

## Candidate A — GitHub approval record

GitHub can provide an auditable control-plane event or repository object and bind a human approval to the exact content presented for approval. This is useful evidence for *which manifest was approved and when*, provided identity, signature/approval validation, repository state, replay protection and authorization semantics are explicitly checked.

GitHub does not independently validate the truth of claims embedded in that manifest. A Windows SID, TPM public-key hash, install path, build identifier or server-instance label remains unverified payload unless another independent mechanism checks it. A signed commit proves use of the signing key; it does not, by itself, prove that the signer's key was initially bound to the accountable Owner or that the machine claims are true.

The GitHub numeric account ID `28608338` remains a candidate only. It was **not adopted** as an immutable governance identity by this review or by the Owner.

**Disposition:** `GITHUB_APPROVAL_AUDIT_LAYER_ONLY`; insufficient as the sole G1 trust anchor.

## Candidate B — TPM-backed issuer

The Microsoft Platform Crypto Provider can use a TPM to protect private keys and prevent their migration/export under the relevant key configuration. That is a useful custody property, but it does not prove which exact process, service configuration or installation is currently authorized to use the key.

Microsoft's key-attestation protocol identifies distinct ways to establish TPM trust:
1. Validate an EKPub/AIKPub hash against an administrator-managed allowlist.
2. Validate an EK/AIK certificate chain to an explicitly trusted CA/root set.
3. Trust the calling client's assertion that the EKPub came from a TPM.

For this workstream, method 3 is unacceptable: it lets the enrolling component supply its own sole trust claim. Method 2 would require a proven, already-trusted certificate chain and acceptable verification capability; no such chain has been established here. Method 1 is the only discussed no-new-infrastructure candidate, but it moves the bootstrap question to how the allowlist's initial value was independently obtained, adopted, protected and made authoritative for readers.

A one-time Owner-approved pin of a TPM identity could be considered only if the fingerprint provenance comes through a genuinely independent channel. Merely reading a fingerprint from a Windows screen controlled by the system being enrolled is not independent evidence when that local display/process is within the threat model.

A non-migratable TPM key can help distinguish hardware, but it does not alone distinguish separate server processes/instances sharing access on the same hardware. The design still needs a separately verifiable binding among the authorized Windows principal/service boundary, protected key use, exact intended installation and the reader's checks.

**Disposition:** `TPM_KEY_PROTECTION_PLAUSIBLE`; `TPM_ATTESTATION_TRUST_AND_EXACT_INSTANCE_BINDING_UNRESOLVED`.

## Combined result

The combined GitHub-manifest + TPM-key candidate cannot close all required authority links on currently evidenced capabilities:

| Required edge | Status | Finding |
|---|---|---|
| Owner intent → approved enrollment transaction | Partial / not established as a root | GitHub can record approval, but the approved claims still need independently verifiable provenance. |
| Owner → authenticated Windows SID | Not established | GitHub does not observe or attest to the local Windows principal. |
| Owner → issuer key | Not established | A manifest can name a key; that does not prove the named key belongs to the intended instance. |
| TPM evidence → trusted hardware identity | Not established | Needs an independently adopted allowlist or a trusted EK/AIK certificate chain; client self-assertion is rejected. |
| Issuer key → exact server instance | Not established | TPM non-migration is not process/install identity. Same-machine key-use access and cloned configuration remain separate concerns. |
| Reader → valid approval and revocation state | Not established end-to-end | GitHub event validation is plausible; machine claims and authoritative IABV revocation still need independent verification. |

### Key correction for future chats

Do not conflate:
- human approval with truth of machine evidence;
- TPM residency/non-exportability with exact process or installation identity;
- an EK/AIK allowlist with an independently trusted allowlist-provisioning ceremony;
- successful identity-provider login with first enrollment authorization;
- a personal passkey/recovery mechanism with the IABV issuer trust root.

## Owner decision still pending

The only no-new-infrastructure candidate worth further bounded design consideration is an explicit Owner-adopted TPM-identity pin established through a genuinely independent source/channel, combined with a separately justified exact-instance binding. This is **not yet a demonstrated viable protocol** and must not be implemented merely because it is mentioned here.

The Owner has not approved the GitHub account ID as the governance identity, has not adopted an EKPub/AIKPub pin as a trust anchor, and has not established an independent channel for verifying that pin. Do not infer any of these decisions from a general “proceed” instruction.

If a future design cannot specify where independently trustworthy TPM identity evidence comes from and how it binds to the exact instance, the correct terminal outcome remains `BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH`.

## Relevant Owner-context boundaries

The Owner prefers a low-friction recovery model that does not make a personal phone the sole means of access. A syncable personal passkey with an offline recovery path remains only a candidate for *human authorization*; no IABV passkey or recovery credential was created. Personal Google-account settings and recovery materials are outside this public repository record and must not be copied here.

## Final state

```ini
TASK=M1A_G1_OWNER_APPROVED_MANIFEST_TPM_BOUND_ISSUER_REVIEW
RESULT=BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH
SONNET_REPORTED_MAIN_SHA=UNVERIFIED_RATE_LIMITED
COORDINATOR_REVALIDATED_MAIN_BEFORE_WRITEBACK=bf3174025bd1eee97cd345bd2deaf0ae76fea2fe
GITHUB_AUTHORITY=APPROVAL_AUDIT_ONLY; NOT_G1_ROOT
GITHUB_ACCOUNT_ID_28608338=NOT_ADOPTED
TPM_AVAILABILITY=UNVERIFIED
TPM_ATTESTATION_TRUST=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
OWNER_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
READER_VERIFICATION=NOT_ESTABLISHED_END_TO_END
NEW_AUTHENTICATION=NOT_PERFORMED
REPOSITORY_PRODUCT_MODIFICATIONS=NONE
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
OWNER_DECISION=MANUAL_TPM_IDENTITY_PIN_AND_EXACT_INSTANCE_BINDING_NOT_ADOPTED
AUTOMATIC_FOLLOW_ON=FALSE
```
