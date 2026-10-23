# M1A G1 — Independent TPM identity pin design

- **Date:** 2026-10-23 (America/Bogota)
- **Task:** `M1A_G1_INDEPENDENT_TPM_PIN_DESIGN`
- **Parent frontier:** `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`
- **Mode:** `READ_ONLY_STATIC_DESIGN_AND_FEASIBILITY`
- **Baseline:** `f6700df1c649cfab4333e527403c489067c4ee6e`
- **Result:** `BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH`
- **Governance:** `KEEP_BLOCKED`

## 1. Executive verdict

The Owner authorized this bounded design study. The static result is **no currently evidenced enrollment path satisfies the existing restrictions**. A TPM identity pin is only conditionally useful: it requires a genuinely independent way to establish that the pinned key belongs to the intended physical device, followed by a separate proof binding the issuer to the exact IABV server instance and an independent reader that validates both.

This does **not** prove that no such path could ever exist. It means no path is established by current canonical project evidence and permitted resources. The most promising conditional input would be an already-available, independently verifiable TPM endorsement-key credential/chain or an already-trusted hardware-identity record, but neither its availability nor its mapping to the Owner's intended device has been evidenced. A TPM fingerprint displayed by the same potentially compromised Windows environment is not independent evidence.

G1 remains blocked. No local device observation, TPM query, credential/key creation, authentication, new service, installation, test, build, runtime, product-code edit, merge, deployment or gate release occurred. No external AI was dispatched for this task.

## 2. Canonical preflight and provenance

Remote `main` was revalidated at `f6700df1c649cfab4333e527403c489067c4ee6e`. The five canonical routes were fetched in the required order:

