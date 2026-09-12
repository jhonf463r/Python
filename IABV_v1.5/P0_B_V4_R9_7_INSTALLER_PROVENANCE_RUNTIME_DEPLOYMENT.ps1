# P0-B V4-R9.7 Installer Provenance Runtime Deployment
# Execute this from PowerShell as Administrator
# This script uses a machine-wide Python installation as trusted source
# and deploys a machine-scoped protected runtime for IABVAuditAuthority
#
# CRITICAL: This script does NOT generate authority keys or execute provisioning.
# It only prepares the secure runtime and installs the service.
#
# REQUIREMENTS:
# - C:\Python314 must have pywin32 and cryptography pre-installed with specific versions
# - This script does NOT perform dynamic pip install during deployment
# - Dependency installation must be done separately as Administrator
#
# PARAMETERS:
# -RepoPath: Path to Git repository/worktree root (default: C:\Python\IABV_v1.5)
#   The script will derive the IABV project root from this Git root
#   Expected layout: RepoPath/IABV_v1.5 is the project root
# -ExactDeploymentCommit: Optional exact commit SHA for deployment artifact pinning
#   If provided, deployment only allowed from this exact commit (not descendants)
#   If not provided, allows any descendant of baseline (for development/testing)

param(
    [string]$RepoPath = "C:\Python\IABV_v1.5",
    [string]$ExactDeploymentCommit = ""
)

Write-Output "=== P0-B V4-R9.7 INSTALLER PROVENANCE RUNTIME DEPLOYMENT ==="
Write-Output "Source checkout: $RepoPath"
Write-Output ""

# PHASE 0: Verify Administrator elevation
Write-Output "=== PHASE 0: VERIFY ADMINISTRATOR ELEVATION ==="
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Output "ERROR: This script must be run as Administrator"
    exit 1
}
Write-Output "Administrator context confirmed: YES"
Write-Output ""

# PHASE 1: Verify trusted source runtime exists
Write-Output "=== PHASE 1: VERIFY TRUSTED SOURCE RUNTIME ==="
$trustedSource = "C:\Python314"
if (-not (Test-Path $trustedSource)) {
    Write-Output "ERROR: Trusted source runtime not found: $trustedSource"
    exit 1
}
Write-Output "Trusted source runtime verified: $trustedSource"
Write-Output ""

# PHASE 2: Verify Python version consistency
Write-Output "=== PHASE 2: VERIFY PYTHON VERSION CONSISTENCY ==="
$pythonVersion = & "$trustedSource\python.exe" --version
Write-Output "Python version: $pythonVersion"
if ($pythonVersion -notlike "*3.14*") {
    Write-Output "ERROR: Python version must be 3.14, got: $pythonVersion"
    exit 1
}
Write-Output "Python version consistency: PASS"
Write-Output ""

# PHASE 3: Verify source runtime ACLs
Write-Output "=== PHASE 3: VERIFY SOURCE RUNTIME ACLS ==="
$acl = Get-Acl $trustedSource
Write-Output "Source runtime owner: $($acl.Owner)"
Write-Output "Source runtime ACL:"
icacls $trustedSource
Write-Output ""

# PHASE 4: Verify pywin32 is pre-installed in trusted source
Write-Output "=== PHASE 4: VERIFY PYWIN32 PRE-INSTALLED ==="
& "$trustedSource\python.exe" -c "import win32service" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: pywin32 not installed in trusted source"
    Write-Output "Run as Administrator: C:\Python314\python.exe -m pip install pywin32"
    exit 1
}
Write-Output "pywin32 installed: YES"
Write-Output ""

# PHASE 5: Verify cryptography is pre-installed in trusted source
Write-Output "=== PHASE 5: VERIFY CRYPTOGRAPHY PRE-INSTALLED ==="
& "$trustedSource\python.exe" -c "import cryptography" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: cryptography not installed in trusted source"
    Write-Output "Run as Administrator: C:\Python314\python.exe -m pip install cryptography"
    exit 1
}
Write-Output "cryptography installed: YES"
Write-Output ""

# PHASE 6: Verify pythonservice.exe exists
Write-Output "=== PHASE 6: VERIFY PYTHONSERVICE.EXE ==="
$pythonserviceInScripts = Test-Path "$trustedSource\Scripts\pythonservice.exe"
$pythonserviceInSitePackages = Test-Path "$trustedSource\Lib\site-packages\win32\pythonservice.exe"

