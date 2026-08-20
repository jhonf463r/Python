# P0.213 V5 Invocation Authority Contract

**Task**: P0.213-AUTHORITY-CONTRACT-RECONSTRUCTION-01  
**Date**: 2026-08-20  
**Repository**: jhonf463r/Python  
**Status**: ARCHITECTURE DEFINITION (NO IMPLEMENTATION)  

---

## A. Root Cause

**Codex Re-audit Findings**:

**F-01**: SelfAudit puede persistir caller_asserted identity cuando identity_authority=None.
- **Root**: Optional authority creates fail-open path
- **Gap**: No mandatory verification before persistence

**F-02**: Lease no representa correctamente parent→child.
- **Root**: consumer_pid field added but not integrated with lease issuance
- **Gap**: Lease doesn't enforce authorized consumer binding

**F-03**: ppid() demuestra lineage, no consumer authorization.
- **Root**: Parent-child relationship ≠ authorization to consume capability
- **Gap**: Lineage verification doesn't prove issuer intended this specific consumer

**F-04**: IPC no valida capability→authorized consumer.
- **Root**: IPC validates PID but not capability binding
- **Gap**: Pipe connection doesn't prove capability ownership

**F-05**: DACL same-user no demuestra process isolation.
- **Root**: Same-user DACL allows sibling processes to connect
- **Gap**: OS-level access control ≠ capability-based authorization

**F-06**: Replay/single-use no es interprocess-atomic.
- **Root**: Local dict registry not atomic across processes
- **Gap**: Single-use enforcement requires interprocess coordination

**F-07**: P0.20 regression evidence is inconsistent (81 claim vs 83 sum).
- **Root**: Test count discrepancy unverified
- **Gap**: Evidence not reproducible

**Fundamental Gap**: V4 treated identity verification as the primary authority, but identity ≠ invocation authorization. A verified identity doesn't prove the current invocation is authorized to execute within a specific scope.

---

## B. Trust Authority

**Definitions**:

**TRUST ANCHOR**: RootTrustAnchor
- **Role**: Bootstrap trust root
- **Authority**: Establishes runtime identity generation
- **Scope**: Single runtime incarnation
- **Cannot**: Issue cross-process capabilities

**AUTHORITY**: RuntimeIdentityAuthority
- **Role**: Issue and verify execution identities
- **Authority**: Bind identity to runtime incarnation
- **Scope**: Single process (self-issued) or parent-child (cross-process)
- **Cannot**: Authorize invocation consumption

**ISSUER**: CapabilityIssuer
- **Role**: Issue invocation capabilities
- **Authority**: Bind capability to authorized consumer
- **Scope**: Parent → child process
- **Cannot**: Verify capability consumption (separate verifier)

**CONSUMER**: Authorized Process
- **Role**: Consume invocation capability
- **Authority**: Execute within authorized scope
- **Scope**: Single invocation (single-use)
- **Cannot**: Issue capabilities to other processes

**VERIFIER**: CapabilityVerifier
- **Role**: Verify and consume capabilities
- **Authority**: Validate capability integrity and binding
- **Scope**: Interprocess atomic verification
- **Cannot**: Issue capabilities (separate issuer)

**Authority Separation**:
- Identity Authority ≠ Capability Authority
- Issuer ≠ Verifier
- Consumer ≠ Issuer
- Lineage ≠ Authorization

**Who can create a trusted invocation?**
- Only the ISSUER (parent process) can issue a capability to an authorized CONSUMER (child process)

**Who can consume it?**
- Only the CONSUMER specified in the capability

**Who can verify it?**
- Only the VERIFIER (trust boundary) can validate and consume the capability

**Who CANNOT create it?**
- Consumer cannot issue capabilities
- Sibling processes cannot issue capabilities
- Unrelated processes cannot issue capabilities
- Identity authority alone cannot authorize invocation

---

## C. Invocation Capability

**Conceptual Definition**:

**InvocationCapability**: A cryptographically bound token that authorizes a specific process to execute within a specific scope for a single invocation.

**Minimal Fields**:

