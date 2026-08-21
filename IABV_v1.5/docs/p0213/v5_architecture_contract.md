# P0.213 V5 Architecture Contract

## Phase 1: Trust Boundary Skeleton (Remediated)

### Phase Classification

- **DESIGNED**: Ownership model and data representation defined
- **NOT_IMPLEMENTED**: Placeholder values, no actual security enforcement
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

### Authority Ownership Model

**ONE canonical owner of:**
- authority (RootTrustAnchor)
- identity (RuntimeIdentityAuthority)
- capability (LeaseIssuerService)
- consumption (LeaseRegistry)

**AUTHORITY OWNERSHIP CONTRACT:**
- ONLY the trusted bootstrap/authority owner may create the canonical authority
- Other components receive references/issued artifacts, NOT authority-construction capability
- Direct construction of RootTrustAnchor is FORBIDDEN unless _authority_authorized=True
- Phase 2: RuntimeAuthority.bootstrap() is the ONLY authorized creation path
- Phase 1: Ownership model defined, placeholder for Phase 2 implementation

**FORBIDDEN:**
- Duplicate authority registries
- Parallel legacy paths
- Compatibility authorities
- Caller-controlled security identity
- Placeholder secret material (b"placeholder")
- Boolean trusted flags as security mechanism
- Secret strings as security mechanism
- Underscore/private naming as security mechanism
- Bootstrap token constants as security mechanism
- Public factory + hidden argument as security mechanism

### Identity Issue Contract

**IDENTITY ISSUE CONTRACT:**
- ObservedProcessIdentity is OS-derived (NOT caller-controlled)
- CanonicalRunRecord is authority-owned (NOT caller-controlled)
- TrustedIdentityAuthority.issue(observed_identity, canonical_run_record) is the canonical API
- Caller CANNOT choose authoritative identity fields

**FORBIDDEN:**
- issue_identity(pid, run_id, scope) as canonical authority API
- Caller-controlled consumer_pid
- Caller-controlled run_id
- Caller-controlled scope
- Caller-controlled metadata

### Immutability vs Authenticity vs Authority

**IMMUTABILITY:**
- dataclass(frozen=True) prevents mutation
- This is a serialization operation, NOT mutation

**AUTHENTICITY:**
- HMAC signature proves not tampered (Phase 2: RUNTIME_VERIFIED)
- Phase 1: DESIGNED (NOT_IMPLEMENTED)

**AUTHORITY:**
- Only RuntimeIdentityAuthority can issue (Phase 1 ownership model)
- Only LeaseIssuerService can issue (Phase 1 ownership model)
- from_dict() is deserialization ONLY, NOT automatic trust
- Deserialized object MUST be verified against canonical authority state before trusted

### Lease Binding Contract

**LEASE BINDING CONTRACT:**
- Issuer owns issuer_pid, producer_pid, issuer_generation (NOT caller-controlled)
- Caller CANNOT choose authoritative lease fields
- Unique lease_id is authority-generated (NOT caller-controlled)
- Authorization context is authority-owned (NOT caller-controlled)

**FORBIDDEN:**
- Caller choosing issuer_pid
- Caller choosing producer_pid
- Caller choosing issuer_generation
- Caller choosing lease_id

### Lease State Ownership

**ONE LEASE STATE OWNER:**
- LeaseRegistry is the ONLY authoritative lease state owner
- No duplicate registries
- No CapabilityRegistry
- No second state store

**ONE CONSUMPTION OWNER:**
- Only LeaseRegistry can authorize consumption

**CANONICAL REJECTION CONDITIONS:**
- Invalid signature
- Invalid issuer
- Stale generation
- Duplicate lease ID
- Mismatched issuer
- Mismatched execution identity
- Expired lease
- Consumed lease
- Invalid binding

### Single-Use Semantics Contract

**SINGLE-USE SEMANTICS CONTRACT:**
- Single-use is an authority invariant
- Phase 2 will provide OS/interprocess atomic enforcement
- Phase 1: Placeholder (NOT_IMPLEMENTED)
- dict.pop() is NOT interprocess exactly-once

**FORBIDDEN:**
- Claiming dict.pop() is interprocess exactly-once
- Exposing placeholder methods as security enforcement

### Fail-Closed Semantics

**CANONICAL REJECTION CONDITIONS:**
- Missing identity
- Missing execution
- Invalid issuer
- Stale generation
- Expired lease
- Invalid signature
- Duplicate use
- Invalid binding

**FAIL-CLOSED:**
- All verification methods return False on any failure (Phase 1)
- Phase 2: Will implement specific rejection conditions

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
- **Phase 1 Status:** DESIGNED (ownership model defined, NOT_IMPLEMENTED)
- **Phase 2 Status:** RUNTIME_VERIFIED (OS authority boundary)
- Authority ownership: Only trusted bootstrap may create canonical instance
- Direct construction FORBIDDEN unless _authority_authorized=True
- OS-controlled trust anchor (Phase 2)
- Secret key management (Phase 2, OS-protected)
- Generation persistence (Phase 2)
- Bootstrap verification (Phase 2)

#### TrustedExecutionIdentity
- **Phase 1 Status:** DESIGNED (ownership model defined, NOT_IMPLEMENTED)
- **Phase 2 Status:** RUNTIME_VERIFIED (HMAC signature, OS identity)
- Identity issue contract: ObservedProcessIdentity + CanonicalRunRecord
- Binds to observed PID (Phase 2: OS-derived)
- Binds to process creation identity (Phase 2: OS-derived)
- Binds to parent/child relation (Phase 2: OS-derived)
- Binds to runtime generation (Phase 2: persisted)
- Binds to execution identity (Phase 2: authority-generated)

