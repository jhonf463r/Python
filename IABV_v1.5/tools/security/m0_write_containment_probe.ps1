#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FixtureRoot,
    [Parameter(Mandatory = $true)]
    [string]$StateRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:Results = [System.Collections.Generic.List[object]]::new()
$script:ExpectedRead = 'M0_READ_CANARY_V1'
$script:ExpectedDelete = 'M0_DELETE_CANARY_V1'
$script:StartedUtc = [DateTime]::UtcNow

function Add-ProbeResult {
    param(
        [Parameter(Mandatory = $true)][string]$Operation,
        [Parameter(Mandatory = $true)][ValidateSet('PASS', 'FAIL', 'INCONCLUSIVE')][string]$Status,
        [Parameter(Mandatory = $true)][string]$Evidence,
        [System.Exception]$Exception = $null
    )

    $exceptionType = $null
    $hresult = $null
    $message = $null
    if ($null -ne $Exception) {
        $exceptionType = $Exception.GetType().FullName
        $hresult = '0x{0:X8}' -f [uint32]($Exception.HResult -band 0xffffffffL)
        $message = ([string]$Exception.Message -replace '[\r\n]+', ' ').Trim()
        if ($message.Length -gt 400) { $message = $message.Substring(0, 400) }
    }
    $script:Results.Add([pscustomobject]@{
        operation = $Operation
        status = $Status
        evidence = $Evidence
        exception_type = $exceptionType
        hresult = $hresult
        message = $message
    }) | Out-Null
}

function Test-OsAccessDenied {
    param([Parameter(Mandatory = $true)][System.Exception]$Exception)

    $current = $Exception
    while ($null -ne $current) {
        $unsignedHresult = [uint32]($current.HResult -band 0xffffffffL)
        if ($unsignedHresult -eq [uint32]0x80070005) { return $true }
        if (($current -is [System.ComponentModel.Win32Exception]) -and ($current.NativeErrorCode -eq 5)) {
            return $true
        }
        $current = $current.InnerException
    }
    return $false
}

function Get-OverallStatus {
    if (@($script:Results | Where-Object status -eq 'FAIL').Count -gt 0) { return 'FAIL' }
    if (@($script:Results | Where-Object status -eq 'INCONCLUSIVE').Count -gt 0) { return 'INCONCLUSIVE' }
    if (@($script:Results | Where-Object status -ne 'PASS').Count -gt 0) { return 'INCONCLUSIVE' }
    return 'PASS'
}

# Do not touch host folders if accidentally invoked outside the default Sandbox account.
$tokenName = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if ($tokenName -notmatch '(^|\\)WDAGUtilityAccount$') {
    [pscustomobject]@{
        overall = 'INCONCLUSIVE'
        operation = 'sandbox_principal_precondition'
        status = 'INCONCLUSIVE'
        evidence = 'Token identity is not the Windows Sandbox default WDAGUtilityAccount; no fixture/state path was accessed.'
        output_channel = 'stdout_only'
        report_persisted = $false
        shared_paths_accessed = $false
    } | ConvertTo-Json -Depth 4
    exit 2
}

