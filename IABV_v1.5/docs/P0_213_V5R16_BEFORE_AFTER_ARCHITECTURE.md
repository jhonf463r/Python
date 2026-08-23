# P0.213 V5 PHASE 3 — ROUND 16 BEFORE/AFTER ARCHITECTURE

**Document Date**: 2026-08-22  
**Document Type**: Architecture Comparison  
**Purpose**: Visualize current vs target architecture for remediation

---

## SECTION A — AUTHORIZATION FLOW (R16B-1)

### CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    UNTRUSTED CALLER                          │
│  (any process, any Windows user, no verification)            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ REQUEST_JOIN(subject_id, public_key)
                            │ [caller-controlled, no validation]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension.handle_request_join        │
│  - Receives request_data                                     │
│  - Receives client_pid (metadata only, never validated)      │
│  - Parses RequestJoinRequest                                  │
│  - NO authentication check                                    │
│  - NO AuthorizationSubject validation                         │
│  - NO subject → public key binding validation                │
│  - NO parent authority verification                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Direct insertion
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              phase3_join_state.db (SQLite)                    │
│  - join_tokens table                                         │
│  - subject_id: [caller-controlled, no validation]            │
│  - public_key: [caller-controlled, no validation]            │
│  - generation: [independent source, not canonical]            │
└─────────────────────────────────────────────────────────────┘

SECURITY GAP: No authentication boundary between untrusted caller and authorization logic
```

### TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    UNTRUSTED CALLER                          │
│  (any process, any Windows user)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ REQUEST_JOIN(subject_id, public_key)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              [NEW] Authentication Layer                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. OS Identity Verification                            │  │
│  │    - Get process token for client_pid                  │  │
│  │    - Verify token is valid                              │  │
│  │    - Extract Windows SID                                │  │
│  │    - Verify SID is authorized user                       │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 2. AuthorizationSubject Validation                      │  │
│  │    - Lookup subject in authorized_subjects table         │  │
│  │    - Verify subject.is_active == 1                      │  │
│  │    - Verify subject.windows_sid == caller_sid           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 3. Subject → Public Key Binding Validation             │  │
│  │    - Parse subject.allowed_public_keys JSON array       │  │
│  │    - Verify public_key is in allowed list               │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 4. Parent Authority Verification                       │  │
│  │    - Get parent PID of client_pid                      │  │
│  │    - Verify parent matches expected authority          │  │
│  │    - Verify parent is authorized Authority process      │  │
│  └───────────────────────────────────────────────────────┘  │
│  IF ANY CHECK FAILS → REJECT REQUEST                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Authorized request
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension.handle_request_join        │
│  - Receives pre-authenticated request                        │
│  - subject_id: [validated against registry]                  │
│  - public_key: [validated against allowed list]              │
│  - caller: [OS-verified Windows SID]                         │
│  - parent: [verified authorized Authority]                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Authorized insertion
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              phase3_join_state.db (SQLite)                    │
│  - join_tokens table                                         │
│  - subject_id: [validated, authorized]                        │
│  - public_key: [validated, authorized]                       │
│  - generation: [canonical source]                            │
└─────────────────────────────────────────────────────────────┘

SECURITY BOUNDARY: Authentication layer enforces caller identity and authorization
```

---

## SECTION B — GENERATION AUTHORITY (R16B-3)

### CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│              run_records (SQLite)                            │
│  - generation: [CANONICAL per Round 15 design]              │
│  - child_authorization_state                                 │
│  - pinned_public_key                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ [NOT READ BY PHASE 3]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension.__init__                   │
│  - Accepts generation parameter                              │
│  - Stores in self._generation [INDEPENDENT SOURCE]           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ [INDEPENDENT SOURCE]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension Methods                    │
│  - handle_request_join: uses self._generation                │
│  - handle_request_challenge: uses self._generation           │
│  - handle_redeem_join: uses self._generation                │
└─────────────────────────────────────────────────────────────┘

DIVERGENCE: Two independent generation sources (run_records vs _generation)
```

### TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│              run_records (SQLite)                            │
│  - generation: [SINGLE CANONICAL SOURCE]                    │
│  - child_authorization_state                                 │
│  - pinned_public_key                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ [READ BY PHASE 3]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension.__init__                   │
│  - Accepts db_connection (to run_records)                    │
│  - NO generation parameter                                  │
│  - NO self._generation field                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ [READS CANONICAL]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension._get_current_generation   │
│  - Reads from run_records.generation                         │
│  - Returns canonical generation value                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ [CANONICAL SOURCE]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase3AuthorityExtension Methods                    │
│  - handle_request_join: calls _get_current_generation        │
│  - handle_request_challenge: calls _get_current_generation   │
│  - handle_redeem_join: calls _get_current_generation        │
└─────────────────────────────────────────────────────────────┘

UNIFICATION: Single canonical source (run_records.generation)
```

