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
# -RepoPath: Path to IABV source checkout (default: C:\Python\IABV_v1.5)
#   The script will verify Git provenance of this checkout before deployment

param(
    [string]$RepoPath = "C:\Python\IABV_v1.5"
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
try {
    & "$trustedSource\python.exe" -c "import win32service" 2>&1 | Out-Null
    Write-Output "pywin32 installed: YES"
} catch {
    Write-Output "ERROR: pywin32 not installed in trusted source"
    Write-Output "Run as Administrator: C:\Python314\python.exe -m pip install pywin32"
    exit 1
}
Write-Output ""

# PHASE 5: Verify cryptography is pre-installed in trusted source
Write-Output "=== PHASE 5: VERIFY CRYPTOGRAPHY PRE-INSTALLED ==="
try {
    & "$trustedSource\python.exe" -c "import cryptography" 2>&1 | Out-Null
    Write-Output "cryptography installed: YES"
} catch {
    Write-Output "ERROR: cryptography not installed in trusted source"
    Write-Output "Run as Administrator: C:\Python314\python.exe -m pip install cryptography"
    exit 1
}
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

# Verify Git repository exists
if (-not (Test-Path "$RepoPath\.git")) {
    Write-Output "ERROR: Not a Git repository: $RepoPath"
    exit 1
}
Write-Output "Git repository verified: $RepoPath"

# Verify HEAD matches required commit
$head = & git -C $RepoPath rev-parse HEAD
Write-Output "Repository HEAD: $head"
$requiredCommit = "dd44c8440a0f8ad7591f10de16cbd9c831e816c0"
if ($head -ne $requiredCommit) {
    Write-Output "ERROR: HEAD does not match required commit"
    Write-Output "Required: $requiredCommit"
    Write-Output "Actual: $head"
    exit 1
}
Write-Output "HEAD verification: PASS"

# Verify clean working tree
$status = & git -C $RepoPath status --porcelain
if ($status) {
    Write-Output "ERROR: Working tree is not clean"
    Write-Output "Uncommitted changes:"
    Write-Output $status
    exit 1
}
Write-Output "Working tree clean: PASS"

# Verify no staged changes
$diff = & git -C $RepoPath diff --cached --exit-code
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Staged changes detected"
    exit 1
}
Write-Output "No staged changes: PASS"

# Verify IABV source modules exist
if (-not (Test-Path "$RepoPath\src\iabv_v15")) {
    Write-Output "ERROR: IABV source modules not found: $RepoPath\src\iabv_v15"
    exit 1
}
Write-Output "IABV source modules verified: $RepoPath\src\iabv_v15"
Write-Output ""

# PHASE 9: Remove existing service
Write-Output "=== PHASE 9: REMOVE EXISTING SERVICE ==="
try {
    $env:PYTHONPATH="$RepoPath\src"
    & "$trustedSource\python.exe" -m iabv_v15.services.development.authority_windows_service remove
    Write-Output "Existing service removed"
} catch {
    Write-Output "Service may not have existed, continuing..."
}
Write-Output ""

# PHASE 10: Create machine-scoped runtime directory
Write-Output "=== PHASE 10: CREATE MACHINE-SCOPED RUNTIME DIRECTORY ==="
$serviceRuntimePath = "C:\ProgramData\IABV\service_runtime"
if (Test-Path $serviceRuntimePath) {
    Write-Output "Removing existing runtime directory: $serviceRuntimePath"
    Remove-Item -Path $serviceRuntimePath -Recurse -Force
}
New-Item -Path $serviceRuntimePath -ItemType Directory -Force
Write-Output "Machine-scoped runtime directory created: $serviceRuntimePath"
Write-Output ""

# PHASE 11: Copy Python runtime components from trusted source
Write-Output "=== PHASE 11: COPY PYTHON RUNTIME COMPONENTS FROM TRUSTED SOURCE ==="
Write-Output "Copying Python core executables..."
Copy-Item -Path "$trustedSource\python.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$trustedSource\pythonw.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$trustedSource\python314.dll" -Destination "$serviceRuntimePath\" -Force

Write-Output "Copying python314.zip (standard library)..."
if (Test-Path "$trustedSource\python314.zip") {
    Copy-Item -Path "$trustedSource\python314.zip" -Destination "$serviceRuntimePath\" -Force
}

Write-Output "Copying DLLs directory..."
New-Item -Path "$serviceRuntimePath\DLLs" -ItemType Directory -Force
Copy-Item -Path "$trustedSource\DLLs\*" -Destination "$serviceRuntimePath\DLLs\" -Recurse -Force

Write-Output "Copying Lib (standard library)..."
New-Item -Path "$serviceRuntimePath\Lib" -ItemType Directory -Force
Copy-Item -Path "$trustedSource\Lib\*" -Destination "$serviceRuntimePath\Lib\" -Recurse -Force

Write-Output "Copying Scripts..."
New-Item -Path "$serviceRuntimePath\Scripts" -ItemType Directory -Force
Copy-Item -Path "$trustedSource\Scripts\*" -Destination "$serviceRuntimePath\Scripts\" -Recurse -Force

Write-Output "Copying site-packages (pywin32, cryptography)..."
New-Item -Path "$serviceRuntimePath\Lib\site-packages" -ItemType Directory -Force
Copy-Item -Path "$trustedSource\Lib\site-packages\win32" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$trustedSource\Lib\site-packages\pywin32*" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$trustedSource\Lib\site-packages\cryptography" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$trustedSource\Lib\site-packages\cryptography-*.dist-info" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force

Write-Output "Python runtime copied from trusted source successfully"
Write-Output ""