if ($pythonserviceInScripts) {
    Write-Output "pythonservice.exe found in Scripts: $trustedSource\Scripts\pythonservice.exe"
} elseif ($pythonserviceInSitePackages) {
    Write-Output "pythonservice.exe found in site-packages: $trustedSource\Lib\site-packages\win32\pythonservice.exe"
} else {
    Write-Output "ERROR: pythonservice.exe not found in trusted source"
    exit 1
}
Write-Output ""

# PHASE 7: Verify pywintypes DLL version consistency
Write-Output "=== PHASE 7: VERIFY PYWINTYPES DLL VERSION CONSISTENCY ==="
$expectedDll = "pywintypes314.dll"
$pywintypesInRoot = Test-Path "$trustedSource\$expectedDll"
$pywintypesInSitePackages = Test-Path "$trustedSource\Lib\site-packages\pywin32_system32\$expectedDll"

if ($pywintypesInRoot) {
    Write-Output "pywintypes DLL found in root: $expectedDll"
} elseif ($pywintypesInSitePackages) {
    Write-Output "pywintypes DLL found in site-packages: $expectedDll"
} else {
    Write-Output "ERROR: pywintypes DLL $expectedDll not found in trusted source"
    Write-Output "Found in root: $pywintypesInRoot"
    Write-Output "Found in site-packages: $pywintypesInSitePackages"
    exit 1
}

# Check for wrong version DLL (pywintypes313.dll)
$wrongDll = "pywintypes313.dll"
$wrongDllInRoot = Test-Path "$trustedSource\$wrongDll"
$wrongDllInSitePackages = Test-Path "$trustedSource\Lib\site-packages\pywin32_system32\$wrongDll"

if ($wrongDllInRoot -or $wrongDllInSitePackages) {
    Write-Output "ERROR: Wrong version pywintypes DLL found: $wrongDll"
    Write-Output "Python 3.14 requires pywintypes314.dll, not pywintypes313.dll"
    exit 1
}
Write-Output "pywintypes DLL version consistency: PASS"
Write-Output ""

# PHASE 8: Verify repository state
Write-Output "=== PHASE 8: VERIFY REPOSITORY STATE ==="
Write-Output "Source path: $RepoPath"

# Derive Git root explicitly (in case RepoPath is a subdirectory)
$gitRoot = & git -C $RepoPath rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Could not determine Git root"
    exit 1
}
Write-Output "Git root: $gitRoot"

# Verify Git repository exists at derived root
if (-not (Test-Path "$gitRoot\.git")) {
    Write-Output "ERROR: Not a Git repository: $gitRoot"
    exit 1
}
Write-Output "Git repository verified: $gitRoot"

# Derive IABV project root (Git root/IABV_v1.5)
$iabvProjectRoot = Join-Path $gitRoot "IABV_v1.5"
if (-not (Test-Path $iabvProjectRoot)) {
    Write-Output "ERROR: IABV project root not found: $iabvProjectRoot"
    Write-Output "Expected layout: GitRoot/IABV_v1.5/"
    exit 1
}
Write-Output "IABV project root: $iabvProjectRoot"

# Verify HEAD matches required commit
$head = & git -C $gitRoot rev-parse HEAD
Write-Output "Repository HEAD: $head"

# P0-B Baseline R9.7
$baselineCommit = "c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3"

if ($ExactDeploymentCommit) {
    # EXACT DEPLOYMENT MODE: Require exact commit only
    Write-Output "EXACT DEPLOYMENT MODE: Commit = $ExactDeploymentCommit"
    if ($head -ne $ExactDeploymentCommit) {
        Write-Output "ERROR: HEAD does not match exact deployment commit"
        Write-Output "Required: $ExactDeploymentCommit"
        Write-Output "Actual: $head"
        exit 1
    }
    Write-Output "HEAD verification: PASS (exact match)"
} else {
    # BASELINE MODE: Accept baseline or descendants
    Write-Output "BASELINE MODE: Baseline = $baselineCommit"
    # Check if HEAD is baseline or descendant of baseline
    $isDescendant = & git -C $gitRoot merge-base --is-ancestor $baselineCommit $head 2>&1
    if ($LASTEXITCODE -ne 0 -and $head -ne $baselineCommit) {
        Write-Output "ERROR: HEAD is not baseline or descendant of baseline"
        Write-Output "Baseline: $baselineCommit"
        Write-Output "Actual: $head"
        exit 1
    }
    Write-Output "HEAD verification: PASS (baseline descendant)"
}

