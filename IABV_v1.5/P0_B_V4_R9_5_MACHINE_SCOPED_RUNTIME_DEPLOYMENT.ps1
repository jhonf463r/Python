# P0-B V4-R9.5 Machine-Scoped Service Runtime Deployment
# Execute this from PowerShell as Administrator
# This script creates a REAL machine-scoped protected runtime for IABVAuditAuthority
# by copying the required Python runtime and IABV modules to C:\ProgramData\IABV\service_runtime

Write-Output "=== P0-B V4-R9.5 MACHINE-SCOPED RUNTIME DEPLOYMENT ==="
Write-Output ""

# Verify elevation
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

# PHASE 2: Remove existing service
Write-Output "=== PHASE 2: REMOVE EXISTING SERVICE ==="
try {
    & 'C:\Users\faber\miniconda3\python.exe' -m iabv_v15.services.development.authority_windows_service remove
    Write-Output "Existing service removed"
} catch {
    Write-Output "Service may not have existed, continuing..."
}
Write-Output ""

# PHASE 3: Create machine-scoped runtime directory
Write-Output "=== PHASE 3: CREATE MACHINE-SCOPED RUNTIME DIRECTORY ==="
$serviceRuntimePath = "C:\ProgramData\IABV\service_runtime"
Remove-Item -Path $serviceRuntimePath -Recurse -Force -ErrorAction SilentlyContinue
New-Item -Path $serviceRuntimePath -ItemType Directory -Force
Write-Output "Machine-scoped runtime directory created: $serviceRuntimePath"
Write-Output ""

# PHASE 4: Copy Python runtime components
Write-Output "=== PHASE 4: COPY PYTHON RUNTIME COMPONENTS ==="
Write-Output "Copying Python core..."
Copy-Item -Path "$sourcePython\python.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\pythonw.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\python313.dll" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\python313.zip" -Destination "$serviceRuntimePath\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$sourcePython\pythonservice.exe" -Destination "$serviceRuntimePath\" -Force
Copy-Item -Path "$sourcePython\pywintypes313.dll" -Destination "$serviceRuntimePath\" -Force

Write-Output "Copying DLLs..."
New-Item -Path "$serviceRuntimePath\DLLs" -ItemType Directory -Force
Copy-Item -Path "$sourcePython\DLLs\*" -Destination "$serviceRuntimePath\DLLs\" -Recurse -Force

Write-Output "Copying Lib (standard library)..."
New-Item -Path "$serviceRuntimePath\Lib" -ItemType Directory -Force
Copy-Item -Path "$sourcePython\Lib\*" -Destination "$serviceRuntimePath\Lib\" -Recurse -Force

Write-Output "Copying site-packages (pywin32, cryptography)..."
New-Item -Path "$serviceRuntimePath\Lib\site-packages" -ItemType Directory -Force
Copy-Item -Path "$sourcePython\Lib\site-packages\win32" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$sourcePython\Lib\site-packages\pywin32*" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$sourcePython\Lib\site-packages\cryptography" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force
Copy-Item -Path "$sourcePython\Lib\site-packages\cryptography-*.dist-info" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force

Write-Output "Python runtime copied successfully"
Write-Output ""

# PHASE 5: Copy IABV service modules
Write-Output "=== PHASE 5: COPY IABV SERVICE MODULES ==="
$iabvSource = "C:\Python\IABV_v1.5\src"
$iabvTarget = "$serviceRuntimePath\iabv_v15"
New-Item -Path $iabvTarget -ItemType Directory -Force
Copy-Item -Path "$iabvSource\iabv_v15" -Destination "$serviceRuntimePath\" -Recurse -Force
Write-Output "IABV service modules copied to: $iabvTarget"
Write-Output ""

# PHASE 6: Configure ACLs for machine-scoped runtime
Write-Output "=== PHASE 6: CONFIGURE MACHINE-SCOPED RUNTIME ACLS ==="
icacls $serviceRuntimePath /inheritance:r
icacls $serviceRuntimePath /grant:r "LocalService:(OI)(CI)RX"
icacls $serviceRuntimePath /grant:r "Administrators:(OI)(CI)F"
icacls $serviceRuntimePath /grant:r "SYSTEM:(OI)(CI)F"
icacls $serviceRuntimePath /deny "Users:(OI)(CI)F"
Write-Output "Machine-scoped runtime ACLs configured"
Write-Output ""

# PHASE 7: Verify ACLs
Write-Output "=== PHASE 7: VERIFY ACLS ==="
icacls $serviceRuntimePath
Write-Output ""

# PHASE 8: Install service with machine-scoped PathName
Write-Output "=== PHASE 8: INSTALL SERVICE WITH MACHINE-SCOPED PATHNAME ==="
$env:PYTHONPATH="$serviceRuntimePath"
$pythonservicePath = "$serviceRuntimePath\pythonservice.exe"
& "$serviceRuntimePath\python.exe" -m iabv_v15.services.development.authority_windows_service install $pythonservicePath
Write-Output ""

# PHASE 9: Verify service installation
Write-Output "=== PHASE 9: VERIFY SERVICE INSTALLATION ==="
$service = Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'"
Write-Output "Service Name: $($service.Name)"
Write-Output "Service State: $($service.State)"
Write-Output "Service StartName: $($service.StartName)"
Write-Output "Service PathName: $($service.PathName)"
Write-Output ""

# PHASE 10: Verify PathName points to machine-scoped runtime
Write-Output "=== PHASE 10: VERIFY EXECUTION BOUNDARY ==="
if ($service.PathName -like "*service_runtime*") {
    Write-Output "SUCCESS: Service PathName points to machine-scoped runtime"
} else {
    Write-Output "ERROR: Service PathName does NOT point to machine-scoped runtime"
    Write-Output "Current PathName: $($service.PathName)"
    exit 1
}
Write-Output ""

Write-Output "=== MACHINE-SCOPED RUNTIME DEPLOYMENT COMPLETE ==="
Write-Output "Next: Start service and execute provisioning"