**Required**:
- `issuer_pid`: PID of the process that issued the capability (parent)
- `authorized_consumer_pid`: PID of the process authorized to consume (child)
- `capability_id`: Unique identifier for this capability
- `invocation_id`: Unique identifier for the authorized invocation
- `scope`: Authorized execution scope (e.g., "tool_execution", "learning_update")
- `issued_at`: Timestamp when capability was issued
- `expires_at`: Timestamp when capability becomes invalid
- `signature`: Cryptographic signature binding all fields

**Optional**:
- `runtime_incarnation`: Runtime generation identifier (prevents cross-run replay)
- `session_id`: Session identifier (prevents cross-session replay)
- `execution_id`: Execution context identifier

**NOT Required**:
- `consumer_pid` (redundant with `authorized_consumer_pid`)
- `issuer_generation` (redundant with runtime_incarnation)
- Separate identity object (capability is the authority)

**Integrity/Authentication**:
- Signature must be computed over all required fields
- Signature must be verifiable by the verifier
- Signature must be unforgeable by consumer

**Single-Use State**:
- Single-use enforcement is NOT a field in the capability
- Single-use is enforced by the verifier at consumption time
- Capability is marked as consumed in an interprocess-atomic registry

---

## D. Consumer Authorization

**Definition**:

"Authorized consumer" means the capability was explicitly issued by the issuer to this specific process PID for this specific invocation scope.

**PROCESS LINEAGE vs PROCESS AUTHORIZATION**:

**PROCESS LINEAGE** (what V4 verified):
- Parent PID (ppid())
- Spawn relationship
- Inherited handles
- Pipe connection

**PROCESS AUTHORIZATION** (what V5 requires):
- Capability explicitly issued to this PID
- Capability scope matches requested execution
- Capability is not expired
- Capability is not already consumed
- Capability signature is valid

**Lineage is NOT Authorization**:
- Parent-child relationship proves lineage, not authorization
- A parent can spawn a child without authorizing it to execute specific scopes
- Sibling processes have same parent but different authorization levels
- Lineage verification is necessary but not sufficient

**Authorization Combination**:

**Required**:
1. **Capability Binding**: Capability explicitly issued to this PID
2. **Lineage Verification**: Consumer is child of issuer (prevents PID spoofing)
3. **OS Identity Verification**: OS confirms PID matches process (prevents forged PID)
4. **Scope Validation**: Requested execution matches capability scope
5. **Temporal Validity**: Capability is not expired
6. **Single-Use Enforcement**: Capability has not been consumed

**Sufficient**: All 6 conditions met

**Evaluating Mechanisms**:

**PID**: Required for capability binding, but insufficient alone (spoofable)
**PPID**: Required for lineage verification, but insufficient alone (lineage ≠ authorization)
**OS Process Identity**: Required for PID verification, but insufficient alone
**Spawn Relationship**: Required for lineage, but insufficient alone
**Inherited Handle**: Useful for IPC, but not for authorization
**Pipe Connection**: Required for IPC, but not for authorization
**Capability Binding**: REQUIRED (core authorization)
**Runtime Registration**: Useful for single-use enforcement, but not for authorization

**Minimal Combination**:
- Capability Binding (explicit authorization)
- Lineage Verification (ppid())
- OS Identity Verification (OS confirms PID)

---

## E. IPC Contract

**Chain**:

OS-observed client identity
→ authorized consumer verification
→ capability validation
→ capability consumption
→ invocation acceptance

**Detailed Flow**:

1. **OS-observed client identity**:
   - Named pipe server calls GetNamedPipeClientProcessId()
   - Returns actual client PID from OS
   - This is the OS-observed identity, not caller-provided

2. **Authorized consumer verification**:
   - Verifier checks if client PID matches capability's authorized_consumer_pid
   - Verifier checks if client is child of issuer (ppid() == issuer_pid)
   - Rejects if PID mismatch or lineage mismatch

3. **Capability validation**:
   - Verifier checks capability signature
   - Verifier checks capability scope matches requested execution
   - Verifier checks capability is not expired
   - Rejects if signature invalid, scope mismatch, or expired

