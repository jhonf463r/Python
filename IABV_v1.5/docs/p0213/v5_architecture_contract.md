# P0.213 V5 Architecture Contract

## Phase 1: Data Contract Only (NON-AUTHORITATIVE)

### CRITICAL ARCHITECTURAL CONCLUSION

**In-process Python objects CANNOT be security boundaries.**

Any caller can import and invoke public constructors, methods, dataclasses,
factories, and deserializers. Therefore:

- RootTrustAnchor cannot be considered a security boundary while directly
  constructible in the same untrusted process.
- TrustedExecutionIdentity cannot be treated as authentic merely because its
  class name says "Trusted".
- TrustedLease cannot be treated as authoritative merely because it is
  immutable.
- LeaseRegistry cannot be called a unique security owner while any caller can
  instantiate another registry.

**Phase 1 is DATA CONTRACT ONLY, NOT AUTHORITY SECURITY ENFORCEMENT.**

The real security boundary will be implemented in Phase 2 using a separate
trusted authority process and OS/IPC enforcement.

### Phase Classification

- **DATA_CONTRACT_ONLY**: Non-authoritative data model and protocol specification
- **PHASE_2_REQUIRED**: Real security enforcement requires Phase 2 authority process
- **RUNTIME_VERIFIED**: OS authority boundary, HMAC signature, interprocess atomicity (Phase 2)

### Canonical Authority Chain

```
trusted bootstrap (Phase 2)
→ RootTrustAnchor (Phase 1: DESIGNED, Phase 2: RUNTIME_VERIFIED)
→ RuntimeIdentityAuthority (Phase 1: DESIGNED, Phase 2: RUNTIME_VERIFIED)
→ TrustedExecutionIdentity (Phase 1: DESIGNED, Phase 2: RUNTIME_VERIFIED)
→ parent/child relationship (Phase 2: RUNTIME_VERIFIED)
→ Windows Named Pipe trust boundary (Phase 2: RUNTIME_VERIFIED)
→ OS-observed client identity (Phase 2: RUNTIME_VERIFIED)
→ trusted lease/capability (Phase 1: DESIGNED, Phase 2: RUNTIME_VERIFIED)
→ exactly-once consumption (Phase 1: DESIGNED, Phase 2: RUNTIME_VERIFIED)
→ SelfAudit (Phase 4)
→ persistence (Phase 2: RUNTIME_VERIFIED)
```

### Authority Ownership Contract (Phase 2)

**ONE canonical owner of:**
- authority (RootTrustAnchor - Phase 2: trusted authority process)
- identity (RuntimeIdentityAuthority - Phase 2: trusted authority process)
- capability (LeaseIssuerService - Phase 2: trusted authority process)
- consumption (LeaseRegistry - Phase 2: trusted authority process)

**PHASE 2 AUTHORITY CONTRACT:**
- Phase 2: Trusted authority process owns the real secret key
- Phase 2: Trusted authority process owns generation state
- Phase 2: Trusted authority process enforces OS-derived identity
- Phase 2: Trusted authority process is the sole lease state owner
- Phase 2: Trusted authority process implements OS/interprocess atomicity

**PHASE 1 DATA CONTRACT:**
- Phase 1: Defines data model and protocol interface (non-authoritative)
- Phase 1: Any caller can construct instances (NOT a security boundary)
- Phase 1: No fake authority enforcement (_authority_authorized, etc.)

**FORBIDDEN IN PHASE 1:**
- Fake authority enforcement (_authority_authorized, boolean flags, secret strings)
- Placeholder secret material (b"placeholder")
- Claims that in-process objects are security boundaries
- verify_identity() -> False as fake security
- verify_lease() -> False as fake security
- Claims that dict.pop() is interprocess exactly-once

### Identity Issue Contract (Phase 2)

**PHASE 2 IDENTITY ISSUE CONTRACT:**
- ObservedProcessIdentity is OS-derived by trusted authority process
- CanonicalRunRecord is authority-owned by trusted authority process
- TrustedIdentityAuthority.issue(observed_identity, canonical_run_record) is the canonical API
- Caller CANNOT choose authoritative identity fields

**PHASE 1 DATA CONTRACT:**
- Phase 1: Defines ObservedProcessIdentity data structure
- Phase 1: Defines CanonicalRunRecord data structure
- Phase 1: Defines RuntimeIdentityAuthority protocol interface
- Phase 1: Caller-constructed instances are NOT authoritative

**FORBIDDEN:**
- issue_identity(pid, run_id, scope) as canonical authority API
- Caller-controlled consumer_pid
- Caller-controlled run_id
- Caller-controlled scope
- Caller-controlled metadata

### Immutability vs Authenticity vs Authority

