# P0.213 V5 Phase 2 Contract: Trusted Authority Process

## Overview

Phase 2 implements the **REAL SECURITY BOUNDARY** using a separate trusted authority process and OS/IPC enforcement. Phase 1 was a data contract only (non-authoritative). Phase 2 provides runtime verification.

## Trusted Authority Process

### Authority Ownership

**ONE canonical owner of:**
- RootTrustAnchor (real secret key, OS-protected storage)
- RuntimeIdentityAuthority (OS-derived identity, HMAC signature)
- LeaseIssuerService (authority-owned lease fields, HMAC signature)
- LeaseRegistry (sole lease state owner, OS/interprocess atomicity)

### Process Boundary

**TRUSTED AUTHORITY PROCESS:**
- Separate process from untrusted worker/child processes
- Owns the real secret key (OS-protected storage)
- Owns generation state (persisted, atomic updates)
- Owns canonical RunRecord lookup (authority-owned state)
- Owns identity issuance (HMAC signature, OS-derived identity)
- Owns lease issuance (HMAC signature, authority-owned fields)
- Owns atomic consumption (OS/interprocess exactly-once)
- Exposes minimal Windows IPC API

**UNTRUSTED/WORKER PROCESS:**
- Cannot construct equivalent authority
- Cannot read root secret
- Cannot choose authoritative PID
- Cannot choose issuer identity
- Cannot bypass consume
- Cannot inject SelfAudit authority

## Windows IPC Trust Boundary

### Named Pipe Protocol

**TRUSTED AUTHORITY PROCESS (Server):**
- Creates Windows Named Pipe with explicit DACL
- Restricts access to authorized child processes
- Verifies client PID via Windows API (GetNamedPipeClientProcessId)
- Rejects remote clients (non-local connections)
- Enforces bounded message size
- Implements framing for partial-read handling
- Rejects malformed messages
- Provides readiness signal
- Coordinates shutdown

**UNTRUSTED/WORKER PROCESS (Client):**
- Connects to authority process via Named Pipe
- Cannot forge client PID (OS-verified)
- Cannot bypass DACL restrictions
- Cannot inject oversized messages
- Cannot replay messages (framing enforced)

### IPC Message Types

**REQUEST: ISSUE_IDENTITY**
- Input: ObservedProcessIdentity (OS-derived by authority)
- Output: TrustedExecutionIdentity (HMAC signed)

**REQUEST: ISSUE_LEASE**
- Input: TrustedExecutionIdentity, authorized_scope
- Output: TrustedLease (HMAC signed)

**REQUEST: CONSUME_LEASE**
- Input: lease_id
- Output: Consumed lease (atomic verify+consume)

**REQUEST: INCREMENT_GENERATION**
- Input: None
- Output: New generation (atomic)

## OS-Derived Identity

### Process Identity

**Phase 2 Implementation:**
- Use psutil/Windows API to observe process state
- Get PID, create_time, ppid from OS
- Cannot be forged by caller input
- Authority process observes directly from OS

**Verification:**
- Compare observed PID against IPC client PID
- Compare create_time to detect PID reuse
- Verify parent-child relationship

## Cryptographic Signing

### HMAC-SHA256

**Phase 2 Implementation:**
- Real secret key stored in OS-protected storage
- HMAC-SHA256 signature for TrustedExecutionIdentity
- HMAC-SHA256 signature for TrustedLease
- Signature covers all authoritative fields
- Deterministic serialization for signing

**Verification:**
- Re-compute HMAC with secret key
- Reject if signature invalid
- Reject if signature missing

## Lease State Ownership

### Sole Authority Owner

**Phase 2 Implementation:**
- LeaseRegistry is the ONLY authoritative lease state owner
- No duplicate registries
- No CapabilityRegistry
- No second state store
- Atomic verify+consume operation

### Interprocess Atomicity

**Phase 2 Implementation:**
- Use Windows file locking for atomic operations
- Survives: concurrent race, replay, restart, stale generation, expiration, crash/recovery
- Exactly-once consumption enforced at OS level
- dict.pop() is NOT used for interprocess atomicity

## Single-Use Semantics

### Authority Invariant