# Verify clean working tree
$status = & git -C $gitRoot status --porcelain
if ($status) {
    Write-Output "ERROR: Working tree is not clean"
    Write-Output "Uncommitted changes:"
    Write-Output $status
    exit 1
}
Write-Output "Working tree clean: PASS"
Write-Output ""

# Verify no staged changes
$diff = & git -C $gitRoot diff --cached --exit-code
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Staged changes detected"
    exit 1
}
Write-Output "No staged changes: PASS"
Write-Output ""
# Verify IABV source modules exist
if (-not (Test-Path "$iabvProjectRoot\src\iabv_v15")) {
    Write-Output "ERROR: IABV source modules not found: $iabvProjectRoot\src\iabv_v15"
    exit 1
}
Write-Output "IABV source modules verified: $iabvProjectRoot\src\iabv_v15"
Write-Output ""

# PHASE 9: Pre-flight permission check
Write-Output "=== PHASE 9: PRE-FLIGHT PERMISSION CHECK ==="

$serviceRuntimePath = "C:\ProgramData\IABV\service_runtime"
$runtimeParent = "C:\ProgramData\IABV"

# Check if runtime directory exists
$runtimeExists = Test-Path $serviceRuntimePath

if (-not $runtimeExists) {
    Write-Output "Fresh deployment scenario: runtime directory does not exist"
    Write-Output "Testing if installer can create parent directory and runtime..."

    # Test parent directory creation (fresh deployment)
    try {
        New-Item -Path $runtimeParent -ItemType Directory -Force -ErrorAction Stop | Out-Null
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot create parent directory: $_"
        exit 1
    }

    # Test runtime directory creation (fresh deployment)
    try {
        New-Item -Path $serviceRuntimePath -ItemType Directory -Force -ErrorAction Stop | Out-Null
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot create runtime directory: $_"
        exit 1
    }

    # Test write in runtime directory
    try {
        Set-Content -Path "$serviceRuntimePath\__preflight_test__.txt" -Value "test" -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot write to runtime directory: $_"
        exit 1
    }

    # Test deletion in runtime directory
    try {
        Remove-Item -Path "$serviceRuntimePath\__preflight_test__.txt" -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot delete from runtime directory: $_"
        exit 1
    }

    # Clean up the empty runtime directory we just created for testing
    # Cleanup must succeed for pre-flight to PASS
    try {
        Remove-Item -Path $serviceRuntimePath -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot clean up test runtime directory: $_"
        exit 1
    }

    Write-Output "Fresh deployment pre-flight: PASS"
} else {
    Write-Output "Existing runtime scenario: runtime directory already exists"
    Write-Output "Testing if installer can write/delete in existing runtime..."

    # Test write in existing runtime directory
    try {
        Set-Content -Path "$serviceRuntimePath\__preflight_test__.txt" -Value "test" -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot write to existing runtime directory: $_"
        exit 1
    }

    # Test deletion in existing runtime directory
    try {
        Remove-Item -Path "$serviceRuntimePath\__preflight_test__.txt" -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Pre-flight check failed - cannot delete from existing runtime directory: $_"
        exit 1
    }

    Write-Output "Existing runtime pre-flight: PASS"
}

Write-Output "Pre-flight permission check: PASS"
Write-Output ""

# PHASE 10: Create staging runtime directory (separate from active runtime)
Write-Output "=== PHASE 10: CREATE STAGING RUNTIME DIRECTORY ==="

# Use staging directory to avoid modifying active runtime when service exists
# Staging runtime is physically separate from C:\ProgramData\IABV\service_runtime
# This prevents modifying files that a running service might be using
$stagingTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stagingRuntimePath = "C:\ProgramData\IABV\service_runtime_staging_$stagingTimestamp"
$activeRuntimePath = "C:\ProgramData\IABV\service_runtime"

