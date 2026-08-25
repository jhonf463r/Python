# C2 Capability Provenance Document

**Date:** 2026-08-24  
**Component:** P0.213 Authority System - C2 Self-Update Production Integration  
**Status:** IN PROGRESS

---

## Executive Summary

This document traces the provenance of execution context and capability identifiers (execution_id, lease_id) through the production self-update tool chain.

**Current State:** Placeholder IDs used for testing  
**Required State:** Genuine IDs from authority process  
**Blocker:** No mechanism to pass execution context to MCP tool invocations

---

## Real Execution Context Source

**File:** `src/iabv_v15/services/trust/trusted_execution_identity.py`

**Data Contract:** `CanonicalRunRecord`
```python
@dataclass(frozen=True)
class CanonicalRunRecord:
    run_id: str
    execution_id: str
    episode_id: Optional[str]
    session_id: Optional[str]
    invocation_id: str
    requested_scope: str
    authorized_scope: str
    action: str
    target: str
    consumer_pid: int
    generation: int
    created_at: float
```

**Source:** Authority Process (Phase 2)  
**Acquisition:** `AuthorityClient.register_execution()`

---

## Real Capability Source

**File:** `src/iabv_v15/services/trust/capability_lifecycle.py`

**Function:** `acquire_capability_for_execution()`

**Protocol:**
```python
def acquire_capability_for_execution(
    *,
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    client = AuthorityClient()
    client.connect()
    
    # REGISTER_EXECUTION
    registration = client.register_execution(
        invocation_id=invocation_id,
        action=action,
        target=target,
        requested_scope=requested_scope,
        task_context="tool_execution",
        episode_id=episode_id,
        session_id=session_id
    )
    
    run_id = registration["run_id"]
    execution_id = registration["execution_id"]
    
    # ISSUE_LEASE
    lease = client.issue_lease(
        run_id=run_id,
        execution_id=execution_id,
        requested_ttl_seconds=3600
    )
    
    lease_id = lease["lease_id"]
    
    return {
        "run_id": run_id,
        "execution_id": execution_id,
        "lease_id": lease_id,
        "action": action,
        "target": target,
        "authorized_scope": authorized_scope
    }
```

**Returns:** run_id, execution_id, lease_id from authority process

---

## Lease Data Contract

**File:** `src/iabv_v15/services/trust/trusted_lease.py`

**Data Contract:** `TrustedLease`
```python
@dataclass(frozen=True)
class TrustedLease:
    # Issuer (authority-owned, NOT caller-controlled)
    issuer_pid: int
    issuer_generation: int
    
    # Identity binding (authority-owned)
    execution_id: str
    invocation_id: str
    
    # Unique lease ID (authority-generated, NOT caller-controlled)
    lease_id: str
    
    # Process binding (authority-owned, NOT caller-controlled)
    producer_pid: int
    
    # Authorization (authority-owned, NOT caller-controlled)
    producer_scope: str
    authorization_context: Optional[str]
    
    # Lifecycle (authority-owned)
    issued_at: float
    expires_at: float
    
    # Cryptographic proof (Phase 2: HMAC signature)
    signature: str
    
    # Consumption flag (has default)
    consumed: bool = False
```

---

## MCP Server Registration

**File:** `src/iabv_v15/infra/mcp/server.py`

**Registration Point:** Line 3178-3185
```python
# Register self-update (write) tools for autonomous self-modification
try:
    from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools
    _n_write_tools = register_self_update_tools(
        mcp=self.mcp,
        workspace_root_fn=self._workspace_root,
        governance_fn=self._governance_block_for_route,
        to_jsonable_fn=_to_jsonable,
        capability_action_bridge=self.capability_action_bridge,  # C-2: Pass canonical authority
    )
    logger.info("self_update_tools: %d write tools registered", _n_write_tools)
except Exception as _sut_exc:
    logger.warning("self_update_tools: failed to register: %s", _sut_exc)
```

**Passed Components:**
- `capability_action_bridge`: Authority bridge for authorization
- `governance_fn`: Governance blocking function
- `workspace_root_fn`: Workspace root function

**Missing Components:**
- ❌ execution_id context
- ❌ lease_id context
- ❌ capability acquisition mechanism

---

## Bootstrap Authority Wiring

**File:** `src/iabv_v15/bootstrap.py`

**Wiring Point:** Line 790-828
```python
# F14: Authority integration - wire authority components
self.authority_client = None
self.capability_action_bridge = None
self.post_action_observer = None

try:
    # Attempt to connect to authority process
    self.authority_client = AuthorityClient()
    self.capability_action_bridge = CapabilityActionBridge(self.authority_client)
    self.post_action_observer = PostActionObserver(self.tool_memory)
    logger.info("F14: Authority components wired successfully")
except Exception as e:
    logger.warning(f"F14: Authority components not available: {e}")
```

