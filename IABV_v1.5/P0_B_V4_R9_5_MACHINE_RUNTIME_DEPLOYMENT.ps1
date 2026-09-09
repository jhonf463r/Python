# P0-B V4-R9.5 Machine-Scoped Service Runtime Deployment
# Execute this from PowerShell as Administrator
# This script creates a REAL machine-scoped protected runtime for IABVAuditAuthority
# by copying the required Python runtime and IABV modules to C:\ProgramData\IABV\service_runtime
#
# CRITICAL: This script does NOT generate authority keys or execute provisioning.
# It only prepares the secure runtime and installs the service.

Write-Output "=== P0-B V4-R9.5 MACHINE-SCOPED RUNTIME DEPLOYMENT ==="
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

# PHASE 1: Verify source runtime exists
Write-Output "=== PHASE 1: VERIFY SOURCE RUNTIME ==="
$sourcePython = "C:\Users\faber\miniconda3"
if (-not (Test-Path $sourcePython)) {
    Write-Output "ERROR: Source Python runtime not found: $sourcePython"
    exit 1
}
Write-Output "Source Python runtime verified: $sourcePython"
Write-Output ""

# PHASE 2: Verify repository state
Write-Output "=== PHASE 2: VERIFY REPOSITORY STATE ==="
$repoPath = "C:\Python\IABV_v1.5"
if (-not (Test-Path "$repoPath\src\iabv_v15")) {
    Write-Output "ERROR: IABV source modules not found: $repoPath\src\iabv_v15"
    exit 1
}
Write-Output "IABV source modules verified: $repoPath\src\iabv_v15"
Write-Output ""

# PHASE 3: Remove existing service
Write-Output "=== PHASE 3: REMOVE EXISTING SERVICE ==="
try {
    $env:PYTHONPATH="$repoPath\src"
    & "$sourcePython\python.exe" -m iabv_v15.services.development.authority_windows_service remove
    Write-Output "Existing service removed"
} catch {
    Write-Output "Service may not have existed, continuing..."
}
Write-Output ""

# PHASE 4: Create machine-scoped runtime directory
Write-Output "=== PHASE 4: CREATE MACHINE-SCOPED RUNTIME DIRECTORY ==="
$serviceRuntimePath = "C:\ProgramData\IABV\service_runtime"
if (Test-Path $serviceRuntimePath) {
    Write-Output "Removing existing runtime directory: $serviceRuntimePath"
    Remove-Item -Path $serviceRuntimePath -Recurse -Force
}
New-Item -Path $serviceRuntimePath -ItemType Directory -Force
Write-Output "Machine-scoped runtime directory created: $serviceRuntimePath"
Write-Output ""

# PHASE 5: Copy Python runtime components
Write-Output "=== PHASE 5: COPY PYTHON RUNTIME COMPONENTS ==="
Write-Output "Copying Python core executables..."
Copy-Item -Path "$sourcePython\python.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\pythonw.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\python313.dll" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\pythonservice.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\pywintypes313.dll" -Destination "$serviceRuntimePath\" -Force

Write-Output "Copying python313.zip (standard library)..."
if (Test-Path "$sourcePython\python313.zip") {
    Copy-Item -Path "$sourcePython\python313.zip" -Destination "$serviceRuntimePath\" -Force
}

Write-Output "Copying DLLs directory..."
New-Item -Path "$serviceRuntimePath\DLLs" -ItemType Directory -Force
Copy-Item -Path "$sourcePython\DLLs\*" -Destination "$serviceRuntimePath\DLLs\" -Recurse -Force

Write-Output "Copying Lib (standard library)..."
New-Item -Path "$serviceRuntimePath\Lib" -ItemType Directory -Force
Copy-Item -Path "$sourcePython\Lib\*" -Destination "$serviceRuntimePath\Lib\" -Recurse -Force

Write-Output "Copying site-packages (pywin32, cryptography)..."
New-Item -Path "$serviceRuntimePath\Lib\site-packages" -ItemType Directory -Force

# Copy pywin32
Write-Output "  - Copying pywin32 modules..."
Copy-Item -Path "$sourcePython\Lib\site-packages\win32" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$sourcePython\Lib\site-packages\pywin32*" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force