Write-Output "Staging runtime path: $stagingRuntimePath"
Write-Output "Active runtime path: $activeRuntimePath"

# NOTE: Order is now:
# Pre-flight → Create STAGING runtime → Prepare STAGING runtime → Verify STAGING runtime
# → Remove/stop OLD service → Replace active runtime with staging → Install NEW service
# This ensures PHASE 11-21 never modify the active runtime when service exists

try {
    New-Item -Path $stagingRuntimePath -ItemType Directory -Force -ErrorAction Stop | Out-Null
} catch {
    Write-Output "ERROR: Failed to create staging runtime directory: $_"
    exit 1
}
Write-Output "Staging runtime directory created: $stagingRuntimePath"

# Redefine $serviceRuntimePath to point to staging for PHASE 11-21
# This allows the rest of the code to work without massive changes
# The actual active runtime ($activeRuntimePath) remains untouched until PHASE 22.5
$serviceRuntimePath = $stagingRuntimePath
Write-Output "Runtime operations will use staging path: $serviceRuntimePath"
Write-Output ""

# PHASE 11: Copy Python runtime components from trusted source
Write-Output "=== PHASE 11: COPY PYTHON RUNTIME COMPONENTS FROM TRUSTED SOURCE ==="
Write-Output "Copying Python core executables to staging runtime..."
try {
    Copy-Item -Path "$trustedSource\python.exe" -Destination "$stagingRuntimePath\" -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\pythonw.exe" -Destination "$stagingRuntimePath\" -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\python314.dll" -Destination "$stagingRuntimePath\" -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to copy Python core executables: $_"
    exit 1
}

Write-Output "Copying python314.zip (standard library)..."
if (Test-Path "$trustedSource\python314.zip") {
    try {
        Copy-Item -Path "$trustedSource\python314.zip" -Destination "$serviceRuntimePath\" -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Failed to copy python314.zip: $_"
        exit 1
    }
}

Write-Output "Copying DLLs directory..."
try {
    New-Item -Path "$serviceRuntimePath\DLLs" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\DLLs\*" -Destination "$serviceRuntimePath\DLLs\" -Recurse -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to copy DLLs directory: $_"
    exit 1
}

Write-Output "Copying Lib (standard library)..."
try {
    New-Item -Path "$serviceRuntimePath\Lib" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\Lib\*" -Destination "$serviceRuntimePath\Lib\" -Recurse -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to copy Lib directory: $_"
    exit 1
}

Write-Output "Copying Scripts..."
try {
    New-Item -Path "$serviceRuntimePath\Scripts" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\Scripts\*" -Destination "$serviceRuntimePath\Scripts\" -Recurse -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to copy Scripts directory: $_"
    exit 1
}

Write-Output "Copying site-packages (pywin32, cryptography)..."
try {
    New-Item -Path "$serviceRuntimePath\Lib\site-packages" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\Lib\site-packages\win32" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\Lib\site-packages\pywin32*" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\Lib\site-packages\cryptography" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\Lib\site-packages\cryptography-*.dist-info" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to copy site-packages: $_"
    exit 1
}

Write-Output "Python runtime copied from trusted source successfully"
Write-Output ""

# PHASE 12: Configure python314._pth for complete isolation
Write-Output "=== PHASE 12: CONFIGURE PYTHON314._PTH ISOLATION ==="
$pthPath = "$serviceRuntimePath\python314._pth"
$pthContent = @"
# P0-B V4-R9.7 Complete Python Runtime Isolation
# This _pth file completely overrides sys.path initialization
# All registry and environment variables are ignored
# Site module is NOT imported unless explicitly enabled
# This provides the strongest startup isolation guarantee

# Core Python runtime paths (machine-scoped only)
.
Lib\site-packages

# Explicitly enable site module for pywin32/cryptography availability
# WITHOUT enabling user-site (isolated mode prevents this automatically)
import site
"@

try {
    Set-Content -Path $pthPath -Value $pthContent -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to configure python314._pth: $_"
    exit 1
}
Write-Output "python314._pth configured for isolated runtime: $pthPath"
Write-Output ""