try {
    $fixture = (Resolve-Path -LiteralPath $FixtureRoot).Path.TrimEnd('\')
    $state = (Resolve-Path -LiteralPath $StateRoot).Path.TrimEnd('\')
    if ($fixture -eq $state -or $fixture.StartsWith($state + '\', [System.StringComparison]::OrdinalIgnoreCase) -or $state.StartsWith($fixture + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'FixtureRoot and StateRoot must be separate, non-overlapping mapped folders.'
    }

    $readCanary = Join-Path $fixture 'M0-READ-CANARY.txt'
    $deleteCanary = Join-Path $fixture 'M0-DELETE-CANARY.txt'
    if (-not (Test-Path -LiteralPath $readCanary -PathType Leaf)) { throw 'Missing M0-READ-CANARY.txt; fixture precondition failed.' }
    if (-not (Test-Path -LiteralPath $deleteCanary -PathType Leaf)) { throw 'Missing M0-DELETE-CANARY.txt; fixture precondition failed.' }

    try {
        $readContent = [System.IO.File]::ReadAllText($readCanary)
        if ($readContent -ceq $script:ExpectedRead) {
            Add-ProbeResult -Operation 'fixture_read' -Status 'PASS' -Evidence 'Known read canary matched exactly.'
        } else {
            Add-ProbeResult -Operation 'fixture_read' -Status 'FAIL' -Evidence 'Canary content did not match the required literal.'
        }
    } catch {
        Add-ProbeResult -Operation 'fixture_read' -Status 'INCONCLUSIVE' -Evidence 'Read raised an exception; this is not evidence of successful read.' -Exception $_.Exception
    }

    $newFile = Join-Path $fixture ('M0-CREATE-PROBE-' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        $stream = [System.IO.File]::Open($newFile, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $stream.Dispose()
        Add-ProbeResult -Operation 'fixture_create' -Status 'FAIL' -Evidence 'A new file was created in the read-only fixture.'
        try {
            [System.IO.File]::Delete($newFile)
            Add-ProbeResult -Operation 'fixture_create_cleanup' -Status 'PASS' -Evidence 'Explicitly deleted only the unexpected probe file.'
        } catch {
            Add-ProbeResult -Operation 'fixture_create_cleanup' -Status 'INCONCLUSIVE' -Evidence 'Could not clean the explicitly named unexpected probe file.' -Exception $_.Exception
        }
    } catch {
        if (Test-Path -LiteralPath $newFile -PathType Leaf) {
            Add-ProbeResult -Operation 'fixture_create' -Status 'FAIL' -Evidence 'The create attempt left a file behind despite raising an exception.' -Exception $_.Exception
            try {
                [System.IO.File]::Delete($newFile)
                Add-ProbeResult -Operation 'fixture_create_cleanup' -Status 'PASS' -Evidence 'Explicitly deleted only the unexpected probe file.'
            } catch {
                Add-ProbeResult -Operation 'fixture_create_cleanup' -Status 'INCONCLUSIVE' -Evidence 'Could not clean the explicitly named unexpected probe file.' -Exception $_.Exception
            }
        } elseif (Test-OsAccessDenied -Exception $_.Exception) {
            Add-ProbeResult -Operation 'fixture_create' -Status 'PASS' -Evidence 'Windows returned access denied (0x80070005 / error 5), and no probe file exists.' -Exception $_.Exception
        } else {
            Add-ProbeResult -Operation 'fixture_create' -Status 'INCONCLUSIVE' -Evidence 'Failure was not identifiable as OS access denied.' -Exception $_.Exception
        }
    }

    try {
        [System.IO.File]::WriteAllText($deleteCanary, 'M0_MODIFY_PROBE_UNEXPECTED')
        Add-ProbeResult -Operation 'fixture_modify' -Status 'FAIL' -Evidence 'The pre-existing delete canary was unexpectedly modified.'
    } catch {
        if (Test-OsAccessDenied -Exception $_.Exception) {
            try {
                if ([System.IO.File]::ReadAllText($deleteCanary) -ceq $script:ExpectedDelete) {
                    Add-ProbeResult -Operation 'fixture_modify' -Status 'PASS' -Evidence 'Windows returned access denied and the canary remained unchanged.' -Exception $_.Exception
                } else {
                    Add-ProbeResult -Operation 'fixture_modify' -Status 'FAIL' -Evidence 'Access was denied, but the canary postcondition changed.' -Exception $_.Exception
                }
            } catch {
                Add-ProbeResult -Operation 'fixture_modify' -Status 'INCONCLUSIVE' -Evidence 'Could not verify the canary after access was denied.' -Exception $_.Exception
            }
        } else {
            Add-ProbeResult -Operation 'fixture_modify' -Status 'INCONCLUSIVE' -Evidence 'Failure was not identifiable as OS access denied.' -Exception $_.Exception
        }
    }

    try {
        [System.IO.File]::Delete($deleteCanary)
        if (Test-Path -LiteralPath $deleteCanary -PathType Leaf) {
            Add-ProbeResult -Operation 'fixture_delete' -Status 'INCONCLUSIVE' -Evidence 'Delete returned without exception but the canary still exists.'
        } else {
            Add-ProbeResult -Operation 'fixture_delete' -Status 'FAIL' -Evidence 'The pre-existing delete canary was unexpectedly deleted.'
        }
    } catch {
        if (Test-OsAccessDenied -Exception $_.Exception) {
            if (Test-Path -LiteralPath $deleteCanary -PathType Leaf) {
                Add-ProbeResult -Operation 'fixture_delete' -Status 'PASS' -Evidence 'Windows returned access denied and the canary remains present.' -Exception $_.Exception
            } else {
                Add-ProbeResult -Operation 'fixture_delete' -Status 'FAIL' -Evidence 'Access was denied, but the canary is missing.' -Exception $_.Exception
            }
        } else {
            Add-ProbeResult -Operation 'fixture_delete' -Status 'INCONCLUSIVE' -Evidence 'Failure was not identifiable as OS access denied.' -Exception $_.Exception
        }
    }

    $stateProbe = Join-Path $state ('M0-STATE-PROBE-' + [guid]::NewGuid().ToString('N') + '.tmp')
    $stateContent = 'M0_STATE_PROBE_V1'
    $stateWriteOk = $false
    try {
        [System.IO.File]::WriteAllText($stateProbe, $stateContent)
        $stateWriteOk = $true
        Add-ProbeResult -Operation 'state_write' -Status 'PASS' -Evidence 'Created the uniquely named state probe.'
    } catch {
        Add-ProbeResult -Operation 'state_write' -Status 'INCONCLUSIVE' -Evidence 'Could not write the authorized state probe.' -Exception $_.Exception
    }
    if ($stateWriteOk) {
        try {
            if ([System.IO.File]::ReadAllText($stateProbe) -ceq $stateContent) {
                Add-ProbeResult -Operation 'state_read' -Status 'PASS' -Evidence 'State probe content matched exactly.'
            } else {
                Add-ProbeResult -Operation 'state_read' -Status 'FAIL' -Evidence 'State probe content did not match.'
            }
        } catch {
            Add-ProbeResult -Operation 'state_read' -Status 'INCONCLUSIVE' -Evidence 'State probe could not be read.' -Exception $_.Exception
        }
        try {
            [System.IO.File]::Delete($stateProbe)
            if (-not (Test-Path -LiteralPath $stateProbe -PathType Leaf)) {
                Add-ProbeResult -Operation 'state_cleanup' -Status 'PASS' -Evidence 'Deleted only the uniquely named state probe.'
            } else {
                Add-ProbeResult -Operation 'state_cleanup' -Status 'FAIL' -Evidence 'State probe still exists after delete.'
            }
        } catch {
            Add-ProbeResult -Operation 'state_cleanup' -Status 'INCONCLUSIVE' -Evidence 'Could not delete only the named state probe.' -Exception $_.Exception
        }
    }

    $reportName = 'm0-write-containment-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [guid]::NewGuid().ToString('N') + '.json'
    $reportPath = Join-Path $state $reportName
    $report = [ordered]@{
        schema = 'm0-write-containment-probe/v1'
        started_utc = $script:StartedUtc.ToString('o')
        token_name = $tokenName
        fixture_root_in_sandbox = $fixture
        state_root_in_sandbox = $state
        overall = (Get-OverallStatus)
        results = @($script:Results)
        scope_note = 'Probe covers mapped fixture and state paths only; it does not prove the real Codex process uses this Sandbox or that all guest-local writes are confined.'
    }
    $json = $report | ConvertTo-Json -Depth 7
    [System.IO.File]::WriteAllText($reportPath, $json, [System.Text.UTF8Encoding]::new($false))
    $persistedJson = [System.IO.File]::ReadAllText($reportPath)
    if ($persistedJson -cne $json) { throw 'Persisted report read-back did not exactly match the report written.' }
    $persistedReport = $persistedJson | ConvertFrom-Json
    if ($persistedReport.schema -cne 'm0-write-containment-probe/v1' -or
        $persistedReport.overall -cne $report.overall -or
        @($persistedReport.results).Count -ne $script:Results.Count) {
        throw 'Persisted report read-back failed schema or result-count verification.'
    }
    [pscustomobject]@{
        overall = $report.overall
        report_path = $reportPath
        result_count = $script:Results.Count
        output_channel = 'stdout_summary'
        report_persisted = $true
    } | ConvertTo-Json -Depth 3
    if ($report.overall -eq 'PASS') { exit 0 }
    if ($report.overall -eq 'FAIL') { exit 1 }
    exit 2
} catch {
    $failure = [pscustomobject]@{
        overall = 'INCONCLUSIVE'
        operation = 'precondition_or_report'
        status = 'INCONCLUSIVE'
        evidence = 'Precondition or report operation failed; do not interpret missing evidence as a pass.'
        output_channel = 'stdout_only'
        report_persisted = $false
        shared_paths_accessed = $true
        partial_results = @($script:Results)
        exception_type = $_.Exception.GetType().FullName
        hresult = '0x{0:X8}' -f [uint32]($_.Exception.HResult -band 0xffffffffL)
        message = ([string]$_.Exception.Message -replace '[\r\n]+', ' ').Trim()
    }
    $failure | ConvertTo-Json -Depth 4 | Write-Output
    exit 2
}