#### TrustedLease
- **Phase 1 Status:** DESIGNED (ownership model defined, NOT_IMPLEMENTED)
- **Phase 2 Status:** RUNTIME_VERIFIED (HMAC signature, OS identity)
- Lease binding contract: Issuer owns authoritative fields
- Binds to execution/run identity (authority-owned)
- Binds to consumer identity (OS-derived)
- Binds to scope (authority-owned)
- Binds to generation (authority-owned)
- Binds to expiry (authority-owned)
- Unique lease_id (authority-generated)

#### LeaseRegistry
- **Phase 1 Status:** DESIGNED (ownership model defined, NOT_IMPLEMENTED)
- **Phase 2 Status:** RUNTIME_VERIFIED (interprocess atomicity)
- ONE lease state owner
- ONE consumption owner
- Rejects: invalid signature, expired lease, stale generation, duplicate lease ID, mismatched issuer, mismatched execution identity

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
1. CALLER_CONTROLLED_SECURITY_IDENTITY - Phase 1: DESIGNED (ownership model prevents caller-controlled identity)
2. REPLAYABLE_AUTHENTICATED_RECEIPT - Phase 1: DESIGNED (single-use invariant defined), Phase 2: RUNTIME_VERIFIED
3. THREAD_CONCURRENCY_NOT_PROCESS_CONCURRENCY - Phase 1: DESIGNED (single-use contract acknowledges dict.pop() is NOT interprocess), Phase 2: RUNTIME_VERIFIED
4. SELF_REFERENTIAL_EVIDENCE_METADATA - Phase 1: DESIGNED (provenance contract forbids self-referential SHA)
5. CONTROL_WITHOUT_PRODUCTION_CONSUMER - Phase 1: DESIGNED (production caller required), Phase 2: RUNTIME_VERIFIED
6. DEFINITION_WITHOUT_PRODUCTION_REACHABILITY - Phase 1: DESIGNED (production caller required), Phase 2: RUNTIME_VERIFIED
7. DUPLICATE_AUTHORITY_OR_STATE - Phase 1: DESIGNED (ONE authority, ONE lease state owner)
8. UNTRUSTED_CONTEXT_AS_VERIFIED_CONTEXT - Phase 1: DESIGNED (from_dict() is deserialization ONLY, NOT automatic trust)
9. EVIDENCE_STANDARD_RELAXATION - Phase 1: DESIGNED (L3-L5 evidence required for security invariants)

**High-severity patterns that REQUIRE REVIEW:**
10. ADVISORY_CONTROL_PRESENTED_AS_ENFORCEMENT - Phase 1: DESIGNED (fail-closed verification)
11. VERSION_CLAIM_WITHOUT_FROZEN_ARTIFACT - Phase 1: DESIGNED (provenance contract requires frozen artifact)
12. CLAIM_WITHOUT_EVIDENCE - Phase 1: DESIGNED (architecture contract requires evidence)
13. CLAIMED_INTEGRATION_WITH_UNIT_TEST_SUBSTITUTE - Phase 1: DESIGNED (L3-L5 evidence required)
14. UNEXECUTABLE_CRITICAL_TEST - Phase 1: DESIGNED (L3-L5 evidence required)

**Medium-severity patterns that WARN:**
15. SECURITY_BY_NAMING_CONVENTION - Phase 1: DESIGNED (forbidden: underscore/private naming as security mechanism)

### Test Strategy

**Test Layers:**
- L1 UNIT: Component unit tests (Phase 1: DESIGNED)
- L2 COMPONENT: Component integration tests (Phase 2: RUNTIME_VERIFIED)
- L3 REAL WINDOWS IPC: Real Windows Named Pipe tests (Phase 2: RUNTIME_VERIFIED)
- L4 REAL MULTIPROCESS: Real parent-child process tests (Phase 2: RUNTIME_VERIFIED)
- L5 ADVERSARIAL: Adversarial input tests (Phase 2: RUNTIME_VERIFIED)
- L6 P0.20 REGRESSION: P0.20 compatibility tests (Phase 2: RUNTIME_VERIFIED)

**Critical security invariants require L3-L5 evidence.**
**Phase 1 tests are UNIT/STATIC architecture tests (NOT runtime tests).**

### Stop Conditions

**STOP implementation and report immediately if:**
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

### Commit Strategy

**Phase 1 Commit (Remediated):**
- Clean trust-boundary skeleton with authority ownership model
- Architecture contract with phase classification (DESIGNED/NOT_IMPLEMENTED/RUNTIME_VERIFIED)
- Identity issue contract (ObservedProcessIdentity + CanonicalRunRecord)
- Lease binding contract (issuer owns authoritative fields)
- Lease state ownership contract (ONE lease state owner)
- Single-use semantics contract (dict.pop() is NOT interprocess exactly-once)
- Fail-closed semantics (canonical rejection conditions)
- Immutability vs authenticity vs authority clarification
- Production ownership/call graph definition
- Phase 1 tests (UNIT/STATIC architecture tests)

**Future commits (not in Phase 1):**
- C2: Real IPC/identity (RUNTIME_VERIFIED)
- C3: Capability/atomic consume (RUNTIME_VERIFIED)
- C4: SelfAudit (RUNTIME_VERIFIED)
- C5: Completion gate (RUNTIME_VERIFIED)
- C6: Metacognitive rules (RUNTIME_VERIFIED)
- C7: Provenance/tool knowledge (RUNTIME_VERIFIED)
- C8: Integration tests (RUNTIME_VERIFIED)