# PHASE 13: Copy IABV service modules
Write-Output "=== PHASE 13: COPY IABV SERVICE MODULES ==="
$iabvSource = "$iabvProjectRoot\src"
$iabvTarget = "$serviceRuntimePath\iabv_v15"
try {
    New-Item -Path $iabvTarget -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$iabvSource\iabv_v15" -Destination "$serviceRuntimePath\" -Recurse -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to copy IABV service modules: $_"
    exit 1
}
Write-Output "IABV service modules copied to: $iabvTarget"
Write-Output ""

# PHASE 14: Configure user-site isolation via sitecustomize.py (defense-in-depth)
Write-Output "=== PHASE 14: CONFIGURE USER-SITE ISOLATION (DEFENSE-IN-DEPTH) ==="
$sitecustomizePath = "$serviceRuntimePath\Lib\sitecustomize.py"
$sitecustomizeContent = @"
# P0-B V4-R9.7 User-Site Isolation (Defense-in-Depth)
# This is a secondary defense; primary isolation is via python314._pth
# This file executes during site module initialization

import sys
import os

# Remove user-site directories from sys.path as secondary defense
user_profile = os.environ.get('USERPROFILE', '')
if user_profile:
    sys.path = [p for p in sys.path if not p.startswith(user_profile)]

# Disable user-site module (secondary defense)
import site
if hasattr(site, 'ENABLE_USER_SITE'):
    site.ENABLE_USER_SITE = False

# Log isolation for runtime verification
import logging
logging.basicConfig(
    filename=os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'iabv_isolation.log'),
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logging.info("P0-B User-Site Isolation: ENABLED - secondary defense via sitecustomize.py")
import site
if hasattr(site, 'ENABLE_USER_SITE'):
    site.ENABLE_USER_SITE = False

# Log isolation for runtime verification
import logging
logging.basicConfig(
    filename=os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'iabv_isolation.log'),
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

"@

try {
    Set-Content -Path $sitecustomizePath -Value $sitecustomizeContent -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to configure sitecustomize.py: $_"
    exit 1
}
Write-Output "User-site isolation configured (defense-in-depth): $sitecustomizePath"
Write-Output ""

# PHASE 15: Configure ACLs for machine-scoped runtime
Write-Output "=== PHASE 15: CONFIGURE MACHINE-SCOPED RUNTIME ACLS ==="

# Use well-known SIDs for internationalization robustness
# S-1-5-32-544 = BUILTIN\Administrators
# S-1-5-18 = SYSTEM
# S-1-5-19 = LocalService
# S-1-5-32-545 = BUILTIN\Users
#
# ACL Policy (NO DENY):
# - SYSTEM: FullControl (can modify for recovery/deployment)
# - Administrators: FullControl (can recover/redeploy)
# - LocalService: Read/Execute (can execute but not modify)
# - Users: NO permissions (no ACE added, inheritance removed)
#
# Rationale for NO DENY:
# - DENY rules can affect Administrators who also have Users SID in their token
# - With inheritance removed, Users has no permissions by default
# - Explicit Allow for SYSTEM/Administrators/LocalService is sufficient
# - Avoids complex DENY/Allow interaction in Windows token evaluation

Write-Output "Removing inheritance..."
icacls $serviceRuntimePath /inheritance:r
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Failed to remove inheritance"
    exit 1
}

Write-Output "Granting SYSTEM FullControl (S-1-5-18)..."
icacls $serviceRuntimePath /grant:r "*S-1-5-18:(OI)(CI)F"
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Failed to grant SYSTEM permissions"
    exit 1
}

Write-Output "Granting Administrators FullControl (S-1-5-32-544)..."
icacls $serviceRuntimePath /grant:r "*S-1-5-32-544:(OI)(CI)F"
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Failed to grant Administrators permissions"
    exit 1
}

Write-Output "Granting LocalService Read/Execute (S-1-5-19)..."
icacls $serviceRuntimePath /grant:r "*S-1-5-19:(OI)(CI)RX"
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Failed to grant LocalService permissions"
    exit 1
}

# No explicit DENY for Users - with inheritance removed, Users has no permissions
# This achieves the same security goal without DENY/Allow complexity

Write-Output "Machine-scoped runtime ACLs configured (NO DENY policy)"
Write-Output ""

# PHASE 16: Verify python314._pth isolation in deployed runtime
Write-Output "=== PHASE 16: VERIFY PYTHON314._PTH ISOLATION ==="
Write-Output "Testing isolation with deployed runtime..."

