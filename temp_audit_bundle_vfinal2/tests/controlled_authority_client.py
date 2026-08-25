"""Controlled AuthorityClient for testing.

This provides a testable implementation of AuthorityClient that satisfies
the production interface but doesn't require a real authority process.
"""

from typing import Any, Optional


class ControlledAuthorityClient:
    """Controlled AuthorityClient for testing without real authority process.
    
    This implementation satisfies the AuthorityClient interface but provides
    deterministic responses for testing. It can be configured to:
    - Accept or reject specific lease IDs
    - Track consumed leases for replay testing
    - Simulate authority unavailability
    """
    
    def __init__(self, authorized: bool = True):
        """Initialize controlled authority client.
        
        Args:
            authorized: Default authorization state
        """
        self.authorized = authorized
        self.consumed_leases = set()
        self.lease_authorizations = {}  # lease_id -> authorized bool
        self.execution_bindings = {}  # execution_id -> allowed actions/targets
    
    def set_lease_authorized(self, lease_id: str, authorized: bool):
        """Set authorization state for a specific lease."""
        self.lease_authorizations[lease_id] = authorized
    
    def set_execution_binding(self, execution_id: str, allowed_action: str, allowed_target: str):
        """Set allowed action/target for a specific execution."""
        self.execution_bindings[execution_id] = (allowed_action, allowed_target)
    
    def connect(self) -> None:
        """Connect (no-op for controlled client)."""
        pass
    
    def disconnect(self) -> None:
        """Disconnect (no-op for controlled client)."""
        pass
    
    def get_status(self) -> dict:
        """Get authority status."""
        return {
            "status": "running",
            "controlled": True,
            "authorized": self.authorized
        }
    
    def register_execution(
        self,
        invocation_id: str,
        action: str,
        target: str,
        requested_scope: str,
        task_context: Optional[str] = None,
        episode_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Register execution with authority."""
        execution_id = f"exec_{invocation_id}"
        return {
            "execution_id": execution_id,
            "run_id": f"run_{invocation_id}",
            "authorized_scope": requested_scope,
            "action": action,
            "target": target
        }
    
    def issue_lease(
        self,
        run_id: str,
        execution_id: str,
        requested_ttl_seconds: Optional[int] = None
    ) -> dict[str, Any]:
        """Issue lease using canonical protocol."""
        lease_id = f"lease_{run_id}"
        return {
            "lease_id": lease_id,
            "execution_id": execution_id,
            "ttl_seconds": requested_ttl_seconds or 300,
            "issued_at": 0.0
        }
    
    def consume_lease(
        self,
        lease_id: str,
        execution_id: str,
        requested_action: str,
        requested_target: str
    ) -> dict[str, Any]:
        """Consume lease using canonical protocol."""
        # Check if lease already consumed (replay detection)
        if lease_id in self.consumed_leases:
            return {
                "consumed": False,
                "error": "Lease already consumed"
            }
        
        # Check lease-specific authorization
        if lease_id in self.lease_authorizations:
            if not self.lease_authorizations[lease_id]:
                return {
                    "consumed": False,
                    "error": "Lease not authorized"
                }
        
        # Check default authorization
        if not self.authorized:
            return {
                "consumed": False,
                "error": "Authorization denied"
            }
        
        # Check execution binding if configured
        if execution_id in self.execution_bindings:
            allowed_action, allowed_target = self.execution_bindings[execution_id]
            if requested_action != allowed_action or requested_target != allowed_target:
                return {
                    "consumed": False,
                    "error": f"Action/target binding violation: requested {requested_action}/{requested_target}, allowed {allowed_action}/{allowed_target}"
                }
        
        # Consume lease
        self.consumed_leases.add(lease_id)
        return {
            "consumed": True,
            "consumed_at": 0.0,
            "run_id": f"run_{lease_id}"
        }
    
    def verify_execution(
        self,
        invocation_id: str,
        expected_scope: str
    ) -> dict[str, Any]:
        """Verify execution identity."""
        return {
            "verified": True,
            "scope": expected_scope
        }