4. **Capability consumption**:
   - Verifier marks capability as consumed in interprocess-atomic registry
   - Prevents replay of same capability
   - Rejects if already consumed

5. **Invocation acceptance**:
   - Only after all previous steps succeed
   - Invocation is now authorized
   - Execution proceeds within authorized scope

**Role of Each Mechanism**:

**DACL**:
- **Role**: Prevent unauthorized pipe connections
- **Limitation**: Same-user DACL allows sibling processes
- **Not**: Capability authorization
- **Use**: First line of defense, not sufficient alone

**Client PID**:
- **Role**: Identify which process is connecting
- **Limitation**: Can be spoofed in some scenarios
- **Not**: Authorization proof
- **Use**: Must match capability's authorized_consumer_pid

**PPID**:
- **Role**: Verify lineage (client is child of issuer)
- **Limitation**: Lineage ≠ authorization
- **Not**: Authorization proof
- **Use**: Must verify client is child of capability issuer

**Producer Scope**:
- **Role**: Identify which issuer issued the capability
- **Limitation**: Scope is a field, not proof of authorization
- **Not**: Authorization proof
- **Use**: Must match capability's issuer_pid

**PPID is NOT the only authority**:
- PPID proves lineage, not authorization
- Capability binding is the primary authority
- PPID is a necessary check to prevent PID spoofing
- Without capability binding, PPID alone is insufficient

---

## F. SelfAudit Contract

**Definition**:

SelfAuditService must accept **VALIDATED INVOCATION CONTEXT**, not **CALLER_ASSERTED IDENTITY**.

**Current V4 Problem**:
- SelfAuditService.run() accepts canonical_identity as parameter
- When identity_authority=None, it persists caller_asserted identity
- This allows unverified identity to be persisted as trusted evidence

**V5 Contract**:

**SelfAuditService.run() must require**:

**VALIDATED INVOCATION CONTEXT** containing:
- capability_id: The capability that authorized this invocation
- invocation_id: The unique invocation identifier
- authorized_consumer_pid: The process authorized to execute
- scope: The authorized execution scope
- verified_at: Timestamp when capability was verified
- verifier_signature: Signature from the verifier confirming verification

**NOT**:
- canonical_identity: Caller-provided identity dict
- identity_authority: Optional verification (must be mandatory)
- identity=None: Fallback path (must be rejected)

**Fail-Closed Rules**:

**Missing capability**:
- REJECT
- Do not persist
- Do not continue execution

**Invalid capability**:
- REJECT
- Do not persist
- Do not continue execution

**Stale capability**:
- REJECT
- Do not persist
- Do not continue execution

**Wrong consumer**:
- REJECT
- Do not persist
- Do not continue execution

**Wrong runtime**:
- REJECT
- Do not persist
- Do not continue execution

**Never**:
- identity=None → continue
- identity=None → persist
- identity_authority=None → accept caller_asserted identity
- verification failure → fallback to unverified identity

**Mandatory Verification**:
- identity_authority is NOT optional
- capability verification is NOT optional
- lineage verification is NOT optional
- All verification paths are fail-closed

---

## G. Single-Use Contract

**Definition**:

Single-use enforcement must be atomic from the perspective of the trust boundary.

**Where VERIFY + CONSUME Occurs**:

**Location**: CapabilityVerifier (trust boundary component)

**Operation**: verify_and_consume_capability()

**Atomicity Requirements**:

1. **Interprocess Atomicity**:
   - Verification and consumption must be atomic across processes
   - Cannot use local dict (not interprocess visible)
   - Must use interprocess synchronization (file lock, named pipe, shared memory)

2. **Concurrency Safety**:
   - Multiple workers must not consume same capability
   - Multiple processes must not consume same capability
   - Must handle race conditions

3. **Replay Prevention**:
   - Once consumed, capability cannot be reused
   - Consumption state must be durable
   - Must survive process restart

**Solving Concurrency**:
- File-based registry with file locks
- Named pipe for interprocess coordination
- Shared memory with atomic operations