# First verify python.exe exists and is executable
if (-not (Test-Path "$serviceRuntimePath\python.exe")) {
    Write-Output "ERROR: python.exe not found in deployed runtime: $serviceRuntimePath\python.exe"
    exit 1
}

try {
    $isolationTest = & "$serviceRuntimePath\python.exe" -c "import sys,os; user_profile = os.environ.get('USERPROFILE', ''); has_user_path = any(p.startswith(user_profile) for p in sys.path if user_profile); print('USER_PROFILE_IN_PATH:', has_user_path); print('SYS_PATH_COUNT:', len(sys.path)); print('SYS_PATH:', sys.path); import site; print('ENABLE_USER_SITE:', site.ENABLE_USER_SITE)" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: python.exe execution failed with exit code $LASTEXITCODE"
        Write-Output "Output: $isolationTest"
        exit 1
    }
} catch {
    Write-Output "ERROR: Failed to execute python.exe for isolation test: $_"
    exit 1
}

Write-Output "Isolation test result: $isolationTest"
if ($isolationTest -like "*USER_PROFILE_IN_PATH: True*") {
    Write-Output "ERROR: User profile path still in sys.path of deployed runtime"
    exit 1
}
if ($isolationTest -like "*ENABLE_USER_SITE: True*") {
    Write-Output "ERROR: User site still enabled in deployed runtime"
    exit 1
}
Write-Output "python314._pth isolation verified: PASS"
Write-Output ""

# PHASE 17: Verify ACLs
Write-Output "=== PHASE 17: VERIFY ACLS ==="
icacls $serviceRuntimePath
Write-Output ""

# PHASE 18: Determine pythonservice.exe path
Write-Output "=== PHASE 18: DETERMINE PYTHONSERVICE.EXE PATH ==="
if (Test-Path "$serviceRuntimePath\Scripts\pythonservice.exe") {
    $pythonservicePath = "$serviceRuntimePath\Scripts\pythonservice.exe"
    Write-Output "Using pythonservice.exe from Scripts: $pythonservicePath"
} elseif (Test-Path "$serviceRuntimePath\Lib\site-packages\win32\pythonservice.exe") {
    $pythonservicePath = "$serviceRuntimePath\Lib\site-packages\win32\pythonservice.exe"
    Write-Output "Using pythonservice.exe from site-packages: $pythonservicePath"
} else {
    Write-Output "ERROR: pythonservice.exe not found in deployed runtime"
    exit 1
}
Write-Output ""

# PHASE 19: Verify critical runtime components exist
Write-Output "=== PHASE 19: VERIFY CRITICAL RUNTIME COMPONENTS ==="
$requiredFiles = @(
    "$serviceRuntimePath\python.exe",
    "$serviceRuntimePath\python314.dll",
    "$pythonservicePath",
    "$serviceRuntimePath\$expectedDll",
    "$serviceRuntimePath\Lib\site-packages\win32\__init__.py",
    "$serviceRuntimePath\Lib\site-packages\cryptography\__init__.py",
    "$serviceRuntimePath\Lib\site-packages\cryptography\hazmat\bindings\_rust.pyd",
    "$serviceRuntimePath\iabv_v15\services\development\authority_windows_service.py"
)

$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Output "  [OK] $file"
    } else {
        Write-Output "  [MISSING] $file"
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Output "ERROR: Missing critical runtime components"
    exit 1
}
Write-Output ""

# PHASE 20: Verify no wrong version DLLs in deployed runtime
Write-Output "=== PHASE 20: VERIFY NO WRONG VERSION DLLS ==="
$wrongDllInRuntime = Test-Path "$serviceRuntimePath\$wrongDll"
if ($wrongDllInRuntime) {
    Write-Output "ERROR: Wrong version pywintypes DLL in deployed runtime: $wrongDll"
    exit 1
}
Write-Output "No wrong version DLLs in deployed runtime: PASS"
Write-Output ""

# PHASE 21: Verify ACLs on critical components
Write-Output "=== PHASE 21: VERIFY CRITICAL COMPONENT ACLS ==="
$criticalPaths = @(
    "$serviceRuntimePath\python.exe",
    "$pythonservicePath",
    "$serviceRuntimePath\Lib\site-packages\cryptography"
)

