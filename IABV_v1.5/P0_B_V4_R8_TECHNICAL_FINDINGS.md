# P0-B V4-r8 Technical Investigation Findings

## A. Git Provenance

```
BASE:
586469d541512277dbc8b98763f56f733d3dfbb7

PARENT:
09e06858668a9b4fbebcfa278d6dbb38dd16f2c4

HEAD:
09e06858668a9b4fbebcfa278d6dbb38dd16f2c4

BRANCH:
provenance/p0-b-separate-audit-authority-v4-r6

ORIGIN:
https://github.com/jhonf463r/Python.git
provenance/p0-b-separate-audit-authority-v4-r6
```

V4-r8 no incluye cambios de código. Este documento documenta los hallazgos técnicos de la investigación.

## B. Files Changed

No files changed in V4-r8. This is a documentation-only release.

## C. Security Findings

### Finding 1: CNG does not support Ed25519 natively

**Severity:** HIGH  
**Root cause:** Windows CNG (Cryptography API: Next Generation) supports RSA, ECDSA, ECDH, but does not support Ed25519 as a standard algorithm identifier. Ed25519 is not in the standard CNG algorithm identifiers documented by Microsoft.  
**Attack:** N/A (algorithm support limitation)  
**Observed result:** Microsoft Learn documentation for CNG Algorithm Identifiers lists RSA, ECDSA, ECDH, but not Ed25519. Custom algorithm registration would be required.  
**Evidence:** Research of Microsoft Learn CNG Algorithm Identifiers documentation.  
**Final status:** DOCUMENTED - Technical limitation of Windows CNG

### Finding 2: pywin32 does not expose CNG APIs

**Severity:** HIGH  
**Root cause:** pywin32 library wraps the legacy CryptoAPI (CAPI) and does not expose the CNG (NCrypt*) APIs. To use CNG from Python would require direct ctypes calls to ncrypt.dll, which is complex and error-prone.  
**Attack:** N/A (library limitation)  
**Observed result:** python-win32 mailing list confirms pywin32 is CAPI-only, not CNG. CNG APIs require ctypes or native extensions.  
**Evidence:** python-win32 mailing list discussion about TPM/CNG integration.  
**Final status:** DOCUMENTED - Python library limitation

### Finding 3: Windows Certificate Store does not support Ed25519 natively

**Severity:** HIGH  
**Root cause:** Windows Certificate Store native certificate formats support RSA and ECDSA public keys. Ed25519 would require custom certificate extensions or non-standard storage formats.  
**Attack:** N/A (certificate format limitation)  
**Observed result:** Windows Certificate Store documentation specifies RSA and ECDSA as standard public key types. Ed25519 would require custom extension (OID) handling.  
**Evidence:** Microsoft Learn documentation on Certificate Store and certificate formats.  
**Final status:** DOCUMENTED - Certificate format limitation

### Finding 4: F14 cannot be closed without changing process identity

**Severity:** CRITICAL  
**Root cause:** Windows DPAPI user-level protection allows any process running under the same user account to decrypt data protected by another process. The only way to block same-user attacker is to change the process identity (e.g., Windows Service with dedicated account, AppContainer sandbox, Protected Process with VBS).  
**Attack:** Process B (same user, different PID) can call CryptUnprotectData on DPAPI-protected data from Process A.  
**Observed result:** Test `test_7_dpapi_same_user_threat_model` in V4-r6 demonstrated successful same-user decryption.  
**Evidence:** Runtime test execution showing same-user decryption success.  
**Final status:** DOCUMENTED - Windows DPAPI architectural limitation

### Finding 5: F5 circular dependency remains with current architecture

**Severity:** MEDIUM  
**Root cause:** Currently, both `provisioner_keypair.json` and `authority_trust.json` reside in the same protected directory with the same ACL boundary. An attacker who can write to the directory could replace both files, breaking the trust anchor independence.  
**Attack:** Attacker replaces both provisioner_keypair.json and authority_trust.json with attacker-controlled content.  
**Observed result:** Not yet tested in V4-r8, but architectural analysis shows the circular dependency.  
**Evidence:** Code inspection of V4-r7 shows both files in same `protected_root` directory.  
**Final status:** DOCUMENTED - Architectural limitation

