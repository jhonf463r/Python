# P0-B V4-R9.4 Secure Service Runtime Deployment
# Execute this from PowerShell as Administrator
# This script creates a machine-scoped protected runtime for IABVAuditAuthority

Write-Output "=== P0-B V4-R9.4 SECURE RUNTIME DEPLOYMENT ==="
Write-Output ""

# Verify elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Output "ERROR: This script must be run as Administrator"
    exit 1
}

Write-Output "Administrator context confirmed: YES"
Write-Output ""

# Verify repository state
Write-Output "Verifying repository state..."
cd C:\Python\IABV_v1.5
$head = git rev-parse HEAD
$expected = "3d65e619a8813d677b68c4c12aaa250da8196744"
if ($head -ne $expected) {
    Write-Output "ERROR: HEAD mismatch. Expected: $expected, Got: $head"
    exit 1
}
Write-Output "Repository HEAD verified: $head"
Write-Output ""

# PHASE 1: Create service runtime directory
Write-Output "=== PHASE 1: CREATE SERVICE RUNTIME DIRECTORY ==="
$serviceRuntimePath = "C:\ProgramData\IABV\service_runtime"
New-Item -Path $serviceRuntimePath -ItemType Directory -Force
Write-Output "Service runtime directory created: $serviceRuntimePath"
Write-Output ""

# PHASE 2: Configure ACL for service runtime
Write-Output "=== PHASE 2: CONFIGURE SERVICE RUNTIME ACL ==="
icacls $serviceRuntimePath /inheritance:r
icacls $serviceRuntimePath /grant:r "LocalService:(OI)(CI)RX"
icacls $serviceRuntimePath /grant:r "Administrators:(OI)(CI)F"
icacls $serviceRuntimePath /grant:r "SYSTEM:(OI)(CI)F"
icacls $serviceRuntimePath /deny "Users:(OI)(CI)F"
Write-Output "Service runtime ACL configured"
Write-Output ""

# PHASE 3: Configure ACL for source directory (make read-only for normal users)
Write-Output "=== PHASE 3: CONFIGURE SOURCE DIRECTORY ACL ==="
$sourcePath = "C:\Python\IABV_v1.5\src"
icacls $sourcePath /inheritance:r
icacls $sourcePath /grant:r "LocalService:(OI)(CI)RX"
icacls $sourcePath /grant:r "Administrators:(OI)(CI)F"
icacls $sourcePath /grant:r "SYSTEM:(OI)(CI)F"
icacls $sourcePath /grant:r "Users:(OI)(CI)R"
Write-Output "Source directory ACL configured (Users=Read only)"
Write-Output ""

# PHASE 4: Grant LocalService access to Python runtime
Write-Output "=== PHASE 4: GRANT LOCALSERVICE ACCESS TO PYTHON RUNTIME ==="
$pythonPath = "C:\Users\faber\miniconda3"
icacls $pythonPath /grant:r "LocalService:(OI)(CI)RX"
Write-Output "LocalService granted Read/Execute to Python runtime"
Write-Output ""

# PHASE 5: Remove existing service
Write-Output "=== PHASE 5: REMOVE EXISTING SERVICE ==="
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m iabv_v15.services.development.authority_windows_service remove
Write-Output ""

# PHASE 6: Install service (removing custom _exe_name_ for simplicity)
Write-Output "=== PHASE 6: INSTALL SERVICE ==="
# Remove custom _exe_name_ to use default pythonservice.exe from existing Python
& 'C:\Users\faber\miniconda3\python.exe' -m iabv_v15.services.development.authority_windows_service install
Write-Output ""

# Verify service installation
Write-Output "=== VERIFY SERVICE INSTALLATION ==="
Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'" | Select-Object Name, State, StartName, PathName, ProcessId
Write-Output ""
sc.exe qc IABVAuditAuthority
Write-Output ""

# Verify service path
$service = Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'"
Write-Output "Service PathName: $($service.PathName)"
if ($service.PathName -notlike "*service_runtime*") {
    Write-Output "WARNING: Service PathName does not point to protected runtime"
}

Write-Output "=== SECURE RUNTIME DEPLOYMENT COMPLETE ==="
Write-Output "Next: Test service startup and proceed with provisioning"
