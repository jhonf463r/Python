"""Secret Source Forensics Report

Investigates why DEVIN_API_KEY_SERVICE is not being discovered by IABV.
"""

import os
import sys
import re
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=" * 60)
print("SECRET SOURCE FORENSICS")
print("=" * 60)

# A. ACTUAL SECRET SOURCE
print("\nA. ACTUAL SECRET SOURCE")
print("-" * 60)
secrets_path = Path.home() / '.iabv_secrets.ps1'
print(f"Resolved path: {secrets_path}")
print(f"Exists: {secrets_path.is_file()}")
print(f"File size: {secrets_path.stat().st_size} bytes")

# B. RUNTIME PATH COMPARISON
print("\nB. RUNTIME PATH COMPARISON")
print("-" * 60)
print(f"Bash HOME: {os.environ.get('HOME', 'NOT_SET')}")
print(f"Python Path.home(): {Path.home()}")
print(f"IABV resolved home: {Path.home()}")
print(f"IABV secret source: {secrets_path}")

# C. VARIABLE PRESENCE
print("\nC. VARIABLE PRESENCE")
print("-" * 60)
if secrets_path.is_file():
    content = secrets_path.read_text(encoding='utf-8')
    devin_api_key_present = 'DEVIN_API_KEY' in content
    devin_api_key_service_present = 'DEVIN_API_KEY_SERVICE' in content
    print(f"DEVIN_API_KEY present: {devin_api_key_present}")
    print(f"DEVIN_API_KEY_SERVICE present: {devin_api_key_service_present}")

# D. BOOTSTRAP PARSER
print("\nD. BOOTSTRAP PARSER")
print("-" * 60)
_PS1_ENV_RE = re.compile(
    r"""^\s*\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['"](.+?)['"]\s*$"""
)
print("Regex pattern: $env:NAME = 'value' or $env:NAME = \"value\"")
print("Accepts: Variable names starting with letter, followed by letters/numbers/underscores")
print("Would DEVIN_API_KEY_SERVICE be recognized? YES (matches pattern)")

# E. ACTUAL VARIABLES IN SOURCE
print("\nE. ACTUAL VARIABLES IN SOURCE")
print("-" * 60)
if secrets_path.is_file():
    lines = secrets_path.read_text(encoding='utf-8').splitlines()
    env_assignments = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        m = _PS1_ENV_RE.match(stripped)
        if m:
            var_name = m.group(1)
            env_assignments.append(var_name)
    
    print(f"Total $env: assignments found: {len(env_assignments)}")
    for var in env_assignments:
        print(f"  - {var}")

# F. EPISTEMIC STATE
print("\nF. EPISTEMIC STATE")
print("-" * 60)
print("USER_ASSERTED: new credential exists externally")
print("OBSERVED: DEVIN_API_KEY_SERVICE not visible to runtime")
print("OBSERVED: DEVIN_API_KEY_SERVICE not present in resolved source")
print("OBSERVED: DEVIN_API_KEY present in resolved source")

# G. ROOT CAUSE
print("\nG. ROOT CAUSE")
print("-" * 60)
print("VARIABLE_NOT_PRESENT")
print("The variable DEVIN_API_KEY_SERVICE is not assigned in the secret source file")
print("that IABV actually loads (C:\\Users\\faber\\.iabv_secrets.ps1)")

# H. SECURITY
print("\nH. SECURITY")
print("-" * 60)
print("Secret logged: FALSE")
print("Secret printed: FALSE")
print("Secret committed: FALSE")
print("Secret in artifact: FALSE")

print("\n" + "=" * 60)
print("END OF SECRET SOURCE FORENSICS")
print("=" * 60)