## D. Evidence Matrix

| Property                    | Structural | Unit | Windows Runtime | Adversarial Runtime | Final |
| --------------------------- | ---------- | ---- | --------------- | ------------------- | ----- |
| F5 provisioner trust anchor | ✅         | ⚠️   | NOT_TESTED      | NOT_TESTED          | NOT_PROVEN |
| F5 trust store              | ✅         | ✅   | ✅              | ⚠️                  | NOT_PROVEN |
| F14 authority key           | ✅         | ✅   | ❌              | ❌                  | NOT_PROVEN |
| Same-user isolation         | ✅         | ✅   | ❌              | ❌                  | NOT_PROVEN |
| Durable identity            | ✅         | ✅   | NOT_TESTED      | NOT_TESTED          | NOT_PROVEN |
| ACL                         | ✅         | ✅   | ⚠️              | NOT_TESTED          | NOT_PROVEN |
| Process separation          | ✅         | ✅   | NOT_TESTED      | NOT_TESTED          | NOT_PROVEN |
| IPC                         | ✅         | ✅   | NOT_TESTED      | NOT_TESTED          | NOT_PROVEN |
| Anti-spoof                  | ✅         | ✅   | NOT_TESTED      | NOT_TESTED          | NOT_PROVEN |
| Replay                      | ✅         | ✅   | ✅              | ✅                  | PROVEN |
| Git                         | ✅         | ✅   | NOT_TESTED      | NOT_TESTED          | NOT_PROVEN |

**Legend:**
- ✅ = Demonstrated/Implemented
- ⚠️ = Partial/With known limitations
- ❌ = Failed/Proven attack
- NOT_TESTED = No evidence collected

## E. Final Verdict

**NOT_PROVEN**

## F. Mandatory Honesty

**F5 = NOT_PROVEN**  
**F14 = FAIL**  
**P0-B = OPEN**

### Technical Reasons:

1. **F5 (Provisioner Trust Anchor):** NOT_PROVEN
   - Circular dependency exists: both provisioner_keypair.json and authority_trust.json in same protected directory
   - Cannot implement independent trust anchor without changing to:
     - Machine-level protected location (C:\ProgramData) with admin-only ACL
     - Windows Certificate Store (requires Ed25519 custom extension handling)
     - Embedded trust anchor in binary (requires installation/rotation policy)
   - CNG/Certificate Store approaches blocked by Ed25519 incompatibility

2. **F14 (Authority Private Key Isolation):** FAIL
   - DPAPI user-level protection allows same-user decryption (proven in V4-r6)
   - CNG non-exportable keys not feasible for Ed25519 (algorithm not supported)
   - Windows Service with dedicated identity would require architectural change
   - AppContainer sandbox would require architectural change
   - Protected Process/VBS requires Windows Enterprise + code signing certificate

### Security Question Answer:

> ¿Puede un proceso atacante que controla los archivos de aplicación o ejecuta bajo la identidad normal del usuario crear una nueva trust root o adquirir la capacidad criptográfica de la autoridad legítima?

**ANSWER: YES** (for F14)  
**ANSWER: UNKNOWN** (for F5 - circular dependency not tested)

### Required Architectural Changes to Close F5 and F14:

To close F5 (independent provisioner trust anchor):
1. Machine-level protected location (C:\ProgramData\IABV) with admin-only ACL
2. OR Windows Certificate Store with custom Ed25519 extension
3. OR embedded trust anchor in application binary with installation ceremony

To close F14 (authority private key isolation):
1. Windows Service with dedicated identity (gMSA/Managed Service Account)
2. OR AppContainer sandbox isolation
3. OR Protected Process / VBS (requires Windows Enterprise + code signing certificate)

These changes are beyond the scope of V4-r8 and would require significant architectural decisions.
