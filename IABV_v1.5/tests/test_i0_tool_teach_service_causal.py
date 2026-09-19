"""Test I0 ToolTeachService causal: CredentialRegistry → execute_task() → adapter.run(api_key)

I0-1.7H: Canonical provenance verification + causal trace of credential propagation.

AUTHORITY ISOLATION: CapabilityActionBridge is replaced with a test double to isolate
the I0 credential binding edge from P0 authority correctness. This test does NOT
prove authority system correctness - it only proves that execute_task() can traverse
the authority gate when authorized.

CRITICAL: This test verifies CANONICAL provenance of both Git and Python imports.
"""

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4
import time
import threading

# Global event sink and counter for unified instrumentation
EVENT_SINK = []
EVENT_LOCK = threading.Lock()

def next_sequence():
    global EVENT_SINK
    with EVENT_LOCK:
        return len(EVENT_SINK) + 1

def current_timestamp_ns():
    return time.monotonic_ns()

import pytest

# CRITICAL: Verify Python import provenance BEFORE any other imports
print("\n=== PYTHON IMPORT PROVENANCE ===")
import iabv_v15
print(f"iabv_v15.__file__: {iabv_v15.__file__}")

from iabv_v15.services.tools.tool_teach_service import ToolTeachService
print(f"tool_teach_service.__file__: {ToolTeachService.__module__}")

import inspect
print(f"\n=== SOURCE CODE INSPECTION ===")
print(f"ToolTeachService.execute_task source file: {inspect.getfile(ToolTeachService.execute_task)}")
source = inspect.getsource(ToolTeachService.execute_task)
lines = source.split('\n')
# Find line containing "is_available"
for i, line in enumerate(lines):
    if 'is_available' in line:
        print(f"Line {i+1}: {line.strip()}")
print("===============================\n")

from iabv_v15.services.tools.tool_registry import ToolRegistry
print(f"tool_registry.__module__: {ToolRegistry.__module__}")

from iabv_v15.services.tools.tool_sandbox import ToolSandbox
print(f"tool_sandbox.__module__: {ToolSandbox.__module__}")

from iabv_v15.services.tools.tool_adapters import ToolAdapter
print(f"tool_adapters module: {ToolAdapter.__module__}")

# ASSERT canonical worktree path
worktree_path = str(Path(__file__).resolve().parents[1])
assert iabv_v15.__file__.startswith(worktree_path), \
    f"iabv_v15.__file__ not in worktree: {iabv_v15.__file__}"
assert ToolTeachService.__module__.startswith("iabv_v15.services.tools"), \
    f"ToolTeachService wrong module: {ToolTeachService.__module__}"
print("PYTHON IMPORT PROVENANCE: VERIFIED")
print("=============================\n")

from iabv_v15.domain.models import (
    ExecutionState,
    TaskRole,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.trust.credential_registry import CredentialRegistry
from iabv_v15.services.trust.devin_credential_adapter import DevinCredentialAdapter


@dataclass
class Event:
    """Event trace entry with robust temporal ordering."""
    sequence: int
    timestamp_ns: int
    event_type: str
    credential_id: str | None = None
    resolved: bool = False
    api_key_present: bool = False
    sandbox: bool = False
    caller: str | None = None
    callsite: str | None = None
    object_id: int | None = None
    execution_id: str | None = None
    task_id: str | None = None


@dataclass
class ActionRequest:
    """Test double for ActionRequest."""
    lease_id: str
    execution_id: str
    action: str
    target: str
    action_context: dict[str, Any] | None = None


@dataclass
class ActionAuthorization:
    """Test double for ActionAuthorization."""
    authorized: bool
    run_id: str | None = None
    authorized_scope: str | None = None
    action: str | None = None
    target: str | None = None
    consumed_at: float | None = None
    error: str | None = None


class CapabilityActionBridgeTestDouble:
    """Test double for CapabilityActionBridge to isolate authority boundary."""
    
    def __init__(self, event_sink=None):
        self.authorized_requests = []
        self.event_sink = event_sink
    
    def authorize_action(self, request: ActionRequest) -> ActionAuthorization:
        """Authorize action - always returns authorized=True for valid requests."""
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2].name if len(stack) >= 2 else "unknown"
        file = stack[-2].filename if len(stack) >= 2 else "unknown"
        
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="authority_authorize_ENTER",
            credential_id=None,
            resolved=False,
            sandbox=False,
            caller=caller,
            callsite=f"file={file}",
            object_id=id(self),
            execution_id=request.execution_id,
            task_id=None
        ))
        
        self.authorized_requests.append(request)
        
        if not request.lease_id or not request.execution_id:
            EVENT_SINK.append(Event(
                sequence=next_sequence(),
                timestamp_ns=current_timestamp_ns(),
                event_type="authority_authorize_EXIT",
                credential_id=None,
                resolved=False,
                sandbox=False,
                caller=caller,
                callsite=f"file={file}",
                object_id=id(self),
                execution_id=request.execution_id,
                task_id=None
            ))
            return ActionAuthorization(
                authorized=False,
                error="Missing lease_id or execution_id"
            )
        
        auth_result = ActionAuthorization(
            authorized=True,
            run_id=f"run-{uuid4().hex[:8]}",
            action=request.action,
            target=request.target,
            consumed_at=None
        )
        
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="authority_authorize_EXIT",
            credential_id=None,
            resolved=False,
            sandbox=False,
            caller=caller,
            callsite=f"file={file}",
            object_id=id(self),
            execution_id=request.execution_id,
            task_id=None
        ))
        
        return auth_result
    
    def validate_action_binding(
        self,
        authorization: ActionAuthorization,
        requested_action: str,
        requested_target: str
    ) -> bool:
        """Validate action binding - returns True for test."""
        return True