**IMMUTABLE OBJECT != AUTHENTIC OBJECT != AUTHORIZED OBJECT:**

**IMMUTABILITY:**
- dataclass(frozen=True) prevents mutation (serialization operation)
- This does NOT confer authenticity
- This does NOT confer authority

**AUTHENTICITY:**
- HMAC signature proves not tampered (Phase 2: RUNTIME_VERIFIED)
- Phase 1: No signature (DATA_CONTRACT_ONLY)
- Phase 1: from_dict() is deserialization ONLY, NOT automatic trust

**AUTHORITY:**
- Only trusted authority process can issue (Phase 2: RUNTIME_VERIFIED)
- Phase 1: Any caller can construct instances (NOT a security boundary)
- Phase 1: Class name "Trusted" does NOT confer security
- Deserialized objects are NEVER automatically authoritative

### Lease Binding Contract (Phase 2)

**PHASE 2 LEASE BINDING CONTRACT:**
- Issuer owns issuer_pid, producer_pid, issuer_generation (NOT caller-controlled)
- Caller CANNOT choose authoritative lease fields
- Unique lease_id is authority-generated (NOT caller-controlled)
- Authorization context is authority-owned (NOT caller-controlled)

**PHASE 1 DATA CONTRACT:**
- Phase 1: Defines TrustedLease data structure
- Phase 1: Defines LeaseIssuerService protocol interface
- Phase 1: Caller-constructed instances are NOT authoritative
- Phase 1: Class name "Trusted" does NOT confer security

**FORBIDDEN:**
- Caller choosing issuer_pid
- Caller choosing producer_pid
- Caller choosing issuer_generation
- Caller choosing lease_id

### Lease State Ownership Contract (Phase 2)

**PHASE 2 LEASE STATE OWNERSHIP:**
- Phase 2 authority process is the ONLY authoritative lease state owner
- Phase 2 authority process is the ONLY consumption owner
- No duplicate registries in Phase 2
- No CapabilityRegistry in Phase 2
- No second state store in Phase 2

**PHASE 1 DATA CONTRACT:**
- Phase 1: Defines LeaseRegistry data structure (NON_AUTHORITATIVE_TEST_MODEL)
- Phase 1: In-process dictionary is NOT authoritative
- Phase 1: dict.pop() is NOT interprocess exactly-once
- Phase 1: Any caller can instantiate another registry (NOT a security boundary)

**PHASE 2 CANONICAL REJECTION CONDITIONS:**
- Invalid signature
- Invalid issuer
- Stale generation
- Duplicate lease ID
- Mismatched issuer
- Mismatched execution identity
- Expired lease
- Consumed lease
- Invalid binding

### Single-Use Semantics Contract (Phase 2)

**PHASE 2 SINGLE-USE SEMANTICS CONTRACT:**
- Single-use is an authority invariant
- Phase 2 provides OS/interprocess atomic enforcement
- Phase 2: Trusted authority process implements atomic consumption

**PHASE 1 DATA CONTRACT:**
- Phase 1: Defines single-use invariant as contract
- Phase 1: dict.pop() is NOT interprocess exactly-once
- Phase 1: In-process data structure is NON_AUTHORITATIVE_TEST_MODEL

**FORBIDDEN:**
- Claiming dict.pop() is interprocess exactly-once
- Exposing placeholder methods as security enforcement
- verify_lease() -> False as fake security

### Fail-Closed Semantics (Phase 2)

**PHASE 2 CANONICAL REJECTION CONDITIONS:**
- Missing identity
- Missing execution
- Invalid issuer
- Stale generation
- Expired lease
- Invalid signature
- Duplicate use
- Invalid binding

**PHASE 1 DATA CONTRACT:**
- Phase 1: Defines rejection conditions as contract
- Phase 1: verify_identity() raises Phase2Required (NOT fake security)
- Phase 1: verify_lease() raises Phase2Required (NOT fake security)
- Phase 1: No return False as fake security enforcement

**FORBIDDEN:**
- verify_identity() -> False as fake security
- verify_lease() -> False as fake security
- Placeholder validation presented as security enforcement

### Production Call graph Requirements

**Every major component must have a production caller.**

**Required lifecycle:**
```
bootstrap (Phase 2)
→ starts authority
→ creates readiness signal
→ launches/accepts real child
→ child connects through real IPC
→ identity derived from connected handle
→ authority issues lease/capability
→ consumer uses it
→ authority verifies/consumes
→ SelfAudit receives only verified evidence
```

**Phase 1 Status:** DESIGNED (ownership model defined, NOT_IMPLEMENTED)
**Phase 2 Status:** RUNTIME_VERIFIED (real IPC, real parent-child process)

### Trust Boundary Principles

