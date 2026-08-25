"""
VFINAL5-R3: Protected Side Effect Classification

Canonical classification for protected side effects that require authority authorization.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ProtectedSideEffectClass(Enum):
    """Classification of protected side effects."""
    
    # Filesystem mutations
    FILESYSTEM_MUTATION = "filesystem_mutation"
    
    # Repository mutations
    REPOSITORY_MUTATION = "repository_mutation"
    
    # Git operations
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    
    # Security/configuration mutations
    SECURITY_MUTATION = "security_mutation"
    CONFIGURATION_MUTATION = "configuration_mutation"
    
    # Process control
    PROCESS_CONTROL = "process_control"
    
    # Credential mutations
    CREDENTIAL_MUTATION = "credential_mutation"
    
    # PR creation
    PR_CREATION = "pr_creation"


@dataclass
class ProtectedSideEffect:
    """Canonical protected side effect definition."""
    
    effect_class: ProtectedSideEffectClass
    action: str
    target: str
    scope: str
    authority_required: bool = True
    capability_required: bool = True
    lease_required: bool = True


# Canonical protected side effect definitions
PROTECTED_SIDE_EFFECTS = {
    # Filesystem mutations
    "write_repository_file": ProtectedSideEffect(
        effect_class=ProtectedSideEffectClass.FILESYSTEM_MUTATION,
        action="WRITE_REPOSITORY_FILE",
        target="file:*",
        scope="self_update",
        authority_required=True,
        capability_required=True,
        lease_required=True
    ),
    
    # Git operations
    "git_commit": ProtectedSideEffect(
        effect_class=ProtectedSideEffectClass.GIT_COMMIT,
        action="GIT_COMMIT",
        target="repository:*",
        scope="self_update",
        authority_required=True,
        capability_required=True,
        lease_required=True
    ),
    
    "git_push": ProtectedSideEffect(
        effect_class=ProtectedSideEffectClass.GIT_PUSH,
        action="GIT_PUSH",
        target="repository:*",
        scope="self_update",
        authority_required=True,
        capability_required=True,
        lease_required=True
    ),
    
    # Security/configuration mutations
    "security_mutation": ProtectedSideEffect(
        effect_class=ProtectedSideEffectClass.SECURITY_MUTATION,
        action="*",
        target="services/trust/*",
        scope="*",
        authority_required=True,
        capability_required=True,
        lease_required=True
    ),
    
    "configuration_mutation": ProtectedSideEffect(
        effect_class=ProtectedSideEffectClass.CONFIGURATION_MUTATION,
        action="*",
        target="security/*",
        scope="*",
        authority_required=True,
        capability_required=True,
        lease_required=True
    ),
    
    # PR creation
    "create_pr": ProtectedSideEffect(
        effect_class=ProtectedSideEffectClass.PR_CREATION,
        action="CREATE_PR",
        target="repository:*",
        scope="self_update",
        authority_required=True,
        capability_required=True,
        lease_required=True
    ),
}


def is_protected_side_effect(action: str, target: str, scope: str) -> bool:
    """
    Determine if an action/target/scope combination is a protected side effect.
    
    Args:
        action: The action being performed
        target: The target of the action
        scope: The scope of the action
        
    Returns:
        True if the action is a protected side effect, False otherwise
    """
    # Check security-critical paths
    from .authority_protocol import canonicalize_target
    
    canonical_target = canonicalize_target(target)
    
    # Security-critical paths are always protected
    security_critical_paths = [
        "services/trust/",
        "security/",
        "authority",
        "bootstrap.py",
        ".git/config",
        ".git/hooks"
    ]
    
    for critical_path in security_critical_paths:
        if critical_path in canonical_target:
            return True
    
    # Self-update scope is protected
    if scope == "self_update":
        return True
    
    return False


def get_required_authority(action: str, target: str, scope: str) -> Optional[str]:
    """
    Get the required authority for a protected side effect.
    
    Args:
        action: The action being performed
        target: The target of the action
        scope: The scope of the action
        
    Returns:
        The required authority scope, or None if no authority required
    """
    if is_protected_side_effect(action, target, scope):
        return "authority"
    return None