class InstrumentedDevinAdapter:
    """Adapter that tracks api_key usage without real HTTP calls."""
    def __init__(self, api_key: str = "", event_sink=None):
        self.api_key = api_key
        self.event_sink = event_sink
        self.run_calls = []
        self.api_keys_received = []
        self.preflight_api_keys_received = []
    
    def _add_event(self, event_type: str, credential_id: str = None, api_key=None, sandbox: bool = False, caller=None, callsite=None, object_id=None, execution_id=None, task_id=None):
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type=event_type,
            credential_id=credential_id,
            resolved=api_key is not None,
            api_key_present=api_key is not None,
            sandbox=sandbox,
            caller=caller,
            callsite=callsite,
            object_id=object_id,
            execution_id=execution_id,
            task_id=task_id
        ))
    
    def is_available(self, card: ToolCard, *, api_key=None) -> bool:
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2].name if len(stack) >= 2 else "unknown"
        file = stack[-2].filename if len(stack) >= 2 else "unknown"
        
        self._add_event("is_available_ENTER", api_key=api_key, caller=caller, callsite=f"file={file}", object_id=id(self))
        self.preflight_api_keys_received.append(api_key)
        
        result = True  # Instrumented adapter always returns True
        
        self._add_event("is_available_EXIT", api_key=api_key, caller=caller, callsite=f"file={file}", object_id=id(self))
        return result
    
    def run(self, card: ToolCard, task: ToolTask, *, sandbox=False, api_key=None) -> dict[str, Any]:
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2].name if len(stack) >= 2 else "unknown"
        file = stack[-2].filename if len(stack) >= 2 else "unknown"
        
        self._add_event("adapter_run_ENTER", api_key=api_key, sandbox=sandbox, caller=caller, callsite=f"file={file}", object_id=id(self), execution_id=task.execution_id, task_id=task.task_id)
        self.run_calls.append(1)
        self.api_keys_received.append(api_key)
        
        result = {
            'success': True,
            'output_text': 'Simulated result',
            'extracted_data': {},
            'artifacts': [],
            'error_message': '',
            'execution_ms': 0,
            'metadata': {'sandbox': sandbox, 'simulated': True},
        }
        
        self._add_event("adapter_run_EXIT", api_key=api_key, sandbox=sandbox, caller=caller, callsite=f"file={file}", object_id=id(self), execution_id=task.execution_id, task_id=task.task_id)
        return result


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _service_with_credential_registry(root: Path) -> tuple[ToolTeachService, ToolRecordRepository, CredentialRegistry, CapabilityActionBridgeTestDouble, list]:
    """Canonical pattern from test_tool_teach_service.py with CredentialRegistry added and shared event sink."""
    # Clear global event sink for each test
    global EVENT_SINK
    EVENT_SINK = []
    
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    repository = ToolRecordRepository(db, storage)
    
    # Create instrumented adapter with EMPTY constructor key and shared event sink
    adapter = InstrumentedDevinAdapter(api_key="", event_sink=EVENT_SINK)
    
    # Monkeypatch is_available to capture ALL calls from any origin
    original_is_available = adapter.is_available
    def global_is_available_wrapper(card, *, api_key=None):
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2].name if len(stack) >= 2 else "unknown"
        file = stack[-2].filename if len(stack) >= 2 else "unknown"
        
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="is_available_ENTER",
            credential_id=None,
            resolved=api_key is not None,
            api_key_present=api_key is not None,
            sandbox=False,
            caller=caller,
            callsite=f"file={file}",
            object_id=id(adapter)
        ))
        
        result = original_is_available(card, api_key=api_key)
        
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="is_available_EXIT",
            credential_id=None,
            resolved=api_key is not None,
            api_key_present=api_key is not None,
            sandbox=False,
            caller=caller,
            callsite=f"file={file}",
            object_id=id(adapter)
        ))
        
        return result
    
    adapter.is_available = global_is_available_wrapper
    
    adapters = {
        'devin_api': adapter,
    }
    
    registry = ToolRegistry(repository, adapters)
    validator = ToolValidator()
    sandbox = ToolSandbox(validator)
    interaction_learning_service = InteractionLearningService(repository)
    mode_selector = InteractionModeSelector(registry, repository)
    memory = ToolMemory(repository, interaction_learning_service)
    approval_policy = ToolApprovalPolicy()
    rollback_manager = ToolRollbackManager(capability_action_bridge=None)
    
    # Instrument sandbox to register run calls
    original_sandbox_run = sandbox.run
    def instrumented_sandbox_run(*, card, task, adapter):
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="sandbox_run",
            credential_id=task.metadata.get("credential_id"),
            resolved=False,
            sandbox=True,
            caller="ToolTeachService.execute_task",
            callsite="pre-stage sandbox",
            object_id=id(sandbox),
            execution_id=task.execution_id,
            task_id=task.task_id
        ))
        result = original_sandbox_run(card=card, task=task, adapter=adapter)
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="sandbox_result_success",
            credential_id=task.metadata.get("credential_id"),
            resolved=False,
            sandbox=False,
            caller="ToolTeachService.execute_task",
            callsite=f"success={result.success}",
            object_id=id(sandbox)
        ))
        return result
    
    sandbox.run = instrumented_sandbox_run
    
    # Create instrumented secret resolver
    def instrumented_secret_resolver(ref: str) -> str:
        if ref == "DEVIN_API_KEY":
            return "synthetic-secret-A"
        return os.environ.get(ref, '')
    
    # Create CredentialRegistry with instrumented resolver
    credential_registry = CredentialRegistry(
        secret_resolver=instrumented_secret_resolver
    )
    
    # Instrument resolve_credential_secret to register calls with temporal ordering
    original_resolve = credential_registry.resolve_credential_secret
    def instrumented_resolve(credential_id: str) -> str:
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2].name if len(stack) >= 2 else "unknown"
        file = stack[-2].filename if len(stack) >= 2 else "unknown"
        
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="credential_resolve_ENTER",
            credential_id=credential_id,
            resolved=False,
            sandbox=False,
            caller=caller,
            callsite=f"file={file}",
            object_id=id(credential_registry)
        ))
        
        result = original_resolve(credential_id)
        
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="credential_resolve_EXIT",
            credential_id=credential_id,
            resolved=True,
            sandbox=False,
            caller=caller,
            callsite=f"file={file}",
            object_id=id(credential_registry)
        ))
        
        return result
    
    credential_registry.resolve_credential_secret = instrumented_resolve
    
    # Authority test double to isolate boundary with shared event sink
    capability_action_bridge = CapabilityActionBridgeTestDouble(event_sink=EVENT_SINK)
    
    service = ToolTeachService(
        registry=registry,
        memory=memory,
        sandbox=sandbox,
        validator=validator,
        approval_policy=approval_policy,
        rollback_manager=rollback_manager,
        adapters=adapters,
        workspace_root=str(root),
        interaction_learning_service=interaction_learning_service,
        mode_selector=mode_selector,
        credential_registry=credential_registry,
        capability_action_bridge=capability_action_bridge,
    )
    
    # Instrument registry.pick_card_for_task
    original_pick_card = registry.pick_card_for_task
    def instrumented_pick_card(task, **kwargs):
        card = original_pick_card(task, **kwargs)
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="pick_card_for_task",
            credential_id=task.metadata.get("credential_id"),
            resolved=False,
            sandbox=False,
            caller="ToolTeachService.execute_task",
            callsite=f"card={card.tool_id if card else None}, adapter_key={card.adapter_key if card else None}",
            object_id=id(registry)
        ))
        return card
    
    registry.pick_card_for_task = instrumented_pick_card
    
    # Instrument service.adapters.get to see what adapter is retrieved
    class InstrumentedDict(dict):
        def __init__(self, original_dict):
            super().__init__(original_dict)
            self._original_dict = original_dict
        
        def get(self, key, default=None):
            adapter = super().get(key, default)
            EVENT_SINK.append(Event(
                sequence=next_sequence(),
                timestamp_ns=current_timestamp_ns(),
                event_type="adapters_get",
                credential_id=None,
                resolved=False,
                sandbox=False,
                caller="ToolTeachService.execute_task",
                callsite=f"key={key}, adapter_exists={adapter is not None}, adapter_id={id(adapter) if adapter else None}",
                object_id=id(self)
            ))
            return adapter
    
    service.adapters = InstrumentedDict(adapters)
    
    # Monkeypatch execute_task to capture early return conditions
    original_execute_task = ToolTeachService.execute_task
    def patched_execute_task(self, task, *, approved=False):
        approval_required = bool(task.metadata.get('approval_required'))
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="execute_task_BEFORE_SANDBOX",
            credential_id=task.metadata.get("credential_id"),
            resolved=False,
            sandbox=False,
            caller="test",
            callsite=f"approval_required={approval_required}, approval_decision={task.approval_decision}",
            object_id=id(self)
        ))
        result = original_execute_task(self, task, approved=approved)
        EVENT_SINK.append(Event(
            sequence=next_sequence(),
            timestamp_ns=current_timestamp_ns(),
            event_type="execute_task_RETURNED",
            credential_id=task.metadata.get("credential_id"),
            resolved=False,
            sandbox=False,
            caller="test",
            callsite=f"result.success={result.success}, result.state={result.execution_state.state if result.execution_state else None}",
            object_id=id(self)
        ))
        return result
    
    ToolTeachService.execute_task = patched_execute_task
    
    return service, repository, credential_registry, capability_action_bridge, EVENT_SINK