**Available in Bootstrap:**
- `authority_client`: AuthorityClient instance
- `capability_action_bridge`: CapabilityActionBridge instance
- `post_action_observer`: PostActionObserver instance

---

## Real Production Call Graph

**C2-1 FIX:** IABVMCPServer now stores capability_action_bridge from container

**File:** `src/iabv_v15/infra/mcp/server.py`

**Registration Point:** Line 131-132
```python
def __init__(self, container: Any, *, name: str = DEFAULT_SERVER_NAME, mcp: Any | None = None) -> None:
    self.container = container
    self.name = name
    # C2-1 FIX: Store capability_action_bridge from container for self-update tools
    self.capability_action_bridge = getattr(container, "capability_action_bridge", None)
```

**Self-Update Registration:** Line 3178-3195
```python
# Register self-update (write) tools for autonomous self-modification
# C2-1 FIX: Security-critical registration - log exact failure and do not silently continue
try:
    from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools
    _n_write_tools = register_self_update_tools(
        mcp=self.mcp,
        workspace_root_fn=self._workspace_root,
        governance_fn=self._governance_block_for_route,
        to_jsonable_fn=_to_jsonable,
        capability_action_bridge=self.capability_action_bridge,  # C-2: Pass canonical authority
    )
    logger.info("self_update_tools: %d write tools registered", _n_write_tools)
except Exception as _sut_exc:
    # C2-1 FIX: Log exact failure with full traceback for security-critical registration
    logger.error("self_update_tools: CRITICAL registration failure: %s", _sut_exc, exc_info=True)
    # C2-1 FIX: Re-raise to make registration failure observable
    raise RuntimeError(f"Self-update tool registration failed: {_sut_exc}") from _sut_exc
```

**C2-2 FIX:** MCP wrappers acquire capability on each invocation

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**MCP Tool Wrapper (write_repo_file):** Line 369-401
```python
# C2 PRODUCTION INTEGRATION: Acquire capability from authority
lease_id = None
execution_id = None

if capability_action_bridge:
    try:
        from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_execution
        capability = acquire_capability_for_execution(
            action='WRITE_REPOSITORY_FILE',
            target=f'file:{relative_path}',
            requested_scope='self_update',
            invocation_id='write_repo_file',
        )
        lease_id = capability.get('lease_id')
        execution_id = capability.get('execution_id')
    except Exception as e:
        # Authority unavailable - FAIL CLOSED
        return {"status": "error", "detail": f"Authorization denied: capability acquisition failed: {e}"}
else:
    # Authority unavailable - FAIL CLOSED
    return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}

# C-2-CRIT-3: Thin wrapper calling tested implementation
return write_repo_file_impl(
    workspace_root=Path(workspace_root_fn()),
    relative_path=relative_path,
    content=content,
    create_dirs=create_dirs,
    governance_fn=governance_fn,
    capability_action_bridge=capability_action_bridge,
    lease_id=lease_id,  # Genuine ID from authority
    execution_id=execution_id,  # Genuine ID from authority
)
```

**Complete Production Flow:**
```
IABV Bootstrap
    ↓
AppBootstrap.__init__()
    ↓
AuthorityClient()
    ↓
CapabilityActionBridge(authority_client)
    ↓
container.capability_action_bridge
    ↓
IABVMCPServer(container)
    ↓
IABVMCPServer.__init__()
    ↓
self.capability_action_bridge = container.capability_action_bridge
    ↓
IABVMCPServer.run()
    ↓
register_self_update_tools(capability_action_bridge=self.capability_action_bridge)
    ↓
MCP tools registered (write_repo_file, apply_text_patch, git_commit_and_push)
    ↓
MCP tool invocation (e.g., write_repo_file)
    ↓
acquire_capability_for_execution(action, target, requested_scope)
    ↓
AuthorityClient.register_execution()
    ↓
AuthorityClient.issue_lease()
    ↓
genuine execution_id
    ↓
genuine lease_id
    ↓
write_repo_file_impl(lease_id, execution_id)
    ↓
ActionRequest(lease_id, execution_id, action, target, action_context)
    ↓
CapabilityActionBridge.authorize_action(action_request)
    ↓
AuthorityService.consume_lease()
    ↓
authorized
    ↓
actual self-update side effect
```

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Function Signature:**
```python
def register_self_update_tools(
    mcp: Any,
    workspace_root_fn: Callable[[], Path],
    governance_fn: Callable[..., Any] | None,
    to_jsonable_fn: Callable[[Any], Any],
    capability_action_bridge: Any,  # C-2: Pass canonical authority
) -> int:
```