**Phase 2 Implementation:**
- Single-use is enforced by authority process
- Atomic verify+consume operation
- Rejects duplicate lease ID
- Rejects already consumed lease
- Rejects stale generation

### Interprocess Enforcement

**Phase 2 Implementation:**
- OS/interprocess atomic enforcement
- Windows file locking for coordination
- Survives process crashes
- Survives concurrent access

## Fail-Closed Semantics

### Canonical Rejection Conditions

**Phase 2 Implementation:**
- Missing identity
- Missing execution
- Invalid issuer
- Stale generation
- Expired lease
- Invalid signature
- Duplicate use
- Invalid binding

**Fail-Closed:**
- Any failure rejects access
- No fallback to insecure path
- No advisory control presented as enforcement

## Production Call Graph

### Required Lifecycle

```
bootstrap (Phase 2)
→ starts authority process
→ authority process creates readiness signal
→ authority process launches/accepts real child
→ child connects through real IPC (Named Pipe)
→ authority verifies client PID via Windows API
→ authority issues identity (HMAC signed)
→ authority issues lease (HMAC signed)
→ consumer uses lease
→ authority verifies/consumes (atomic)
→ SelfAudit receives only verified evidence
```

### Production Reachability

**Phase 2 Implementation:**
- Real parent-child process relationship
- Real Windows Named Pipe communication
- Real OS PID verification
- Real HMAC signature verification
- Real interprocess atomicity

## Component Definitions (Phase 2)

### RootTrustAnchor
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- Real secret key in OS-protected storage
- Real generation state (persisted, atomic updates)
- Real OS-derived process identity
- SECURITY: Phase 2 implements real authority boundary

### TrustedExecutionIdentity
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- HMAC-SHA256 signature
- Binds to OS-derived PID
- Binds to persisted generation
- SECURITY: Phase 2 implements real authenticity

### TrustedLease
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- HMAC-SHA256 signature
- Binds to authority-owned fields
- Binds to execution identity
- SECURITY: Phase 2 implements real authenticity

### LeaseRegistry
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- Sole lease state owner
- OS/interprocess atomicity
- Windows file locking
- SECURITY: Phase 2 implements real atomicity

### Windows Named Pipe Trust Boundary
- **Phase 2 Status:** RUNTIME_VERIFIED
- Explicit DACL
- Remote-client rejection
- Bounded message size
- Framing
- Partial-read handling
- Malformed message rejection
- Readiness signal
- Shutdown coordination

### Exactly-Once Consumption
- **Phase 2 Status:** RUNTIME_VERIFIED (interprocess atomicity)
- ONE canonical atomic consume operation
- Survives: concurrent race, replay, restart, stale generation, expiration, crash/recovery
- Windows file locking

### SelfAudit
- **Phase 4 Status:** RUNTIME_VERIFIED
- Accepts evidence ONLY after canonical authority verification
- Rejected context produces: NO SNAPSHOT, NO HISTORY ENTRY, NO PARTIAL PERSISTENCE
- Persistence is atomic/recoverable

## Metacognitive Rules (Phase 2)

**Critical patterns that BLOCK:**
1. IN_PROCESS_OBJECT_AUTHORITY_IS_NOT_A_SECURITY_BOUNDARY - Phase 2: BLOCK (authority process is separate)
2. FAKE_AUTHORITY_OWNER_DECLARATION - Phase 2: BLOCK (real authority enforcement)
3. PLACEHOLDER_VALIDATION_PRESENTED_AS_SECURITY - Phase 2: BLOCK (real HMAC verification)
4. IMMUTABILITY_CONFUSED_WITH_AUTHENTICITY - Phase 2: BLOCK (HMAC signature provides authenticity)
5. DATA_MODEL_CONFUSED_WITH_AUTHORITY - Phase 2: BLOCK (authority process provides authority)
6. CALLER_CONTROLLED_SECURITY_IDENTITY - Phase 2: BLOCK (OS-derived identity)
7. REPLAYABLE_AUTHENTICATED_RECEIPT - Phase 2: BLOCK (interprocess atomicity)
8. SELF_REFERENTIAL_EVIDENCE_METADATA - Phase 2: BLOCK (provenance contract)
9. DUPLICATE_AUTHORITY_OR_STATE - Phase 2: BLOCK (ONE authority, ONE lease state owner)
10. UNTRUSTED_CONTEXT_AS_VERIFIED_CONTEXT - Phase 2: BLOCK (IPC boundary)

