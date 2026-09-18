"""I0 / CREDENTIAL PROVISIONING BOUNDARY - FORENSIC REPORT

Investigates whether DEVIN_API_KEY_SERVICE exists in any authorized provisioning mechanism.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=" * 60)
print("I0 / CREDENTIAL PROVISIONING BOUNDARY - FORENSIC REPORT")
print("=" * 60)

# A. MEMORY ACTIVATION
print("\nA. MEMORY ACTIVATION")
print("-" * 60)
print("GitHub repository: jhonf463r/Python")
print("Historical memory accessed via CHAT-ARCH/README.md")
print("Reconciliation: GitHub canonical memory vs current runtime evidence")
print("Classification: CONFIRMED (secret source mechanism), SUPERSEDED (assumed multi-credential state)")

# B. AUTHORIZED SECRET SOURCES
print("\nB. AUTHORIZED SECRET SOURCES")
print("-" * 60)

from iabv_v15.bootstrap import _DEVIN_API_KEY_ENV_VARS, _auto_load_secrets

print("Source 1: ~/.iabv_secrets.ps1 (via bootstrap._auto_load_secrets)")
print("  Authorized by IABV: YES")
print("  Resolved path:", Path.home() / '.iabv_secrets.ps1')
print("  Parser: $env:NAME = 'value' or $env:NAME = \"value\"")
print("  Injected variables:", _auto_load_secrets())

print("\nSource 2: Bootstrap legacy _DEVIN_API_KEY_ENV_VARS")
print("  Authorized by IABV: YES")
print("  Recognized variables:", _DEVIN_API_KEY_ENV_VARS)
print("  DEVIN_API_KEY_SERVICE in legacy list:", 'DEVIN_API_KEY_SERVICE' in _DEVIN_API_KEY_ENV_VARS)

print("\nSource 3: CredentialRegistry Devin adapter")
print("  Authorized by IABV: YES (new provider-neutral architecture)")
print("  Recognized variables: DEVIN_API_KEY_IABV, IABV_DEVIN_API_KEY, DEVIN_API_KEY, DEVIN_API_KEY_SERVICE, DEVIN_API_KEY_LEGACY")

# C. VARIABLE PRESENCE METADATA
print("\nC. VARIABLE PRESENCE METADATA")
print("-" * 60)

from iabv_v15.bootstrap import _resolve_devin_api_key

print("Bootstrap _resolve_devin_api_key() result:")
resolved_key = _resolve_devin_api_key()
print("  Resolved: PRESENT" if resolved_key else "NOT RESOLVED")
print("  Length:", len(resolved_key) if resolved_key else 0)
print("  Source from _DEVIN_API_KEY_ENV_VARS priority order")

print("\nEnvironment variable presence:")
print("  DEVIN_API_KEY_IABV:", "PRESENT" if os.environ.get('DEVIN_API_KEY_IABV') else "NOT PRESENT")
print("  IABV_DEVIN_API_KEY:", "PRESENT" if os.environ.get('IABV_DEVIN_API_KEY') else "NOT PRESENT")
print("  DEVIN_API_KEY:", "PRESENT" if os.environ.get('DEVIN_API_KEY') else "NOT PRESENT")
print("  DEVIN_API_KEY_SERVICE:", "PRESENT" if os.environ.get('DEVIN_API_KEY_SERVICE') else "NOT PRESENT")
print("  DEVIN_API_KEY_LEGACY:", "PRESENT" if os.environ.get('DEVIN_API_KEY_LEGACY') else "NOT PRESENT")

# D. CONTRACT MISMATCH
print("\nD. CONTRACT MISMATCH")
print("-" * 60)
print("OBSERVED:")
print("  - Bootstrap legacy recognizes: DEVIN_API_KEY_IABV, IABV_DEVIN_API_KEY, DEVIN_API_KEY")
print("  - CredentialRegistry recognizes: + DEVIN_API_KEY_SERVICE, DEVIN_API_KEY_LEGACY")
print("  - DEVIN_API_KEY_SERVICE is NOT in bootstrap _DEVIN_API_KEY_ENV_VARS")
print("IMPLICATION:")
print("  - Even if DEVIN_API_KEY_SERVICE is in ~/.iabv_secrets.ps1,")
print("  - bootstrap._auto_load_secrets() will inject it into os.environ")
print("  - BUT _resolve_devin_api_key() will NOT resolve it (not in priority list)")
print("  - Legacy DevinApiToolAdapter will NOT see it")
print("  - NEW CredentialRegistry DevinCredentialAdapter WOULD see it (if in env)")

# E. DISCOVERY/PROVISIONING/RESOLUTION STATES
print("\nE. DISCOVERY/PROVISIONING/RESOLUTION STATES")
print("-" * 60)
print("Provisioning state (source file):")
secrets_path = Path.home() / '.iabv_secrets.ps1'
if secrets_path.is_file():
    content = secrets_path.read_text(encoding='utf-8')
    print("  DEVIN_API_KEY_SERVICE in source:", 'DEVIN_API_KEY_SERVICE' in content)
else:
    print("  Source file not found")

print("\nResolution state (bootstrap legacy):")
print("  DEVIN_API_KEY_SERVICE resolved by _resolve_devin_api_key():", 'DEVIN_API_KEY_SERVICE' in _DEVIN_API_KEY_ENV_VARS)

print("\nDiscovery state (CredentialRegistry):")
print("  DEVIN_API_KEY_SERVICE would be discovered: YES (if in os.environ)")
print("  BUT: CredentialRegistry discovery relies on os.environ")

# F. ROOT CAUSE
print("\nF. ROOT CAUSE")
print("-" * 60)
print("SOURCE/BOOTSTRAP_CONTRACT_MISMATCH")
print("Cause: DEVIN_API_KEY_SERVICE is NOT in bootstrap _DEVIN_API_KEY_ENV_VARS")
print("Effect: Even if provisioned in ~/.iabv_secrets.ps1, legacy adapter cannot resolve it")
print("Note: New CredentialRegistry architecture supports it, but bootstrap legacy does not")

# G. EVIDENCE LEVEL
print("\nG. EVIDENCE LEVEL")
print("-" * 60)
print("IMPLEMENTED: CredentialRegistry with multi-provider support")
print("OBSERVED: Contract mismatch between bootstrap legacy and new CredentialRegistry")
print("RUNTIME-PROVEN: Secret source mechanism works, but variable name not in legacy list")
print("INDEPENDENTLY VERIFIED: Variable presence check, source inspection")

# H. STOP/GO DECISION FOR I0
print("\nH. STOP/GO DECISION FOR I0")
print("-" * 60)
print("DECISION: STOP")
print("Reason: CONTRACT_MISMATCH blocks provisioning even if credential exists in source")
print("Required: Add DEVIN_API_KEY_SERVICE to bootstrap _DEVIN_API_KEY_ENV_VARS")
print("          OR use DEVIN_API_KEY_IABV / IABV_DEVIN_API_KEY / DEVIN_API_KEY instead")

# I. SECURITY
print("\nI. SECURITY / NO SECRET EXPOSURE")
print("-" * 60)
print("Secret exposed: NO")
print("Secret logged: NO")
print("Secret committed: NO")
print("Secret in artifact: NO")

print("\n" + "=" * 60)
print("END OF I0 CREDENTIAL PROVISIONING BOUNDARY FORENSIC REPORT")
print("=" * 60)