1. `IABV_v1.5/AGENTS.md` — blob `51a69cb7d1ce33d1ac185d4b84f6c6061f8cc187`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md` — blob `15238ae53ef343b2cde01e30224d7e6bfc700dd6`
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — blob `9eb021b896c73eaab61ca16ea8dbf7d4fb3f4afc`
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md` — blob `f617e1343cdac54e6e044a0e1850144be9dbbb3d`
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md` — blob `9b52fff88f61bc6175c7f290dfc0d9d79c8f51cd`

The preceding handoff at `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-M1A-G1-new-chat-continuity-handoff.md` was fetched and its blob `949f47a32c6f3fa303cdcb6d493784ffb7dccbd1` matched the expected hash exactly.

Evidence classes:
- **CONFIRMED_BY_SOURCE:** current public GitHub route/baseline and official Microsoft documentation cited below.
- **OWNER_SUPPLIED_REVIEW:** the earlier Sonnet report and terminal verdict; this task did not independently dispatch Sonnet or claim a new correlated invocation.
- **PROPOSED:** any protocol/acceptance condition in this report.
- **UNVERIFIED / UNRESOLVED:** Owner-machine TPM availability, EK certificate-chain availability/trust, the Owner-to-device mapping, independent verifier availability, Owner-to-Windows principal, exact server-instance binding and end-to-end reader/revocation behavior.
- **NOT_PERFORMED:** local probing, authentication, key/credential creation, tests, build, runtime, transport and implementation.

## 3. Source-grounded technical boundary

### TPM identity and key attestation

Microsoft's TPM key-attestation documentation describes trust via (a) an administrator-managed EKPub/AIKPub allowlist, (b) a manufacturer certificate chain validated to administrator-selected roots, or (c) trust in the calling client's assertion. The third is not independent verification. An allowlist presupposes trusted initial contents and protection; Microsoft also states that not all TPMs have an EK certificate.

Sources:
- [Microsoft Learn — TPM Key Attestation](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/component-updates/tpm-key-attestation)
- [Microsoft Open Specifications — MS-WCCE, Key Attestation](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wcce/adc2aab5-701b-4f91-9dc0-5615543712bf)

The Microsoft Platform Crypto Provider can use a TPM for hardware-backed key storage and non-extractability. That is a key-custody property, not proof of the process or installation authorized to request a signature.

Source:
- [Microsoft Learn — CNG Key Storage Providers](https://learn.microsoft.com/en-us/windows/win32/seccertenroll/cng-key-storage-providers)

### Boot evidence versus exact process identity

Measured Boot/TPM attestation can provide evidence about the hardware trust chain and measured boot state to a relying party. Microsoft's reference architecture requires a relying party to validate the evidence and describes an attestation service to validate boot measurements. This does not, by itself, attest the exact currently running IABV server executable, its loaded code, configuration/policy or service instance. An external attestation service cannot be assumed under current constraints.

Sources:
- [Microsoft Learn — TPM attestation overview for Azure](https://learn.microsoft.com/en-us/azure/attestation/tpm-attestation-concepts)
- [Microsoft Learn — How Windows uses the TPM](https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/how-windows-uses-the-tpm)
- [Microsoft Learn — Secure the Windows boot process](https://learn.microsoft.com/en-us/windows/threat-protection/secure-the-windows-10-boot-process)

Windows service identities, object ACLs and service security descriptors can restrict which security tokens access a protected key or endpoint. They are valuable local enforcement primitives, but their existence in documentation does not establish a trusted Owner identity, trustworthy initial service installation, process-integrity attestation or reader-side enforcement. The trustworthiness of service configuration and the privilege boundary against an administrator must be part of the threat model.

Source:
- [Microsoft Learn — Service Security and Access Rights](https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights)

## 4. Candidate-channel decision table

| Candidate | What it can establish | Decision under current evidence |
|---|---|---|
| Existing GitHub approval | An auditable approval event for a payload | Does not prove machine claims; account ID `28608338` remains unadopted |
| Phone approval, QR code, manually shown challenge or copied fingerprint | Human approval of a value presented to the phone | Insufficient where the value originates only from the target; no prior IABV-to-TPM binding exists |
| EKPub hash read from target Windows UI | A reported fingerprint | Not an independent pin; the target may misreport it |
| Manufacturer EKCert + already-trusted certificate chain | Potentially authenticates that an EK public key was certified by a trusted manufacturer | Conditional only: EKCert presence, trusted roots and mapping to the Owner's intended device are unverified |
| Pre-existing Owner-managed EKPub allowlist | Can identify enrolled TPMs if its initial source and protection are trusted | No independently established initial allowlist/authority is evidenced in the scoped project memory |
| New remote attestation/cloud/enterprise CA | Could supply a separate verifier and/or hardware trust chain | Not an assumed capability and outside current no-new-service/no-extra-spend constraints |
| Service SID + key ACL + protected configuration | Local restrictions after an authority has been established | Defense in depth only; not an initial trust root or independently verified exact-process identity |

No candidate satisfies every required edge today.

## 5. Conditional protocol and stop conditions

This is a **design specification only**, not an executable or authorized enrollment procedure.

1. **Create a fresh single-use enrollment transaction.** Define a nonce/transaction ID, expiry, intended device identity, issuer public-key fingerprint, exact installation identifier, executable/configuration digests, policy revision and revocation generation. Nothing is trusted at creation.
2. **Establish hardware identity independently.** Validate an already-trusted EK certificate chain or an already-protected allowlist, and establish that it identifies the physical device the Owner intends to enroll. An untrusted Windows assertion alone fails this gate. If no acceptable existing root/source is available, stop.
3. **Bind the issuer key to the trusted TPM.** Require evidence tying the issuer key to the TPM/AIK/EK trust chain, bound to the fresh challenge and exact transaction. Non-exportability alone is insufficient. If TPM/attestation support or root provenance is absent or unknown, stop.
4. **Bind the key to the exact server instance.** Require evidence of installed service identity, executable/configuration/policy digest and a defensible OS enforcement boundary preventing a different process or cloned instance from using the issuer. A self-asserted installation ID, copied files, service name or boot quote alone is insufficient. If the local OS boundary cannot substantiate the claim, stop.
5. **Obtain transaction-specific Owner approval.** The approved payload must be presented by a verifier that has independently validated the evidence, not merely prepared by the target. Approval is limited to this transaction/key/instance/policy and expires. GitHub may record the decision but cannot validate machine claims it does not verify.
6. **Verify from an independent reader.** Check approval provenance, attestation chain, key binding, exact-instance evidence, fresh nonce, expiry, policy version, integrity, replay state and authoritative revocation/replacement. Missing, stale, revoked, conflicting or unverifiable evidence denies enrollment.
7. **Close only with correlated evidence.** A later separately authorized validation must prove the complete request→verification→approval→issuer→exact server→reader chain. A document, design PASS, self-asserted signature or successful GitHub login never releases G1 by itself.

**Step 2 cannot pass with evidence currently established in the permitted scope.** Even if step 2 later passes, step 4 and independent reader/revocation verification remain separate blockers. The first step is not to generate a key; it is to prove an existing independently trusted hardware-identity source is available.

## 6. Minimal next discriminating action

There is no legitimate way to declare the block resolved from this design. The smallest useful next action would be a **separately authorized, read-only assessment of existing TPM trust assets**, limited to whether the device has a TPM and whether a manufacturer EK credential/chain can be validated against a trust store that already exists and is independently defensible. It must not create keys, change trust stores, register accounts/services or configure authentication. Any result from the target OS remains an observation whose provenance must be evaluated, not an independent root by itself.

This preflight is **not authorized by this design-only task** and has not been performed. Before it starts, the Owner must authorize that distinct local-inspection scope. If no independent identity channel and defensible exact-instance proof can be identified, preserve the block rather than inventing a root or widening the task.

## 7. Acceptance criteria for reopening G1

Reconsider a later candidate only if evidence demonstrates all of the following:
- A pre-existing independent trust source and trustworthy mapping to the Owner's intended physical device.
- Verified TPM/EK/AIK provenance and issuer-key-to-TPM binding, with a fresh transaction nonce.
- Explicit Owner approval tied to the exact transaction, key, installation, policy revision and expiry.
- A documented threat model and enforceable binding between the issuer key and exact running server instance, including clone/replay/replacement resistance.
- Independent reader verification, tamper-resistant authoritative revocation/replacement and fail-closed behavior when verification is unavailable.
- Separately authorized empirical validation with correlated artifacts before any operational gate can be considered.

A missing item keeps G1 open. A successful test of one component cannot be promoted to end-to-end readiness.

## 8. Traceability / reusable knowledge

- **Parent concept:** `UAAL-ROOT-001` (the universal adaptive reasoning loop; identity, trust, evidence, constraints, governed action and verification remain separate stages).
- **Child concept:** `UAAL-D017` — Independent Trust Bootstrap and Exact-Instance Evidence Boundary.
- **Derivation:** a locally plausible identity mechanism is not a usable capability until provenance, authority, target binding, reader verification, failure states and revocation are evidenced.
- **Falsifier:** new source evidence proves an already available independent TPM identity source and a separate defensible exact-instance/reader-verification path without an unapproved trust root or excluded infrastructure.
- **Next open edge:** determine whether an existing independent source is available, only through a separately authorized bounded assessment.

## 9. Final status

```text
TASK=M1A_G1_INDEPENDENT_TPM_PIN_DESIGN
TASK_RESULT=BLOCKED_NO_INDEPENDENT_ENROLLMENT_PATH
RESULT_SCOPE=STATIC_DESIGN_ONLY; CURRENT_EVIDENCE_AND_CONSTRAINTS
BASE_MAIN=f6700df1c649cfab4333e527403c489067c4ee6e
GITHUB_CURRENT_SOURCE=CONFIRMED_BY_SOURCE
SONNET_REVIEW=OWNER_SUPPLIED; NOT_REDISPATCHED
TPM_AVAILABILITY=UNVERIFIED
INDEPENDENT_TPM_IDENTITY_SOURCE=NOT_ESTABLISHED
TPM_ATTESTATION_TRUST=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
OWNER_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
READER_VERIFICATION=NOT_ESTABLISHED_END_TO_END
REVOCATION_AUTHORITY_AND_CONSISTENCY=NOT_ESTABLISHED
LOCAL_DEVICE_ACCESS=NOT_PERFORMED
NEW_AUTHENTICATION=NOT_PERFORMED
KEYS_OR_CREDENTIALS_CREATED=NONE
NEW_SERVICES_OR_ACCOUNTS=NONE
PRODUCT_CODE_CHANGES=NONE
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MERGE_DEPLOY=NOT_PERFORMED
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=OWNER_DECISION_ONLY; DISTINCT_READ_ONLY_ASSESSMENT_NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
```