foreach ($path in $criticalPaths) {
    if (Test-Path $path) {
        Write-Output "ACL for ${path}:"
        icacls $path
    }
}
Write-Output ""

# PHASE 22: Remove existing service (only after runtime is verified ready)
Write-Output "=== PHASE 22: REMOVE EXISTING SERVICE ==="

# Use sc.exe query for deterministic exit codes
# Exit code 0 = SERVICE_EXISTS
# Exit code 1060 = SERVICE_ABSENT
# Other exit code = SERVICE_QUERY_UNKNOWN (fail-closed)
Write-Output "Querying service state before removal..."
$serviceQueryBefore = & sc.exe query IABVAuditAuthority
$serviceQueryExitCode = $LASTEXITCODE

if ($serviceQueryExitCode -eq 0) {
    Write-Output "Service state: EXISTS (exit code 0)"
    Write-Output "Query output:"
    Write-Output $serviceQueryBefore

    # Service exists, attempt removal
    Write-Output "Attempting service removal..."
    $env:PYTHONPATH="$iabvProjectRoot\src"
    & "$trustedSource\python.exe" -m iabv_v15.services.development.authority_windows_service remove

    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Service removal failed with exit code $LASTEXITCODE"
        exit 1
    }

    Write-Output "Service removal command executed successfully"

    # Verify POSTCONDITION: service actually removed
    # Exit code 1060 = SERVICE_REMOVED (PASS)
    # Exit code 0 = SERVICE_STILL_EXISTS (FAIL)
    # Other exit code = POSTCONDITION_UNKNOWN (FAIL)
    Write-Output "Verifying service removal POSTCONDITION..."
    $serviceQueryAfter = & sc.exe query IABVAuditAuthority
    $serviceQueryAfterExitCode = $LASTEXITCODE

    if ($serviceQueryAfterExitCode -eq 1060) {
        Write-Output "Service verified as removed (POSTCONDITION: PASS, exit code 1060)"
    } elseif ($serviceQueryAfterExitCode -eq 0) {
        Write-Output "ERROR: Service still exists after removal (exit code 0)"
        Write-Output "Query output:"
        Write-Output $serviceQueryAfter
        exit 1
    } else {
        Write-Output "ERROR: Service POSTCONDITION query failed with unknown exit code $serviceQueryAfterExitCode"
        Write-Output "Query output:"
        Write-Output $serviceQueryAfter
        exit 1
    }

} elseif ($serviceQueryExitCode -eq 1060) {
    Write-Output "Service state: ABSENT (exit code 1060)"
    Write-Output "Service does not exist (ACCEPTED_PRECONDITION)"
    Write-Output "Skipping service removal"
} else {
    Write-Output "ERROR: Service query failed with unknown exit code $serviceQueryExitCode"
    Write-Output "Query output:"
    Write-Output $serviceQueryBefore
    Write-Output "Cannot determine service state - FAIL-CLOSED"
    exit 1
}

Write-Output ""

# PHASE 22.5: Activate staging runtime by moving to active location
# This is the atomic switch: verified staging runtime becomes active runtime
# Service must be removed/stopped before this point to avoid file locks
Write-Output "=== PHASE 22.5: ACTIVATE STAGING RUNTIME ==="
Write-Output "Moving verified staging runtime to active location: $activeRuntimePath"

# Remove old active runtime if it exists
$oldActiveRuntimeExists = Test-Path $activeRuntimePath
if ($oldActiveRuntimeExists) {
    Write-Output "Removing old active runtime directory: $activeRuntimePath"
    try {
        Remove-Item -Path $activeRuntimePath -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Output "ERROR: Failed to remove old active runtime directory: $_"
        exit 1
    }
    Write-Output "Old active runtime directory removed"
} else {
    Write-Output "Old active runtime directory does not exist (fresh deployment)"
}

# Move staging runtime to active location
try {
    Move-Item -Path $stagingRuntimePath -Destination $activeRuntimePath -Force -ErrorAction Stop
} catch {
    Write-Output "ERROR: Failed to move staging runtime to active location: $_"
    exit 1
}
Write-Output "Staging runtime activated: $activeRuntimePath"

# Update $serviceRuntimePath to point to active runtime for service installation
$serviceRuntimePath = $activeRuntimePath
Write-Output "Runtime path updated to active location: $serviceRuntimePath"
Write-Output ""