**NEVER trust:**
- `request["pid"]`
- `request["consumer_pid"]`
- `request["sid"]`

**Identity MUST come from:**
- OS-observed process identity (Phase 2: RUNTIME_VERIFIED)
- Windows Named Pipe client process ID (Phase 2: RUNTIME_VERIFIED)
- Process creation identity (Phase 2: RUNTIME_VERIFIED)

**If identity cannot be established:**
- FAIL CLOSED

### Component Definitions

#### RootTrustAnchor
- **Phase 1 Status:** DATA_CONTRACT_ONLY (non-authoritative specification)
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- Phase 1: Data model for process identity, runtime identity, secret key requirements
- Phase 2: Trusted authority process owns real secret key (OS-protected)
- Phase 2: Trusted authority process owns generation state (persisted)
- Phase 2: Trusted authority process enforces OS-derived identity
- SECURITY WARNING: Phase 1 is NOT a security boundary

#### TrustedExecutionIdentity
- **Phase 1 Status:** DATA_CONTRACT_ONLY (non-authoritative specification)
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- Phase 1: Data model for execution identity
- Phase 1: Protocol interface for identity issuance
- Phase 2: Trusted authority process issues with HMAC signature
- Phase 2: Binds to OS-derived PID, persisted generation
- SECURITY WARNING: Phase 1 class name "Trusted" does NOT confer security

#### TrustedLease
- **Phase 1 Status:** DATA_CONTRACT_ONLY (non-authoritative specification)
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- Phase 1: Data model for lease/capability
- Phase 1: Protocol interface for lease issuance
- Phase 2: Trusted authority process issues with HMAC signature
- Phase 2: Binds to authority-owned fields (issuer_pid, producer_pid, lease_id)
- SECURITY WARNING: Phase 1 immutability does NOT provide authenticity

#### LeaseRegistry
- **Phase 1 Status:** DATA_CONTRACT_ONLY (non-authoritative test model)
- **Phase 2 Status:** RUNTIME_VERIFIED (separate trusted authority process)
- Phase 1: In-process dictionary (NON_AUTHORITATIVE_TEST_MODEL)
- Phase 2: Trusted authority process is sole lease state owner
- Phase 2: Trusted authority process implements OS/interprocess atomicity
- SECURITY WARNING: Phase 1 dict.pop() is NOT interprocess exactly-once

#### Windows Named Pipe Trust Boundary
- **Phase 1 Status:** NOT_IMPLEMENTED
- **Phase 2 Status:** RUNTIME_VERIFIED
- Explicit DACL
- Remote-client rejection
- Bounded message size
- Framing
- Partial-read handling
- Malformed message rejection
- Readiness signal
- Shutdown coordination

#### Exactly-Once Consumption
- **Phase 1 Status:** DESIGNED (ownership model defined, NOT_IMPLEMENTED)
- **Phase 2 Status:** RUNTIME_VERIFIED (interprocess atomicity)
- ONE canonical atomic consume operation
- Survives: concurrent race, replay, restart, stale generation, expiration, crash/recovery

#### SelfAudit
- **Phase 1 Status:** NOT_IMPLEMENTED
- **Phase 4 Status:** RUNTIME_VERIFIED
- Accepts evidence ONLY after canonical authority verification
- Rejected context produces: NO SNAPSHOT, NO HISTORY ENTRY, NO PARTIAL PERSISTENCE
- Persistence is atomic/recoverable

### Metacognitive Rules (from V12)

**Critical patterns that BLOCK:**
1. IN_PROCESS_OBJECT_AUTHORITY_IS_NOT_A_SECURITY_BOUNDARY - Phase 1: BLOCK (in-process objects cannot be security boundaries)
2. FAKE_AUTHORITY_OWNER_DECLARATION - Phase 1: BLOCK (fake _authority_authorized, boolean flags, secret strings)
3. PLACEHOLDER_VALIDATION_PRESENTED_AS_SECURITY - Phase 1: BLOCK (verify_identity() -> False, verify_lease() -> False)
4. IMMUTABILITY_CONFUSED_WITH_AUTHENTICITY - Phase 1: BLOCK (dataclass(frozen=True) does NOT confer authenticity)
5. DATA_MODEL_CONFUSED_WITH_AUTHORITY - Phase 1: BLOCK (class name "Trusted" does NOT confer security)
6. CALLER_CONTROLLED_SECURITY_IDENTITY - Phase 1: BLOCK (caller-controlled identity fields)
7. REPLAYABLE_AUTHENTICATED_RECEIPT - Phase 1: BLOCK (dict.pop() is NOT interprocess exactly-once)
8. SELF_REFERENTIAL_EVIDENCE_METADATA - Phase 1: BLOCK (provenance contract forbids self-referential SHA)
9. DUPLICATE_AUTHORITY_OR_STATE - Phase 1: BLOCK (ONE authority, ONE lease state owner in Phase 2)
10. UNTRUSTED_CONTEXT_AS_VERIFIED_CONTEXT - Phase 1: BLOCK (from_dict() is deserialization ONLY, NOT automatic trust)

