# L5 Evidence Capture Script
# Captures git provenance externally before test execution
# Calculates artifact SHA256 independently after test execution

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Capture git provenance BEFORE execution
$provenance = @{}
try {
    $provenance['tested_head'] = git rev-parse HEAD
    $provenance['parent'] = git rev-parse HEAD^
    $provenance['tree'] = git rev-parse HEAD^{tree}
    $provenance['branch'] = git branch --show-current
    $provenance['repo'] = git config --get remote.origin.url
    $provenance['timestamp_start'] = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
} catch {
    Write-Host "ERROR: Could not capture git provenance: $_"
    exit 1
}

Write-Host "=== GIT PROVENANCE CAPTURE ==="
Write-Host "REPO: $($provenance['repo'])"
Write-Host "BRANCH: $($provenance['branch'])"
Write-Host "TESTED_HEAD: $($provenance['tested_head'])"
Write-Host "PARENT: $($provenance['parent'])"
Write-Host "TREE_SHA: $($provenance['tree'])"
Write-Host "TIMESTAMP_START: $($provenance['timestamp_start'])"
Write-Host ""

# Run the test
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "l5_experiment_${timestamp}_runtime.log"

Write-Host "=== RUNNING L5 TEST ==="
Write-Host "LOG: $logFile"
Write-Host ""

$env:PYTHONPATH = "$scriptDir\src"
$testResult = python -m pytest -vv -s tests/windows_e2e/test_l5_real_g3_causal_closure.py::test_l5_real_g3_causal_closure 2>&1 | Tee-Object -FilePath $logFile

$provenance['timestamp_end'] = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$provenance['exit_code'] = $LASTEXITCODE

Write-Host ""
Write-Host "=== TEST COMPLETED ==="
Write-Host "EXIT_CODE: $($provenance['exit_code'])"
Write-Host "TIMESTAMP_END: $($provenance['timestamp_end'])"
Write-Host ""

# Calculate artifact SHA256 independently
if (Test-Path $logFile) {
    $artifactSha = certutil -hashfile $logFile SHA256
    $artifactSha256 = ($artifactSha -split '\n')[1].Trim().ToLower()

    Write-Host "=== ARTIFACT INTEGRITY ==="
    Write-Host "ARTIFACT_PATH: $logFile"
    Write-Host "ARTIFACT_SHA256: $artifactSha256"
    Write-Host ""

    # Create manifest
    $manifest = @"
EXPERIMENT_ID: $timestamp
REPO: $($provenance['repo'])
BRANCH: $($provenance['branch'])
TESTED_HEAD: $($provenance['tested_head'])
PARENT: $($provenance['parent'])
TREE_SHA: $($provenance['tree'])
RUNTIME_START: $($provenance['timestamp_start'])
RUNTIME_END: $($provenance['timestamp_end'])
ARTIFACT_PATH: $logFile
ARTIFACT_SHA256: $artifactSha256
EXIT_CODE: $($provenance['exit_code'])
"@

    $manifestFile = "l5_experiment_${timestamp}_manifest.txt"
    $manifest | Out-File -FilePath $manifestFile -Encoding UTF8

    Write-Host "=== MANIFEST CREATED ==="
    Write-Host "MANIFEST: $manifestFile"
    Write-Host ""

    Write-Host "=== COMPLETE EVIDENCE PACKAGE ==="
    Write-Host "1. Runtime log: $logFile"
    Write-Host "2. Manifest: $manifestFile"
    Write-Host "3. SHA256: $artifactSha256"
} else {
    Write-Host "ERROR: Log file not created: $logFile"
    exit 1
}

exit $provenance['exit_code']