---

## SECTION C — HANDLE INHERITANCE (R16B-2)

### CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│              Parent Process                                  │
│  - stdin read handle [inheritable]                          │
│  - stdout handle [inheritable]                               │
│  - stderr handle [inheritable]                               │
│  - unrelated handle A [inheritable]                          │
│  - unrelated handle B [inheritable]                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ CreateProcess with bInheritHandles=TRUE
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Child Process                                   │
│  - stdin read handle [INHERITED]                             │
│  - stdout handle [INHERITED]                                 │
│  - stderr handle [INHERITED]                                 │
│  - unrelated handle A [INHERITED] ← SECURITY GAP             │
│  - unrelated handle B [INHERITED] ← SECURITY GAP             │
└─────────────────────────────────────────────────────────────┘

SECURITY GAP: Global inheritance allows all inheritable handles to be inherited
```

### TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│              Parent Process                                  │
│  - stdin read handle [inheritable]                          │
│  - stdout handle [inheritable]                               │
│  - stderr handle [inheritable]                               │
│  - unrelated handle A [inheritable]                          │
│  - unrelated handle B [inheritable]                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ CreateProcess with STARTUPINFOEX
                            │ + PROC_THREAD_ATTRIBUTE_HANDLE_LIST
                            │ Handle List: [stdin read handle only]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Child Process                                   │
│  - stdin read handle [INHERITED]                             │
│  - stdout handle [NOT INHERITED]                             │
│  - stderr handle [NOT INHERITED]                             │
│  - unrelated handle A [NOT INHERITED] ← FIXED                │
│  - unrelated handle B [NOT INHERITED] ← FIXED                │
└─────────────────────────────────────────────────────────────┘

SECURITY FIX: Explicit handle list restricts inheritance to only stdin
```

---

## SECTION D — REVOCATION FLOW (ROUND 15 COMPLIANCE)

### CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│              Preparation Failure                              │
│  - child creation fails                                      │
│  - runtime error occurs                                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ [NO REVOCATION LOGIC]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Stale State                                     │
│  - capability N remains PENDING/CONSUMED                     │
│  - pinned_public_key N remains                              │
│  - generation N remains                                     │
│  - No way to recover                                        │
└─────────────────────────────────────────────────────────────┘

GAP: No atomic revocation on failure
```

### TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│              Preparation Failure                              │
│  - child creation fails                                      │
│  - runtime error occurs                                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ revoke_failed_preparation()
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Atomic Recovery Transaction                     │
│  BEGIN IMMEDIATE                                            │
│  1. REVOKE all capabilities for generation N                 │
│  2. REVOKE all join tokens for generation N                 │
│  3. ATOMIC generation advance (N → N+1)                     │
│  4. SET state to REQUIRES_NEW_AUTHORIZATION                 │
│  5. CLEAR pinned_public_key                                  │
│  COMMIT                                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Clean State (Generation N+1)                    │
│  - capability N REVOKED                                      │
│  - pinned_public_key NULL                                   │
│  - generation N+1                                           │
│  - state: REQUIRES_NEW_AUTHORIZATION                        │
│  - Ready for new capability                                  │
└─────────────────────────────────────────────────────────────┘

FIX: Atomic revocation enables recovery from failures
```

---

## SECTION E — COMPLETE AUTHORIZATION CHAIN

### CURRENT ARCHITECTURE

```
Untrusted Caller
    ↓ [NO AUTHENTICATION]
Phase3AuthorityExtension
    ↓ [INDEPENDENT GENERATION]
phase3_join_state.db
    ↓ [GLOBAL HANDLE INHERITANCE]
Child Process
    ↓ [NO REVOCATION]
Execution
```

**Security Properties**:
- ❌ No caller authentication
- ❌ No AuthorizationSubject validation
- ❌ Divergent generation sources
- ❌ Unrestricted handle inheritance
- ❌ No failure revocation

### TARGET ARCHITECTURE

```
Untrusted Caller
    ↓ [OS IDENTITY VERIFICATION]
Authentication Layer
    ↓ [SUBJECT VALIDATION]
AuthorizationSubject Registry
    ↓ [KEY BINDING VALIDATION]
Phase3AuthorityExtension
    ↓ [CANONICAL GENERATION]
run_records.generation
    ↓ [EXPLICIT HANDLE LIST]
Child Process
    ↓ [ATOMIC REVOCATION]
Execution
```