**_impl Function Signature:**
```python
def write_repo_file_impl(
    workspace_root: Path,
    relative_path: str,
    content: str,
    create_dirs: bool = True,
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
    lease_id: str | None = None,  # REQUIRED for production
    execution_id: str | None = None,  # REQUIRED for production
) -> dict[str, Any]:
```

**MCP Tool Wrapper:**
```python
@mcp.tool()
def write_repo_file(
    relative_path: str,
    content: str,
    create_dirs: bool = True,
) -> dict[str, Any]:
    # C-2-CRIT-3: Thin wrapper calling tested implementation
    return write_repo_file_impl(
        workspace_root=Path(workspace_root_fn()),
        relative_path=relative_path,
        content=content,
        create_dirs=create_dirs,
        governance_fn=governance_fn,
        capability_action_bridge=capability_action_bridge,
        # ❌ MISSING: lease_id, execution_id
    )
```

---

## Critical Gap: Execution Context Propagation

**Problem:** MCP tools are registered once at server startup, but each tool invocation needs its own execution context (execution_id, lease_id).

**Current Architecture:**
```
Server Startup
    ↓
register_self_update_tools() (one-time)
    ↓
MCP tools registered with fixed capability_action_bridge
    ↓
Tool Invocation (many times)
    ↓
❌ No execution_id available
    ↓
❌ No lease_id available
    ↓
❌ Cannot construct valid ActionRequest
```

**Required Architecture:**
```
Server Startup
    ↓
register_self_update_tools() (one-time)
    ↓
MCP tools registered with context acquisition mechanism
    ↓
Tool Invocation (many times)
    ↓
✅ Acquire execution_id from current context
    ↓
✅ Acquire lease_id from authority
    ↓
✅ Construct valid ActionRequest
    ↓
✅ Authorize via CapabilityActionBridge
    ↓
✅ Execute self-update
```

---

## Proposed Solution: Context-Aware MCP Tools

**Option 1: Thread-Local Context**
- Store execution context in thread-local storage
- MCP tools read from thread-local context
- Requires context manager around tool execution

**Option 2: Capability Acquisition in Tool**
- Each MCP tool acquires capability on invocation
- Calls `acquire_capability_for_execution()` internally
- Requires action/target to be known before tool call

**Option 3: Context Parameter Injection**
- Modify MCP tool signature to accept context
- MCP framework injects context on each call
- Requires MCP framework changes

**Option 4: Capability Action Bridge Context**
- Store context in CapabilityActionBridge instance
- CapabilityActionBridge manages context lifecycle
- Requires CapabilityActionBridge modification

---

## Current Placeholder Usage

**Test Files:**
- `tests/test_c2_self_update_security.py`: Uses `'test_lease'`, `'test_execution'`
- `tests/controlled_authority_client.py`: Test-only authority client

**Production Files:**
- `src/iabv_v15/infra/mcp/self_update_tools.py`: MCP wrappers don't pass lease_id/execution_id
- `_impl` functions require lease_id/execution_id but receive None from MCP wrappers

**Placeholder Count in Production:**
- PRODUCTION_PLACEHOLDER_CAPABILITY_IDS = 0 (no hardcoded placeholders)
- MISSING_CAPABILITY_CONTEXT = 3 (MCP tools don't pass context)

---

## Required Production Integration

**Step 1: Choose Context Propagation Mechanism**
- Evaluate thread-local vs. capability acquisition vs. context injection
- Select mechanism compatible with MCP framework

**Step 2: Modify MCP Tool Registration**
- Add context acquisition to MCP tool wrappers
- Ensure each invocation gets fresh execution context

**Step 3: Integrate with Authority Lifecycle**
- Call `acquire_capability_for_execution()` in tool invocation
- Pass lease_id and execution_id to _impl functions

**Step 4: Remove Placeholder Dependencies**
- Ensure no test-only placeholders in production path
- Validate all production calls use genuine IDs

**Step 5: Create Real Integration Tests**
- Test with actual authority process
- Verify genuine capability acquisition
- Verify authorization with real IDs

---

## Status

**REAL_EXECUTION_CONTEXT_SOURCE:** AuthorityClient.register_execution()  
**REAL_CAPABILITY_SOURCE:** AuthorityClient.issue_lease()  
**REAL_LEASE_SOURCE:** Authority process (via AuthorityClient)  
**CONTEXT_PROPAGATION_MECHANISM:** ❌ NOT IMPLEMENTED  
**PRODUCTION_INTEGRATION:** ❌ INCOMPLETE

---

## Next Steps

1. Evaluate context propagation options
2. Implement chosen mechanism
3. Modify MCP tool wrappers
4. Create real integration tests
5. Validate production integration
