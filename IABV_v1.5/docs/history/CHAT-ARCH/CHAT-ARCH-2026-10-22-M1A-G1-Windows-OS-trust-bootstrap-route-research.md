# M1A G1 — Windows OS-enforced trust-bootstrap route research

- Date: 2026-10-22, America/Bogota.
- Parent blocker: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`.
- Research result: `OS_SECURITY_PRIMITIVES_CONFIRMED; PROJECT_BOOTSTRAP_NOT_YET_IMPLEMENTED_OR_VERIFIED`.
- Scope: official public Microsoft documentation; no local-machine probe or project runtime.

## 1. Why this is new evidence

The previous G1 attempt stopped because the candidate did not evidence an independent enrollment authority or requester/issuer/reader separation. This bounded research finds documented Windows primitives from which a concrete candidate architecture can be implemented without assuming an external paid identity provider or treating the existing in-process broker as the trust root.

This does not establish that those primitives are integrated into IABV or configured on the Owner's machine. It is new evidence that Windows supports an OS-enforced process/key/IPC boundary that can be designed and implemented, not evidence of operational readiness.

## 2. Grounded Windows primitives

1. **A distinct service security principal.** Microsoft documents service SIDs, including `SERVICE_SID_TYPE_RESTRICTED`, which adds a service SID to the process token and restricted SID list. Service accounts run with an OS access token used for access checks. Sources:
   - https://learn.microsoft.com/en-us/windows/desktop/api/winsvc/ns-winsvc-service_sid_info
   - https://learn.microsoft.com/en-us/windows/win32/services/service-user-accounts

2. **Protected cryptographic key and explicit key ACL.** CNG provides persisted keys and the `NCRYPT_SECURITY_DESCR_PROPERTY` through which a key object's owner/group/DACL can be managed. The Microsoft Platform Crypto Provider uses TPM-backed key storage, but TPM availability cannot be presumed; implementation must either select a verified supported provider or fail closed. Sources:
   - https://learn.microsoft.com/en-us/windows/win32/api/ncrypt/nf-ncrypt-ncryptcreatepersistedkey
   - https://learn.microsoft.com/en-us/windows/win32/api/ncrypt/nf-ncrypt-ncryptsetproperty
   - https://learn.microsoft.com/en-us/windows/win32/seccertenroll/cng-key-storage-providers

3. **Controlled IPC.** Windows named pipes support explicit security descriptors and access checks. Microsoft documents that a NULL/default named-pipe security descriptor can grant read access to Everyone and anonymous users; an implementation must set an explicit restrictive DACL, not rely on defaults. Source:
   - https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights

4. **Explicit Owner authentication factor, if supported.** Windows WebAuthn exposes relying-party information and credential creation APIs. Those APIs provide a mechanism to register/authenticate a credential for an RP but do not by themselves prove that an arbitrary first registrant is the project Owner. Source:
   - https://learn.microsoft.com/en-us/windows/win32/api/webauthn/
   - https://learn.microsoft.com/en-us/windows/win32/api/webauthn/ns-webauthn-webauthn_rp_entity_information
   - https://learn.microsoft.com/en-us/windows/win32/api/webauthn/nf-webauthn-webauthnauthenticatormakecredential

5. **Important identity limitation.** Windows Hello for Business is not designed for local Windows accounts. In its supported organization scenarios, keys are registered to a user through a relying identity provider such as Microsoft Entra ID or AD FS. Regular Windows Hello convenience sign-in for a local account is not equivalent to a resource-authentication key. Sources:
   - https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/hello-faq
   - https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/hello-how-it-works
   - https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/deploy/

## 3. Bounded candidate design to implement and review

Try an explicitly installed, separate Windows issuer/broker process, not a Python class in `server.py`:

- It runs under its own least-privilege Windows service identity with a restricted service SID; only the intended service identity and SYSTEM have access to the issuer private key and writable issuer state.
- The issuer key is a real persisted CNG signing key with a restrictive DACL. Provider support is detected when the later authorized enrollment runs; no TPM/software guarantee is assumed in source.
- The issuer's service configuration, enrollment policy and trust-anchor files reside in a protected installation/state location whose DACL prevents the requester/reader process from changing the root. Only SYSTEM and the authorized installer/Owner administration boundary can replace it.
- IPC uses a named pipe with an explicit restrictive DACL; never use the default NULL descriptor. Authentication/authorization is based on actual Windows process tokens and SIDs, not caller-supplied strings.
- Enrollment is never automatic at service startup. It must be a distinct, explicit Owner-initiated ceremony, with an OS-authenticated interactive principal, user presence and, if a supported WebAuthn relying-party path is implemented, a fresh challenge bound to the fixed RP ID. Record the enrolling Windows SID as a local OS principal only after that ceremony; do not claim it is a civil identity or an external IdP identity.
- Enrollment binds the approved principal, issuer public key/key identity, policy revision, and exact IABV server-instance identity. Any ambiguity, unavailable API/provider, malformed state, mismatch, or inability to enforce ACLs fails closed.
- The MCP requester and reader never possess the issuer private key, cannot create/replace enrollment records or root configuration, and cannot write the protected key/state. The reader validates scoped issuer-signed decisions at its protected read boundary using a trust anchor it cannot mutate. G1 is not operationally closed merely because source code exists.
- Keep G2–G8 and Entry 274 receipt-ledger requirements separate. This task must not mislabel the durable ledger as G3; G3 remains the versioned operation-to-target resolver.

The installed service/program-file/state ACL boundary must be real at deployment. A Python module, role name, named-pipe name, generated JSON owner row, key file in the user-writable checkout, or untested claim is not proof of separation.

## 4. What remains unknown

- Whether the later installed environment supports the required Windows service APIs, selected CNG provider, interactive enrollment path and WebAuthn integration.
- Whether IABV has a stable server-instance identity contract that can be bound without trusting a caller's claim.
- Whether the existing reader path can be connected to the protected trust root without letting its own requester-controlled workspace substitute code or trust state.
- Actual service installation, key enrollment, ACL inspection, signature verification at the reader boundary, revocation/freshness and durable evidence all require a later, separately authorized validation step.

Therefore the research outcome is conditional. It grounds a real OS-boundary implementation attempt but does not claim that G1 is already established.

## 5. Activities and exclusions

Performed: public Microsoft documentation searches; design synthesis; read-only GitHub continuity and candidate-state checks.

Not performed: local checkout or OS inspection; shell/PowerShell; querying local accounts, TPM, Hello, CNG provider availability or service configuration; service installation; credential enrollment/key generation; tests/build/runtime; protected reads, MCP calls, or transport; merge/deploy or operational-block release. No local data/SQLite/secrets/.env were accessed.

## 6. State

```text
TASK=M1A_G1_WINDOWS_OS_TRUST_BOOTSTRAP_CANDIDATE
RESULT=OS_SECURITY_PRIMITIVES_CONFIRMED; PROJECT_BOOTSTRAP_NOT_YET_IMPLEMENTED_OR_VERIFIED
OWNER_POLICY=ACCEPTED_FOR_CANDIDATE_IMPLEMENTATION
CANDIDATE_BRANCH=m1a-g1-g3-governance-route-candidate-20261022
CANDIDATE_BASE=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
CANDIDATE_SOURCE_CHANGES=NONE_AT_RESEARCH_STAGE
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION=NEXT_BOUNDED_CANDIDATE_ATTEMPT_TO_BE_HANDED_TO_CODEX
GOVERNANCE=KEEP_BLOCKED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
LOCAL_CHECKOUT=NOT_ACCESSED
SERVICE_INSTALLATION=NOT_PERFORMED
CREDENTIAL_ENROLLMENT=NOT_PERFORMED
REAL_TRANSPORT=NOT_RUN
MERGE_DEPLOY=NOT_AUTHORIZED
BLOCK_RELEASE=NOT_AUTHORIZED
BRIDGE=BRIDGE_NOT_READY
```