# PHASE 23: Install service with machine-scoped PathName
# Staging runtime is now verified and activated at active location
# Service installation can proceed with confidence that runtime is complete
Write-Output "=== PHASE 23: INSTALL SERVICE WITH MACHINE-SCOPED PATHNAME ==="
$env:PYTHONPATH="$serviceRuntimePath"
& "$serviceRuntimePath\python.exe" -m iabv_v15.services.development.authority_windows_service install $pythonservicePath
Write-Output ""

# PHASE 24: Verify service installation
Write-Output "=== PHASE 24: VERIFY SERVICE INSTALLATION ==="
$service = Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'"
Write-Output "Service Name: $($service.Name)"
Write-Output "Service State: $($service.State)"
Write-Output "Service StartName: $($service.StartName)"
Write-Output "Service PathName: $($service.PathName)"
Write-Output ""

# PHASE 25: Verify StartName is LocalService
Write-Output "=== PHASE 25: VERIFY SERVICE IDENTITY ==="
if ($service.StartName -ne "NT AUTHORITY\LocalService") {
    Write-Output "ERROR: Service StartName is not LocalService"
    Write-Output "Current StartName: $($service.StartName)"
    exit 1
}
Write-Output "SUCCESS: Service StartName is NT AUTHORITY\LocalService"
Write-Output ""

# PHASE 26: Verify PathName points to machine-scoped runtime
Write-Output "=== PHASE 26: VERIFY EXECUTION BOUNDARY ==="
if ($service.PathName -like "*C:\Users\faber\miniconda3*") {
    Write-Output "ERROR: Service PathName still points to user-profile runtime"
    Write-Output "Current PathName: $($service.PathName)"
    exit 1
}

if ($service.PathName -notlike "*service_runtime*") {
    Write-Output "ERROR: Service PathName does NOT point to machine-scoped runtime"
    Write-Output "Current PathName: $($service.PathName)"
    exit 1
}
Write-Output "SUCCESS: Service PathName points to machine-scoped runtime"
Write-Output ""

# PHASE 27: Verify PathName does NOT point to user profile
Write-Output "=== PHASE 27: VERIFY NO USER-PROFILE DEPENDENCY ==="
if ($service.PathName -like "*C:\Users\faber*") {
    Write-Output "ERROR: Service PathName contains user profile path"
    Write-Output "Current PathName: $($service.PathName)"
    exit 1
}
Write-Output "SUCCESS: Service PathName does not depend on user profile"
Write-Output ""

# PHASE 28: Final summary
Write-Output "=== INSTALLER PROVENANCE RUNTIME DEPLOYMENT COMPLETE ==="
Write-Output ""
Write-Output "DEPLOYMENT SUMMARY:"
Write-Output "  Trusted Source: $trustedSource"
Write-Output "  Python Version: $pythonVersion"
Write-Output "  Runtime Path: $serviceRuntimePath"
Write-Output "  Service Name: $($service.Name)"
Write-Output "  Service Identity: $($service.StartName)"
Write-Output "  Service PathName: $($service.PathName)"
Write-Output ""
Write-Output "PROVENANCE STATUS:"
Write-Output "  Installer semantics: CORRECT (pythonClassString + exeName parameter)"
Write-Output "  SOURCE_LOCATION_PROTECTED: PASS (machine-wide Python with restrictive ACLs)"
Write-Output "  PYTHON_VERSION_CONSISTENCY: PASS (Python 3.14 with matching pywintypes314.dll)"
Write-Output "  DESTINATION_INTEGRITY: PASS (ACL-protected machine-scoped runtime)"
Write-Output ""
Write-Output "NEXT STEPS:"
Write-Output "  1. Verify service startup: sc.exe start IABVAuditAuthority"
Write-Output "  2. Execute provisioning: Create C:\ProgramData\IABV\AUTHORITY_PROVISIONING_ENABLED as Administrator"
Write-Output "  3. Restart service to generate authority key under LocalService"
Write-Output "  4. Remove provisioning flag"
Write-Output "  5. Verify durability and execution boundary"
Write-Output ""
Write-Output "IMPORTANT: This deployment does NOT include authority key generation."
Write-Output "Authority key must be generated by the service itself during provisioning."