**Solving Replay**:
- Persistent consumption registry
- Capability ID → consumed timestamp mapping
- Check consumption before verification

**Solving Multiple Workers**:
- Each worker has unique invocation_id
- Capability is bound to specific invocation_id
- Single invocation cannot be split across workers

**Solving Multiple Processes**:
- Capability is bound to specific authorized_consumer_pid
- Only that PID can consume the capability
- Other processes cannot consume even if they have the capability

**Solving Restart**:
- Consumption registry is persistent
- On restart, reload consumption state
- Already-consumed capabilities remain consumed

**Local Dict is NOT Sufficient**:
- Local dict is not interprocess visible
- Local dict is not durable across restart
- Local dict does not provide atomicity
- Local dict cannot prevent replay across processes

---

## H. Persistence Contract

**Definition**:

SelfAuditSnapshot can be persisted as **TRUSTED_EVIDENCE** only when all trust conditions are met.

**TRUSTED_EVIDENCE Requirements**:

**Required**:

1. **Validated Invocation**:
   - Capability was verified by CapabilityVerifier
   - Capability was consumed atomically
   - Verification succeeded (not rejected)

2. **Authorized Consumer**:
   - Consumer PID matches capability's authorized_consumer_pid
   - Consumer is child of issuer (lineage verified)
   - OS confirms consumer PID is valid

3. **Trusted Identity**:
   - Identity is bound to the capability
   - Identity signature is valid
   - Identity is not forged

4. **Accepted Scope**:
   - Execution scope matches capability scope
   - No scope escalation occurred
   - Execution stayed within authorized boundaries

5. **Non-Replayed Invocation**:
   - invocation_id is unique
   - Capability was not previously consumed
   - No replay occurred

**If Any Condition Fails**:
- Do NOT persist as TRUSTED_EVIDENCE
- May persist as UNVERIFIED_EVIDENCE (with clear label)
- Must distinguish between trusted and unverified

**Persistence Labels**:

**TRUSTED_EVIDENCE**:
- All 5 conditions met
- Can be used for learning
- Can be used for provenance
- Can be used for audit

**UNVERIFIED_EVIDENCE**:
- At least 1 condition failed
- Can be used for debugging
- Can be used for forensics
- CANNOT be used for learning
- CANNOT be used for provenance

**FORGED_EVIDENCE**:
- Caller attempted to inject unverified identity
- Capability verification failed
- Must be rejected, not persisted

---

## I. Existing Architecture Reuse

**Locating Components**:

**bootstrap**:
- **Current Role**: Application startup
- **Reuse**: Capability issuer initialization
- **Authority**: Can be the ISSUER for child processes

**MCP server**:
- **Current Role**: Model Context Protocol server
- **Reuse**: IPC trust boundary
- **Authority**: Can be the VERIFIER for capabilities

**dispatcher**:
- **Current Role**: Task dispatching
- **Reuse**: Scope enforcement
- **Authority**: Can enforce capability scope

**RunRecord**:
- **Current Role**: Execution record tracking
- **Reuse**: Invocation context tracking
- **Authority**: Can store validated invocation context

**AdaptiveSession**:
- **Current Role**: Session management
- **Reuse**: Session-scoped capability issuance
- **Authority**: Can issue session-scoped capabilities

**SelfAuditService**:
- **Current Role**: Self-auditing
- **Reuse**: TRUSTED_EVIDENCE persistence
- **Authority**: Can persist only verified invocations

**lease infrastructure**:
- **Current Role**: Lease management
- **Reuse**: Capability registry
- **Authority**: Can be extended for single-use enforcement

**TaskOutcomeRecorder**:
- **Current Role**: Task outcome recording
- **Reuse**: Scope validation
- **Authority**: Can verify execution stayed within scope

**ExperimentLab**:
- **Current Role**: Experiment management
- **Reuse**: Learning provenance
- **Authority**: Can consume only TRUSTED_EVIDENCE

**Where Capability Layer Lives**:

**OPTION A**: Extend existing lease infrastructure
- **Pros**: Reuses existing registry, minimal changes
- **Cons**: Lease semantics may not match capability semantics
- **Verdict**: Possible, but requires careful semantic alignment

