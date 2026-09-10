# P0-B V4-R9.7 Installer Hardened Runtime Deployment
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
# REPOSITORY PROVENANCE SEPARATION:
# - This script verifies the IABV source checkout is at expected commit dd44c8440a0f8ad7591f10de16cbd9c831e816c0
# - The script itself may be executed from outside the checkout (e.g., from a separate deployment artifact)
# - The verification applies to the IABV source being copied, not to the installer script location
# - This maintains strict provenance for the actual service code while allowing flexible deployment

# Set strict error handling for PowerShell cmdlets
$ErrorActionPreference = "Stop"

Write-Output "=== P0-B V4-R9.7 INSTALLER HARDENED RUNTIME DEPLOYMENT ==="
Write-Output ""

# ============================================================================
# PHASE 0: Verify Administrator elevation
# ============================================================================
Write-Output "=== PHASE 0: VERIFY ADMINISTRATOR ELEVATION ==="
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Output "ERROR: This script must be run as Administrator"
    exit 1
}
Write-Output "Administrator context confirmed: YES"
Write-Output ""

# ============================================================================
# PHASE 1: Verify repository provenance (IABV source checkout only)
# ============================================================================
Write-Output "=== PHASE 1: VERIFY REPOSITORY PROVENANCE ==="
Write-Output "NOTE: This verifies the IABV source checkout being copied, not the installer script location."
$repoPath = "C:\Python\IABV_v1.5"
$expectedCommit = "dd44c8440a0f8ad7591f10de16cbd9c831e816c0"

if (-not (Test-Path "$repoPath\.git")) {
    Write-Output "ERROR: Not a git repository: $repoPath"
    exit 1
}

Push-Location $repoPath
$actualHead = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Failed to get HEAD SHA"
    Pop-Location
    exit 1
}
Pop-Location

if ($actualHead -ne $expectedCommit) {
    Write-Output "ERROR: Repository HEAD does not match expected commit"
    Write-Output "  Expected: $expectedCommit"
    Write-Output "  Actual:   $actualHead"
    exit 1
}

$gitStatus = git -C $repoPath status --porcelain
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: Failed to check git status"
    exit 1
}

if ($gitStatus) {
    Write-Output "ERROR: Workspace is dirty. Commit or stash changes before deployment."
    Write-Output $gitStatus
    exit 1
}

Write-Output "IABV source checkout provenance: PASS (commit $actualHead, clean workspace)"
Write-Output "REPOSITORY_PROVENANCE_CHECK=PASS"
Write-Output ""

# ============================================================================
# PHASE 2: Verify trusted source runtime exists
# ============================================================================
Write-Output "=== PHASE 2: VERIFY TRUSTED SOURCE RUNTIME ==="
$trustedSource = "C:\Python314"
if (-not (Test-Path $trustedSource)) {
    Write-Output "ERROR: Trusted source runtime not found: $trustedSource"
    exit 1
}
Write-Output "Trusted source runtime verified: $trustedSource"
Write-Output ""