# Copy cryptography
Write-Output "  - Copying cryptography package..."
Copy-Item -Path "$sourcePython\Lib\site-packages\cryptography" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$sourcePython\Lib\site-packages\cryptography-*.dist-info" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force

Write-Output "Python runtime copied successfully"
Write-Output ""

# PHASE 6: Copy IABV service modules
Write-Output "=== PHASE 6: COPY IABV SERVICE MODULES ==="
$iabvSource = "$repoPath\src"
$iabvTarget = "$serviceRuntimePath\iabv_v15"
New-Item -Path $iabvTarget -ItemType Directory -Force
Copy-Item -Path "$iabvSource\iabv_v15" -Destination "$serviceRuntimePath\" -Recurse -Force
Write-Output "IABV service modules copied to: $iabvTarget"
Write-Output ""

# PHASE 7: Configure ACLs for machine-scoped runtime
Write-Output "=== PHASE 7: CONFIGURE MACHINE-SCOPED RUNTIME ACLS ==="
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

# PHASE 8: Verify ACLs
Write-Output "=== PHASE 8: VERIFY ACLS ==="
icacls $serviceRuntimePath
Write-Output ""

# PHASE 9: Install service with machine-scoped PathName
Write-Output "=== PHASE 9: INSTALL SERVICE WITH MACHINE-SCOPED PATHNAME ==="
$env:PYTHONPATH="$serviceRuntimePath"
$pythonservicePath = "$serviceRuntimePath\pythonservice.exe"
& "$serviceRuntimePath\python.exe" -m iabv_v15.services.development.authority_windows_service install $pythonservicePath
Write-Output ""

# PHASE 10: Verify service installation
Write-Output "=== PHASE 10: VERIFY SERVICE INSTALLATION ==="
$service = Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'"
Write-Output "Service Name: $($service.Name)"
Write-Output "Service State: $($service.State)"
Write-Output "Service StartName: $($service.StartName)"
Write-Output "Service PathName: $($service.PathName)"
Write-Output ""

# PHASE 11: Verify StartName is LocalService
Write-Output "=== PHASE 11: VERIFY SERVICE IDENTITY ==="
if ($service.StartName -ne "NT AUTHORITY\LocalService") {
    Write-Output "ERROR: Service StartName is not LocalService"
    Write-Output "Current StartName: $($service.StartName)"
    exit 1
}
Write-Output "SUCCESS: Service StartName is NT AUTHORITY\LocalService"
Write-Output ""

# PHASE 12: Verify PathName points to machine-scoped runtime
Write-Output "=== PHASE 12: VERIFY EXECUTION BOUNDARY ==="
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

# PHASE 13: Verify critical runtime components exist
Write-Output "=== PHASE 13: VERIFY CRITICAL RUNTIME COMPONENTS ==="
$requiredFiles = @(
    "$serviceRuntimePath\python.exe",
    "$serviceRuntimePath\python313.dll",
    "$serviceRuntimePath\pythonservice.exe",
    "$serviceRuntimePath\pywintypes313.dll",
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

# PHASE 14: Verify ACLs on critical components
Write-Output "=== PHASE 14: VERIFY CRITICAL COMPONENT ACLS ==="
$criticalPaths = @(
    "$serviceRuntimePath\python.exe",
    "$serviceRuntimePath\pythonservice.exe",
    "$serviceRuntimePath\Lib\site-packages\cryptography"
)

foreach ($path in $criticalPaths) {
    if (Test-Path $path) {
        Write-Output "ACL for $path:"
        icacls $path
    }
}
Write-Output ""

# PHASE 15: Final summary
Write-Output "=== MACHINE-SCOPED RUNTIME DEPLOYMENT COMPLETE ==="
Write-Output ""
Write-Output "DEPLOYMENT SUMMARY:"
Write-Output "  Runtime Path: $serviceRuntimePath"
Write-Output "  Service Name: $($service.Name)"
Write-Output "  Service Identity: $($service.StartName)"
Write-Output "  Service PathName: $($service.PathName)"
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