**OPTION B**: Small InvocationCapability layer
- **Pros**: Clear separation, minimal scope
- **Cons**: New component, integration points
- **Verdict**: Preferred for clarity and minimal scope

**OPTION C**: Integrate into SelfAuditService
- **Pros**: Centralized verification
- **Cons**: Blurs concerns, SelfAudit should only persist
- **Verdict**: Not recommended (separation of concerns)

**OPTION D**: Integrate into IPC trust boundary
- **Pros**: Natural verification point
- **Cons**: IPC should be transport, not authority
- **Verdict**: Not recommended (separation of concerns)

**Recommended**: OPTION B - Small InvocationCapability layer
- Minimal scope
- Clear separation of concerns
- Can integrate with existing components
- Can leverage existing lease infrastructure for registry

---

## J. Threat Model

**Threat Analysis**:

**same-user sibling**:
- **Threat**: Sibling process connects to pipe, spoofs authorized consumer
- **Existing Protection**: DACL (same-user allows siblings)
- **Required Protection**: Capability binding (sibling cannot consume capability issued to other sibling)
- **Gap**: V4 DACL allows siblings, V5 capability binding prevents sibling consumption
- **Status**: CLOSED by capability binding

**wrong child**:
- **Threat**: Wrong child process attempts to consume capability
- **Existing Protection**: ppid() verification
- **Required Protection**: Capability binding (wrong child PID doesn't match authorized_consumer_pid)
- **Gap**: V4 ppid() only, V5 adds capability binding
- **Status**: CLOSED by capability binding + ppid()

**wrong parent**:
- **Threat**: Process claims to be child of wrong parent
- **Existing Protection**: ppid() verification
- **Required Protection**: OS identity verification (OS confirms actual ppid)
- **Gap**: V4 ppid() only, V5 adds OS identity verification
- **Status**: CLOSED by OS identity verification

**forged PID**:
- **Threat**: Process forges PID in capability or IPC message
- **Existing Protection**: None (caller-provided PID)
- **Required Protection**: OS-observed PID (GetNamedPipeClientProcessId)
- **Gap**: V4 caller-provided PID, V5 OS-observed PID
- **Status**: CLOSED by OS-observed PID

**forged identity**:
- **Threat**: Process forges identity signature
- **Existing Protection**: Signature verification
- **Required Protection**: Capability binding (identity must be bound to capability)
- **Gap**: V4 signature only, V5 adds capability binding
- **Status**: CLOSED by capability binding

**forged capability**:
- **Threat**: Process forges capability signature
- **Existing Protection**: Signature verification
- **Required Protection**: Cryptographic binding to issuer
- **Gap**: V4 signature only, V5 adds issuer binding
- **Status**: CLOSED by issuer binding

**stale capability**:
- **Threat**: Process uses expired capability
- **Existing Protection**: Expiry check
- **Required Protection**: Temporal validation (issued_at, expires_at)
- **Gap**: V4 expiry only, V5 adds runtime_incarnation
- **Status**: CLOSED by temporal validation + runtime_incarnation

**replay**:
- **Threat**: Process reuses same capability multiple times
- **Existing Protection**: None (local dict not interprocess atomic)
- **Required Protection**: Interprocess-atomic single-use enforcement
- **Gap**: V4 local dict, V5 interprocess registry
- **Status**: CLOSED by interprocess registry

**cross-run**:
- **Threat**: Process uses capability from previous runtime
- **Existing Protection**: None
- **Required Protection**: Runtime incarnation binding
- **Gap**: V4 none, V5 runtime_incarnation
- **Status**: CLOSED by runtime_incarnation

**cross-session**:
- **Threat**: Process uses capability from previous session
- **Existing Protection**: None
- **Required Protection**: Session binding
- **Gap**: V4 none, V5 session_id
- **Status**: CLOSED by session_id

**cross-generation**:
- **Threat**: Process uses capability from previous generation
- **Existing Protection**: None
- **Required Protection**: Generation binding
- **Gap**: V4 none, V5 issuer_generation
- **Status**: CLOSED by generation binding

**unauthorized pipe connection**:
- **Threat**: Unrelated process connects to pipe
- **Existing Protection**: DACL
- **Required Protection**: Capability binding (unrelated process cannot consume capability)
- **Gap**: V4 DACL only, V5 adds capability binding
- **Status**: CLOSED by capability binding

**SelfAudit direct call**:
- **Threat**: Caller directly calls SelfAudit with forged identity
- **Existing Protection**: Optional identity_authority
- **Required Protection**: Mandatory validated invocation context
- **Gap**: V4 optional, V5 mandatory
- **Status**: CLOSED by mandatory verification

**direct persistence injection**:
- **Threat**: Caller injects unverified identity into persistence
- **Existing Protection**: None (identity_authority=None allows this)
- **Required Protection**: Mandatory verification before persistence
- **Gap**: V4 optional, V5 mandatory
- **Status**: CLOSED by mandatory verification

**Summary**:
- All 13 threats addressed
- V4 had partial protection for some threats
- V5 adds capability binding as primary authority
- V5 adds interprocess atomicity for single-use
- V5 adds mandatory verification for SelfAudit

---

## K. Minimality Analysis

**OPTION A: Reuse existing runtime capability**

**Approach**: Extend existing lease infrastructure to handle invocation authorization

**Pros**:
- Reuses existing LeaseIssuer, LeaseRegistry
- Minimal new code
- Leverages existing persistence

**Cons**:
- Lease semantics (time-bound resource) ≠ capability semantics (single-use authorization)
- Lease doesn't enforce consumer binding
- Lease doesn't have interprocess atomicity
- Would require significant lease semantic changes

**Complexity**: Medium (semantic alignment challenges)
**New Components**: 0 (extend existing)
**Risk**: Medium (semantic mismatch)

**Verdict**: NOT RECOMMENDED (semantic mismatch)

---

**OPTION B: Small InvocationCapability layer**

**Approach**: Create minimal InvocationCapability component with clear semantics

**Pros**:
- Clear separation of concerns
- Minimal scope (only capability issuance/verification)
- Can integrate with existing lease infrastructure for registry
- Semantics match authorization requirements
- Easy to test in isolation

**Cons**:
- New component (small, ~500 lines)
- Integration points with existing components
- Requires interprocess registry

**Complexity**: Low (clear scope, minimal code)
**New Components**: 1 (InvocationCapability layer)
**Risk**: Low (minimal scope, clear semantics)

**Verdict**: RECOMMENDED (minimal scope, clear semantics)

---

**OPTION C: Extend existing lease authority**

**Approach**: Extend RuntimeIdentityAuthority to handle capabilities

**Pros**:
- Single authority for identity and capability
- Reuses existing trust anchor
- Minimal new components

**Cons**:
- Blurs identity authority with capability authority
- Identity ≠ authorization (semantic mismatch)
- Single authority becomes bottleneck
- Violates separation of concerns

**Complexity**: Medium (semantic confusion)
**New Components**: 0 (extend existing)
**Risk**: High (semantic mismatch, single point of failure)

**Verdict**: NOT RECOMMENDED (semantic mismatch, single authority)

---

**OPTION D: New dedicated authorization component**

**Approach**: Create comprehensive AuthorizationService

**Pros**:
- Complete separation of concerns
- Can handle all authorization scenarios
- Future-proof for complex authorization

**Cons**:
- Over-engineering for current requirements
- New large component (~2000 lines)
- Integration complexity
- Violates minimality principle

**Complexity**: High (large scope, many integration points)
**New Components**: 1 (large component)
**Risk**: High (over-engineering, complexity)

**Verdict**: NOT RECOMMENDED (over-engineering)

---

**MINIMALITY VERDICT**: OPTION B

**Justification**:
- Minimal scope (only capability issuance/verification)
- Clear semantics (authorization, not identity)
- Can reuse existing lease infrastructure for registry
- Easy to test in isolation
- Low complexity, low risk
- No over-engineering

**Implementation Size**: ~500 lines
**Integration Points**: 3 (bootstrap, IPC, SelfAudit)
**New Components**: 1 (InvocationCapability layer)

---

## L. V4 Lessons

**Documented Lessons**:

**frozen object != authority**:
- **V4 Assumption**: Frozen dataclass with signature = authority
- **V5 Reality**: Frozen object can be forged if not bound to issuer
- **Lesson**: Authority requires cryptographic binding to trusted issuer, not just immutability

**signature != authorization**:
- **V4 Assumption**: Valid signature = authorized
- **V5 Reality**: Signature proves integrity, not authorization to consume
- **Lesson**: Authorization requires explicit capability binding, not just signature verification

**lineage != identity**:
- **V4 Assumption**: Parent-child relationship = identity
- **V5 Reality**: Lineage proves relationship, not authorized identity
- **Lesson**: Identity requires explicit capability binding, lineage is necessary but not sufficient

**PID field != OS identity**:
- **V4 Assumption**: PID field in object = OS process identity
- **V5 Reality**: PID field can be forged, must verify with OS
- **Lesson**: OS-observed identity (GetNamedPipeClientProcessId) required, caller-provided PID insufficient

**DACL != capability authorization**:
- **V4 Assumption**: DACL on pipe = authorization
- **V5 Reality**: DACL provides access control, not capability authorization
- **Lesson**: Capability binding required, DACL is first line of defense not sufficient

**local registry != interprocess atomicity**:
- **V4 Assumption**: Local dict registry = single-use enforcement
- **V5 Reality**: Local dict not visible across processes, not atomic
- **Lesson**: Interprocess synchronization required for single-use enforcement

**mock != runtime evidence**:
- **V4 Assumption**: Mocked tests = runtime proof
- **V5 Reality**: Mocks don't prove real runtime behavior
- **Lesson**: Real runtime proof requires real processes, real IPC, real OS calls

**optional authority != fail-closed trust boundary**:
- **V4 Assumption**: Optional identity_authority = backward compatible
- **V5 Reality**: Optional authority creates fail-open path
- **Lesson**: Trust boundaries must be fail-closed, mandatory verification required

**consumer_pid != authorized consumer**:
- **V4 Assumption**: consumer_pid field = authorized consumer
- **V5 Reality**: consumer_pid field can be forged, requires capability binding
- **Lesson**: Authorized consumer requires explicit capability, not just field

**ppid() != authorization**:
- **V4 Assumption**: ppid() verification = authorization
- **V5 Reality**: ppid() proves lineage, not authorization
- **Lesson**: Authorization requires capability binding, lineage is necessary but not sufficient

---

## M. Future Implementation Contract

**Contract Definition**:

**TRUST_ANCHOR**:
- **Component**: RootTrustAnchor (existing)
- **Role**: Bootstrap trust root
- **Authority**: Establish runtime identity generation
- **Contract**: Initialize at bootstrap, single runtime incarnation

**AUTHORITY**:
- **Component**: RuntimeIdentityAuthority (existing)
- **Role**: Issue and verify execution identities
- **Authority**: Bind identity to runtime incarnation
- **Contract**: Identity authority only, NOT capability authority

**ISSUER**:
- **Component**: CapabilityIssuer (new, part of InvocationCapability layer)
- **Role**: Issue invocation capabilities
- **Authority**: Bind capability to authorized consumer
- **Contract**: Issue only to child processes, single-use semantics

**CONSUMER**:
- **Component**: Authorized Process (existing child processes)
- **Role**: Consume invocation capability
- **Authority**: Execute within authorized scope
- **Contract**: Consume only capabilities issued to this PID

**CAPABILITY**:
- **Component**: InvocationCapability (new dataclass)
- **Role**: Authorization token
- **Authority**: Cryptographically bound to issuer and consumer
- **Contract**: Minimal fields, signature binding, single-use semantics

**VERIFIER**:
- **Component**: CapabilityVerifier (new, part of InvocationCapability layer)
- **Role**: Verify and consume capabilities
- **Authority**: Validate capability integrity and binding
- **Contract**: Interprocess atomic verification, fail-closed

**IPC_AUTHENTICATION**:
- **Component**: IpcTrustBoundary (existing, extended)
- **Role**: OS-observed client identity
- **Authority**: Verify client PID and lineage
- **Contract**: GetNamedPipeClientProcessId, ppid() verification

**SINGLE_USE**:
- **Component**: CapabilityRegistry (new, interprocess-atomic)
- **Role**: Track consumed capabilities
- **Authority**: Enforce single-use across processes
- **Contract**: File-based registry with file locks, persistent state

**STALE_INVALIDATION**:
- **Component**: CapabilityVerifier (temporal validation)
- **Role**: Invalidate stale capabilities
- **Authority**: Check expiry, runtime_incarnation, session_id
- **Contract**: Reject expired, cross-run, cross-session capabilities

**SELFAUDIT_ENTRY**:
- **Component**: SelfAuditService (existing, modified)
- **Role**: Persist TRUSTED_EVIDENCE
- **Authority**: Accept only validated invocation context
- **Contract**: Mandatory verification, reject unverified identity

**PERSISTENCE_ENTRY**:
- **Component**: SelfAuditSnapshot (existing, modified)
- **Role**: Distinguish TRUSTED_EVIDENCE from UNVERIFIED_EVIDENCE
- **Authority**: Label evidence based on verification status
- **Contract**: Clear labeling, no mixing of trusted/unverified

---

## N. P0.20 Evidence

**Inconsistency**:

**Claim**: 81 tests passing
**Sum**: 83 tests (19 + 23 + 29 + 12)
**Discrepancy**: 2 tests unaccounted

**Root Cause**:
- Test count discrepancy not investigated
- Evidence not reproducible
- No clear accounting of which tests failed

**V5 Treatment**:

**P020_EVIDENCE_UNVERIFIED**:
- Do not claim P0.20 regression verified
- Do not claim 81 tests passing
- Document discrepancy as UNVERIFIED
- Require reproducible test suite before claiming verification

**Required Action**:
- Run reproducible test suite
- Document exact test count
- Document any failures
- Only then claim P0.20 regression verified

**Contract**:
- Do not modify P0.20 code
- Do not fix P0.20 tests
- Only document evidence inconsistency
- Leave resolution for separate task

---

## O. FINAL VERDICT

**P0_213_AUTHORITY_CONTRACT_READY**

**Justification**:

1. **Unique Definition**: Single, coherent definition of invocation authority established
2. **Authority Separation**: Clear separation between identity authority and capability authority
3. **Consumer Authorization**: Distinction between lineage and authorization defined
4. **IPC Contract**: Complete chain from OS-observed identity to invocation acceptance defined
5. **SelfAudit Contract**: Mandatory verification, no fail-open paths defined
6. **Single-Use Contract**: Interprocess atomicity requirements defined
7. **Persistence Contract**: TRUSTED_EVIDENCE requirements defined
8. **Minimality**: OPTION B (small InvocationCapability layer) selected as minimal solution
9. **Threat Model**: All 13 threats addressed with specific protections
10. **V4 Lessons**: 10 lessons documented to prevent repeat mistakes

**No Human Decision Required**:
- Contract is complete and coherent
- Minimality analysis has clear recommendation
- Threat model has clear protections
- No trade-offs requiring human judgment

**No Blocking Evidence**:
- All required concepts defined
- All gaps identified and addressed
- Implementation contract is complete

---

## P. NEXT_SINGLE_ACTION

**P0_213_V5_ARCHITECTURE_DEFINITION_COMPLETE**

The invocation authority contract is now defined. The next step is to review this contract with the user to confirm alignment with requirements before proceeding to V5 implementation.

**Expected Learning**:
- User confirms or rejects the contract
- User identifies any missing requirements
- User approves minimality analysis
- User approves threat model

**Risk**: LOW (architecture definition only, no code changes)

**BLOCKER**: None (contract is complete)

**NEXT_SINGLE_ACTION**: USER_REVIEW_INVOCATION_AUTHORITY_CONTRACT
