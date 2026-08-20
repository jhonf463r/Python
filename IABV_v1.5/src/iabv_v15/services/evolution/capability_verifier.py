"""
Capability Verifier - P0.213 V5

Verifies and consumes invocation capabilities atomically.

This is the VERIFIER in the trust authority chain:
TRUST ANCHOR → AUTHORITY → ISSUER → INVOCATION CAPABILITY → CONSUMER → VERIFIER

Key Principle: VERIFY + CONSUME must be atomic from the perspective of
the trust boundary. A local dict is not sufficient because it's not
visible across processes.
"""

import os
import time
import psutil
from typing import Optional, Tuple

from iabv_v15.services.evolution.invocation_capability import InvocationCapability
from iabv_v15.services.evolution.capability_issuer import CapabilityIssuer
from iabv_v15.services.evolution.capability_registry import CapabilityRegistry


class CapabilityVerificationResult:
    """Result of capability verification."""
    
    def __init__(
        self,
        success: bool,
        reason: Optional[str] = None,
        invocation_id: Optional[str] = None,
    ):
        self.success = success
        self.reason = reason
        self.invocation_id = invocation_id


class CapabilityVerifier:
    """
    Verifies and consumes invocation capabilities.
    
    This performs the complete verification chain:
    1. Capability signature verification
    2. Consumer authorization verification
    3. OS-observed consumer identity verification
    4. Lineage verification (ppid)
    5. Scope validation
    6. Runtime incarnation validation
    7. Temporal validity (expiry)
    8. Single-use enforcement (atomic consume)
    """
    
    def __init__(
        self,
        issuer: CapabilityIssuer,
        registry: CapabilityRegistry,
    ):
        """
        Initialize the capability verifier.
        
        Args:
            issuer: The capability issuer (for signature verification)
            registry: The capability registry (for single-use enforcement)
        """
        self._issuer = issuer
        self._registry = registry
        self._current_runtime_incarnation = issuer.runtime_incarnation
    
    def verify_and_consume(
        self,
        capability: InvocationCapability,
        actual_consumer_pid: int,
        requested_scope: str,
    ) -> CapabilityVerificationResult:
        """
        Verify and consume a capability atomically.
        
        This is the core verification chain. All checks must pass for
        the capability to be consumed.
        
        Args:
            capability: The capability to verify and consume
            actual_consumer_pid: OS-observed PID of the consumer process
            requested_scope: The scope being requested
        
        Returns:
            CapabilityVerificationResult: Result of verification
        """
        # Step 1: Check if already consumed (single-use enforcement)
        if self._registry.is_consumed(capability.capability_id):
            return CapabilityVerificationResult(
                success=False,
                reason="Capability already consumed (replay attempt)",
            )
        
        # Step 2: Verify signature (integrity/authentication)
        if not self._issuer.verify_capability_signature(capability):
            return CapabilityVerificationResult(
                success=False,
                reason="Invalid capability signature (forged or corrupted)",
            )
        
        # Step 3: Verify consumer authorization (capability binding)
        if not capability.is_valid_for_consumer(actual_consumer_pid):
            return CapabilityVerificationResult(
                success=False,
                reason=f"Capability not authorized for consumer PID {actual_consumer_pid} (authorized for {capability.authorized_consumer_pid})",
            )
        
        # Step 4: Verify OS-observed consumer identity (prevent PID spoofing)
        if not self._verify_os_identity(actual_consumer_pid):
            return CapabilityVerificationResult(
                success=False,
                reason=f"OS identity verification failed for PID {actual_consumer_pid}",
            )
        
        # Step 5: Verify lineage (ppid check - necessary but not sufficient)
        if not self._verify_lineage(actual_consumer_pid, capability.issuer_pid):
            return CapabilityVerificationResult(
                success=False,
                reason=f"Lineage verification failed: consumer PID {actual_consumer_pid} is not child of issuer PID {capability.issuer_pid}",
            )
        
        # Step 6: Verify scope (scope validation)
        if not capability.is_valid_for_scope(requested_scope):
            return CapabilityVerificationResult(
                success=False,
                reason=f"Capability scope '{capability.scope}' does not match requested scope '{requested_scope}'",
            )
        
        # Step 7: Verify runtime incarnation (prevent cross-run replay)
        if not capability.is_valid_for_runtime(self._current_runtime_incarnation):
            return CapabilityVerificationResult(
                success=False,
                reason=f"Capability runtime incarnation {capability.runtime_incarnation} does not match current incarnation {self._current_runtime_incarnation}",
            )
        
        # Step 8: Verify temporal validity (expiry)
        if capability.is_expired():
            return CapabilityVerificationResult(
                success=False,
                reason=f"Capability expired at {capability.expires_at}",
            )
        
        # Step 9: Atomic consume (single-use enforcement)
        if not self._registry.mark_consumed(capability.capability_id):
            return CapabilityVerificationResult(
                success=False,
                reason="Capability already consumed (race condition detected)",
            )
        
        # All checks passed - capability successfully verified and consumed
        return CapabilityVerificationResult(
            success=True,
            invocation_id=capability.invocation_id,
        )
    
    def _verify_os_identity(self, pid: int) -> bool:
        """
        Verify that the OS confirms this PID exists.
        
        This prevents forged PID values.
        
        Args:
            pid: The PID to verify
        
        Returns:
            bool: True if OS confirms PID exists, False otherwise
        """
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _verify_lineage(self, consumer_pid: int, expected_parent_pid: int) -> bool:
        """
        Verify that the consumer is a child of the expected parent.
        
        This is necessary but not sufficient for authorization.
        Lineage verification alone does not prove authorization.
        
        Args:
            consumer_pid: PID of the consumer process
            expected_parent_pid: Expected parent PID (issuer PID)
        
        Returns:
            bool: True if consumer is child of expected parent, False otherwise
        """
        try:
            consumer_process = psutil.Process(consumer_pid)
            actual_parent_pid = consumer_process.ppid()
            return actual_parent_pid == expected_parent_pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def verify_capability_only(
        self,
        capability: InvocationCapability,
    ) -> CapabilityVerificationResult:
        """
        Verify a capability without consuming it.
        
        This is useful for pre-flight checks where you want to verify
        validity without consuming the single-use token.
        
        Args:
            capability: The capability to verify
        
        Returns:
            CapabilityVerificationResult: Result of verification
        """
        # Verify signature
        if not self._issuer.verify_capability_signature(capability):
            return CapabilityVerificationResult(
                success=False,
                reason="Invalid capability signature",
            )
        
        # Check if already consumed
        if self._registry.is_consumed(capability.capability_id):
            return CapabilityVerificationResult(
                success=False,
                reason="Capability already consumed",
            )
        
        # Verify temporal validity
        if capability.is_expired():
            return CapabilityVerificationResult(
                success=False,
                reason="Capability expired",
            )
        
        # Verify runtime incarnation
        if not capability.is_valid_for_runtime(self._current_runtime_incarnation):
            return CapabilityVerificationResult(
                success=False,
                reason="Runtime incarnation mismatch",
            )
        
        return CapabilityVerificationResult(
            success=True,
            invocation_id=capability.invocation_id,
        )
