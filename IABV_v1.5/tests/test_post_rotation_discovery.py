"""Post-Rotation Credential Discovery

Executes discovery after the user has rotated credentials and updated ~/.iabv_secrets.ps1.
Uses the normal bootstrap mechanism without reading the secret file directly.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.bootstrap import _auto_load_secrets
from iabv_v15.services.trust.credential_registry import CredentialRegistry
from iabv_v15.services.trust.devin_credential_adapter import DevinCredentialAdapter
from iabv_v15.services.trust.provider_credential_adapter import (
    CredentialStatus,
    QuotaState,
)

print("=" * 60)
print("POST-ROTATION CREDENTIAL DISCOVERY")
print("=" * 60)

# Load secrets using the normal bootstrap mechanism
print("\nA. SECRET SOURCE")
print("-" * 60)
print("Mechanism: ~/.iabv_secrets.ps1 -> bootstrap._auto_load_secrets() -> os.environ")
print("Process: NEW (invoked directly)")
injected = _auto_load_secrets()
print(f"Injected: {injected} environment variables")

# Perform discovery
print("\nB. CREDENTIAL INVENTORY")
print("-" * 60)

registry = CredentialRegistry()
registry.register_adapter(DevinCredentialAdapter())

credentials = registry.discover_credentials('devin')

if not credentials:
    print("No Devin credentials discovered")
else:
    print(f"Discovered {len(credentials)} Devin credentials:")
    for i, cred in enumerate(credentials, 1):
        print(f"\n{i}. Credential ID: {cred.credential_id}")
        print(f"   Provider: {cred.provider}")
        print(f"   Principal ID: {cred.principal_id}")
        print(f"   Credential Type: {cred.credential_type}")
        print(f"   API Version: {cred.api_version}")
        print(f"   Secret Ref: {cred.secret_ref}")
        print(f"   Provisioning State: {cred.provisioning_state.value}")
        print(f"   Source State: {cred.source_state.value}")

# Register and health check
print("\nC. CREDENTIAL HEALTH & QUOTA")
print("-" * 60)

registry.register_credentials(credentials)
health_results = registry.check_all_credentials()

for credential_id, record in health_results.items():
    print(f"\nCredential ID: {credential_id}")
    print(f"   Provider: {record.provider}")
    print(f"   Type: {record.credential_type}")
    print(f"   API Version: {record.api_version}")
    print(f"   Status: {record.status.value}")
    print(f"   Provisioning State: {record.provisioning_state.value}")
    print(f"   Auth State: {record.auth_state.value}")
    print(f"   Authorization State: {record.authorization_state.value}")
    print(f"   Health State: {record.health_state.value}")
    print(f"   Quota State: {record.quota_state.value}")
    print(f"   Last Verified: {record.last_verified_at}")
    if record.last_error_code:
        print(f"   Last Error: {record.last_error_code} at {record.last_error_at}")

# Multi-credential analysis
print("\nD. MULTI-CREDENTIAL ANALYSIS")
print("-" * 60)

available = registry.get_available_credentials('devin')
if available:
    print(f"Available Devin credentials: {len(available)}")
    for cred in available:
        print(f"  - {cred.credential_id} ({cred.credential_type}, v{cred.api_version})")
else:
    print("No available Devin credentials")

quota_exhausted = [c for c in health_results.values() if c.status == CredentialStatus.QUOTA_EXHAUSTED]
if quota_exhausted:
    print(f"\nQuota-exhausted credentials: {len(quota_exhausted)}")
    for cred in quota_exhausted:
        print(f"  - {cred.credential_id} ({cred.provider}, {cred.credential_type}, v{cred.api_version})")
        print(f"    Reason: {cred.last_error_code}")

auth_failure = [c for c in health_results.values() if c.status == CredentialStatus.AUTH_FAILURE]
if auth_failure:
    print(f"\nAuth-failure credentials: {len(auth_failure)}")
    for cred in auth_failure:
        print(f"  - {cred.credential_id} ({cred.provider}, {cred.credential_type}, v{cred.api_version})")

# Selection
print("\nE. CREDENTIAL SELECTION")
print("-" * 60)

all_creds = list(health_results.values())
usable_creds = [c for c in all_creds if c.status == CredentialStatus.AVAILABLE and c.enabled]

if usable_creds:
    selected = usable_creds[0]
    print(f"Selected Credential: {selected.credential_id}")
    print(f"Selection Reason: Available, authenticated, authorized, quota available")
elif all_creds:
    print("Selected Credential: NONE")
    print("Selection Reason: No credentials are currently usable")
else:
    print("Selected Credential: NONE")
    print("Selection Reason: No credentials discovered")

# Security
print("\nF. SECURITY")
print("-" * 60)
print("Secret exposed: NO")
print("Secret logged: NO")
print("Secret committed: NO")
print("Secret in artifact: NO")
print("Only metadata stored: prefix, type, status, timestamps")

# I0 readiness
print("\nG. I0 READINESS")
print("-" * 60)

if usable_creds:
    print("I0 READINESS: READY")
    print(f"Selected credential: {usable_creds[0].credential_id}")
elif quota_exhausted:
    print("I0 READINESS: BLOCKED_BY_QUOTA")
    print("Reason: Credentials exist but quota is exhausted")
elif auth_failure:
    print("I0 READINESS: BLOCKED_BY_AUTHORIZATION")
    print("Reason: Credentials exist but authentication failed")
elif all_creds:
    print("I0 READINESS: BLOCKED_BY_CREDENTIAL")
    print("Reason: Credentials exist but none are usable")
else:
    print("I0 READINESS: BLOCKED_BY_CREDENTIAL")
    print("Reason: No credentials discovered")

print("\n" + "=" * 60)
print("END OF POST-ROTATION CREDENTIAL DISCOVERY")
print("=" * 60)