**High-severity patterns that REQUIRE REVIEW:**
11. ADVISORY_CONTROL_PRESENTED_AS_ENFORCEMENT - Phase 2: REVIEW (fail-closed enforcement)
12. VERSION_CLAIM_WITHOUT_FROZEN_ARTIFACT - Phase 2: REVIEW (provenance contract)
13. CLAIM_WITHOUT_EVIDENCE - Phase 2: REVIEW (architecture contract)
14. CLAIMED_INTEGRATION_WITH_UNIT_TEST_SUBSTITUTE - Phase 2: REVIEW (L3-L5 evidence required)

**Medium-severity patterns that WARN:**
15. SECURITY_BY_NAMING_CONVENTION - Phase 2: WARN (underscore/private naming as security mechanism)

## Test Strategy (Phase 2)

**Test Layers:**
- L1 UNIT/CONTRACT: Data model and protocol interface tests (Phase 1: DATA_CONTRACT_ONLY)
- L2 COMPONENT: Component integration tests (Phase 2: RUNTIME_VERIFIED)
- L3 REAL WINDOWS IPC: Real Windows Named Pipe tests (Phase 2: RUNTIME_VERIFIED)
- L4 REAL MULTIPROCESS: Real parent-child process tests (Phase 2: RUNTIME_VERIFIED)
- L5 ADVERSARIAL: Adversarial input tests (Phase 2: RUNTIME_VERIFIED)
- L6 P0.20 REGRESSION: P0.20 compatibility tests (Phase 2: RUNTIME_VERIFIED)

**Critical security invariants require L3-L5 evidence.**

## Stop Conditions (Phase 2)

**STOP implementation and report immediately if:**
- In-process object is claimed as security boundary
- Fake authority enforcement appears
- Placeholder validation presented as security
- Immutability confused with authenticity
- Class name "Trusted" is claimed as security
- Data model confused with authority
- Duplicate authority appears
- Duplicate capability registry appears
- A security path becomes optional
- Production caller cannot be identified
- A unit test is being used to claim system integration
- Test requirement is being reduced to obtain PASS
- Artifact provenance becomes self-referential
- Legacy path becomes active
- Tool result is treated as proof without independent verification
- Placeholder secret material appears
- Boolean trusted flags appear as security mechanism
- Secret strings appear as security mechanism
- Underscore/private naming appears as security mechanism
- Bootstrap token constants appear as security mechanism
- Public factory + hidden argument appears as security mechanism
- dict.pop() is claimed as interprocess exactly-once
- IPC boundary is bypassed
- OS identity is not verified
- HMAC signature is not verified

## Commit Strategy (Phase 2)

**Phase 2 Commit (Real Authority Boundary):**
- Separate trusted authority process
- Windows Named Pipe trust boundary
- OS-derived identity verification
- HMAC signature implementation
- Interprocess atomicity (Windows file locking)
- Real IPC/identity (RUNTIME_VERIFIED)
- Capability/atomic consume (RUNTIME_VERIFIED)
- L3-L5 integration tests (RUNTIME_VERIFIED)

**Future commits (not in Phase 2):**
- C4: SelfAudit (RUNTIME_VERIFIED)
- C5: Completion gate (RUNTIME_VERIFIED)
- C6: Metacognitive rules (RUNTIME_VERIFIED)
- C7: Provenance/tool knowledge (RUNTIME_VERIFIED)
- C8: Integration tests (RUNTIME_VERIFIED)

## Summary

**Phase 1:** DATA_CONTRACT_ONLY (non-authoritative specification)
**Phase 2:** RUNTIME_VERIFIED (separate trusted authority process)

The real security boundary is implemented in Phase 2 using:
- Separate trusted authority process
- Windows Named Pipe trust boundary
- OS-derived identity verification
- HMAC signature verification
- Interprocess atomicity

Phase 1 was a data contract only and did NOT implement real security enforcement.