**High-severity patterns that REQUIRE REVIEW:**
11. ADVISORY_CONTROL_PRESENTED_AS_ENFORCEMENT - Phase 1: REVIEW (placeholder methods must be explicit)
12. VERSION_CLAIM_WITHOUT_FROZEN_ARTIFACT - Phase 1: REVIEW (provenance contract requires frozen artifact)
13. CLAIM_WITHOUT_EVIDENCE - Phase 1: REVIEW (architecture contract requires evidence)
14. CLAIMED_INTEGRATION_WITH_UNIT_TEST_SUBSTITUTE - Phase 1: REVIEW (L3-L5 evidence required for security invariants)

**Medium-severity patterns that WARN:**
15. SECURITY_BY_NAMING_CONVENTION - Phase 1: WARN (underscore/private naming as security mechanism)

### Test Strategy

**Test Layers:**
- L1 UNIT/CONTRACT: Data model and protocol interface tests (Phase 1: DATA_CONTRACT_ONLY)
- L2 COMPONENT: Component integration tests (Phase 2: RUNTIME_VERIFIED)
- L3 REAL WINDOWS IPC: Real Windows Named Pipe tests (Phase 2: RUNTIME_VERIFIED)
- L4 REAL MULTIPROCESS: Real parent-child process tests (Phase 2: RUNTIME_VERIFIED)
- L5 ADVERSARIAL: Adversarial input tests (Phase 2: RUNTIME_VERIFIED)
- L6 P0.20 REGRESSION: P0.20 compatibility tests (Phase 2: RUNTIME_VERIFIED)

**Critical security invariants require L3-L5 evidence.**
**Phase 1 tests are UNIT/CONTRACT tests (NOT security tests).**

**Phase 1 tests must verify:**
1. Data-model invariants (required fields, types)
2. Immutability (dataclass frozen=True)
3. Serialization round-trip (to_dict/from_dict)
4. Explicit non-authoritative semantics
5. Phase 2 required interfaces (NotImplementedError)
6. Architecture contract consistency
7. Absence of fake authority bypass parameters
8. Absence of placeholder secrets
9. Absence of verify_identity() -> False fake security
10. Absence of verify_lease() -> False fake security

**Phase 1 tests must NOT claim:**
1. OS identity verification
2. Real authority enforcement
3. IPC security
4. Exactly-once consumption
5. Production reachability

### Stop Conditions

**STOP implementation and report immediately if:**
- In-process object is claimed as security boundary
- Fake authority enforcement appears (_authority_authorized, boolean flags, secret strings)
- Placeholder validation presented as security (verify_identity() -> False, verify_lease() -> False)
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
- Placeholder secret material appears (b"placeholder")
- Boolean trusted flags appear as security mechanism
- Secret strings appear as security mechanism
- Underscore/private naming appears as security mechanism
- Bootstrap token constants appear as security mechanism
- Public factory + hidden argument appears as security mechanism
- dict.pop() is claimed as interprocess exactly-once

### Commit Strategy

**Phase 1 Commit (Contract-Only Reset):**
- Data contract only (NON-AUTHORITATIVE specification)
- Architecture contract with phase classification (DATA_CONTRACT_ONLY/PHASE_2_REQUIRED/RUNTIME_VERIFIED)
- Identity issue contract (ObservedProcessIdentity + CanonicalRunRecord data models)
- Lease binding contract (issuer owns authoritative fields in Phase 2)
- Lease state ownership contract (Phase 2 authority process is sole owner)
- Single-use semantics contract (dict.pop() is NOT interprocess exactly-once)
- Immutability vs authenticity vs authority clarification
- Explicit non-authoritative semantics
- Phase 1 tests (UNIT/CONTRACT tests, NOT security tests)

**Future commits (not in Phase 1):**
- C2: Real IPC/identity (RUNTIME_VERIFIED - separate trusted authority process)
- C3: Capability/atomic consume (RUNTIME_VERIFIED - OS/interprocess atomicity)
- C4: SelfAudit (RUNTIME_VERIFIED)
- C5: Completion gate (RUNTIME_VERIFIED)
- C6: Metacognitive rules (RUNTIME_VERIFIED)
- C7: Provenance/tool knowledge (RUNTIME_VERIFIED)
- C8: Integration tests (RUNTIME_VERIFIED)