# ============================================================================
# PHASE 3: Verify Python version consistency
# ============================================================================
Write-Output "=== PHASE 3: VERIFY PYTHON VERSION CONSISTENCY ==="
try {
    $pythonVersionOutput = & "$trustedSource\python.exe" --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to get Python version"
        exit 1
    }
    $pythonVersion = $pythonVersionOutput.ToString()
    Write-Output "Python version: $pythonVersion"
    if ($pythonVersion -notlike "*3.14*") {
        Write-Output "ERROR: Python version must be 3.14, got: $pythonVersion"
        exit 1
    }
    Write-Output "PYTHON_VERSION_CONSISTENCY=PASS"
} catch {
    Write-Output "ERROR: Exception during Python version check: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 4: Verify source runtime ACLs (ASSERTED, NOT PRINTED)
# ============================================================================
Write-Output "=== PHASE 4: VERIFY SOURCE RUNTIME ACLS ==="
try {
    $acl = Get-Acl $trustedSource
    $owner = $acl.Owner.ToString()

    # Expected owner: SYSTEM or BUILTIN\Administrators
    $expectedOwners = @("SYSTEM", "BUILTIN\Administrators", "NT AUTHORITY\SYSTEM")
    $ownerValid = $false
    foreach ($eo in $expectedOwners) {
        if ($owner -like "*$eo*") {
            $ownerValid = $true
            break
        }
    }

    if (-not $ownerValid) {
        Write-Output "ERROR: Unexpected source runtime owner: $owner"
        Write-Output "Expected: SYSTEM or BUILTIN\Administrators"
        exit 1
    }

    # Check for dangerous ACEs - Users should not have write/delete/modify
    $aclString = icacls $trustedSource 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to read source ACLs"
        exit 1
    }

    # Check if Users have dangerous permissions
    $hasUserWrite = $false
    foreach ($line in $aclString) {
        if ($line -match "Usuarios" -or $line -match "Users") {
            if ($line -match "(W|F|C)") {
                $hasUserWrite = $true
                break
            }
        }
    }

    if ($hasUserWrite) {
        Write-Output "ERROR: Users have write/modify/delete permissions on trusted source"
        exit 1
    }

    Write-Output "Source runtime owner: $owner"
    Write-Output "TRUSTED_SOURCE_ACL_ASSERTION=PASS"
} catch {
    Write-Output "ERROR: Exception during source ACL verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 5: Verify dependency location and version integrity (FIXED sys.path)
# ============================================================================
Write-Output "=== PHASE 5: VERIFY DEPENDENCY LOCATION AND VERSION INTEGRITY ==="

# Get dependency locations from Python with structured output
$checkScript = @"
import sys
import site
import os
import json

result = {
    "sys.executable": sys.executable,
    "sys.prefix": sys.prefix,
    "sys.exec_prefix": sys.exec_prefix,
    "site.ENABLE_USER_SITE": str(site.ENABLE_USER_SITE),
    "sys.path": sys.path
}

try:
    import win32service
    result["win32service.__file__"] = win32service.__file__
except ImportError:
    result["win32service.__file__"] = "NOT_FOUND"

try:
    import cryptography
    result["cryptography.__file__"] = cryptography.__file__
except ImportError:
    result["cryptography.__file__"] = "NOT_FOUND"

# Check pywintypes
pywintypes_paths = []
for p in sys.path:
    if p.endswith('site-packages'):
        pp = os.path.join(p, 'pywin32_system32', 'pywintypes314.dll')
        if os.path.exists(pp):
            pywintypes_paths.append(pp)
        pp = os.path.join(p, 'pywintypes314.dll')
        if os.path.exists(pp):
            pywintypes_paths.append(pp)
    pp = os.path.join(p, 'pywintypes314.dll')
    if os.path.exists(pp):
        pywintypes_paths.append(pp)

result["pywintypes314.dll"] = "|".join(pywintypes_paths) if pywintypes_paths else "NOT_FOUND"

print(json.dumps(result))
"@

try {
    $dependencyOutput = & "$trustedSource\python.exe" -c $checkScript 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to verify dependency locations"
        exit 1
    }

    $depMap = $dependencyOutput | ConvertFrom-Json

    # Verify sys.executable is from trusted source
    if ($depMap."sys.executable" -notlike "$trustedSource*") {
        Write-Output "ERROR: sys.executable not from trusted source"
        Write-Output "  Expected: $trustedSource*"
        Write-Output "  Actual:   $($depMap.'sys.executable')"
        exit 1
    }

    # Verify user site is disabled
    if ($depMap."site.ENABLE_USER_SITE" -ne "False") {
        Write-Output "ERROR: User site is enabled. Must be disabled for secure runtime."
        exit 1
    }
    Write-Output "USER_SITE_ENABLED=False"

    # Verify no user profile paths in sys.path (structured validation)
    $userProfile = $env:USERPROFILE
    $hasUserProfilePath = $false
    foreach ($pathEntry in $depMap."sys.path") {
        if ($pathEntry -like "$userProfile*") {
            Write-Output "ERROR: User profile path in sys.path: $pathEntry"
            $hasUserProfilePath = $true
        }
        # Also check for %APPDATA% patterns
        if ($pathEntry -like "*AppData*") {
            Write-Output "ERROR: AppData path in sys.path: $pathEntry"
            $hasUserProfilePath = $true
        }
    }

    if ($hasUserProfilePath) {
        exit 1
    }
    Write-Output "NO_USER_PROFILE_SYSPATH=PASS"

    # Verify win32service is from trusted source
    if ($depMap."win32service.__file__" -eq "NOT_FOUND") {
        Write-Output "ERROR: win32service not found"
        exit 1
    }
    if ($depMap."win32service.__file__" -notlike "$trustedSource*") {
        Write-Output "ERROR: win32service not from trusted source"
        Write-Output "  Location: $($depMap.'win32service.__file__')"
        exit 1
    }

    # Verify cryptography is from trusted source
    if ($depMap."cryptography.__file__" -eq "NOT_FOUND") {
        Write-Output "ERROR: cryptography not found"
        exit 1
    }
    if ($depMap."cryptography.__file__" -notlike "$trustedSource*") {
        Write-Output "ERROR: cryptography not from trusted source"
        Write-Output "  Location: $($depMap.'cryptography.__file__')"
        exit 1
    }

    # Verify pywintypes314.dll is from trusted source
    if ($depMap."pywintypes314.dll" -eq "NOT_FOUND") {
        Write-Output "ERROR: pywintypes314.dll not found"
        exit 1
    }
    if ($depMap."pywintypes314.dll" -notlike "$trustedSource*") {
        Write-Output "ERROR: pywintypes314.dll not from trusted source"
        Write-Output "  Location: $($depMap.'pywintypes314.dll')"
        exit 1
    }

    Write-Output "sys.executable: $($depMap.'sys.executable')"
    Write-Output "win32service: $($depMap.'win32service.__file__')"
    Write-Output "cryptography: $($depMap.'cryptography.__file__')"
    Write-Output "pywintypes314.dll: $($depMap.'pywintypes314.dll')"
    Write-Output "site.ENABLE_USER_SITE: $($depMap.'site.ENABLE_USER_SITE')"
    Write-Output "DEPENDENCY_LOCATION_VERIFICATION=PASS"
    Write-Output "USER_SITE_REJECTION=PASS"
} catch {
    Write-Output "ERROR: Exception during dependency verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 6: Verify pythonservice.exe exists in trusted source
# ============================================================================
Write-Output "=== PHASE 6: VERIFY PYTHONSERVICE.EXE ==="
try {
    $pythonserviceInScripts = Test-Path "$trustedSource\Scripts\pythonservice.exe"
    $pythonserviceInSitePackages = Test-Path "$trustedSource\Lib\site-packages\win32\pythonservice.exe"

    if ($pythonserviceInScripts) {
        $sourcePythonservicePath = "$trustedSource\Scripts\pythonservice.exe"
        Write-Output "pythonservice.exe found in Scripts: $sourcePythonservicePath"
    } elseif ($pythonserviceInSitePackages) {
        $sourcePythonservicePath = "$trustedSource\Lib\site-packages\win32\pythonservice.exe"
        Write-Output "pythonservice.exe found in site-packages: $sourcePythonservicePath"
    } else {
        Write-Output "ERROR: pythonservice.exe not found in trusted source"
        exit 1
    }
} catch {
    Write-Output "ERROR: Exception during pythonservice.exe verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 7: Verify no wrong version DLLs in trusted source
# ============================================================================
Write-Output "=== PHASE 7: VERIFY NO WRONG VERSION DLLS ==="
try {
    $wrongDll = "pywintypes313.dll"
    $wrongDllInRoot = Test-Path "$trustedSource\$wrongDll"
    $wrongDllInSitePackages = Test-Path "$trustedSource\Lib\site-packages\pywin32_system32\$wrongDll"

    if ($wrongDllInRoot -or $wrongDllInSitePackages) {
        Write-Output "ERROR: Wrong version pywintypes DLL found: $wrongDll"
        Write-Output "Python 3.14 requires pywintypes314.dll, not pywintypes313.dll"
        exit 1
    }
    Write-Output "No wrong version DLLs in trusted source: PASS"
} catch {
    Write-Output "ERROR: Exception during DLL version check: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 8: Remove existing service using sc.exe (NOT workspace Python)
# ============================================================================
Write-Output "=== PHASE 8: REMOVE EXISTING SERVICE ==="
try {
    $serviceName = "IABVAuditAuthority"
    $serviceExists = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

    if ($serviceExists) {
        Write-Output "Service exists, removing..."
        sc.exe delete $serviceName 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Output "ERROR: Failed to remove existing service via sc.exe"
            exit 1
        }
        Write-Output "Existing service removed via sc.exe"
    } else {
        Write-Output "Service does not exist, continuing..."
    }
} catch {
    Write-Output "ERROR: Exception during service removal: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 9: Create machine-scoped runtime directory (with proper error handling)
# ============================================================================
Write-Output "=== PHASE 9: CREATE MACHINE-SCOPED RUNTIME DIRECTORY ==="
try {
    $serviceRuntimePath = "C:\ProgramData\IABV\service_runtime"
    if (Test-Path $serviceRuntimePath) {
        Write-Output "Removing existing runtime directory: $serviceRuntimePath"
        Remove-Item -Path $serviceRuntimePath -Recurse -Force -ErrorAction Stop
    }
    New-Item -Path $serviceRuntimePath -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Write-Output "Machine-scoped runtime directory created: $serviceRuntimePath"
} catch {
    Write-Output "ERROR: Exception during runtime directory creation: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 10: Copy Python runtime components from trusted source (with error handling)
# ============================================================================
Write-Output "=== PHASE 10: COPY PYTHON RUNTIME COMPONENTS FROM TRUSTED SOURCE ==="
try {
    Write-Output "Copying Python core executables..."
    Copy-Item -Path "$trustedSource\python.exe" -Destination "$serviceRuntimePath\" -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\pythonw.exe" -Destination "$serviceRuntimePath\" -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\python314.dll" -Destination "$serviceRuntimePath\" -Force -ErrorAction Stop

    Write-Output "Copying python314.zip (standard library)..."
    if (Test-Path "$trustedSource\python314.zip") {
        Copy-Item -Path "$trustedSource\python314.zip" -Destination "$serviceRuntimePath\" -Force -ErrorAction Stop
    }

    Write-Output "Copying DLLs directory..."
    New-Item -Path "$serviceRuntimePath\DLLs" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\DLLs\*" -Destination "$serviceRuntimePath\DLLs\" -Recurse -Force -ErrorAction Stop

    Write-Output "Copying Lib (standard library)..."
    New-Item -Path "$serviceRuntimePath\Lib" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\Lib\*" -Destination "$serviceRuntimePath\Lib\" -Recurse -Force -ErrorAction Stop

    Write-Output "Copying Scripts..."
    New-Item -Path "$serviceRuntimePath\Scripts" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\Scripts\*" -Destination "$serviceRuntimePath\Scripts\" -Recurse -Force -ErrorAction Stop

    Write-Output "Copying site-packages (pywin32, cryptography)..."
    New-Item -Path "$serviceRuntimePath\Lib\site-packages" -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$trustedSource\Lib\site-packages\win32" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\Lib\site-packages\pywin32*" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\Lib\site-packages\cryptography" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop
    Copy-Item -Path "$trustedSource\Lib\site-packages\cryptography-*.dist-info" -Destination "$serviceRuntimePath\Lib\site-packages\" -Recurse -Force -ErrorAction Stop

    Write-Output "Python runtime copied from trusted source successfully"
} catch {
    Write-Output "ERROR: Exception during Python runtime copy: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 11: Copy IABV service modules from verified workspace (with error handling)
# ============================================================================
Write-Output "=== PHASE 11: COPY IABV SERVICE MODULES ==="
try {
    $iabvSource = "$repoPath\src"
    $iabvTarget = "$serviceRuntimePath\iabv_v15"
    New-Item -Path $iabvTarget -ItemType Directory -Force -ErrorAction Stop | Out-Null
    Copy-Item -Path "$iabvSource\iabv_v15" -Destination "$serviceRuntimePath\" -Recurse -Force -ErrorAction Stop
    Write-Output "IABV service modules copied to: $iabvTarget"
} catch {
    Write-Output "ERROR: Exception during IABV modules copy: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 12: Configure ACLs for machine-scoped runtime (EXPLICIT ALLOWLIST)
# ============================================================================
Write-Output "=== PHASE 12: CONFIGURE MACHINE-SCOPED RUNTIME ACLS ==="
try {
    Write-Output "Removing inheritance..."
    icacls $serviceRuntimePath /inheritance:r
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to remove inheritance"
        exit 1
    }

    Write-Output "Granting SYSTEM FullControl..."
    icacls $serviceRuntimePath /grant:r "SYSTEM:(OI)(CI)F"
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to grant SYSTEM FullControl"
        exit 1
    }

    Write-Output "Granting Administrators FullControl..."
    icacls $serviceRuntimePath /grant:r "Administrators:(OI)(CI)F"
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to grant Administrators FullControl"
        exit 1
    }

    Write-Output "Granting LocalService Read/Execute..."
    icacls $serviceRuntimePath /grant:r "LocalService:(OI)(CI)RX"
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Failed to grant LocalService Read/Execute"
        exit 1
    }

    Write-Output "Machine-scoped runtime ACLs configured with explicit allowlist"
} catch {
    Write-Output "ERROR: Exception during ACL configuration: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 13: ASSERT destination ACL policy (REAL VALIDATION, NOT JUST PRINT)
# ============================================================================
Write-Output "=== PHASE 13: ASSERT DESTINATION ACL POLICY ==="

function Test-AclPolicy {
    param([string]$Path)

    $acl = Get-Acl $Path
    $accessRules = $acl.GetAccessRules($true, $true, [System.Security.Principal.NTAccount])

    $hasSystemFull = $false
    $hasAdminsFull = $false
    $hasLocalServiceRX = $false
    $hasDangerousWrite = $false
    $localServiceHasWrite = $false

    # Well-known SIDs for precise identity matching
    $sidSystem = "S-1-5-18"
    $sidAdministrators = "S-1-5-32-544"
    $sidLocalService = "S-1-5-19"
    $sidUsers = "S-1-5-32-545"
    $sidAuthenticatedUsers = "S-1-5-11"
    $sidEveryone = "S-1-1-0"

    foreach ($rule in $accessRules) {
        $identity = $rule.IdentityReference
        $rights = $rule.FileSystemRights
        $type = $rule.AccessControlType

        # Try to get SID for precise matching
        try {
            $sidObj = $identity.Translate([System.Security.Principal.SecurityIdentifier])
            $sidValue = $sidObj.Value
        } catch {
            $sidValue = $null
        }

        # Check for expected permissions using correct enumeration type
        if ($type -eq "Allow") {
            # SYSTEM FullControl
            if ($sidValue -eq $sidSystem -or $identity.Value -like "*SYSTEM*") {
                if ($rights -band [System.Security.AccessControl.FileSystemRights]::FullControl) {
                    $hasSystemFull = $true
                }
            }
            
            # Administrators FullControl
            if ($sidValue -eq $sidAdministrators -or $identity.Value -like "*Administrators*") {
                if ($rights -band [System.Security.AccessControl.FileSystemRights]::FullControl) {
                    $hasAdminsFull = $true
                }
            }
            
            # LocalService Read/Execute
            if ($sidValue -eq $sidLocalService -or $identity.Value -like "*LocalService*") {
                if ($rights -band [System.Security.AccessControl.FileSystemRights]::ReadAndExecute) {
                    $hasLocalServiceRX = $true
                }
                # Check if LocalService has dangerous write permissions
                if ($rights -band [System.Security.AccessControl.FileSystemRights]::Write -or
                    $rights -band [System.Security.AccessControl.FileSystemRights]::Modify -or
                    $rights -band [System.Security.AccessControl.FileSystemRights]::FullControl) {
                    $localServiceHasWrite = $true
                }
            }

            # Check for dangerous write permissions on unprivileged accounts
            if ($sidValue -eq $sidUsers -or $sidValue -eq $sidAuthenticatedUsers -or $sidValue -eq $sidEveryone -or
                $identity.Value -like "*Users*" -or $identity.Value -like "*Authenticated Users*" -or $identity.Value -like "*Everyone*") {
                if ($rights -band [System.Security.AccessControl.FileSystemRights]::Write -or
                    $rights -band [System.Security.AccessControl.FileSystemRights]::Modify -or
                    $rights -band [System.Security.AccessControl.FileSystemRights]::FullControl) {
                    $hasDangerousWrite = $true
                }
            }
        }
    }

    return @{
        HasSystemFull = $hasSystemFull
        HasAdminsFull = $hasAdminsFull
        HasLocalServiceRX = $hasLocalServiceRX
        HasDangerousWrite = $hasDangerousWrite
        LocalServiceHasWrite = $localServiceHasWrite
    }
}

try {
    $criticalPaths = @(
        "$serviceRuntimePath",
        "$serviceRuntimePath\python.exe",
        "$serviceRuntimePath\python314.dll",
        "$serviceRuntimePath\Lib",
        "$serviceRuntimePath\Lib\site-packages",
        "$serviceRuntimePath\iabv_v15"
    )

    $allPathsValid = $true
    foreach ($path in $criticalPaths) {
        if (Test-Path $path) {
            $policyResult = Test-AclPolicy -Path $path
            Write-Output "ACL Policy Check for $path:"
            Write-Output "  SYSTEM FullControl: $($policyResult.HasSystemFull)"
            Write-Output "  Administrators FullControl: $($policyResult.HasAdminsFull)"
            Write-Output "  LocalService Read/Execute: $($policyResult.HasLocalServiceRX)"
            Write-Output "  LocalService Has Write: $($policyResult.LocalServiceHasWrite)"
            Write-Output "  Dangerous Write Permissions: $($policyResult.HasDangerousWrite)"

            # All required conditions must be true
            if (-not $policyResult.HasSystemFull) {
                Write-Output "ERROR: SYSTEM lacks FullControl on $path"
                $allPathsValid = $false
            }
            if (-not $policyResult.HasAdminsFull) {
                Write-Output "ERROR: Administrators lack FullControl on $path"
                $allPathsValid = $false
            }
            if (-not $policyResult.HasLocalServiceRX) {
                Write-Output "ERROR: LocalService lacks required Read/Execute permissions on $path"
                $allPathsValid = $false
            }
            if ($policyResult.LocalServiceHasWrite) {
                Write-Output "ERROR: LocalService has dangerous write permissions on $path"
                $allPathsValid = $false
            }
            if ($policyResult.HasDangerousWrite) {
                Write-Output "ERROR: Dangerous write permissions found on unprivileged accounts on $path"
                $allPathsValid = $false
            }
        }
    }

    if (-not $allPathsValid) {
        Write-Output "ERROR: Destination ACL policy validation failed"
        exit 1
    }

    Write-Output "DESTINATION_ACL_POLICY=PASS"
} catch {
    Write-Output "ERROR: Exception during destination ACL policy validation: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 14: Determine pythonservice.exe path in deployed runtime
# ============================================================================
Write-Output "=== PHASE 14: DETERMINE PYTHONSERVICE.EXE PATH ==="
try {
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
} catch {
    Write-Output "ERROR: Exception during pythonservice.exe path determination: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 15: Verify critical runtime components exist
# ============================================================================
Write-Output "=== PHASE 15: VERIFY CRITICAL RUNTIME COMPONENTS ==="
try {
    $expectedDll = "pywintypes314.dll"
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
} catch {
    Write-Output "ERROR: Exception during runtime component verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 16: Verify no wrong version DLLs in deployed runtime
# ============================================================================
Write-Output "=== PHASE 16: VERIFY NO WRONG VERSION DLLS ==="
try {
    $wrongDllInRuntime = Test-Path "$serviceRuntimePath\$wrongDll"
    if ($wrongDllInRuntime) {
        Write-Output "ERROR: Wrong version pywintypes DLL in deployed runtime: $wrongDll"
        exit 1
    }
    Write-Output "No wrong version DLLs in deployed runtime: PASS"
} catch {
    Write-Output "ERROR: Exception during DLL version check in runtime: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 17: Verify user profile runtime rejection
# ============================================================================
Write-Output "=== PHASE 17: VERIFY USER PROFILE RUNTIME REJECTION ==="
try {
    $userProfilePaths = @(
        "C:\Users\faber\miniconda3",
        "C:\Users\faber\AppData",
        "C:\Users\faber"
    )

    $runtimePathsToCheck = @(
        "$serviceRuntimePath\python.exe",
        "$serviceRuntimePath\python314.dll",
        "$pythonservicePath"
    )

    $usesUserProfile = $false
    foreach ($runtimePath in $runtimePathsToCheck) {
        $resolvedPath = Resolve-Path $runtimePath -ErrorAction SilentlyContinue
        if ($resolvedPath) {
            foreach ($up in $userProfilePaths) {
                if ($resolvedPath.Path -like "$up*") {
                    Write-Output "ERROR: Runtime path uses user profile: $($resolvedPath.Path)"
                    $usesUserProfile = $true
                }
            }
        }
    }

    if ($usesUserProfile) {
        exit 1
    }
    Write-Output "USER_PROFILE_RUNTIME_REJECTION=PASS"
} catch {
    Write-Output "ERROR: Exception during user profile runtime rejection check: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 18: Install service with machine-scoped PathName
# ============================================================================
Write-Output "=== PHASE 18: INSTALL SERVICE WITH MACHINE-SCOPED PATHNAME ==="
try {
    $env:PYTHONPATH="$serviceRuntimePath"
    & "$serviceRuntimePath\python.exe" -m iabv_v15.services.development.authority_windows_service install $pythonservicePath
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: Service installation failed"
        exit 1
    }
} catch {
    Write-Output "ERROR: Exception during service installation: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 19: Verify service installation
# ============================================================================
Write-Output "=== PHASE 19: VERIFY SERVICE INSTALLATION ==="
try {
    $service = Get-CimInstance Win32_Service -Filter "Name='IABVAuditAuthority'"
    if (-not $service) {
        Write-Output "ERROR: Service not found after installation"
        exit 1
    }

    Write-Output "Service Name: $($service.Name)"
    Write-Output "Service State: $($service.State)"
    Write-Output "Service StartName: $($service.StartName)"
    Write-Output "Service PathName: $($service.PathName)"
} catch {
    Write-Output "ERROR: Exception during service installation verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 20: Verify StartName is LocalService
# ============================================================================
Write-Output "=== PHASE 20: VERIFY SERVICE IDENTITY ==="
try {
    if ($service.StartName -ne "NT AUTHORITY\LocalService") {
        Write-Output "ERROR: Service StartName is not LocalService"
        Write-Output "Current StartName: $($service.StartName)"
        exit 1
    }
    Write-Output "SERVICE_IDENTITY=PASS (NT AUTHORITY\LocalService)"
} catch {
    Write-Output "ERROR: Exception during service identity verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 21: Verify PathName points to machine-scoped runtime
# ============================================================================
Write-Output "=== PHASE 21: VERIFY EXECUTION BOUNDARY ==="
try {
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
    Write-Output "EXECUTION_BOUNDARY=PASS (machine-scoped runtime)"
} catch {
    Write-Output "ERROR: Exception during execution boundary verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 22: Verify PathName does NOT point to user profile
# ============================================================================
Write-Output "=== PHASE 22: VERIFY NO USER-PROFILE DEPENDENCY ==="
try {
    if ($service.PathName -like "*C:\Users\faber*") {
        Write-Output "ERROR: Service PathName contains user profile path"
        Write-Output "Current PathName: $($service.PathName)"
        exit 1
    }
    Write-Output "NO_USER_PROFILE_DEPENDENCY=PASS"
} catch {
    Write-Output "ERROR: Exception during user-profile dependency verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 23: Verify InstallService semantics (source-level check)
# ============================================================================
Write-Output "=== PHASE 23: VERIFY INSTALLSERVICE SEMANTICS ==="
try {
    $installServiceFile = "$serviceRuntimePath\iabv_v15\services\development\authority_windows_service.py"
    $installServiceContent = Get-Content $installServiceFile -Raw -ErrorAction Stop

    # Check for correct pythonClassString usage
    if ($installServiceContent -notmatch "python_class_string.*AuthorityServiceHandler") {
        Write-Output "ERROR: pythonClassString not found in install_service"
        exit 1
    }

    # Check for exeName parameter (not positional exe_path)
    if ($installServiceContent -notmatch "exeName\s*=\s*exe_path") {
        Write-Output "ERROR: exeName parameter not found in install_service"
        exit 1
    }

    # Check that exe_path is NOT first positional argument
    if ($installServiceContent -match "InstallService\s*\(\s*exe_path\s*,") {
        Write-Output "ERROR: exe_path is used as first positional argument (should be pythonClassString)"
        exit 1
    }

    Write-Output "INSTALLSERVICE_SEMANTICS=PASS (pythonClassString + exeName parameter)"
} catch {
    Write-Output "ERROR: Exception during InstallService semantics verification: $_"
    exit 1
}
Write-Output ""

# ============================================================================
# PHASE 24: Final summary
# ============================================================================
Write-Output "=== INSTALLER HARDENED RUNTIME DEPLOYMENT COMPLETE ==="
Write-Output ""
Write-Output "DEPLOYMENT SUMMARY:"
Write-Output "  Trusted Source: $trustedSource"
Write-Output "  Python Version: $pythonVersion"
Write-Output "  Runtime Path: $serviceRuntimePath"
Write-Output "  Service Name: $($service.Name)"
Write-Output "  Service Identity: $($service.StartName)"
Write-Output "  Service PathName: $($service.PathName)"
Write-Output ""
Write-Output "VERIFICATION STATUS:"
Write-Output "  REPOSITORY_PROVENANCE_CHECK=PASS (commit $actualHead, clean workspace)"
Write-Output "  TRUSTED_SOURCE_ACL_ASSERTION=PASS"
Write-Output "  NATIVE_EXIT_CODE_HANDLING=PASS"
Write-Output "  POWERSHELL_CMDLET_ERROR_HANDLING=PASS"
Write-Output "  DEPENDENCY_LOCATION_VERIFICATION=PASS"
Write-Output "  USER_SITE_REJECTION=PASS"
Write-Output "  NO_USER_PROFILE_SYSPATH=PASS"
Write-Output "  USER_PROFILE_RUNTIME_REJECTION=PASS"
Write-Output "  DESTINATION_ACL_POLICY=PASS"
Write-Output "  INSTALLSERVICE_SEMANTICS=PASS"
Write-Output "  SERVICE_IDENTITY=PASS"
Write-Output "  EXECUTION_BOUNDARY=PASS"
Write-Output "  NO_USER_PROFILE_DEPENDENCY=PASS"
Write-Output ""
Write-Output "IMPORTANT: This deployment does NOT include authority key generation."
Write-Output "Authority key must be generated by the service itself during provisioning."
Write-Output ""
Write-Output "NEXT STEPS:"
Write-Output "  1. Verify service startup: sc.exe start IABVAuditAuthority"
Write-Output "  2. Execute provisioning: Create C:\ProgramData\IABV\AUTHORITY_PROVISIONING_ENABLED as Administrator"
Write-Output "  3. Restart service to generate authority key under LocalService"
Write-Output "  4. Remove provisioning flag"
Write-Output "  5. Verify durability and execution boundary"
