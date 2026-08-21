# P0.213 V5 Architecture Contract

## Phase 1: Trust Boundary Skeleton

### Canonical Authority Chain

```
trusted bootstrap
→ RootTrustAnchor
→ TrustedExecutionIdentity
→ parent/child relationship
→ Windows Named Pipe trust boundary
→ OS-observed client identity
→ trusted lease/capability
→ exactly-once consumption
→ SelfAudit
→ persistence
```

### Single Authority Ownership

**ONE canonical owner of:**
- authority
- identity
- capability
- consumption

**FORBIDDEN:**
- Duplicate authority registries
- Parallel legacy paths
- Compatibility authorities

### Production Call graph Requirements

**Every major component must have a production caller.**

**Required lifecycle:**
```
bootstrap
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

### Trust Boundary Principles

**NEVER trust:**
- `request["pid"]`
- `request["consumer_pid"]`
- `request["sid"]`

**Identity MUST come from:**
- OS-observed process identity
- Windows Named Pipe client process ID
- Process creation identity

**If identity cannot be established:**
- FAIL CLOSED

### Component Definitions

#### RootTrustAnchor
- OS-controlled trust anchor
- Secret key management
- Generation persistence
- Bootstrap verification

#### TrustedExecutionIdentity
- Binds to observed PID
- Binds to process creation identity
- Binds to parent/child relation
- Binds to runtime generation
- Binds to execution identity

#### Windows Named Pipe Trust Boundary
- Explicit DACL
- Remote-client rejection
- Bounded message size
- Framing
- Partial-read handling
- Malformed message rejection
- Readiness signal
- Shutdown coordination

#### Trusted Lease/Capability
- Binds to execution/run identity
- Binds to consumer identity
- Binds to scope
- Binds to generation
- Binds to expiry
- Binds to action/target where applicable

#### Exactly-Once Consumption
- ONE canonical atomic consume operation
- Survives: concurrent race, replay, restart, stale generation, expiration, crash/recovery

#### SelfAudit
- Accepts evidence ONLY after canonical authority verification
- Rejected context produces: NO SNAPSHOT, NO HISTORY ENTRY, NO PARTIAL PERSISTENCE
- Persistence is atomic/recoverable

### Metacognitive Rules (from V12)

**Critical patterns that BLOCK:**
1. CALLER_CONTROLLED_SECURITY_IDENTITY
2. REPLAYABLE_AUTHENTICATED_RECEIPT
3. THREAD_CONCURRENCY_NOT_PROCESS_CONCURRENCY
4. SELF_REFERENTIAL_EVIDENCE_METADATA
5. CONTROL_WITHOUT_PRODUCTION_CONSUMER
6. DEFINITION_WITHOUT_PRODUCTION_REACHABILITY
7. DUPLICATE_AUTHORITY_OR_STATE
8. UNTRUSTED_CONTEXT_AS_VERIFIED_CONTEXT
9. EVIDENCE_STANDARD_RELAXATION

**High-severity patterns that REQUIRE REVIEW:**
10. ADVISORY_CONTROL_PRESENTED_AS_ENFORCEMENT
11. VERSION_CLAIM_WITHOUT_FROZEN_ARTIFACT
12. CLAIM_WITHOUT_EVIDENCE
13. CLAIMED_INTEGRATION_WITH_UNIT_TEST_SUBSTITUTE
14. UNEXECUTABLE_CRITICAL_TEST

**Medium-severity patterns that WARN:**
15. SECURITY_BY_NAMING_CONVENTION

### Test Strategy

**Test Layers:**
- L1 UNIT: Component unit tests
- L2 COMPONENT: Component integration tests
- L3 REAL WINDOWS IPC: Real Windows Named Pipe tests
- L4 REAL MULTIPROCESS: Real parent-child process tests
- L5 ADVERSARIAL: Adversarial input tests
- L6 P0.20 REGRESSION: P0.20 compatibility tests

**Critical security invariants require L3-L5 evidence.**

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

### Commit Strategy

**Phase 1 Commit:**
- Clean trust-boundary skeleton
- Architecture contract
- Production ownership/call graph definition
- Test definitions for Phase 1

**Future commits (not in Phase 1):**
- C2: Real IPC/identity
- C3: Capability/atomic consume
- C4: SelfAudit
- C5: Completion gate
- C6: Metacognitive rules
- C7: Provenance/tool knowledge
- C8: Integration tests