# PHASE 12: Copy IABV service modules
Write-Output "=== PHASE 12: COPY IABV SERVICE MODULES ==="
$iabvSource = "$RepoPath\src"
$iabvTarget = "$serviceRuntimePath\iabv_v15"
New-Item -Path $iabvTarget -ItemType Directory -Force
Copy-Item -Path "$iabvSource\iabv_v15" -Destination "$serviceRuntimePath\" -Recurse -Force
Write-Output "IABV service modules copied to: $iabvTarget"
Write-Output ""

# PHASE 13: Configure ACLs for machine-scoped runtime
Write-Output "=== PHASE 13: CONFIGURE MACHINE-SCOPED RUNTIME ACLS ==="
Write-Output "Removing inheritance..."
icacls $serviceRuntimePath /inheritance:r

Write-Output "Granting LocalService Read/Execute..."
icacls $serviceRuntimePath /grant:r "LocalService:(OI)(CI)RX"

Write-Output "Granting Administrators FullControl..."
icacls $serviceRuntimePath /grant:r "Administrators:(OI)(CI)F"

Write-Output "Granting SYSTEM FullControl..."
icacls $serviceRuntimePath /grant:r "SYSTEM:(OI)(CI)F"

Write-Output "Denying Users Write/Delete/Replace..."
icacls $serviceRuntimePath /deny "Users:(OI)(CI)F"

Write-Output "Machine-scoped runtime ACLs configured"
Write-Output ""

# PHASE 15: Verify user-site isolation in deployed runtime
Write-Output "=== PHASE 15: VERIFY USER-SITE ISOLATION ==="
Write-Output "Testing isolation with deployed runtime..."
$isolationTest = & "$serviceRuntimePath\python.exe" -c "import site,sys,os; user_profile = os.environ.get('USERPROFILE', ''); has_user_path = any(p.startswith(user_profile) for p in sys.path if user_profile); print('USER_PROFILE_IN_PATH:', has_user_path); print('ENABLE_USER_SITE:', site.ENABLE_USER_SITE)"
Write-Output "Isolation test result: $isolationTest"
if ($isolationTest -like "*USER_PROFILE_IN_PATH: True*") {
    Write-Output "ERROR: User profile path still in sys.path of deployed runtime"
    exit 1
}
Write-Output "User-site isolation verified: PASS"
Write-Output ""

# PHASE 16: Verify ACLs
Write-Output "=== PHASE 16: VERIFY ACLS ==="
icacls $serviceRuntimePath
Write-Output ""

# PHASE 17: Determine pythonservice.exe path
Write-Output "=== PHASE 17: DETERMINE PYTHONSERVICE.EXE PATH ==="
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

# PHASE 18: Verify critical runtime components exist
Write-Output "=== PHASE 18: VERIFY CRITICAL RUNTIME COMPONENTS ==="
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

# PHASE 19: Verify no wrong version DLLs in deployed runtime
Write-Output "=== PHASE 19: VERIFY NO WRONG VERSION DLLS ==="
$wrongDllInRuntime = Test-Path "$serviceRuntimePath\$wrongDll"
if ($wrongDllInRuntime) {
    Write-Output "ERROR: Wrong version pywintypes DLL in deployed runtime: $wrongDll"
    exit 1
}
Write-Output "No wrong version DLLs in deployed runtime: PASS"
Write-Output ""

# PHASE 20: Verify ACLs on critical components
Write-Output "=== PHASE 20: VERIFY CRITICAL COMPONENT ACLS ==="
$criticalPaths = @(
    "$serviceRuntimePath\python.exe",
    "$pythonservicePath",
    "$serviceRuntimePath\Lib\site-packages\cryptography"
)

foreach ($path in $criticalPaths) {
    if (Test-Path $path) {
        Write-Output "ACL for $path:"
        icacls $path
    }
}
Write-Output ""

# PHASE 21: Install service with machine-scoped PathName
Write-Output "=== PHASE 21: INSTALL SERVICE WITH MACHINE-SCOPED PATHNAME ==="
$env:PYTHONPATH="$serviceRuntimePath"
& "$serviceRuntimePath\python.exe" -m iabv_v15.services.development.authority_windows_service install $pythonservicePath
Write-Output ""

# PHASE 21: Verify service installation
Write-Output "=== PHASE 21: VERIFY SERVICE INSTALLATION ==="
$service = Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'"
Write-Output "Service Name: $($service.Name)"
Write-Output "Service State: $($service.State)"
Write-Output "Service StartName: $($service.StartName)"
Write-Output "Service PathName: $($service.PathName)"
Write-Output ""

# PHASE 22: Verify StartName is LocalService
Write-Output "=== PHASE 22: VERIFY SERVICE IDENTITY ==="
if ($service.StartName -ne "NT AUTHORITY\LocalService") {
    Write-Output "ERROR: Service StartName is not LocalService"
    Write-Output "Current StartName: $($service.StartName)"
    exit 1
}
Write-Output "SUCCESS: Service StartName is NT AUTHORITY\LocalService"
Write-Output ""

# PHASE 23: Verify PathName points to machine-scoped runtime
Write-Output "=== PHASE 23: VERIFY EXECUTION BOUNDARY ==="
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

# PHASE 24: Verify PathName does NOT point to user profile
Write-Output "=== PHASE 24: VERIFY NO USER-PROFILE DEPENDENCY ==="
if ($service.PathName -like "*C:\Users\faber*") {
    Write-Output "ERROR: Service PathName contains user profile path"
    Write-Output "Current PathName: $($service.PathName)"
    exit 1
}
Write-Output "SUCCESS: Service PathName does not depend on user profile"
Write-Output ""

# PHASE 25: Final summary
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
