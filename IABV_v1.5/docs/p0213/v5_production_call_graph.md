# P0.213 V5 Production Call Graph

## Phase 1: Production Ownership and Call Graph

### Production Callers (To Be Implemented)

**Phase 1 Status:** Skeleton components defined. Production callers to be identified in Phase 2.

### Required Production Lifecycle

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

### Component Ownership

**RootTrustAnchor**
- Owner: Trusted bootstrap process
- Production Caller: Bootstrap service (to be implemented in Phase 2)
- Current Status: Skeleton interface defined

**RuntimeIdentityAuthority**
- Owner: RootTrustAnchor
- Production Caller: Bootstrap service (to be implemented in Phase 2)
- Current Status: Skeleton interface defined

**LeaseIssuerService**
- Owner: RuntimeIdentityAuthority
- Production Caller: IPC authority service (to be implemented in Phase 2)
- Current Status: Skeleton interface defined

**LeaseRegistry**
- Owner: IPC authority service
- Production Caller: IPC authority service (to be implemented in Phase 2)
- Current Status: Skeleton interface defined

### Trust Chain

```
Trusted Bootstrap (Phase 2)
→ RootTrustAnchor (Phase 1 skeleton)
→ RuntimeIdentityAuthority (Phase 1 skeleton)
→ TrustedExecutionIdentity (Phase 1 skeleton)
→ LeaseIssuerService (Phase 1 skeleton)
→ TrustedLease (Phase 1 skeleton)
→ LeaseRegistry (Phase 1 skeleton)
→ SelfAudit (Phase 4)
```

### Stop Condition Check

**Phase 1 Status:**
- ✅ No duplicate authority
- ✅ No duplicate capability registry
- ✅ No security path is optional (all skeletons require implementation)
- ⚠️ Production caller cannot be identified yet (Phase 2)
- ✅ No unit test claiming system integration (skeletons only)
- ✅ No test requirement reduction (no tests yet)
- ✅ No self-referential provenance (not implemented yet)
- ✅ No legacy path (clean reconstruction)
- ✅ No tool result treated as proof (not implemented yet)

### Unresolved Items (Phase 2)

1. Identify production caller for RootTrustAnchor
2. Identify production caller for RuntimeIdentityAuthority
3. Identify production caller for LeaseIssuerService
4. Implement Windows Named Pipe trust boundary
5. Implement real parent-child process lifecycle
6. Implement real IPC communication
7. Implement OS-observed client identity
8. Implement atomic consumption with interprocess locking
9. Implement SelfAudit trust boundary
10. Implement completion gate

### Architecture Decisions (Phase 1)

**Decision 1:** Use single canonical authority chain
- Rationale: Prevents duplicate authority and state
- Status: Implemented in skeleton

**Decision 2:** Fail-closed verification for all components
- Rationale: Security by default, reject invalid input
- Status: Implemented in skeleton (placeholder returns False)

**Decision 3:** OS-controlled identity only
- Rationale: Prevents caller-controlled security identity
- Status: Defined in interface, implementation in Phase 2

**Decision 4:** Cryptographic binding for all identities and leases
- Rationale: Prevents tampering and forgery
- Status: Defined in interface, implementation in Phase 2

**Decision 5:** Single-use semantics for leases
- Rationale: Prevents replay attacks
- Status: Defined in interface, implementation in Phase 2