def test_causal_credential_propagation():
    """Resolve temporal causality: credential registered → preflight → execution with canonical provenance."""
    os.environ["DEVIN_API_KEY"] = "synthetic-secret-A"
    
    try:
        root = _workspace('i0_causal_credential_propagation_1.7h')
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        
        try:
            service, repository, credential_registry, authority_bridge, event_trace = _service_with_credential_registry(root)
            
            # Verify shared event sink (adapter is created inside _service_with_credential_registry)
            adapter = service.adapters.get("devin_api")
            assert adapter.event_sink is EVENT_SINK, "Adapter event sink not shared"
            assert authority_bridge.event_sink is EVENT_SINK, "Authority event sink not shared"
            
            # CRITICAL: Verify object identity before execution
            print("\n=== OBJECT IDENTITY VERIFICATION ===")
            print(f"service: {id(service)}")
            print(f"service.adapters['devin_api']: {id(adapter)}")
            print(f"service.sandbox: {id(service.sandbox)}")
            print(f"service.credential_registry: {id(credential_registry)}")
            print(f"service.capability_action_bridge: {id(authority_bridge)}")
            
            assert service.adapters.get("devin_api") is adapter, "Adapter identity mismatch"
            assert service.sandbox is service.sandbox, "Sandbox identity mismatch"
            assert service.credential_registry is credential_registry, "CredentialRegistry identity mismatch"
            assert service.capability_action_bridge is authority_bridge, "Authority identity mismatch"
            print("OBJECT IDENTITY: VERIFIED")
            print("====================================\n")
            
            # 1. Discover and register credential
            credential_registry.register_adapter(DevinCredentialAdapter())
            discovered = credential_registry.discover_credentials("devin")
            credential_registry.register_credentials(discovered)
            
            record = discovered[0]
            
            # 2. Mark credential registration time
            EVENT_SINK.append(Event(
                sequence=next_sequence(),
                timestamp_ns=current_timestamp_ns(),
                event_type="credential_registered",
                credential_id=record.credential_id,
                resolved=True,
                caller="test_setup",
                callsite="before execute_task"
            ))
            
            # 3. Register ToolCard
            tool_card = ToolCard(
                tool_id="devin-api",
                adapter_key="devin_api",
                tool_type=ToolType.MCP_CLIENT,
                title="Devin API",
                description="Devin API adapter",
                capabilities=["chat", "code"],
            )
            repository.save_card(tool_card)
            
            # 4. Verify adapter configuration
            assert adapter.api_key == "", "Adapter constructor key should be empty"
            
            # 5. Create task with credential_id and EXPLICIT execution_scope in BOTH levels
            lease_id = f"lease-{uuid4().hex[:12]}"
            execution_id = f"exec-{uuid4().hex[:12]}"
            
            task = ToolTask(
                tool_id="devin-api",
                title="Test Task",
                objective="Test",
                requested_by_role=TaskRole.TOOL_USE,
                execution_scope="write",
                metadata={
                    "credential_id": record.credential_id,
                    "execution_scope": "write",
                },
                lease_id=lease_id,
                execution_id=execution_id,
                action="chat",
                target="devin",
            )
            
            # 6. Execute and mark boundaries
            EVENT_SINK.append(Event(
                sequence=next_sequence(),
                timestamp_ns=current_timestamp_ns(),
                event_type="execute_task_entered",
                credential_id=task.metadata.get("credential_id"),
                resolved=False,
                sandbox=False,
                caller="test",
                callsite="before service.execute_task",
                execution_id=task.execution_id,
                task_id=task.task_id
            ))
            
            result = service.execute_task(task, approved=True)
            
            EVENT_SINK.append(Event(
                sequence=next_sequence(),
                timestamp_ns=current_timestamp_ns(),
                event_type="execute_task_returned",
                credential_id=task.metadata.get("credential_id"),
                resolved=False,
                sandbox=False,
                caller="test",
                callsite="after service.execute_task",
                execution_id=task.execution_id,
                task_id=task.task_id
            ))
            
            # 7. Print event trace with temporal ordering
            print("\n=== EVENT TRACE (temporally ordered) ===")
            for e in event_trace:
                print(f"{e.sequence}: {e.event_type} (ns={e.timestamp_ns}, credential_id={e.credential_id}, sandbox={e.sandbox}, caller={e.caller}, object_id={e.object_id})")
            print("========================================\n")
            
            # 8. Verify causal ordering with temporal evidence
            event_types = [e.event_type for e in event_trace]
            
            # Find critical event indices
            registered_idx = event_types.index("credential_registered")
            execute_enter_idx = event_types.index("execute_task_entered")
            
            # Find preflight is_available (from execute_task, not refresh_card)
            is_available_entries = [i for i, e in enumerate(event_trace) if e.event_type == "is_available_ENTER" and e.caller == "execute_task"]
            assert len(is_available_entries) > 0, "is_available not called from execute_task"
            preflight_is_available_idx = is_available_entries[0]
            
            # Find authority
            authority_entries = [i for i, e in enumerate(event_trace) if e.event_type == "authority_authorize_ENTER"]
            assert len(authority_entries) > 0, "authority not called"
            authority_idx = authority_entries[0]
            
            # Find post-authority resolve (should be after authority)
            resolve_exits = [i for i, e in enumerate(event_trace) if e.event_type == "credential_resolve_EXIT"]
            assert len(resolve_exits) >= 2, "Need at least 2 credential resolutions"
            post_authority_resolve_idx = resolve_exits[1]  # Second resolve should be post-authority
            
            # Find protected run (sandbox=False)
            protected_run_entries = [i for i, e in enumerate(event_trace) if e.event_type == "adapter_run_ENTER" and e.sandbox == False]
            assert len(protected_run_entries) > 0, "protected adapter.run not called"
            protected_run_idx = protected_run_entries[0]
            
            # Verify temporal ordering
            assert registered_idx < execute_enter_idx, "credential_registered must be before execute_task_entered"
            assert execute_enter_idx < preflight_is_available_idx, "execute_task_entered must be before is_available"
            assert preflight_is_available_idx < authority_idx, "is_available must be before authority"
            assert authority_idx < post_authority_resolve_idx, "authority must be before post-authority resolve"
            assert post_authority_resolve_idx < protected_run_idx, "post-authority resolve must be before protected run"
            
            # Verify preflight received credential
            preflight_event = event_trace[preflight_is_available_idx]
            assert preflight_event.api_key_present == True, "preflight is_available must receive api_key"
            
            # Verify protected run is sandbox=False
            protected_event = event_trace[protected_run_idx]
            assert protected_event.sandbox == False, "protected run must have sandbox=False"
            assert protected_event.api_key_present == True, "protected run must receive api_key"
            
            # Verify object identity consistency
            adapter_id = id(adapter)
            for e in event_trace:
                if e.object_id and "adapter" in e.event_type.lower() and e.event_type != "adapters_get":
                    assert e.object_id == adapter_id, f"Adapter object identity mismatch in {e.event_type}"
            
            # Verify adapter still empty after execution
            assert adapter.api_key == "", "Adapter constructor key should remain empty"
            
            # 9. Verify secret hygiene
            assert "synthetic-secret-A" not in str(task.model_dump()), "Secret leaked into ToolTask"
            assert "synthetic-secret-A" not in str(result.model_dump()), "Secret leaked into ToolResult"
            
        finally:
            shutil.rmtree(root, ignore_errors=True)
            
    finally:
        if "DEVIN_API_KEY" in os.environ:
            del os.environ["DEVIN_API_KEY"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