**Security Properties**:
- ✅ OS identity verified
- ✅ AuthorizationSubject validated
- ✅ Subject → key binding enforced
- ✅ Single canonical generation source
- ✅ Explicit handle inheritance
- ✅ Atomic failure revocation

---

## SECTION F — DATA FLOW COMPARISON

### REQUEST_JOIN Flow

#### CURRENT
```
Caller → RequestJoinRequest(subject_id, public_key)
         ↓ [NO VALIDATION]
         Phase3AuthorityExtension.handle_request_join
         ↓ [DIRECT INSERT]
         phase3_join_state.db
```

#### TARGET
```
Caller → RequestJoinRequest(subject_id, public_key)
         ↓ [OS IDENTITY CHECK]
         Authentication Layer.verify_caller_identity
         ↓ [SUBJECT REGISTRY CHECK]
         Authentication Layer.validate_subject_key_binding
         ↓ [PARENT AUTHORITY CHECK]
         Authentication Layer.verify_parent_authority
         ↓ [AUTHORIZED]
         Phase3AuthorityExtension.handle_request_join
         ↓ [CANONICAL GENERATION]
         run_records.generation
         ↓ [AUTHORIZED INSERT]
         phase3_join_state.db
```

### GENERATION READ Flow

#### CURRENT
```
Phase3AuthorityExtension._generation [INDEPENDENT]
         ↓
         Authorization decisions
```

#### TARGET
```
run_records.generation [CANONICAL]
         ↓
         Phase3AuthorityExtension._get_current_generation
         ↓
         Authorization decisions
```

### CHILD SPAWN Flow

#### CURRENT
```
Parent → CreateProcess(bInheritHandles=TRUE)
         ↓ [GLOBAL INHERITANCE]
         Child inherits ALL inheritable handles
```

#### TARGET
```
Parent → CreateProcess(STARTUPINFOEX)
         ↓ [EXPLICIT HANDLE LIST]
         Child inherits ONLY stdin read handle
```

---

## SECTION G — COMPONENT INVENTORY

### NEW COMPONENTS

1. **AuthenticationLayer**
   - verify_caller_identity()
   - validate_subject_key_binding()
   - verify_parent_authority()

2. **authorized_subjects Table**
   - subject_id
   - windows_sid
   - allowed_public_keys (JSON)
   - parent_authority
   - created_at
   - revoked_at
   - is_active

### MODIFIED COMPONENTS

1. **Phase3AuthorityExtension**
   - Remove: generation parameter
   - Remove: _generation field
   - Add: db_connection parameter
   - Add: _get_current_generation() method
   - Add: _auth_layer integration
   - Modify: All methods to use canonical generation

2. **child_spawn.py**
   - Replace: STARTUPINFO → STARTUPINFOEX
   - Add: PROC_THREAD_ATTRIBUTE_HANDLE_LIST
   - Add: Explicit handle list
   - Add: Attribute list cleanup

### UNCHANGED COMPONENTS

1. **phase3_protocol.py** (dataclasses remain)
2. **ed25519_keys.py** (crypto functions remain)
3. **credential_transport.py** (pipe logic remains)
4. **process_security.py** (security descriptor remains)

---

## SECTION H — SECURITY BOUNDARY SUMMARY

### CURRENT BOUNDARIES

```
[NO BOUNDARY] Untrusted Caller → Phase3AuthorityExtension
[NO BOUNDARY] Independent Generation → Canonical Generation
[NO BOUNDARY] Global Handle Inheritance → Child
[NO BOUNDARY] Failure → Revocation
```

### TARGET BOUNDARIES

```
[BOUNDARY] Untrusted Caller → Authentication Layer
[BOUNDARY] Authentication Layer → Phase3AuthorityExtension
[BOUNDARY] Canonical Generation → Authorization Decisions
[BOUNDARY] Explicit Handle List → Child
[BOUNDARY] Failure → Atomic Revocation
```

---

## FINAL ARCHITECTURE VERDICT

**P0_213_V5R16_BEFORE_AFTER_ARCHITECTURE_COMPLETE**

This document visualizes the exact architectural changes required to remediate all 4 findings:
- R16B-1: Add authentication boundary
- R16B-2: Implement explicit handle list
- R16B-3: Unify generation authority
- R16B-4: Correct bundle integrity

Implementation may proceed after this architecture is approved.
